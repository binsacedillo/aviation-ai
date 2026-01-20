# Semantic Guardrails Integration Guide

## Overview

Semantic Guardrails provide **automated verification** of agent responses before they reach users. This implements a "Feedback Loop with Self-Auditing" pattern - safety-critical for aviation applications.

## The 3-Knot Rule

**Principle**: If `|V_agent - V_math| > 3 kt`, trigger reflection and re-evaluation.

**Why 3 knots?**
- Accounts for rounding in agent responses (7.7 vs 7.66)
- Allows minor variations in wind gusts
- Catches significant calculation errors (15 kt vs 7.66 kt)
- Aviation safety: 3 kt is negligible, 7+ kt is dangerous

## Architecture

```
User Query
    ↓
Agent Generates Response
    ↓
[GUARDRAIL VERIFICATION] ← Automated Self-Audit
    ↓
┌─────────────┬─────────────┐
│ PASSED      │ FAILED      │
│ ≤ 3 kt      │ > 3 kt      │
└─────────────┴─────────────┘
    ↓              ↓
Send to User   REFLECTION NODE
                   ↓
               Re-read METAR
               Recalculate
               Generate New Response
                   ↓
               [GUARDRAIL VERIFICATION]
```

## Implementation

### Step 1: Import Guardrail

```python
from src.tools.guardrails import CrosswindGuardrail

# Initialize with 3-knot threshold
guardrail = CrosswindGuardrail(threshold_kt=3.0)
```

### Step 2: Add Verification Before Sending Response

```python
def send_response_to_user(agent_response, metar_data, runway_heading):
    """
    Send response with automated verification.
    """
    # Verify response accuracy
    result = guardrail.verify_with_details(
        agent_response=agent_response,
        metar_data=metar_data,
        runway_heading=runway_heading
    )
    
    if result["passed"]:
        # Safe to send
        return agent_response
    else:
        # Trigger reflection
        return reflection_node(
            metar_data=metar_data,
            runway_heading=runway_heading,
            error_details=result
        )
```

### Step 3: Implement Reflection Node

```python
def reflection_node(metar_data, runway_heading, error_details):
    """
    Re-evaluate when guardrail detects error.
    
    This forces the agent to:
    1. Re-read METAR wind data
    2. Re-read runway heading
    3. Recalculate crosswind mathematically
    4. Generate corrected response
    """
    from src.tools.tools import calculate_crosswind
    
    # Extract mathematical truth
    correct_crosswind = error_details["mathematical_truth"]
    
    # Generate corrected response
    corrected_response = f"""
    Based on current METAR at {metar_data['airport']}:
    Wind: {metar_data['wind_direction']}° @ {metar_data['wind_speed']} kt
    Runway: {runway_heading}°
    
    Crosswind Component: {correct_crosswind:.1f} kt
    
    This is {'within' if correct_crosswind <= 10 else 'above'} safe limits 
    for most general aviation aircraft.
    """
    
    # Verify corrected response (should always pass)
    verification = guardrail.verify(
        corrected_response,
        metar_data,
        runway_heading
    )
    
    if verification["passed"]:
        return corrected_response
    else:
        # Fallback to mathematical-only response
        return f"Crosswind: {correct_crosswind:.1f} kt"
```

## LangGraph Integration

### Option 1: Add as Node in Graph

```python
from langgraph.graph import StateGraph

def create_agent_with_guardrails():
    workflow = StateGraph(AgentState)
    
    # Existing nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    # Add guardrail verification node
    workflow.add_node("verify_response", verify_response_node)
    workflow.add_node("reflection", reflection_node)
    
    # Flow
    workflow.add_edge("agent", "verify_response")
    
    # Conditional: pass or reflect
    workflow.add_conditional_edges(
        "verify_response",
        should_reflect,
        {
            "send": END,      # Verification passed
            "reflect": "reflection"  # Verification failed
        }
    )
    
    workflow.add_edge("reflection", "verify_response")
    
    return workflow.compile()

def verify_response_node(state):
    """Guardrail verification node."""
    result = guardrail.verify_with_details(
        agent_response=state["messages"][-1].content,
        metar_data=state["metar_data"],
        runway_heading=state["runway_heading"]
    )
    
    state["verification_result"] = result
    return state

def should_reflect(state):
    """Routing function."""
    if state["verification_result"]["passed"]:
        return "send"
    else:
        return "reflect"
```

### Option 2: Inline Verification

```python
def agent_response_with_guardrails(user_query, metar_data, runway_heading):
    """
    Generate response with inline verification.
    """
    max_attempts = 2
    
    for attempt in range(max_attempts):
        # Generate response
        response = agent.invoke(user_query)
        
        # Verify
        result = guardrail.verify_with_details(
            response,
            metar_data,
            runway_heading
        )
        
        if result["passed"]:
            return response
        else:
            # Log reflection
            print(f"Attempt {attempt + 1}: Failed verification")
            print(f"  Discrepancy: {result['discrepancy']:.2f} kt")
            
            # Add reflection context for next attempt
            user_query = f"""
            Previous response had error. Let me recalculate:
            
            METAR: Wind {metar_data['wind_direction']}° @ {metar_data['wind_speed']} kt
            Runway: {runway_heading}°
            
            Mathematical crosswind: {result['mathematical_truth']:.2f} kt
            
            {user_query}
            """
    
    # Max attempts reached - use mathematical fallback
    return f"Crosswind: {result['mathematical_truth']:.1f} kt (calculated)"
```

## Testing Guardrails

### Unit Tests

```python
# tests/test_guardrails.py
import pytest
from src.tools.guardrails import CrosswindGuardrail

def test_correct_claim_passes():
    guardrail = CrosswindGuardrail(threshold_kt=3.0)
    
    result = guardrail.verify(
        agent_response="Crosswind is 7.7 kt",
        metar_data={"wind_direction": 220, "wind_speed": 10},
        runway_heading=170
    )
    
    assert result["passed"] == True
    assert result["discrepancy"] < 0.1

def test_incorrect_claim_fails():
    guardrail = CrosswindGuardrail(threshold_kt=3.0)
    
    result = guardrail.verify(
        agent_response="Crosswind is 15 kt",
        metar_data={"wind_direction": 220, "wind_speed": 10},
        runway_heading=170
    )
    
    assert result["passed"] == False
    assert result["discrepancy"] > 3.0
    assert "TRIGGER REFLECTION" in result["recommendation"]
```

### Integration Tests

```python
def test_guardrails_prevent_bad_data():
    """
    Verify guardrails catch errors before reaching user.
    """
    # Simulate agent making calculation error
    bad_response = "The crosswind is 20 kt - DO NOT FLY!"
    
    metar = {"wind_direction": 220, "wind_speed": 10}
    runway = 170
    
    # Guardrail should catch this
    result = guardrail.verify_with_details(bad_response, metar, runway)
    
    assert result["passed"] == False
    assert result["agent_claim"] == 20.0
    assert result["mathematical_truth"] < 10.0
    assert result["discrepancy"] > 10.0
    
    # Response should NOT be sent to user
    # Instead, trigger reflection
    corrected = reflection_node(metar, runway, result)
    
    # Verify corrected response
    corrected_result = guardrail.verify(corrected, metar, runway)
    assert corrected_result["passed"] == True
```

## Monitoring and Logging

### Track Verification Failures

```python
import logging

logger = logging.getLogger("guardrails")

def verify_with_logging(agent_response, metar_data, runway_heading):
    result = guardrail.verify_with_details(
        agent_response,
        metar_data,
        runway_heading
    )
    
    if not result["passed"]:
        logger.warning(
            f"Guardrail failure: "
            f"Agent claimed {result['agent_claim']} kt, "
            f"math shows {result['mathematical_truth']} kt, "
            f"discrepancy {result['discrepancy']:.2f} kt"
        )
    
    return result
```

### Metrics to Track

1. **Verification Pass Rate**: % of responses passing guardrail
2. **Average Discrepancy**: Mean |V_agent - V_math| for all responses
3. **Reflection Frequency**: How often reflection node is triggered
4. **Reflection Success Rate**: % of reflections that fix the error

```python
class GuardrailMetrics:
    def __init__(self):
        self.total_checks = 0
        self.passed_checks = 0
        self.total_discrepancy = 0.0
        self.reflections_triggered = 0
        
    def record(self, result):
        self.total_checks += 1
        if result["passed"]:
            self.passed_checks += 1
        else:
            self.reflections_triggered += 1
        
        if result["discrepancy"] is not None:
            self.total_discrepancy += result["discrepancy"]
    
    def report(self):
        pass_rate = (self.passed_checks / self.total_checks) * 100
        avg_discrepancy = self.total_discrepancy / self.total_checks
        
        return {
            "pass_rate": f"{pass_rate:.1f}%",
            "avg_discrepancy": f"{avg_discrepancy:.2f} kt",
            "reflections": self.reflections_triggered
        }
```

## Best Practices

### 1. Always Verify Before Sending

```python
# ❌ BAD: Send without verification
def bad_approach(agent_response):
    return agent_response  # No verification!

# ✅ GOOD: Verify first
def good_approach(agent_response, metar_data, runway_heading):
    result = guardrail.verify(agent_response, metar_data, runway_heading)
    if result["passed"]:
        return agent_response
    else:
        return reflection_node(metar_data, runway_heading, result)
```

### 2. Log All Verification Failures

Every failed verification indicates a potential safety issue. Log it for analysis.

### 3. Test Edge Cases

- No crosswind claim in response
- Multiple crosswind claims
- Gust wind vs steady wind
- Variable wind direction
- Calm wind (0 kt)

### 4. Tune Threshold Based on Data

Monitor your `avg_discrepancy` metric:
- If too many false positives (< 1 kt discrepancies failing), increase threshold
- If missing real errors (> 5 kt discrepancies passing), decrease threshold
- 3 kt is a good starting point for aviation

### 5. Implement Max Reflection Attempts

```python
MAX_REFLECTION_ATTEMPTS = 2

def safe_agent_response(query, metar, runway):
    for attempt in range(MAX_REFLECTION_ATTEMPTS):
        response = generate_response(query)
        result = guardrail.verify(response, metar, runway)
        
        if result["passed"]:
            return response
        
        # Reflection
        query = add_reflection_context(query, result)
    
    # Fallback: return mathematical calculation only
    return f"Crosswind: {calculate_crosswind(metar, runway):.1f} kt"
```

## Production Deployment

### Environment Configuration

```python
# config/guardrails.py

class GuardrailConfig:
    # Threshold in knots
    THRESHOLD_KT = 3.0
    
    # Enable/disable guardrails
    ENABLED = True  # Set False only for testing
    
    # Max reflection attempts
    MAX_REFLECTIONS = 2
    
    # Logging level
    LOG_LEVEL = "WARNING"  # Log all failures
```

### Feature Flag

```python
def agent_response_with_optional_guardrails(
    agent_response, 
    metar_data, 
    runway_heading,
    use_guardrails=True
):
    if not use_guardrails:
        return agent_response
    
    result = guardrail.verify(agent_response, metar_data, runway_heading)
    
    if result["passed"]:
        return agent_response
    else:
        return reflection_node(metar_data, runway_heading, result)
```

## Summary

**Semantic Guardrails = Automated Quality Control**

Before any response reaches the user:
1. Extract agent's crosswind claim
2. Calculate mathematical truth from METAR
3. Compare: `|V_agent - V_math|`
4. If > 3 kt: **TRIGGER REFLECTION**
5. If ≤ 3 kt: **ALLOW TO SEND**

This is the difference between demo code and production-ready safety-critical software. 🛡️

**The system audits itself before sending potentially dangerous information to pilots.**

## Next Steps

1. ✅ Implement CrosswindGuardrail class
2. ✅ Create comprehensive tests
3. ⏳ Integrate with LangGraph agent
4. ⏳ Add monitoring and metrics
5. ⏳ Deploy to production with feature flag

---

**Questions?** See `test_guardrails.py` for working examples.

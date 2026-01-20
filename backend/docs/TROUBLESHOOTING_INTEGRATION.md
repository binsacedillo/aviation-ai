# 🔍 Troubleshooting Guide - When Math Doesn't Match

## The Warning: "If they differ significantly: ⚠️ Check integration"

When you manually calculate crosswind and it doesn't match the agent's claim, it means there's a problem somewhere in the data pipeline. Here's how to diagnose it.

## What "Check Integration" Means

The integration has **multiple steps** where errors can occur:

```
User Query
    ↓
Agent Understanding ← Could misinterpret query
    ↓
Tool Call (fetch_metar) ← Could call wrong airport
    ↓
AVWX API ← Could return stale/wrong data
    ↓
Data Parsing ← Could extract wrong values
    ↓
Math Calculation ← Could use wrong formula
    ↓
Agent Response ← Could round incorrectly
```

If the final answer doesn't match your hand calculation, **one of these steps is broken**.

## Example Scenarios

### Scenario 1: Agent Uses Stale Data ⚠️

**Your calculation:**
```
Current METAR: Wind 220° @ 10kt
Crosswind: 10 × sin(50°) = 7.66 kt
```

**Agent claims:**
```
"The crosswind at KDEN is 12 knots"
```

**What's wrong?**
- Agent fetched old METAR (wind was 220° @ 15kt an hour ago)
- Agent's math is correct: 15 × sin(50°) = 11.49 ≈ 12kt
- **Problem:** Data caching or not calling AVWX API

**How to check:**
```python
from src.tools.tools import fetch_metar
print(fetch_metar("KDEN")["raw"])  # Check timestamp
```

---

### Scenario 2: Agent Uses Wrong Airport ⚠️

**Your calculation:**
```
KDEN Runway 17L: Wind 220° @ 10kt → 7.66 kt
```

**Agent claims:**
```
"The crosswind at Denver is 3 knots"
```

**What's wrong?**
- Agent fetched KBDU (Boulder) instead of KDEN
- KBDU has different wind: 260° @ 5kt → 0.87 kt ≈ 3kt
- **Problem:** Tool called with wrong ICAO parameter

**How to check:**
```bash
# Run trace audit
python test_trace_audit.py

# Look for tool call:
🔧 TOOL CALL: fetch_metar
   Arguments: {"icao_code": "KBDU"}  ← Wrong airport!
```

---

### Scenario 3: Agent Uses Wrong Runway ⚠️

**Your calculation:**
```
KDEN Runway 17L (170°): Wind 220° @ 10kt → 7.66 kt
```

**Agent claims:**
```
"The crosswind at KDEN is 10 knots"
```

**What's wrong?**
- Agent calculated for Runway 35R (350°) instead of 17L
- 220° - 350° = 130° → 10 × sin(130°) = 7.66 kt... wait, that's wrong
- Actually: 10 × sin(130°) ≈ 7.66, but if angle is 90°: 10 × sin(90°) = 10 kt
- **Problem:** Agent chose perpendicular runway or wrong calculation

**How to check:**
- Verify which runway the agent assumed
- Check if runway selection logic is correct

---

### Scenario 4: Math Formula Wrong ⚠️

**Your calculation:**
```
Wind 220° @ 10kt, Runway 170°
Crosswind: 10 × sin(50°) = 7.66 kt
```

**Agent claims:**
```
"The crosswind at KDEN is 6.4 knots"
```

**What's wrong?**
- Agent used wrong formula: 10 × cos(50°) = 6.43 kt
- **Problem:** Used cosine instead of sine (headwind formula instead of crosswind)

**How to check:**
```python
# Look at the crosswind calculation code
import math

# Correct:
crosswind = wind_speed * math.sin(math.radians(angle))

# Wrong:
crosswind = wind_speed * math.cos(math.radians(angle))  # This is headwind!
```

---

### Scenario 5: Rounding Differences ✅ (Acceptable)

**Your calculation:**
```
Crosswind: 10 × sin(50°) = 7.660444431
```

**Agent claims:**
```
"The crosswind at KDEN is 8 knots"
```

**What's wrong?**
- Nothing! Agent rounded to nearest whole number
- 7.66 ≈ 8 is acceptable rounding
- **This is OK** - not a real discrepancy

**Rule of thumb:**
- Difference < 1 kt: ✅ Acceptable rounding
- Difference 1-3 kt: ⚠️ Check calculations
- Difference > 3 kt: ❌ Serious integration error

---

## Diagnostic Checklist

When math doesn't match, check in this order:

### 1. ✅ Verify You're Using Same Data
```python
# Get the exact METAR the agent would see
from src.tools.tools import fetch_metar
metar = fetch_metar("KDEN")
print(f"Wind: {metar['wind']}")
print(f"Time: {metar.get('time', 'unknown')}")
```

**Check:**
- Is timestamp recent? (Should be within 1 hour)
- Do wind values match what you used?

### 2. ✅ Verify Airport Code
```bash
# Look at agent trace
python test_trace_audit.py

# Confirm tool call:
🔧 TOOL CALL: fetch_metar
   Arguments: {"icao_code": "KDEN"}  ← Correct?
```

**Check:**
- Did agent call the right airport?
- Are you calculating for the same airport?

### 3. ✅ Verify Runway Selection
```python
# Check what runway the agent assumed
# In agent's response, look for runway mention
```

**Check:**
- Did agent specify a runway?
- Are you using the same runway heading?
- Is runway heading correct? (Runway 17 = 170°, not 17°)

### 4. ✅ Verify Angle Calculation
```python
wind_direction = 220
runway_heading = 170
angle = abs(wind_direction - runway_heading)

# Normalize to 0-180
if angle > 180:
    angle = 360 - angle

print(f"Angle: {angle}°")  # Should be 50°
```

**Check:**
- Is angle normalized correctly?
- Is angle in degrees, not radians?

### 5. ✅ Verify Formula
```python
import math

# CORRECT formulas:
crosswind = wind_speed * math.sin(math.radians(angle))
headwind = wind_speed * math.cos(math.radians(angle))

# WRONG formulas:
crosswind = wind_speed * math.cos(math.radians(angle))  # NO!
crosswind = wind_speed * math.sin(angle)  # NO! (degrees, not radians)
```

**Check:**
- Is sine used for crosswind? (not cosine)
- Is angle converted to radians?

### 6. ✅ Check for Gusts
```python
# METAR might show:
# "Wind 220° @ 10kt gusting 18kt"

# Agent might use gust speed instead of sustained wind
```

**Check:**
- Are you using sustained wind speed?
- Did agent use gust speed?

---

## Example: Full Debugging Session

**Agent claims:** "Crosswind at KDEN Runway 17L is 12 knots"

**Your calculation:**
```python
import math
from src.tools.tools import fetch_metar

# Step 1: Get real data
metar = fetch_metar("KDEN")
print(f"Wind: {metar['wind']}")  # Output: 220 @ 10

# Step 2: Extract values
wind_direction = 220
wind_speed = 10
runway_heading = 170

# Step 3: Calculate
angle = abs(220 - 170)  # = 50
crosswind = 10 * math.sin(math.radians(50))
print(f"Crosswind: {crosswind:.2f} kt")  # Output: 7.66 kt
```

**Result:** You got 7.66 kt, agent said 12 kt → **5.34 kt difference** ❌

**Diagnosis:**
```
Difference > 3 kt → Serious error
12 / 7.66 = 1.57 → Agent's value is ~57% higher

Possible causes:
1. Agent used old METAR (wind was stronger earlier)
2. Agent used wrong angle (maybe 220° - 160° = 60°?)
   Check: 10 × sin(60°) = 8.66 kt ✗ Still doesn't match
3. Agent used gust speed instead of sustained wind
   Check: If gusts were 15kt, 15 × sin(50°) = 11.49 ≈ 12 kt ✅ This matches!

CONCLUSION: Agent is using gust speed, not sustained wind speed.
FIX: Update code to use metar['wind_speed'] not metar['wind_gust']
```

---

## When to Worry vs When to Accept

### ✅ Acceptable Differences (Normal)

| Your Calc | Agent Says | Difference | Reason |
|-----------|------------|------------|--------|
| 7.66 kt | 8 kt | 0.34 kt | Rounding to integer |
| 7.66 kt | 7.7 kt | 0.04 kt | Rounding to 1 decimal |
| 7.66 kt | 7 kt | 0.66 kt | Conservative rounding |

### ⚠️ Concerning Differences (Investigate)

| Your Calc | Agent Says | Difference | Likely Issue |
|-----------|------------|------------|--------------|
| 7.66 kt | 10 kt | 2.34 kt | Wrong angle or wind speed |
| 7.66 kt | 5 kt | 2.66 kt | Wrong formula or runway |
| 7.66 kt | 15 kt | 7.34 kt | Using total wind, not component |

### ❌ Serious Errors (Integration Broken)

| Your Calc | Agent Says | Difference | Likely Issue |
|-----------|------------|------------|--------------|
| 7.66 kt | 3 kt | 4.66 kt | Wrong airport entirely |
| 7.66 kt | 20 kt | 12.34 kt | Using wrong METAR data |
| 7.66 kt | 0 kt | 7.66 kt | Not fetching weather at all |

---

## Quick Reference: Common Errors

### Error 1: Degrees vs Radians
```python
# WRONG:
crosswind = 10 * math.sin(50)  # Python expects radians!

# CORRECT:
crosswind = 10 * math.sin(math.radians(50))
```

### Error 2: Sine vs Cosine
```python
# WRONG:
crosswind = 10 * math.cos(math.radians(50))  # This is headwind!

# CORRECT:
crosswind = 10 * math.sin(math.radians(50))
```

### Error 3: Angle > 180°
```python
# WRONG:
angle = abs(300 - 100)  # = 200° (should be 160°)

# CORRECT:
angle = abs(300 - 100)
if angle > 180:
    angle = 360 - angle  # = 160°
```

### Error 4: Runway Heading
```python
# WRONG:
runway_heading = 17  # Runway 17 is NOT 17°!

# CORRECT:
runway_heading = 170  # Runway 17 means 170°
```

---

## Bottom Line

**"Check integration" means:**

1. **Verify inputs** - Same METAR? Same runway? Same time?
2. **Verify calculations** - Correct formula? Radians? Angle normalized?
3. **Verify rounding** - Is difference just rounding, or real error?

**If difference > 1 kt after checking all these:** Your integration has a bug.

**If difference < 1 kt:** Integration is working correctly, just rounding differences.

---

## Test Your Understanding

**Practice Problem:**

Agent claims: "The crosswind at KBDU Runway 26 is 5 knots"

Your turn to verify:
```python
# 1. Get real METAR
metar = fetch_metar("KBDU")  # Wind: 250 @ 16

# 2. Set runway
runway_heading = 260  # Runway 26 = 260°

# 3. Calculate
angle = abs(250 - 260)  # = 10°
crosswind = 16 * math.sin(math.radians(10))
# = 16 × 0.1736
# = 2.78 kt

# 4. Compare
Agent: 5 kt
You: 2.78 kt
Difference: 2.22 kt ⚠️
```

**Diagnosis:** Agent's value is too high. Possible causes:
- Used wrong angle (maybe 250° - 240° = 10°?)
- Used wrong wind speed (maybe 30kt from different time?)
- Used wrong formula

**Action:** Run trace audit and check which values agent actually used.

---

**Remember:** Math is your friend. If the numbers don't match, something is broken. The beauty of this test is that it's **independently verifiable** - you don't have to trust the system, you can prove it's correct (or find where it's wrong). 🔍

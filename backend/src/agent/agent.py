"""
LangGraph Agent - The reasoning loop.
This is the "brain" that decides what to do step-by-step.
"""

from typing import Any, TypedDict
import json
import re
from ..tools.tools import TOOLS, execute_tool
from ..tools.guardrails import CrosswindGuardrail
from config import settings


# ============================================
# WIND NORMALIZATION (for guardrail injection)
# ============================================

def normalize_wind_field(wind_field: Any) -> dict[str, Any] | None:
    """
    Accept either:
      - {'dir': int, 'speed_kt': int, 'gust_kt': int} (structured)
      - "270° @ 18kt" or "VRB 03KT" (string)
    
    Returns normalized dict or None.
    """
    if not wind_field:
        return None
    
    if isinstance(wind_field, dict):
        # Already structured; ensure numeric types
        try:
            return {
                "dir": int(wind_field.get("dir")) if wind_field.get("dir") is not None else None,
                "speed_kt": float(wind_field.get("speed_kt", 0)),
                "gust_kt": float(wind_field.get("gust_kt")) if wind_field.get("gust_kt") is not None else None,
            }
        except (ValueError, TypeError):
            return wind_field  # Return as-is, let caller handle
    
    # Parse string like "270° @ 18kt", "270 18KT", "VRB 03KT"
    s = str(wind_field).replace("\u00b0", " ").replace("°", " ").strip()
    
    # VRB case
    if s.upper().startswith("VRB"):
        m_speed = re.search(r"(\d{1,2})(?:\.\d+)?\s*kt", s, re.IGNORECASE)
        speed = float(m_speed.group(1)) if m_speed else 0.0
        return {"dir": None, "speed_kt": speed, "gust_kt": None}
    
    # numeric direction like "270 @ 18kt" or "27018KT"
    m = re.search(r"(\d{1,3})\D+(\d{1,2})(?:\.\d+)?\s*kt", s, re.IGNORECASE)
    if m:
        dir_val = int(m.group(1))
        speed_val = float(m.group(2))
        m_gust = re.search(r"gust(?:ed)?\s*(\d{1,2})\s*kt", s, re.IGNORECASE)
        gust = float(m_gust.group(1)) if m_gust else None
        return {"dir": dir_val, "speed_kt": speed_val, "gust_kt": gust}
    
    # fallback: extract any speed
    m_any = re.search(r"(\d{1,2})\s*kt", s, re.IGNORECASE)
    if m_any:
        return {"dir": None, "speed_kt": float(m_any.group(1)), "gust_kt": None}
    
    return None


# ============================================
# AGENT STATE (What the agent remembers)
# ============================================

class AgentState(TypedDict):
    """State that persists through the agent loop"""
    messages: list[dict]  # Chat history
    current_plan: str  # What the agent is trying to do
    tool_calls: list[dict]  # Tools it's called
    final_response: str  # The answer


# ============================================
# AGENT LOGIC
# ============================================

class FlightAssistantAgent:
    """
    Simple agentic AI that loops:
    Think → Call Tools → Observe → Decide → Respond → Verify with Guardrails
    """
    
    def __init__(self):
        self.loop_count = 0
        self.max_loops = settings.MAX_AGENT_LOOPS  # Prevent infinite loops
        self.use_real_llm = settings.has_openai_key or settings.has_anthropic_key or settings.has_groq_key or settings.has_ollama
        self.guardrail = CrosswindGuardrail(threshold_kt=3.0)
        self.metar_data = None  # Store METAR from last fetch
        self.runway_heading = None  # Store runway heading from last selection

    def _requires_tools(self, user_query: str) -> bool:
        """Decide if this query needs the tool-calling loop (weather/runway math)."""
        keywords = [
            "crosswind",
            "wind",
            "metar",
            "taf",
            "runway",
            "landing",
            "gust",
            "headwind",
            "tailwind",
            "weather",
        ]
        uq = user_query.lower()
        return any(k in uq for k in keywords)
    
    def create_agent_prompt(self, user_query: str, tool_results: list[dict] = None) -> str:
        """Build the prompt that tells the LLM what to do"""
        
        # List available tools
        tool_descriptions = "\n".join([
            f"- {name}: {TOOLS[name]['description']}"
            for name in TOOLS.keys()
        ])
        
        prompt = f"""You are a Flight Assistant AI with access to tools.

USER QUERY: {user_query}

AVAILABLE TOOLS:
{tool_descriptions}

INSTRUCTIONS:
1. Analyze the user's query
2. Plan what tools you need to call
3. Call tools in order
4. Analyze results
5. Give a final answer

VERIFICATION REQUIREMENT:
Your response will be automatically verified against mathematical calculations.
Ensure your wind component calculations are accurate (within 3 knots of true math).
If your answer disagrees with the math by >3 kt, the system will ask you to recalculate.

Current step: Decide what to do next.
"""
        
        if tool_results:
            prompt += "\n\nTOOL RESULTS FROM PREVIOUS STEPS:\n"
            for result in tool_results:
                prompt += f"- Called {result['tool']}: {json.dumps(result['result'])}\n"
        
        return prompt
    
    def verify_response(self, response: str) -> dict[str, Any]:
        """
        Verify agent's response using semantic guardrails.
        
        Checks:
        1. Crosswind calculations (3-knot rule)
        2. Magnetic correction applied
        3. Gust vs sustained wind handling
        
        Returns dict with:
        - passed: bool (True if verification passed)
        - details: detailed verification results from guardrail
        - reflection_prompt: If failed, prompt for agent reflection
        """
        # Only verify if we have METAR data and runway heading from tool calls
        if not self.metar_data or not self.runway_heading:
            return {
                "passed": True,
                "details": {"issue": "No METAR/runway data available for verification"},
                "reflection_prompt": None,
            }
        
        # Run guardrail verification
        result = self.guardrail.verify_with_details(
            agent_response=response,
            metar_data=self.metar_data,
            runway_heading=self.runway_heading,
            use_gust=False,  # Use sustained wind by default
        )
        
        if result["passed"]:
            print(f"✅ GUARDRAIL PASSED: {result.get('explanation', 'Verification successful')}", flush=True)
            return {
                "passed": True,
                "details": result,
                "reflection_prompt": None,
            }
        else:
            # Create reflection prompt for agent
            reflection_prompt = f"""
⚠️ VERIFICATION FAILED - Please recalculate

Issue: {result["issue"]}

Calculation Details:
{json.dumps(result.get("calculation_details", {}), indent=2)}

Please re-read the wind data and runway heading, then recalculate the crosswind component.
The mathematical truth is {result["mathematical_truth"]} kt, but your response claimed {result["agent_claim"]} kt.

Your recalculated response:
"""
            
            print(f"⚠️ GUARDRAIL TRIGGERED REFLECTION", flush=True)
            print(f"   Issue: {result['issue']}", flush=True)
            print(f"   Reflection will be requested...", flush=True)
            
            return {
                "passed": False,
                "details": result,
                "reflection_prompt": reflection_prompt,
            }
    
    def reflect_and_correct(self, verification_result: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """
        When guardrail fails, ask agent to reflect and recalculate.
        
        This simulates an agent reflection loop where the agent
        re-examines its previous calculation and provides a corrected answer.
        
        Returns:
            tuple: (corrected_response, re_verification_result)
        """
        details = verification_result["details"]
        print(f"\n🔄 AGENT REFLECTION TRIGGERED", flush=True)
        print(f"-" * 60, flush=True)
        
        # Generate corrected response with accurate calculation
        corrected_response = (
            f"I apologize for the calculation error. Let me recalculate:\n\n"
            f"Wind: {details['wind_data'].get('speed_used')} knots at "
            f"{details['wind_data'].get('direction_magnetic')}°\n"
            f"Runway heading: {self.runway_heading}°\n"
            f"Angle between wind and runway: {details['calculation_details'].get('angle')}°\n"
            f"\n"
            f"Crosswind = {details['wind_data'].get('speed_used')} × sin({details['calculation_details'].get('angle')}°) = "
            f"{details['mathematical_truth']:.2f} knots\n\n"
            f"The correct crosswind component is {details['mathematical_truth']:.2f} knots."
        )
        
        print(f"✅ CORRECTED RESPONSE: {corrected_response}", flush=True)
        
        # Re-verify the corrected response
        re_verification = self.verify_response(corrected_response)
        
        return corrected_response, re_verification
    
    def _safe_fail_response(self, original_failure: dict[str, Any], reflection_failure: dict[str, Any]) -> str:
        """
        Generate a safe fallback response when guardrails fail even after reflection.
        
        This is the last line of defense - returns conservative guidance and logs audit trail.
        
        Args:
            original_failure: Initial verification failure details
            reflection_failure: Verification failure after reflection
        
        Returns:
            Conservative fallback response with clear labeling
        """
        from ..tools.tracing import TraceLogger
        import time
        
        print(f"\n⚠️ SAFE-FAIL TRIGGERED: Guardrails failed after reflection", flush=True)
        print(f"-" * 60, flush=True)
        
        # Log audit trail
        audit_logger = TraceLogger(category="safe_fail")
        audit_logger.set_context(
            timestamp=time.time(),
            airport=self.metar_data.get("station") if self.metar_data else None,
            runway_heading=self.runway_heading,
            original_claim=original_failure["details"].get("agent_claim"),
            original_discrepancy=original_failure["details"].get("discrepancy"),
            reflection_claim=reflection_failure["details"].get("agent_claim"),
            reflection_discrepancy=reflection_failure["details"].get("discrepancy"),
        )
        audit_logger.log_input(
            raw_metar=self.metar_data.get("raw") if self.metar_data else "N/A",
            wind_str=self.metar_data.get("wind") if self.metar_data else "N/A",
        )
        # Use log_operation for the safe-fail event
        audit_logger.log_operation(
            function="safe_fail_triggered",
            angle_deg=None,
            expression="Guardrails failed after reflection",
        )
        # Emit trace to file
        audit_logger.emit()
        
        # Generate conservative fallback
        wind_data = self.metar_data.get("wind", "N/A") if self.metar_data else "N/A"
        math_truth = original_failure["details"].get("mathematical_truth", "N/A")
        
        fallback_response = (
            f"⚠️ VERIFICATION FAILURE - CONSERVATIVE GUIDANCE PROVIDED\n\n"
            f"I was unable to provide a verified crosswind calculation. "
            f"For safety, please use the following information:\n\n"
            f"Current Wind: {wind_data}\n"
            f"Calculated Crosswind Component: {math_truth:.2f} kt (mathematically verified)\n\n"
            f"RECOMMENDATION: Verify wind conditions independently before flight. "
            f"Consult METAR/TAF directly and perform your own crosswind calculations.\n\n"
            f"[AUDIT: Response generated via safe-fail path due to verification failure. "
            f"Trace ID logged to logs/trace.jsonl]\n"
        )
        
        print(f"🔴 SAFE-FAIL RESPONSE: {fallback_response}", flush=True)
        
        return fallback_response
    
    def _format_professional_response(self, metar: dict[str, Any], include_crosswind: bool = False) -> str:
        """
        Format METAR data into a professional, formal aviation response.
        Ignores casual phrasing in query; always responds with proper terminology.
        """
        station = metar.get("station", "UNKNOWN")
        raw = metar.get("raw", "N/A")
        temp = metar.get("temp_c")
        dewpoint = metar.get("dewpoint_c")
        wind = metar.get("wind", {})
        flight_cat = metar.get("flight_category", "UNKNOWN")
        
        wind_dir = wind.get("dir") if isinstance(wind, dict) else None
        wind_speed = wind.get("speed_kt") if isinstance(wind, dict) else None
        wind_gust = wind.get("gust_kt") if isinstance(wind, dict) else None
        
        # Build professional response with double newlines for proper spacing
        parts = [
            f"📍 **Station:** {station}",
            f"⏰ **Report:** {metar.get('time', 'Current')}",
            "",
            f"**METAR:** {raw}",
            "",
        ]
        
        # Wind section
        if wind_dir is not None and wind_speed is not None:
            wind_desc = f"💨 **Wind:** {wind_dir:03d}° at {wind_speed:.0f} knots"
            if wind_gust and wind_gust > wind_speed:
                wind_desc += f", gusting {wind_gust:.0f} knots"
            parts.append(wind_desc)
            parts.append("")
        
        # Crosswind calculation if requested
        if include_crosswind and wind_dir is not None and wind_speed is not None:
            import math
            # Determine best runway based on wind (round to nearest 10°, divide by 10)
            runway_heading = round(wind_dir / 10) * 10
            runway_number = runway_heading // 10
            if runway_number == 0:
                runway_number = 36
            
            # Calculate angle between wind and runway
            angle_diff = abs(wind_dir - runway_heading)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            
            # Crosswind = wind_speed × sin(angle)
            crosswind = wind_speed * abs(math.sin(math.radians(angle_diff)))
            headwind = wind_speed * abs(math.cos(math.radians(angle_diff)))
            
            parts.append(f"🛫 **Landing Analysis:**")
            parts.append(f"• Runway in use: **{runway_number:02d}** ({runway_heading}°)")
            parts.append(f"• Crosswind: **{crosswind:.1f} knots**")
            parts.append(f"• Headwind: {headwind:.1f} knots")
            parts.append("")
        
        # Temperature section
        if temp is not None:
            temp_str = f"🌡️ **Temperature:** {temp}°C"
            if dewpoint is not None:
                temp_str += f" | Dewpoint: {dewpoint}°C"
            parts.append(temp_str)
            parts.append("")
        
        # Flight category
        cat_emoji = {
            "VFR": "✅ **VFR** (Visual Flight Rules)",
            "MVFR": "⚠️ **MVFR** (Marginal VFR)",
            "IFR": "🔴 **IFR** (Instrument Flight Rules)",
            "LIFR": "🚫 **LIFR** (Low IFR)",
        }
        parts.append(f"✈️ **Conditions:** {cat_emoji.get(flight_cat, flight_cat)}")
        
        return "\n\n".join(parts)
    
    def _track_metar_and_runway(self, tool_results: list[dict]):
        """
        Extract METAR and runway data from tool results for guardrail verification.
        """
        for result in tool_results:
            tool_name = result.get("tool", "")
            tool_result = result.get("result", {})
            
            # Track METAR from fetch_metar tool
            if tool_name == "fetch_metar" and isinstance(tool_result, dict):
                self.metar_data = tool_result
                print(f"   📊 Tracked METAR: {tool_result.get('station')} at {tool_result.get('time')}", flush=True)
            
            # Track runway from select_best_runway tool
            elif tool_name == "select_best_runway" and isinstance(tool_result, dict):
                runway_str = tool_result.get("selected_runway", "")
                if runway_str:
                    try:
                        # Extract numeric heading from runway string (e.g., "26" from "26L")
                        runway_num = int(runway_str.rstrip("LRC"))
                        self.runway_heading = runway_num * 10  # Convert to heading (26 → 260°)
                        print(f"   🛫 Tracked runway: {runway_str} ({self.runway_heading}°)", flush=True)
                    except (ValueError, AttributeError):
                        pass
    
    def run(self, user_query: str) -> dict[str, Any]:
        """
        Execute the agent loop
        """
        print(f"\n🤖 AGENT STARTING: '{user_query}'", flush=True)
        print("-" * 60, flush=True)
        
        state = AgentState(
            messages=[{"role": "user", "content": user_query}],
            current_plan="",
            tool_calls=[],
            final_response="",
        )
        
        tool_results = []
        self.loop_count = 0
        verification_result = None
        
        # If a real LLM is available (Ollama/OpenAI/Claude), try once when tools aren't required.
        if self.use_real_llm and not self._requires_tools(user_query):
            provider = (
                "Ollama" if settings.has_ollama else (
                    "OpenAI" if settings.has_openai_key else (
                        "Claude" if settings.has_anthropic_key else "LLM"
                    )
                )
            )
            print(f"💡 Using {provider} for a direct response...", flush=True)
            llm_text = self._llm_response(user_query)
            
            # Check if response is valid (not an error message)
            if llm_text and not any(err in llm_text for err in ["failed", "timed out", "status", "not configured"]):
                state["final_response"] = llm_text
                self.loop_count = 1
                return {
                    "query": user_query,
                    "final_response": state["final_response"],
                    "tool_calls": state["tool_calls"],
                    "loops": self.loop_count,
                    "guardrail_verification": None,
                }
            else:
                print(f"⚠️ LLM response failed or unavailable; falling back to simulated response.", flush=True)
                # Fallback for general queries when LLM unavailable
                state["final_response"] = self._fallback_general_response(user_query)
                self.loop_count = 1
                return {
                    "query": user_query,
                    "final_response": state["final_response"],
                    "tool_calls": state["tool_calls"],
                    "loops": self.loop_count,
                    "guardrail_verification": None,
                }

        # ============================================
        # THE LOOP: Think, Act, Observe, Decide
        # ============================================
        while self.loop_count < self.max_loops:
            self.loop_count += 1
            print(f"\n📍 Loop {self.loop_count}/{self.max_loops}")
            
            # STEP 1: CREATE PROMPT
            prompt = self.create_agent_prompt(user_query, tool_results)
            
            # STEP 2: DECIDE WHAT TO DO (Simulated LLM)
            decision = self._simulate_llm_decision(user_query, tool_results)
            
            if decision["action"] == "respond":
                # ✅ Agent decided to respond
                state["final_response"] = decision["response"]
                print(f"✅ AGENT DECIDES: Respond\n{decision['response']}")
                
                # STEP 5: INJECT TOOL WIND IF MISSING
                # Extract wind from most recent METAR tool call
                metar_tool_wind = None
                for tr in reversed(tool_results):  # Latest first
                    if tr.get("tool") == "fetch_metar" and isinstance(tr.get("result"), dict):
                        metar_tool_wind = tr["result"].get("wind")
                        break
                
                # If METAR has wind and we haven't injected it yet, normalize and store
                if metar_tool_wind and not hasattr(self, "_injected_wind"):
                    normalized = normalize_wind_field(metar_tool_wind)
                    if normalized:
                        self._injected_wind = normalized
                        print(f"💉 Injected tool wind for guardrails: {normalized}", flush=True)
                
                # STEP 5: VERIFY RESPONSE WITH GUARDRAILS
                print(f"\n🔍 GUARDRAIL CHECK...", flush=True)
                self._track_metar_and_runway(tool_results)
                verification_result = self.verify_response(state["final_response"])
                
                if not verification_result["passed"]:
                    # Reflection triggered - recalculate and provide corrected response
                    corrected_response, re_verification = self.reflect_and_correct(verification_result)
                    
                    if re_verification["passed"]:
                        # Reflection successful - use corrected response
                        state["final_response"] = corrected_response
                        verification_result = re_verification
                    else:
                        # SAFE-FAIL: Even reflection failed verification
                        state["final_response"] = self._safe_fail_response(
                            original_failure=verification_result,
                            reflection_failure=re_verification
                        )
                        # Mark as safe-fail in verification result
                        verification_result["safe_fail_triggered"] = True
                        verification_result["reflection_also_failed"] = True
                
                break
            
            elif decision["action"] == "call_tool":
                # 🔧 Agent wants to call a tool
                tool_name = decision["tool"]
                tool_args = decision["args"]
                
                print(f"🔧 Calling tool: {tool_name}")
                print(f"   Args: {tool_args}")
                
                # STEP 3: EXECUTE TOOL
                result = execute_tool(tool_name, **tool_args)
                print(f"   Result: {json.dumps(result, indent=2)}")
                
                # STEP 4: OBSERVE & STORE
                tool_results.append({
                    "tool": tool_name,
                    "result": result,
                })
                state["tool_calls"].append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result,
                })
        
        return {
            "query": user_query,
            "final_response": state["final_response"],
            "tool_calls": state["tool_calls"],
            "loops": self.loop_count,
            "guardrail_verification": verification_result,
        }

    def run_stream(self, user_query: str):
        """Generator that yields progress events while answering the query.
        Events are dictionaries suitable for NDJSON streaming.
        """
        yield {"type": "start", "query": user_query}

        # Real LLM path (single-shot) when tools aren't required
        if self.use_real_llm and not self._requires_tools(user_query):
            provider = (
                "Ollama" if settings.has_ollama else (
                    "OpenAI" if settings.has_openai_key else (
                        "Claude" if settings.has_anthropic_key else "LLM"
                    )
                )
            )
            yield {"type": "llm_start", "provider": provider, "model": settings.OLLAMA_MODEL if settings.has_ollama else None}
            llm_text = self._llm_response(user_query)
            yield {"type": "llm_result", "text": llm_text}
            yield {"type": "final", "final_response": llm_text, "loops": 1, "tool_calls": []}
            return

        # Simulated tool-calling loop
        tool_results: list[dict] = []
        self.loop_count = 0
        while self.loop_count < self.max_loops:
            self.loop_count += 1
            yield {"type": "loop", "loop": self.loop_count, "max_loops": self.max_loops}

            decision = self._simulate_llm_decision(user_query, tool_results)

            if decision["action"] == "respond":
                # Track METAR and runway before verification
                self._track_metar_and_runway(tool_results)
                verification_result = self.verify_response(decision["response"])
                
                response_text = decision["response"]
                if not verification_result["passed"]:
                    corrected_response, re_verification = self.reflect_and_correct(verification_result)
                    
                    if re_verification["passed"]:
                        # Reflection successful
                        response_text = corrected_response
                        verification_result = re_verification
                    else:
                        # SAFE-FAIL: Reflection also failed
                        response_text = self._safe_fail_response(
                            original_failure=verification_result,
                            reflection_failure=re_verification
                        )
                        verification_result["safe_fail_triggered"] = True
                        verification_result["reflection_also_failed"] = True
                        yield {
                            "type": "safe_fail",
                            "reason": "Guardrails failed after reflection",
                            "original_discrepancy": verification_result.get("details", {}).get("discrepancy"),
                            "reflection_discrepancy": re_verification.get("details", {}).get("discrepancy"),
                        }
                
                yield {
                    "type": "guardrail",
                    "verification_passed": verification_result["passed"],
                    "issue": verification_result.get("details", {}).get("issue"),
                    "safe_fail_triggered": verification_result.get("safe_fail_triggered", False),
                }
                yield {"type": "final", "final_response": response_text, "loops": self.loop_count, "tool_calls": tool_results}
                return

            elif decision["action"] == "call_tool":
                tool_name = decision["tool"]
                tool_args = decision["args"]
                yield {"type": "tool_call", "tool": tool_name, "args": tool_args}
                result = execute_tool(tool_name, **tool_args)
                tool_results.append({"tool": tool_name, "args": tool_args, "result": result})
                yield {"type": "tool_result", "tool": tool_name, "result": result}

    def _llm_response(self, user_query: str) -> str:
        """Generate a response using an available LLM (Groq → Ollama → fallback)."""
        prompt = self._create_llm_direct_prompt(user_query)

        # Try Groq first (fast, free, cloud-based)
        if settings.has_groq_key:
            try:
                from groq import Groq
                client = Groq(api_key=settings.GROQ_API_KEY)
                completion = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=500,
                )
                return completion.choices[0].message.content
            except ImportError:
                print("⚠️ Groq SDK not installed. Run: pip install groq", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ Groq API exception: {exc}. Falling back...", flush=True)
                # Continue to Ollama fallback

        # Try Ollama when enabled (use direct HTTP API to avoid streaming hangs)
        if settings.has_ollama:
            try:
                import httpx
                resp = httpx.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.2},
                    },
                    timeout=httpx.Timeout(10.0, connect=5.0),  # 10 sec timeout
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("response", "")
                return f"Ollama returned status {resp.status_code}: {resp.text}"
            except httpx.TimeoutException:
                return "Ollama request timed out. Please ensure Ollama service is running."
            except Exception as exc:  # noqa: BLE001
                return (
                    "Ollama request failed. Ensure Ollama service is running and reachable at OLLAMA_BASE_URL. "
                    f"Error: {exc}"
                )

        # Fallback if other LLM keys exist but not implemented
        return (
            "LLM integration is enabled but no provider is configured. "
            "Add GROQ_API_KEY or enable Ollama to use real LLM responses."
        )

    def _create_llm_direct_prompt(self, user_query: str) -> str:
        """A small, fast prompt for direct LLM answering (keeps latency low)."""
        return (
            "You are a helpful flight assistant. Answer the user's question clearly and concisely using "
            "general aviation knowledge and sound judgment. If weather reports, aircraft tail number, or "
            "airports are missing but needed, politely ask for them in one short sentence.\n\n"
            f"Question: {user_query}\n"
        )
    
    def _fallback_general_response(self, user_query: str) -> str:
        """Fallback response for general queries when LLM unavailable."""
        q_lower = user_query.lower().strip()
        
        # Greetings
        if any(word in q_lower for word in ["hello", "hi", "hey", "greetings"]):
            return "👋 Hello! I'm a flight assistant. I can help you with:\n\n" \
                   "✈️ **METAR & Weather Reports** - Ask for `metar KDEN` or `weather at Miami`\n" \
                   "🛫 **Runway & Crosswind Info** - Ask for `crosswind at KJFK` or `landing at KSFO`\n" \
                   "📋 **Flight Planning** - General aviation questions\n\n" \
                   "What can I help you with?"
        
        # Help
        if q_lower in ["help", "?"]:
            return "📚 **Flight Assistant Help**\n\n" \
                   "🔍 **Try asking:**\n" \
                   "- `metar KMCO` (get live weather for Orlando)\n" \
                   "- `what's the wind at KJFK` (get wind for JFK)\n" \
                   "- `crosswind for KSFO` (crosswind calculation)\n" \
                   "- `is RPLL good for landing` (flight conditions)\n\n" \
                   "I specialize in aviation weather and runway operations."
        
        # Default fallback
        return "I'm a specialized flight assistant focused on aviation weather and runway operations. " \
               "Please ask about METAR reports, weather conditions, or runways at specific airports. " \
               "Try: `metar KDEN` or `weather at Denver`"
    
    
    def _simulate_llm_decision(self, user_query: str, tool_results: list[dict]) -> dict[str, Any]:
        """
        Pattern-based decision logic for weather/runway queries.
        Extracts airport codes dynamically and routes to appropriate tools.
        """
        import re
        
        uq_lower = user_query.lower()
        
        # Extract ICAO codes from query (K followed by 3 letters, or any 4-letter code)
        icao_pattern = r'\b([Kk][A-Za-z]{3}|[A-Z]{4})\b'
        icao_matches = re.findall(icao_pattern, user_query)
        icao_codes = [code.upper() for code in icao_matches]
        
        # Common airport names to ICAO mapping
        airport_map = {
            "denver": "KDEN",
            "boulder": "KBDU",
            "jfk": "KJFK",
            "lax": "KLAX",
            "ord": "KORD",
            "atlanta": "KATL",
            "chicago": "KORD",
            "san francisco": "KSFO",
            "seattle": "KSEA",
            "miami": "KMIA",
        }
        
        # Find airports mentioned in query
        for name, icao in airport_map.items():
            if name in uq_lower and icao not in icao_codes:
                icao_codes.append(icao)
        
        # Weather/runway query path
        if self._requires_tools(user_query):
            metar_results = [t for t in tool_results if t.get("tool") == "fetch_metar"]
            
            # Step 1: Fetch METAR for first airport
            if not metar_results:
                target_icao = icao_codes[0] if icao_codes else "KDEN"
                return {
                    "action": "call_tool",
                    "tool": "fetch_metar",
                    "args": {"icao_code": target_icao},
                }
            
            # Step 2: Build professional response with METAR data (ignore casual phrasing)
            metar = metar_results[0].get("result", {})
            if isinstance(metar, dict) and metar.get("raw"):
                # Check if crosswind calculation is needed
                needs_crosswind = any(word in uq_lower for word in ["crosswind", "landing", "runway"])
                
                # Use professional formatter
                response = self._format_professional_response(metar, include_crosswind=needs_crosswind)
                return {
                    "action": "respond",
                    "response": response,
                }
            else:
                return {
                    "action": "respond",
                    "response": f"⚠️ Could not retrieve METAR data for {icao_codes[0] if icao_codes else 'the requested airport'}. Please verify the airport code.",
                }
        
        # Non-weather queries: provide general response
        return {
            "action": "respond",
            "response": "I can help with weather and runway information. Please specify an airport (e.g., 'crosswind at KDEN' or 'weather at Denver').",
        }

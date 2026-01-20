"""
Tracing Utility for Introspective Logging

Provides structured, JSON-based traces to make decision paths observable.

Tracked items:
- Input: Raw METAR string from AVWX
- Transformation: Parsed floats (e.g., 10.0 kt, 220.0°)
- Operation: Trig function used (e.g., sin(50°))
- Result: Final numbers handed to the agent/LLM
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional


class TraceLogger:
    """
    Collects step-by-step events and emits NDJSON traces.
    """

    def __init__(self, category: str = "crosswind"):
        self.category = category
        self.trace_id = f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
        self.events: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}

    def set_context(self, **kwargs) -> None:
        self.context.update(kwargs)

    def log_input(self, raw_metar: Optional[str], wind_str: Optional[str]) -> None:
        self.events.append({
            "type": "input",
            "raw_metar": raw_metar,
            "wind_str": wind_str,
            "ts": time.time(),
        })

    def log_transformation(self, wind_direction: Optional[float], wind_speed: Optional[float]) -> None:
        self.events.append({
            "type": "transformation",
            "wind_direction_deg": wind_direction,
            "wind_speed_kt": wind_speed,
            "ts": time.time(),
        })

    def log_operation(self, function: str, angle_deg: Optional[float], expression: Optional[str]) -> None:
        self.events.append({
            "type": "operation",
            "function": function,
            "angle_deg": angle_deg,
            "expression": expression,
            "ts": time.time(),
        })

    def log_result(self, crosswind_kt: Optional[float], headwind_kt: Optional[float]) -> None:
        self.events.append({
            "type": "result",
            "crosswind_kt": crosswind_kt,
            "headwind_kt": headwind_kt,
            "ts": time.time(),
        })

    def to_json(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "category": self.category,
            "context": self.context,
            "events": self.events,
        }

    def emit(self, path: str = "logs/trace.jsonl") -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(self.to_json()) + "\n")


if __name__ == "__main__":
    # Simple self-test
    tracer = TraceLogger()
    tracer.set_context(airport="KDEN", runway_heading=170)
    tracer.log_input(raw_metar="METAR KDEN 181953Z 22010KT ...", wind_str="220 @ 10")
    tracer.log_transformation(wind_direction=220.0, wind_speed=10.0)
    tracer.log_operation(function="sin", angle_deg=50.0, expression="10 × sin(50°)")
    tracer.log_result(crosswind_kt=7.66, headwind_kt=6.43)
    tracer.emit()
    print("Trace emitted to logs/trace.jsonl")

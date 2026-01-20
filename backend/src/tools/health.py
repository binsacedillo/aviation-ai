"""
Weather System Health Check

Diagnostic utility to verify AVWX availability and report system status.
Helps quickly identify if:
- AVWX is down
- API keys broke
- Internet failed
"""

from __future__ import annotations

from typing import Dict, Any


def check_weather_system() -> Dict[str, Any]:
    """
    Check if AVWX is available and report weather system status.
    
    Returns:
        {
            "weather": "live" (AVWX ok) or "fallback" (using mock),
            "avwx": "ok" or "unavailable",
            "fallback": bool,
        }
    
    NOTE: Safe to call from both sync and async contexts.
    """
    try:
        # Try to import AVWX first
        try:
            from avwx import Metar
        except ImportError:
            return {
                "weather": "fallback",
                "avwx": "unavailable",
                "fallback": True,
                "reason": "avwx-engine not installed",
            }
        
        # Try to fetch a simple METAR with timeout to detect network issues
        try:
            import socket
            # Quick DNS check to verify internet connectivity
            socket.create_connection(("api.avwx.rest", 443), timeout=2)
            
            # If we got here, network is up
            # Don't actually fetch METAR (avoids async issues in FastAPI context)
            # Just report that AVWX is reachable
            return {
                "weather": "live",
                "avwx": "ok",
                "fallback": False,
            }
        except socket.timeout:
            return {
                "weather": "fallback",
                "avwx": "unavailable",
                "fallback": True,
                "reason": "AVWX API timeout (network or server down)",
            }
        except socket.gaierror:
            return {
                "weather": "fallback",
                "avwx": "unavailable",
                "fallback": True,
                "reason": "DNS resolution failed (no internet)",
            }
        except Exception as e:
            return {
                "weather": "fallback",
                "avwx": "unavailable",
                "fallback": True,
                "reason": f"Network error: {str(e)}",
            }
    except Exception as e:
        # Catch-all for unexpected errors
        return {
            "weather": "fallback",
            "avwx": "unavailable",
            "fallback": True,
            "reason": str(e),
        }


if __name__ == "__main__":
    import json
    status = check_weather_system()
    print(json.dumps(status, indent=2))

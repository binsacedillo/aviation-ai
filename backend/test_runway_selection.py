#!/usr/bin/env python
"""
Test Runway Selection

Validates selection and outputs phrase like:
  "Runway 26 favored, 11 kt headwind, 3 kt crosswind"
"""

from src.tools.tools import fetch_metar
from src.tools.runway_selection import select_best_runway

# Example with Denver-like winds and two opposite runways
metar = fetch_metar("KDEN")

# Provide two reciprocal runways; designator parsing will infer headings
runways = ["26", "08"]

result = select_best_runway(
    metar_data=metar,
    runways=runways,
    max_crosswind_threshold=10.0,
    use_gust=False,
)

print("Phrase:", result.get("phrase"))
print("Best:", result.get("best"))
print("Candidates:")
for c in result.get("candidates", []):
    print(" ", c)

print("Used:", result.get("used"))

"""
Test real-time weather integration with AVWX Engine.
Demonstrates DATA-DRIVEN mode: using actual live METAR data.
"""

print("🌤️ Testing Real-Time Weather Integration\n")
print("=" * 70)

try:
    from src.tools.metar_real import fetch_metar_real
    import json
    
    # Test with real METAR from AVWX
    airports = ["KDEN", "KBDU", "KJFK"]
    
    for code in airports:
        print(f"\n📍 Fetching METAR for {code}...\n")
        result = fetch_metar_real(code)
        
        # Pretty print the result
        for key, value in result.items():
            if key != "raw":
                print(f"  {key:20s}: {value}")
        if "raw" in result:
            print(f"  {'raw':20s}: {result['raw'][:80]}...")
        
        print()
    
    print("=" * 70)
    print("✅ Real METAR integration working!")
    print("\nNow when the agent asks 'Can I fly from KDEN to KBDU?',")
    print("it will check ACTUAL current weather conditions, not mock data.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

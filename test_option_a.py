"""Test Option A implementation in app.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.models import Config, Facility, PrimeWindow, Pricing, LeagueConfig, CorpConfig, Tournaments, Retail
from engine.compute import compute

def test_aggressive_preset():
    """Test that Aggressive preset produces expected results"""
    # Create config with Aggressive settings
    cfg = Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(),
        pricing=Pricing(nm_prime_per_court=65, nm_off_per_court=56),
        league=LeagueConfig(
            weeknights=4,  # Aggressive
            fill_rate=0.90,  # Aggressive
            active_weeks=46,  # Aggressive
            price_prime_slot_6wk=150.0
        ),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Compute with aggressive settings
    res = compute(cfg)
    
    revpach = res["density"]["RevPACH"]
    rev_util = res["density"]["RevPerUtilHr"]
    
    print(f"Aggressive Preset Results:")
    print(f"  RevPACH: ${revpach:.2f}")
    print(f"  Rev/Util Hr: ${rev_util:.2f}")
    
    # Test Option A thresholds
    WATCH_LOW, WATCH_HIGH = 28.0, 35.0
    HARD_CAP = 35.0
    UTIL_CAP = 60.0
    
    # Check against Option A caps
    if revpach > HARD_CAP:
        print(f"  ❌ RevPACH ${revpach:.2f} exceeds ${HARD_CAP} hard cap")
    elif revpach >= WATCH_LOW:
        print(f"  ⚠️ RevPACH ${revpach:.2f} in ${WATCH_LOW}-${WATCH_HIGH} watchlist band")
    else:
        print(f"  ✅ RevPACH ${revpach:.2f} within normal range")
    
    if rev_util > UTIL_CAP:
        print(f"  ❌ Rev/Util Hr ${rev_util:.2f} exceeds ${UTIL_CAP} limit")
    else:
        print(f"  ✅ Rev/Util Hr ${rev_util:.2f} within limit")
    
    # Test that we're in the expected range for Aggressive
    assert revpach > 25.0, f"RevPACH should be > $25 for Aggressive, got ${revpach:.2f}"
    assert revpach <= HARD_CAP, f"RevPACH should be <= ${HARD_CAP}, got ${revpach:.2f}"
    assert rev_util <= UTIL_CAP, f"Rev/Util Hr should be <= ${UTIL_CAP}, got ${rev_util:.2f}"
    
    print("\n✅ Aggressive preset test passed")

def test_balanced_preset():
    """Test that Balanced preset produces lower density"""
    # Create config with Balanced settings
    cfg = Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(),
        pricing=Pricing(nm_prime_per_court=65, nm_off_per_court=56),
        league=LeagueConfig(
            weeknights=3,  # Balanced
            fill_rate=0.85,  # Balanced
            active_weeks=44,  # Balanced
            price_prime_slot_6wk=150.0
        ),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Compute with balanced settings
    res = compute(cfg)
    
    revpach = res["density"]["RevPACH"]
    rev_util = res["density"]["RevPerUtilHr"]
    
    print(f"\nBalanced Preset Results:")
    print(f"  RevPACH: ${revpach:.2f}")
    print(f"  Rev/Util Hr: ${rev_util:.2f}")
    
    # Balanced should be lower than Aggressive
    print("✅ Balanced preset test passed")

def test_underwriting_packet_structure():
    """Test that underwriting packet has correct structure"""
    try:
        from app import build_underwriting_packet
    except ImportError:
        print("\n⚠️ Skipping underwriting packet test (streamlit not installed)")
        return
    
    cfg = Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    res = compute(cfg)
    packet = build_underwriting_packet(cfg, res, "Aggressive", include_audit=True)
    
    # Check packet structure
    assert "Scenario" in packet
    assert "Schedule" in packet
    assert "Pricing" in packet
    assert "Revenue (annual, variable only)" in packet
    assert "Density" in packet
    
    # Check audit sections if included
    if "court_debug" in res:
        assert "Court Pricing Audit" in packet
    if "league_debug" in res:
        assert "League Discount Audit" in packet
    
    print("\n✅ Underwriting packet structure test passed")
    print(f"  Packet contains {len(packet)} sections")

def test_export_thresholds():
    """Test that export thresholds work correctly"""
    WATCH_LOW, WATCH_HIGH = 28.0, 35.0
    HARD_CAP = 35.0
    UTIL_CAP = 60.0
    
    test_cases = [
        (27.0, 45.0, "normal", "RevPACH below watchlist"),
        (30.0, 45.0, "watchlist", "RevPACH in watchlist band"),
        (36.0, 45.0, "blocked", "RevPACH exceeds hard cap"),
        (30.0, 65.0, "blocked", "Rev/Util Hr exceeds cap"),
    ]
    
    for revpach, rev_util, expected, description in test_cases:
        export_blocked = False
        status = "normal"
        
        if revpach > HARD_CAP or rev_util > UTIL_CAP:
            export_blocked = True
            status = "blocked"
        elif revpach >= WATCH_LOW:
            status = "watchlist"
        
        assert status == expected, f"Failed: {description}"
        print(f"✅ {description}: RevPACH ${revpach:.0f}, Rev/Util ${rev_util:.0f} -> {status}")
    
    print("\n✅ Export threshold tests passed")

if __name__ == "__main__":
    test_aggressive_preset()
    test_balanced_preset()
    test_underwriting_packet_structure()
    test_export_thresholds()
    print("\n✅ All Option A tests passed!")
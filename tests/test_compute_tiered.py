"""Test the compute function with tiered member pricing"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
from engine.models import Config, Facility, PrimeWindow, Pricing, LeagueConfig, CorpConfig, Tournaments, Retail
from engine.compute import compute

def test_compute_with_tiered_pricing():
    """Test that compute works with tiered pricing enabled"""
    
    # Create a config
    cfg = Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(
            mon_thu_start=16.0, mon_thu_end=22.0,
            fri_start=16.0, fri_end=21.0,
            weekend_morning_hours=4.0
        ),
        pricing=Pricing(
            nm_prime_per_court=65.0,
            nm_off_per_court=56.0
        ),
        league=LeagueConfig(
            session_len_h=1.5, buffer_min=10,
            weeknights=4, weekend_morns=1,
            courts_used=4, players_per_court=4,
            fill_rate=0.90, active_weeks=46,
            price_prime_slot_6wk=150.0
        ),
        corp=CorpConfig(
            prime_rate_per_court=200.0,
            events_per_month=2, hours_per_event=6.0
        ),
        tourneys=Tournaments(per_quarter_revenue=9000.0),
        retail=Retail(monthly_sales=3000.0)
    )
    
    # Define member mix
    class MemberMix:
        pct_community = 0.30
        pct_player = 0.50
        pct_pro = 0.20
    
    # Run compute with tiered pricing (now default)
    result_tiered = compute(cfg)
    
    # Check that we get results
    assert "weekly" in result_tiered
    assert "annual" in result_tiered
    assert "density" in result_tiered
    assert "court_debug" in result_tiered  # Should have debug info
    assert "league_debug" in result_tiered  # Should have league debug info
    
    # Check debug structure has expected fields
    debug = result_tiered["court_debug"]
    assert "per_court_rates" in debug
    assert "rev_breakdown" in debug
    assert "mem_prime_tier" in debug
    assert "mem_off_tier" in debug
    
    # Verify per-court rates are correct
    rates = debug["per_court_rates"]
    assert rates["community"]["prime"] == 56.0  # $14 * 4
    assert rates["community"]["off"] == 44.0    # $11 * 4
    assert rates["player"]["prime"] == 36.0     # $9 * 4
    assert rates["player"]["off"] == 0.0        # Included
    assert rates["pro"]["prime"] == 0.0         # Included
    assert rates["pro"]["off"] == 0.0           # Included
    
    print(f"✅ Court revenue/week: ${result_tiered['weekly']['court_rev']:,.2f}")
    print(f"✅ League revenue/week: ${result_tiered['weekly']['league_rev']:,.2f}")
    
    # Check league debug info
    league_dbg = result_tiered["league_debug"]
    assert "disc_member_price" in league_dbg
    assert "avg_slot_price" in league_dbg
    print(f"✅ League avg slot price: ${league_dbg['avg_slot_price']:,.2f}")
    
    print("✅ Compute with tiered pricing test passed")

def test_member_mix_affects_revenue():
    """Test that different member mixes produce different revenues"""
    
    from engine.models import MemberMix
    
    # Config with mostly community
    cfg1 = Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    cfg1.member_mix.pct_community = 0.80
    cfg1.member_mix.pct_player = 0.15
    cfg1.member_mix.pct_pro = 0.05
    
    # Config with mostly pro
    cfg2 = Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    cfg2.member_mix.pct_community = 0.10
    cfg2.member_mix.pct_player = 0.20
    cfg2.member_mix.pct_pro = 0.70
    
    result1 = compute(cfg1)
    result2 = compute(cfg2)
    
    # Mix1 should generate more court revenue (community pays, pro doesn't)
    assert result1["weekly"]["court_rev"] > result2["weekly"]["court_rev"]
    
    print(f"✅ Mix1 (80% community): ${result1['weekly']['court_rev']:,.2f}/week")
    print(f"✅ Mix2 (70% pro): ${result2['weekly']['court_rev']:,.2f}/week")
    print("✅ Member mix affects revenue test passed")

if __name__ == "__main__":
    test_compute_with_tiered_pricing()
    test_member_mix_affects_revenue()
    print("\n✅ All compute integration tests passed!")
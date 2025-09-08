import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
from engine.models import MemberPlans, LeagueDiscounts
from engine.revenue import per_court_from_per_person, tier_per_court_rates, court_rental_revenue_week_tiered, league_effective_price

def test_per_person_to_per_court_conversion():
    """Test that per-person rates convert correctly to per-court rates"""
    mp = MemberPlans(players_per_court=4)
    # Community: $14 / $11 per person ⇒ $56 / $44 per court
    rates = tier_per_court_rates(mp)
    assert math.isclose(rates["community"]["prime"], 56.0, rel_tol=1e-6)
    assert math.isclose(rates["community"]["off"],   44.0, rel_tol=1e-6)
    # Player: $9 prime ⇒ $36 per court; Off-peak included ⇒ $0
    assert math.isclose(rates["player"]["prime"], 36.0, rel_tol=1e-6)
    assert math.isclose(rates["player"]["off"],    0.0, rel_tol=1e-6)
    # Pro: included everywhere ⇒ $0
    assert math.isclose(rates["pro"]["prime"], 0.0, rel_tol=1e-6)
    assert math.isclose(rates["pro"]["off"],   0.0, rel_tol=1e-6)
    print("✅ Per-person to per-court conversion test passed")

def test_league_discounts_apply_exactly_and_example_99():
    """Test that league discounts apply correctly to base prices"""
    disc = LeagueDiscounts(community_pct=0.0, player_pct=0.15, pro_pct=0.25)
    # Base prime = 150 ⇒ player 127.5, pro 112.5
    p150 = league_effective_price(150.0, disc)
    assert math.isclose(p150["community"], 150.0, rel_tol=1e-6)
    assert math.isclose(p150["player"],    127.5, rel_tol=1e-6)
    assert math.isclose(p150["pro"],       112.5, rel_tol=1e-6)
    # Your example at $99 ⇒ $84.15 and $74.25
    p99 = league_effective_price(99.0, disc)
    assert math.isclose(p99["player"], 84.15, abs_tol=0.01)
    assert math.isclose(p99["pro"],    74.25, abs_tol=0.01)
    print("✅ League discount test passed")

def test_tiered_court_revenue_respects_inclusion_rules():
    """Test that tiered court revenue calculation respects $0 inclusion for Player off-peak & Pro everywhere"""
    # Simple weekly scenario to check $0 inclusion for Player off-peak & Pro everywhere.
    class Mix:  # 20% / 60% / 20%
        pct_community=0.20
        pct_player=0.60
        pct_pro=0.20

    mp = MemberPlans(players_per_court=4)
    # open hours: 10 prime, 10 off-peak; utilization 100% to keep numbers simple
    total_rev, dbg = court_rental_revenue_week_tiered(
        open_prime_ch_wk=10.0, open_off_ch_wk=10.0,
        util_prime=1.0, util_off=1.0,
        member_share_prime=0.60, member_share_off=0.60,
        member_mix=Mix(), member_plans=mp,
        nm_prime_per_court=65.0, nm_off_per_court=56.0,
    )
    # Member utilized CH: 6 prime, 6 off. Split by mix: comm=1.2, player=3.6, pro=1.2 in each bucket.
    # Per-court rates: community $56/$44; player $36/$0; pro $0/$0
    rev_member_prime = 1.2*56 + 3.6*36 + 1.2*0   # = 67.2 + 129.6 = 196.8
    rev_member_off   = 1.2*44 + 3.6*0  + 1.2*0   # = 52.8
    # Non-member utilized CH: 4 prime, 4 off
    rev_nm_prime = 4*65   # = 260
    rev_nm_off   = 4*56   # = 224
    expected_total = rev_member_prime + rev_member_off + rev_nm_prime + rev_nm_off
    assert math.isclose(total_rev, expected_total, rel_tol=1e-9)

    # Check debug structure and that player/pro off-peak produce $0 by rate
    assert dbg["per_court_rates"]["player"]["off"] == 0.0
    assert dbg["per_court_rates"]["pro"]["prime"] == 0.0
    assert dbg["per_court_rates"]["pro"]["off"] == 0.0
    print("✅ Tiered court revenue test passed")

def test_member_plan_pricing_structure():
    """Test the complete member plan pricing structure"""
    mp = MemberPlans()
    
    # Test defaults match spec
    assert mp.community_prime_pp == 14.0
    assert mp.community_off_pp == 11.0
    assert mp.player_prime_pp == 9.0
    assert mp.player_off_pp == 0.0  # Included
    assert mp.pro_prime_pp == 0.0  # Included
    assert mp.pro_off_pp == 0.0  # Included
    assert mp.players_per_court == 4
    
    # Test conversion
    rates = tier_per_court_rates(mp)
    
    # Community: Standard rates
    assert rates["community"]["prime"] == 56.0  # $14 * 4
    assert rates["community"]["off"] == 44.0    # $11 * 4
    
    # Player: Prime discounted, off-peak included
    assert rates["player"]["prime"] == 36.0  # $9 * 4
    assert rates["player"]["off"] == 0.0     # Included
    
    # Pro: All included
    assert rates["pro"]["prime"] == 0.0  # Included
    assert rates["pro"]["off"] == 0.0    # Included
    
    print("✅ Member plan pricing structure test passed")

def test_booking_windows():
    """Test booking window configuration"""
    from engine.models import BookingWindows
    
    bw = BookingWindows()
    assert bw.community_days == 3
    assert bw.player_days == 7
    assert bw.pro_days == 14
    print("✅ Booking windows test passed")

def test_revenue_breakdown_with_real_scenario():
    """Test a realistic revenue scenario with member tiers"""
    class MemberMix:
        # Realistic mix: 30% community, 50% player, 20% pro
        pct_community = 0.30
        pct_player = 0.50
        pct_pro = 0.20
    
    mp = MemberPlans()
    
    # Scenario: 20 prime hours, 30 off-peak hours per week
    # 70% utilization prime, 50% off-peak
    # 50% member share
    total_rev, dbg = court_rental_revenue_week_tiered(
        open_prime_ch_wk=20.0,
        open_off_ch_wk=30.0,
        util_prime=0.70,
        util_off=0.50,
        member_share_prime=0.50,
        member_share_off=0.50,
        member_mix=MemberMix(),
        member_plans=mp,
        nm_prime_per_court=65.0,
        nm_off_per_court=56.0,
    )
    
    # Verify the calculation
    # Utilized: 14 prime, 15 off-peak
    assert math.isclose(dbg["util_prime_ch"], 14.0, rel_tol=1e-6)
    assert math.isclose(dbg["util_off_ch"], 15.0, rel_tol=1e-6)
    
    # Member/non-member split: 7 prime member, 7.5 off member
    assert math.isclose(dbg["mem_prime_ch"], 7.0, rel_tol=1e-6)
    assert math.isclose(dbg["mem_off_ch"], 7.5, rel_tol=1e-6)
    assert math.isclose(dbg["nm_prime_ch"], 7.0, rel_tol=1e-6)
    assert math.isclose(dbg["nm_off_ch"], 7.5, rel_tol=1e-6)
    
    # Check tier splits
    assert math.isclose(dbg["mem_prime_tier"]["community"], 2.1, rel_tol=1e-6)
    assert math.isclose(dbg["mem_prime_tier"]["player"], 3.5, rel_tol=1e-6)
    assert math.isclose(dbg["mem_prime_tier"]["pro"], 1.4, rel_tol=1e-6)
    
    # Manual calculation:
    # Member prime: 2.1*56 + 3.5*36 + 1.4*0 = 117.6 + 126 = 243.6
    # Member off: 2.25*44 + 3.75*0 + 1.5*0 = 99
    # Non-member prime: 7*65 = 455
    # Non-member off: 7.5*56 = 420
    expected = 243.6 + 99 + 455 + 420
    assert math.isclose(total_rev, expected, abs_tol=0.1)
    
    print("✅ Revenue breakdown with real scenario test passed")

if __name__ == "__main__":
    test_per_person_to_per_court_conversion()
    test_league_discounts_apply_exactly_and_example_99()
    test_tiered_court_revenue_respects_inclusion_rules()
    test_member_plan_pricing_structure()
    test_booking_windows()
    test_revenue_breakdown_with_real_scenario()
    print("\n✅ All membership plan tests passed!")
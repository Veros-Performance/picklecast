"""Test 24-month projections with S-curve ramp"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import *
from engine.projections import build_24_month_projection, logistic_members
from engine.compute import compute

def base_cfg():
    return Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(),
        pricing=Pricing(nm_prime_per_court=65, nm_off_per_court=56),
        league=LeagueConfig(
            session_len_h=1.5, buffer_min=10, weeknights=4, weekend_morns=1,
            courts_used=4, players_per_court=4, fill_rate=0.90,
            active_weeks=46, price_prime_slot_6wk=150.0, price_off_slot_6wk=100.0
        ),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail(),
        member_plans=MemberPlans(players_per_court=4),
        league_discounts=LeagueDiscounts(),
        openplay=OpenPlay(),
        member_mix=MemberMix(),
        league_participants=LeagueParticipants(),
        growth=GrowthConfig(),
        seasonality=Seasonality(),
        costs=CostsConfig(),
        finance=FinanceConfig(),
    )

def test_membership_scurve_monotonic_and_capped():
    """Test that membership follows S-curve, is monotonic, and respects cap"""
    cfg = base_cfg()
    res = build_24_month_projection(cfg)
    members = [m["members"] for m in res["months"]]
    
    # Check monotonic increase
    for i in range(len(members) - 1):
        assert members[i] <= members[i + 1], f"Members should increase: {members[i]} > {members[i+1]} at month {i}"
    
    # Check cap respected
    assert max(members) <= cfg.growth.K, f"Members {max(members)} exceeds cap {cfg.growth.K}"
    
    # Check starts at or above start_members
    assert members[0] >= cfg.growth.start_members, f"Should start with at least {cfg.growth.start_members} members"
    
    print(f"✅ S-curve test passed: {members[0]} → {members[-1]} members (cap: {cfg.growth.K})")

def test_y1_y2_rollup_present_and_finite():
    """Test that Y1 and Y2 rollups are computed correctly"""
    cfg = base_cfg()
    res = build_24_month_projection(cfg)
    
    y1 = res["summary"]["Y1"]
    y2 = res["summary"]["Y2"]
    
    # Check revenues are positive
    assert y1["rev_total"] > 0, "Y1 revenue should be positive"
    assert y2["rev_total"] > 0, "Y2 revenue should be positive"
    
    # Check DSCR is finite (can be negative in early months)
    assert y1["min_DSCR"] != float("inf"), "Y1 min DSCR should be finite"
    assert y2["min_DSCR"] != float("inf"), "Y2 min DSCR should be finite"
    
    # Y2 should generally be higher than Y1 (after ramp)
    assert y2["rev_total"] > y1["rev_total"], "Y2 revenue should exceed Y1 (post-ramp)"
    
    print(f"✅ Y1 revenue: ${y1['rev_total']:,.0f}, Y2 revenue: ${y2['rev_total']:,.0f}")
    print(f"✅ Y1 min DSCR: {y1['min_DSCR']:.2f}, Y2 avg DSCR: {y2['avg_DSCR']:.2f}")

def test_monthly_sums_equal_yearly_with_steady_state():
    """Test that steady-state months are consistent"""
    cfg = base_cfg()
    # Force immediate steady-state (no ramp): start_members = K, r large
    cfg.growth.start_members = cfg.growth.K
    cfg.growth.r = 10.0  # very steep curve
    cfg.growth.t_mid = 0  # immediate
    
    proj = build_24_month_projection(cfg)
    
    # Compare months 13–24 (should be relatively flat after steady state)
    y2 = proj["months"][12:]
    revs = [m["rev_total"] for m in y2]
    
    # Allow small variation due to seasonality
    avg_rev = sum(revs) / len(revs)
    for i, rev in enumerate(revs):
        variance = abs(rev - avg_rev) / avg_rev
        assert variance < 0.15, f"Month {12+i} revenue ${rev:.0f} varies >15% from avg ${avg_rev:.0f}"
    
    print(f"✅ Steady-state test passed: Y2 revenues consistent (avg: ${avg_rev:,.0f})")

def test_league_weeks_sum_to_46():
    """Test that league weeks per year sum to 46"""
    cfg = base_cfg()
    res = build_24_month_projection(cfg)
    
    # Sum league weeks for Y1 and Y2
    y1_weeks = sum(m["league_weeks_m"] for m in res["months"][:12])
    y2_weeks = sum(m["league_weeks_m"] for m in res["months"][12:])
    
    # Should be very close to 46
    assert abs(y1_weeks - 46.0) < 0.1, f"Y1 league weeks {y1_weeks:.2f} should sum to 46"
    assert abs(y2_weeks - 46.0) < 0.1, f"Y2 league weeks {y2_weeks:.2f} should sum to 46"
    
    print(f"✅ League weeks test passed: Y1={y1_weeks:.1f}, Y2={y2_weeks:.1f}")

def test_logistic_function():
    """Test the logistic S-curve function directly"""
    K = 350
    r = 0.35
    t_mid = 8
    start = 50
    
    # Test at various points
    assert logistic_members(0, K, r, t_mid, start) >= start
    assert logistic_members(t_mid, K, r, t_mid, start) > K * 0.4  # Around midpoint
    assert logistic_members(24, K, r, t_mid, start) <= K
    
    # Test monotonic increase
    prev = 0
    for t in range(25):
        curr = logistic_members(t, K, r, t_mid, start)
        assert curr >= prev, f"Logistic should be monotonic: {curr} < {prev} at t={t}"
        prev = curr
    
    print("✅ Logistic function test passed")

def test_cash_flow_accumulation():
    """Test that cumulative cash flow is tracked correctly"""
    cfg = base_cfg()
    res = build_24_month_projection(cfg)
    
    # Verify cumulative cash calculation
    cum_cash = cfg.finance.wc_reserve_start
    for i, m in enumerate(res["months"]):
        cum_cash += m["cash_flow_m"]
        assert abs(m["cum_cash"] - cum_cash) < 0.01, f"Month {i} cum_cash mismatch"
    
    print(f"✅ Cash flow test passed: Ending cash ${res['months'][-1]['cum_cash']:,.0f}")

def test_break_even_identification():
    """Test that break-even month is correctly identified"""
    cfg = base_cfg()
    res = build_24_month_projection(cfg)
    
    # Find first positive EBITDA month
    expected_be = None
    for m in res["months"]:
        if m["EBITDA_m"] >= 0:
            expected_be = m["month"]
            break
    
    y1_be = res["summary"]["Y1"]["break_even_month"]
    
    if expected_be and expected_be <= res["months"][11]["month"]:
        assert y1_be == expected_be, f"Break-even should be {expected_be}, got {y1_be}"
        print(f"✅ Break-even test passed: Month {y1_be}")
    else:
        assert y1_be is None, "No break-even in Y1 as expected"
        print("✅ Break-even test passed: Not achieved in Y1")

if __name__ == "__main__":
    test_logistic_function()
    test_membership_scurve_monotonic_and_capped()
    test_y1_y2_rollup_present_and_finite()
    test_monthly_sums_equal_yearly_with_steady_state()
    test_league_weeks_sum_to_46()
    test_cash_flow_accumulation()
    test_break_even_identification()
    print("\n✅ All projection tests passed!")
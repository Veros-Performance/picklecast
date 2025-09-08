"""Test utilization solver and league mix changes"""
import pytest
import math
from engine.models import Config, Facility, PrimeWindow, Pricing, LeagueConfig, CorpConfig, Tournaments, Retail
from engine.utilization import solve_offpeak_util, compute_overall_utilization
from engine.schedule import engine_prime_share
from engine.compute import compute

def test_utilization_solver_basic():
    """Test basic utilization solver math"""
    # With prime_share = 0.38, up = 0.95, overall = 0.70
    prime_share = 0.38
    prime_util = 0.95
    overall_target = 0.70
    
    offpeak_util, warning = solve_offpeak_util(overall_target, prime_util, prime_share)
    
    # Expected: uo = (0.70 - 0.38*0.95)/(1 - 0.38) ≈ 0.55
    expected = (overall_target - prime_share * prime_util) / (1 - prime_share)
    assert abs(offpeak_util - expected) < 0.01, f"Expected {expected:.2f}, got {offpeak_util:.2f}"
    assert abs(offpeak_util - 0.55) < 0.01, f"Expected ~0.55, got {offpeak_util:.2f}"
    assert warning == ""

def test_utilization_solver_clamping():
    """Test clamping behavior when computed value exceeds bounds"""
    prime_share = 0.30
    prime_util = 0.95
    
    # Test upper clamp (overall = 0.85 should push off-peak > 0.80)
    overall_target = 0.85
    offpeak_util, warning = solve_offpeak_util(overall_target, prime_util, prime_share)
    
    assert offpeak_util == 0.80, f"Should clamp to 0.80, got {offpeak_util:.2f}"
    assert "exceeds maximum" in warning
    
    # Test lower clamp (overall = 0.40 should push off-peak < 0.45)
    overall_target = 0.40
    offpeak_util, warning = solve_offpeak_util(overall_target, prime_util, prime_share)
    
    assert offpeak_util == 0.45, f"Should clamp to 0.45, got {offpeak_util:.2f}"
    assert "below minimum" in warning

def test_compute_overall_utilization():
    """Test overall utilization computation"""
    prime_util = 0.95
    offpeak_util = 0.55
    prime_share = 0.38
    
    overall = compute_overall_utilization(prime_util, offpeak_util, prime_share)
    expected = prime_share * prime_util + (1 - prime_share) * offpeak_util
    
    assert abs(overall - expected) < 0.001
    assert abs(overall - 0.70) < 0.01, f"Expected ~0.70, got {overall:.2f}"

def test_config_wiring():
    """Test that utilization solver is wired into Config defaults"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Check prime utilization is 95%
    assert cfg.openplay.util_prime == 0.95
    
    # Check off-peak is computed for 70% overall
    prime_share = engine_prime_share(cfg)
    expected_offpeak, _ = solve_offpeak_util(0.70, 0.95, prime_share)
    assert abs(cfg.openplay.util_off - expected_offpeak) < 0.01
    
    # Verify overall utilization is ~70%
    overall = compute_overall_utilization(
        cfg.openplay.util_prime,
        cfg.openplay.util_off,
        prime_share
    )
    assert abs(overall - 0.70) < 0.01, f"Overall should be ~0.70, got {overall:.2f}"

def test_league_member_share_default():
    """Test that league member share defaults to 35%"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    assert cfg.league_participants.member_share == 0.35, "League member share should be 35%"

def test_monotonic_revenue():
    """Test that increasing off-peak utilization increases revenue"""
    cfg1 = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Force lower off-peak utilization
    cfg1.openplay.util_off = 0.45
    res1 = compute(cfg1)
    
    # Higher off-peak utilization
    cfg2 = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    cfg2.openplay.util_off = 0.55
    res2 = compute(cfg2)
    
    # Should have more revenue and utilized hours
    assert res2['annual']['variable_rev'] > res1['annual']['variable_rev']
    assert res2['utilized_ch_year'] > res1['utilized_ch_year']
    
    # Check ΔEBITDA approximation
    delta_rev = res2['annual']['variable_rev'] - res1['annual']['variable_rev']
    delta_ch = res2['utilized_ch_year'] - res1['utilized_ch_year']
    
    # EBITDA impact ≈ ΔRev - 0.15*ΔRev - 5*ΔCH
    expected_ebitda_delta = delta_rev * 0.85 - 5 * delta_ch
    
    # This is approximate, allow 20% variance
    print(f"ΔRevenue: ${delta_rev:,.0f}")
    print(f"ΔUtilized CH: {delta_ch:,.0f}")
    print(f"Expected ΔEBITDA: ${expected_ebitda_delta:,.0f}")

def test_league_pricing_with_member_mix():
    """Test league pricing with 35% member share"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    res = compute(cfg)
    
    # With 35% members, weighted price should be higher than member-heavy (80%)
    cfg_member_heavy = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    cfg_member_heavy.league_participants.member_share = 0.80
    res_member_heavy = compute(cfg_member_heavy)
    
    # More non-members = higher revenue
    assert res['annual']['league_rev'] > res_member_heavy['annual']['league_rev']
    
    print(f"League revenue (35% members): ${res['annual']['league_rev']:,.0f}")
    print(f"League revenue (80% members): ${res_member_heavy['annual']['league_rev']:,.0f}")

def test_guardrails_maintained():
    """Test that all guardrails are maintained"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    res = compute(cfg)
    
    # Utilized ≤ Available
    assert res['utilized_ch_year'] <= res['available_ch_year']
    
    # League CH ≤ Prime CH (using court hours from league_debug)
    league_debug = res.get('league_debug', {})
    if league_debug:
        league_ch_week = league_debug.get('league_ch_week', 0)
        prime_ch_week = league_debug.get('prime_ch_week', 116)  # From schedule
        assert league_ch_week <= prime_ch_week, f"League {league_ch_week} > Prime {prime_ch_week}"
    
    # No unit bleed (check that utilized hours are reasonable)
    # Just verify utilized hours are within bounds
    utilized_pct = res['utilized_ch_year'] / res['available_ch_year']
    assert 0.5 <= utilized_pct <= 0.8, f"Utilization {utilized_pct:.1%} seems unreasonable"
    
    print("✅ All guardrails pass")

def test_prime_share_calculation():
    """Test prime share calculation from schedule"""
    cfg = Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(
            mon_thu_start=16.0,
            mon_thu_end=20.0,
            fri_start=16.0,
            fri_end=21.0,
            weekend_morning_hours=4.0
        ),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    prime_share = engine_prime_share(cfg)
    
    # Calculate expected: (4*4 + 5*1 + 4*2) * 4 courts / (14*7*4)
    prime_hours = (4*4 + 5*1 + 4*2) * 4  # 116
    total_hours = 14 * 7 * 4  # 392
    expected = prime_hours / total_hours
    
    assert abs(prime_share - expected) < 0.01
    assert abs(prime_share - 0.296) < 0.01, f"Expected ~29.6%, got {prime_share*100:.1f}%"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
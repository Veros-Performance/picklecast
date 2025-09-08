"""Test the uplift changes: +1pp utilization and +1 corporate event"""
import pytest
from engine.models import Config, Facility, PrimeWindow, Pricing, LeagueConfig, CorpConfig, Tournaments, Retail
from engine.utilization import solve_offpeak_util, compute_overall_utilization
from engine.schedule import engine_prime_share
from engine.compute import compute
from engine.revenue import corporate_revenue_year

def test_utilization_uplift():
    """Test that utilization increases by 1pp to 71%"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Check prime is still 95%
    assert cfg.openplay.util_prime == 0.95
    
    # Check overall utilization is 71%
    prime_share = engine_prime_share(cfg)
    overall = compute_overall_utilization(cfg.openplay.util_prime, cfg.openplay.util_off, prime_share)
    assert abs(overall - 0.71) < 0.005, f"Overall utilization should be 71%, got {overall*100:.1f}%"
    
    # Check off-peak increased by ~1pp from 70% case
    # With prime_share ~29.6%, the 70% case had off-peak ~64%
    # The 71% case should have off-peak ~65.4%
    expected_offpeak_70, _ = solve_offpeak_util(0.70, 0.95, prime_share)
    expected_offpeak_71, _ = solve_offpeak_util(0.71, 0.95, prime_share)
    delta = expected_offpeak_71 - expected_offpeak_70
    
    assert 0.005 <= delta <= 0.02, f"Off-peak should increase by ~1pp, got {delta*100:.2f}pp"
    print(f"✅ Off-peak utilization: {expected_offpeak_70*100:.1f}% → {expected_offpeak_71*100:.1f}% (+{delta*100:.2f}pp)")

def test_corporate_extra_events():
    """Test adding 1 extra corporate event per year"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(
            events_per_month=2,
            hours_per_event=6.0,
            courts_used=4,
            off_rate_per_court=170.0,
            extra_events_per_year=1
        ),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Calculate revenue with extra event
    corp_rev_with_extra = corporate_revenue_year(cfg.corp, prime=False)
    
    # Calculate revenue without extra event
    cfg_no_extra = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(
            events_per_month=2,
            hours_per_event=6.0,
            courts_used=4,
            off_rate_per_court=170.0,
            extra_events_per_year=0
        ),
        tourneys=Tournaments(),
        retail=Retail()
    )
    corp_rev_without = corporate_revenue_year(cfg_no_extra.corp, prime=False)
    
    # Expected delta: 1 event × 4 courts × 6 hours × $170/court-hour = $4,080
    expected_delta = 1 * 4 * 6 * 170
    actual_delta = corp_rev_with_extra - corp_rev_without
    
    assert abs(actual_delta - expected_delta) < 1, f"Expected ${expected_delta}, got ${actual_delta}"
    print(f"✅ Corporate revenue increase: ${actual_delta:,.0f} (1 extra event)")

def test_ebitda_impact():
    """Test EBITDA impact of uplift changes"""
    # Baseline config
    cfg_base = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(extra_events_per_year=0),  # No extra events
        tourneys=Tournaments(),
        retail=Retail()
    )
    # Force 70% utilization
    prime_share = engine_prime_share(cfg_base)
    cfg_base.openplay.util_off, _ = solve_offpeak_util(0.70, 0.95, prime_share)
    
    res_base = compute(cfg_base)
    
    # Uplift config (default now has 71% util and +1 corp event)
    cfg_uplift = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),  # Has extra_events_per_year=1 by default
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    res_uplift = compute(cfg_uplift)
    
    # Check revenue increase
    delta_rev = res_uplift['annual']['variable_rev'] - res_base['annual']['variable_rev']
    delta_ch = res_uplift['utilized_ch_year'] - res_base['utilized_ch_year']
    
    # Expected EBITDA impact: ΔRev × 0.85 - 5 × ΔCH
    expected_ebitda_delta = delta_rev * 0.85 - 5 * delta_ch
    
    print(f"✅ Revenue increase: ${delta_rev:,.0f}")
    print(f"✅ Utilized CH increase: {delta_ch:,.0f} hours")
    print(f"✅ Expected EBITDA impact: ${expected_ebitda_delta:,.0f}")
    
    # Should have positive revenue impact
    assert delta_rev > 0, "Revenue should increase with uplift"
    assert delta_ch > 0, "Utilized hours should increase"

def test_no_double_counting():
    """Test that utilized hours don't exceed available hours"""
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
    
    # Check utilized ≤ available
    assert res['utilized_ch_year'] <= res['available_ch_year'], \
        f"Utilized ({res['utilized_ch_year']}) exceeds available ({res['available_ch_year']})"
    
    # Check league hours ≤ prime hours
    league_debug = res.get('league_debug', {})
    if league_debug:
        league_ch = league_debug.get('league_ch_week', 0)
        prime_ch = league_debug.get('prime_ch_week', 116)
        assert league_ch <= prime_ch, f"League hours ({league_ch}) exceed prime hours ({prime_ch})"
    
    print("✅ No double counting: all guardrails pass")

def test_acceptance_criteria():
    """Test that uplift achieves acceptance criteria"""
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
    
    # Check RevPACH
    revpach = res['density']['RevPACH']
    assert revpach <= 40, f"RevPACH ${revpach:.2f} exceeds $40 hard limit"
    
    if revpach <= 38:
        print(f"✅ RevPACH ${revpach:.2f} ≤ $38 (good)")
    elif revpach <= 39:
        print(f"⚠️ RevPACH ${revpach:.2f} in $38-39 range (acceptable)")
    else:
        print(f"⚠️ RevPACH ${revpach:.2f} approaching $40 limit")
    
    # Check overall utilization
    prime_share = engine_prime_share(cfg)
    overall = compute_overall_utilization(cfg.openplay.util_prime, cfg.openplay.util_off, prime_share)
    assert abs(overall - 0.71) < 0.01, f"Overall utilization should be 71%, got {overall*100:.1f}%"
    
    print(f"✅ Overall utilization: {overall*100:.0f}%")
    print(f"✅ Corporate events: {cfg.corp.events_per_month * 12 + cfg.corp.extra_events_per_year}/year")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
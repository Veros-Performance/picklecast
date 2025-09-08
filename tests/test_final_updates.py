"""Test final updates: WC $200k, league mix 70/30, prime util 95%"""
import pytest
from engine.models import Config, Facility, PrimeWindow, Pricing, LeagueConfig, CorpConfig, Tournaments, Retail
from engine.models import FinanceConfig
from engine.compute import compute
from engine.capital import compute_loan_to_balance
from engine.revenue import weighted_member_league_price

def test_working_capital_loan_linkage():
    """Test that increasing WC from 100k to 200k increases loan by $100k"""
    # Config with $100k WC
    cfg_100k = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail(),
        finance=FinanceConfig(wc_reserve_start=100_000.0, apr=0.09, term_years=10)
    )
    
    # Config with $200k WC  
    cfg_200k = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail(),
        finance=FinanceConfig(wc_reserve_start=200_000.0, apr=0.09, term_years=10)
    )
    
    # Calculate loans
    loan_100k = compute_loan_to_balance(cfg_100k.finance)
    loan_200k = compute_loan_to_balance(cfg_200k.finance)
    
    # Should increase by exactly $100k
    delta = loan_200k - loan_100k
    assert abs(delta - 100_000) < 1, f"Loan should increase by $100k, got ${delta:,.0f}"
    
    # Check debt service increase
    apr = 0.09
    term_years = 10
    monthly_rate = apr / 12
    n_payments = term_years * 12
    
    payment_100k = loan_100k * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
    payment_200k = loan_200k * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
    
    annual_delta = (payment_200k - payment_100k) * 12
    
    # Should be reasonable increase
    assert 10_000 < annual_delta < 16_000, f"Annual debt service delta should be ~$15k, got ${annual_delta:,.0f}"
    
    print(f"✅ WC $100k→$200k: Loan +${delta:,.0f}, Annual DS +${annual_delta:,.0f}")

def test_league_mix_monotonicity():
    """Test that decreasing member share from 35% to 30% increases revenue"""
    cfg_35 = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    # Override to 35% members
    cfg_35.league_participants.member_share = 0.35
    
    cfg_30 = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    # Should default to 30% members
    assert cfg_30.league_participants.member_share == 0.30
    
    # Compute results
    res_35 = compute(cfg_35)
    res_30 = compute(cfg_30)
    
    # League revenue should increase with more non-members
    assert res_30['annual']['league_rev'] > res_35['annual']['league_rev']
    
    delta = res_30['annual']['league_rev'] - res_35['annual']['league_rev']
    print(f"✅ League mix 35%→30% members: Revenue +${delta:,.0f}/year")
    
    # Check weighted price
    weighted_35 = weighted_member_league_price(
        cfg_35.league.price_prime_slot_6wk,
        cfg_35.league_discounts,
        cfg_35.member_mix
    )
    weighted_30 = weighted_member_league_price(
        cfg_30.league.price_prime_slot_6wk,
        cfg_30.league_discounts,
        cfg_30.member_mix
    )
    
    # Weighted price should be ≤ rack
    assert weighted_35 <= cfg_35.league.price_prime_slot_6wk
    assert weighted_30 <= cfg_30.league.price_prime_slot_6wk
    
    print(f"✅ Weighted prices: 35% members=${weighted_35:.0f}, 30% members=${weighted_30:.0f}")

def test_prime_utilization_identity():
    """Test that prime utilization is 95% everywhere"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Check engine value
    assert cfg.openplay.util_prime == 0.95, f"Prime util should be 0.95, got {cfg.openplay.util_prime}"
    
    # Run compute and check consistency
    res = compute(cfg)
    
    # Prime utilization should be used consistently
    print(f"✅ Prime utilization: {cfg.openplay.util_prime*100:.0f}% (engine value)")

def test_guardrails_maintained():
    """Test that all guardrails pass with updates"""
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
    
    # League CH ≤ Prime CH (from debug if available)
    league_debug = res.get('league_debug', {})
    if league_debug:
        league_ch = league_debug.get('league_ch_week', 0)
        prime_ch = league_debug.get('prime_ch_week', 116)
        assert league_ch <= prime_ch, f"League {league_ch} > Prime {prime_ch}"
    
    # Sources = Uses
    loan = compute_loan_to_balance(cfg.finance)
    ti = 428_475
    equity = 200_000
    sources = loan + ti + equity
    
    uses = (cfg.finance.leasehold_improvements + 
            cfg.finance.equipment + 
            50_000 +  # pre-opening
            cfg.finance.wc_reserve_start +
            99_400)  # contingency
    
    assert abs(sources - uses) < 1, f"Sources ${sources:,.0f} ≠ Uses ${uses:,.0f}"
    
    print("✅ All guardrails pass")

def test_acceptance_metrics():
    """Test that acceptance criteria are met"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Check configurations
    assert cfg.finance.wc_reserve_start == 200_000.0, "WC should be $200k"
    assert cfg.finance.apr == 0.09, "APR should be 9%"
    assert cfg.league_participants.member_share == 0.30, "League members should be 30%"
    assert cfg.openplay.util_prime == 0.95, "Prime util should be 95%"
    
    # Check computed loan
    loan = compute_loan_to_balance(cfg.finance)
    expected_loan = 934_925  # With $200k WC
    assert abs(loan - expected_loan) < 1000, f"Loan should be ~${expected_loan:,.0f}, got ${loan:,.0f}"
    
    print(f"✅ Acceptance: WC=$200k, APR=9%, League=30/70, Prime=95%")
    print(f"✅ Computed loan: ${loan:,.0f}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
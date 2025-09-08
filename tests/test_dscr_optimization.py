"""Test DSCR optimization changes"""
import pytest
from engine.models import Config, Facility, PrimeWindow, Pricing, LeagueConfig, CorpConfig, Tournaments, Retail
from engine.models import MemberPlans, LeagueDiscounts, BookingWindows, LeagueParticipants, MemberMix, OpenPlay
from engine.models import GrowthConfig, Seasonality, CostsConfig, FinanceConfig
from engine.projections import build_24_month_projection
from datetime import date

def test_membership_pricing_updated():
    """Test that membership fees are correctly updated"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Check new membership pricing
    assert cfg.member_plans.player_monthly_fee == 99.0, "Player fee should be $99"
    assert cfg.member_plans.pro_monthly_fee == 189.0, "Pro fee should be $189"
    assert cfg.member_plans.community_monthly_fee == 0.0, "Community fee should be $0"

def test_fixed_costs_reduced():
    """Test that fixed costs are reduced by $2k/month"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Check reduced fixed costs
    assert cfg.costs.fixed_monthly_base == 60000.0, "Fixed monthly base should be $60k"
    assert cfg.costs.rent_monthly == 37000.0, "Rent should remain $37k"
    
    # Non-rent fixed should be $23k
    non_rent_fixed = cfg.costs.fixed_monthly_base - cfg.costs.rent_monthly
    assert non_rent_fixed == 23000.0, f"Non-rent fixed should be $23k, got ${non_rent_fixed}"

def test_league_member_share():
    """Test that league member share is reduced to 65%"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    assert cfg.league_participants.member_share == 0.65, "League member share should be 65%"

def test_working_capital_increased():
    """Test that working capital is increased to $200k"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    assert cfg.finance.wc_reserve_start == 200000.0, "Working capital should be $200k"

def test_dscr_improvement():
    """Test that Y2 DSCR improves with changes"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Run projections
    proj = build_24_month_projection(cfg)
    
    # Check Y2 average DSCR
    y2_avg_dscr = proj["summary"]["Y2"]["avg_DSCR"]
    
    # Should be closer to or above 1.25 target
    assert y2_avg_dscr > 1.15, f"Y2 DSCR should be > 1.15, got {y2_avg_dscr:.2f}"
    
    # Check Y2 minimum DSCR
    y2_min_dscr = proj["summary"]["Y2"]["min_DSCR"]
    assert y2_min_dscr > 1.0, f"Y2 min DSCR should be > 1.0, got {y2_min_dscr:.2f}"

def test_membership_revenue_calculation():
    """Test that membership revenue correctly uses new pricing"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    # Set known member counts
    cfg.growth.K = 300  # cap
    cfg.growth.start_members = 300  # start at cap for simple calc
    
    proj = build_24_month_projection(cfg)
    
    # Check last month (should be at steady state)
    last_month = proj["months"][-1]
    members = last_month["members"]
    
    # Calculate expected membership revenue
    # With default mix: 20% community, 60% player, 20% pro
    comm = round(members * 0.20)
    play = round(members * 0.60)
    pro = members - comm - play
    
    expected_membership = (
        comm * 0.0 +  # Community $0
        play * 99.0 +  # Player $99
        pro * 189.0    # Pro $189
    )
    
    actual_membership = last_month["rev_membership"]
    
    # Allow small rounding difference
    assert abs(actual_membership - expected_membership) < 100, \
        f"Membership revenue mismatch: expected ${expected_membership:.0f}, got ${actual_membership:.0f}"

def test_costs_structure():
    """Test that cost structure is properly configured"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    proj = build_24_month_projection(cfg)
    
    # Check first month costs
    first_month = proj["months"][0]
    
    # Fixed costs should start at $60k (no rent abatement)
    assert first_month["fixed_opex_m"] == 60000.0, f"First month fixed should be $60k, got ${first_month['fixed_opex_m']:.0f}"
    
    # Rent component should be $37k
    assert first_month["rent_m"] == 37000.0, f"First month rent should be $37k, got ${first_month['rent_m']:.0f}"
    
    # Non-rent fixed should be $23k
    assert first_month["non_rent_fixed_m"] == 23000.0, f"First month non-rent should be $23k, got ${first_month['non_rent_fixed_m']:.0f}"

def test_cash_position_improvement():
    """Test that cash position improves with increased working capital"""
    cfg = Config(
        facility=Facility(),
        prime=PrimeWindow(),
        pricing=Pricing(),
        league=LeagueConfig(),
        corp=CorpConfig(),
        tourneys=Tournaments(),
        retail=Retail()
    )
    
    proj = build_24_month_projection(cfg)
    
    # Check starting cash
    first_month = proj["months"][0]
    starting_cash = cfg.finance.wc_reserve_start
    
    # First month cumulative cash should be starting + first month cash flow
    expected_first_cum = starting_cash + first_month["cash_flow_m"]
    assert abs(first_month["cum_cash"] - expected_first_cum) < 1.0, \
        f"First month cum cash mismatch: expected ${expected_first_cum:.0f}, got ${first_month['cum_cash']:.0f}"
    
    # Check that we maintain positive cash throughout
    min_cash = min(m["cum_cash"] for m in proj["months"])
    assert min_cash > 0, f"Should maintain positive cash, minimum was ${min_cash:.0f}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
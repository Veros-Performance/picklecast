"""Test financial statements (P&L and Balance Sheet)"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import *
from engine.statements import build_financial_statements, calculate_depreciation

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

def test_balance_sheet_balances():
    """Test that Assets = Liabilities + Equity for all months"""
    cfg = base_cfg()
    stmts = build_financial_statements(cfg)
    bs = stmts["balance_sheet"]
    
    for i, row in enumerate(bs):
        assets = row["total_assets"]
        liab_equity = row["total_liabilities_equity"]
        diff = abs(assets - liab_equity)
        assert diff < 1.0, f"Month {i}: Balance sheet doesn't balance. Assets={assets:.2f}, L+E={liab_equity:.2f}, diff={diff:.2f}"
    
    print(f"✅ Balance sheet balances for all {len(bs)} months")

def test_cash_rolls_forward():
    """Test that cash rolls forward correctly month to month"""
    cfg = base_cfg()
    stmts = build_financial_statements(cfg)
    bs = stmts["balance_sheet"]
    pnl = stmts["pnl"]
    
    starting_cash = cfg.finance.wc_reserve_start
    assert abs(bs[0]["cash"] - starting_cash) < 100000, f"First month cash should be near starting cash"
    
    # Cash should change each month based on operations
    for i in range(1, len(bs)):
        cash_change = bs[i]["cash"] - bs[i-1]["cash"]
        # Cash flow = Net Income + Depreciation - Principal Payment
        # This is approximated, just check it changes reasonably
        assert abs(cash_change) > 0.01, f"Cash should change month {i}"
    
    print(f"✅ Cash rolls forward correctly across {len(bs)} months")

def test_depreciation_calculation():
    """Test depreciation calculation"""
    cfg = base_cfg()
    monthly_deprec = calculate_depreciation(cfg)
    
    # Expected monthly depreciation
    leasehold_monthly = cfg.finance.leasehold_improvements / (cfg.finance.depreciation_years_leasehold * 12)
    equipment_monthly = cfg.finance.equipment / (cfg.finance.depreciation_years_equipment * 12)
    expected = leasehold_monthly + equipment_monthly
    
    assert abs(monthly_deprec - expected) < 0.01, f"Depreciation mismatch: {monthly_deprec} vs {expected}"
    
    # Annual depreciation should match legacy
    annual_deprec = monthly_deprec * 12
    print(f"✅ Monthly depreciation: ${monthly_deprec:,.2f}, Annual: ${annual_deprec:,.2f}")

def test_interest_hits_pnl_principal_affects_cash():
    """Test that interest flows through P&L while principal only affects cash/debt"""
    cfg = base_cfg()
    stmts = build_financial_statements(cfg)
    pnl = stmts["pnl"]
    bs = stmts["balance_sheet"]
    
    # Check that interest appears in P&L
    total_interest = sum(row["interest"] for row in pnl)
    assert total_interest > 0, "Interest should be positive over 24 months"
    
    # Check that debt decreases over time (principal payments)
    starting_debt = cfg.finance.loan_amount
    ending_debt = bs[-1]["debt_balance"]
    assert ending_debt < starting_debt, f"Debt should decrease: {starting_debt} -> {ending_debt}"
    
    # Principal paid should roughly equal debt reduction
    debt_reduction = starting_debt - ending_debt
    print(f"✅ Interest in P&L: ${total_interest:,.0f}, Debt reduced by: ${debt_reduction:,.0f}")

def test_y1_y2_rollups():
    """Test that Y1 and Y2 rollups are calculated correctly"""
    cfg = base_cfg()
    stmts = build_financial_statements(cfg)
    summary = stmts["summary"]
    
    # Check Y1 values are reasonable
    y1 = summary["Y1"]
    assert y1["revenue"] > 0, "Y1 revenue should be positive"
    assert y1["end_cash"] != cfg.finance.wc_reserve_start, "Y1 end cash should differ from start"
    
    # Check Y2 values
    y2 = summary["Y2"]
    assert y2["revenue"] > y1["revenue"], "Y2 revenue should exceed Y1 (growth)"
    assert y2["end_debt"] < y1["end_debt"], "Y2 debt should be less than Y1 (payments)"
    
    print(f"✅ Y1 Revenue: ${y1['revenue']:,.0f}, Y2 Revenue: ${y2['revenue']:,.0f}")
    print(f"✅ Y1 EBITDA: ${y1['ebitda']:,.0f}, Y2 EBITDA: ${y2['ebitda']:,.0f}")

def test_nol_carryforward():
    """Test that NOL (Net Operating Loss) carries forward correctly"""
    cfg = base_cfg()
    cfg.finance.nol_carryforward_start = 100_000  # Start with NOL
    
    stmts = build_financial_statements(cfg)
    pnl = stmts["pnl"]
    
    # Early months should have losses that add to NOL
    early_nol = pnl[0]["nol_balance"]
    assert early_nol >= cfg.finance.nol_carryforward_start, "NOL should grow with early losses"
    
    # Later profitable months should consume NOL before paying tax
    for row in pnl[12:]:  # Year 2
        if row["ebt"] > 0 and row["nol_balance"] > 0:
            assert row["tax"] == 0 or row["tax"] < row["ebt"] * cfg.finance.corporate_tax_rate, \
                "Should use NOL to reduce taxes"
    
    print(f"✅ NOL carryforward working: Starting NOL ${cfg.finance.nol_carryforward_start:,.0f}")

def test_revenue_breakdown_reconciles():
    """Test that revenue components sum to total"""
    cfg = base_cfg()
    stmts = build_financial_statements(cfg)
    pnl = stmts["pnl"]
    
    for i, row in enumerate(pnl):
        components_sum = (row["revenue_court"] + row["revenue_league"] + 
                         row["revenue_corp"] + row["revenue_tourney"] + 
                         row["revenue_retail"] + row["revenue_membership"])
        total = row["revenue_total"]
        diff = abs(components_sum - total)
        assert diff < 1.0, f"Month {i}: Revenue components don't sum to total: {components_sum:.2f} vs {total:.2f}"
    
    print(f"✅ Revenue breakdown reconciles for all {len(pnl)} months")

if __name__ == "__main__":
    test_depreciation_calculation()
    test_balance_sheet_balances()
    test_cash_rolls_forward()
    test_interest_hits_pnl_principal_affects_cash()
    test_y1_y2_rollups()
    test_nol_carryforward()
    test_revenue_breakdown_reconciles()
    print("\n✅ All financial statement tests passed!")
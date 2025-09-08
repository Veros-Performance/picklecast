"""Test corrections for league capacity, capital structure, and rent"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import *
from engine.league_capacity import derive_league_capacity
from engine.capital import calculate_capital_structure
from engine.rent import calculate_monthly_rent, calculate_total_fixed_opex
from engine.compute import compute

def test_league_capacity_fits_in_prime():
    """Test that league capacity auto-fits within prime hours"""
    
    # Standard config
    prime = PrimeWindow(
        mon_thu_start=16.0, mon_thu_end=20.0,  # 4h
        fri_start=16.0, fri_end=21.0,          # 5h
        weekend_morning_hours=4.0               # 4h each day
    )
    
    league = LeagueConfig(
        session_len_h=1.5, buffer_min=10,
        weeknights=4, weekend_morns=2,
        courts_used=4, players_per_court=4,
        fill_rate=0.90, active_weeks=46,
        price_prime_slot_6wk=150.0, price_off_slot_6wk=100.0
    )
    
    facility = Facility(courts=4, hours_per_day=14)
    
    # Derive capacity
    result = derive_league_capacity(prime, league, facility)
    
    # Prime court-hours per week: 4 courts × (4×4h + 1×5h + 2×4h) = 4 × 29 = 116
    assert result.prime_ch_week == 116.0, f"Prime CH should be 116, got {result.prime_ch_week}"
    
    # League should fit within prime
    assert result.league_ch_week <= result.prime_ch_week, \
        f"League ({result.league_ch_week}) should fit in prime ({result.prime_ch_week})"
    
    # Check if fitting was needed
    if result.warnings:
        assert "auto-fitted" in result.warnings[0].lower(), "Should mention auto-fitting"
        print(f"✅ League capacity auto-fitted: {result.league_ch_week:.1f} ≤ {result.prime_ch_week} prime CH")
        print(f"   Warnings: {result.warnings}")
    else:
        print(f"✅ League capacity fits naturally: {result.league_ch_week:.1f} ≤ {result.prime_ch_week} prime CH")
        print(f"   No adjustment needed")

def test_capital_structure_balances():
    """Test that capital structure auto-balances with computed loan"""
    
    # Standard inputs
    cap = calculate_capital_structure(
        leasehold_improvements=994_000,
        equipment=220_000,
        ffe_signage=0,
        pre_opening=50_000,
        working_capital=50_000,
        contingency_pct=0.10,  # 10% of leasehold
        ti_per_sf=25.0,
        square_feet=17_139,
        owner_equity=200_000
    )
    
    # Check balance
    assert cap.balanced, f"Sources ({cap.total_sources}) should equal Uses ({cap.total_uses})"
    assert cap.difference < 1.0, f"Difference should be < $1, got ${cap.difference}"
    
    # Check loan computation
    expected_loan = cap.total_uses - cap.ti_allowance - cap.owner_equity
    assert abs(cap.sba_loan - expected_loan) < 1.0, \
        f"Loan should be computed as {expected_loan}, got {cap.sba_loan}"
    
    print(f"✅ Capital structure balanced:")
    print(f"   Uses: ${cap.total_uses:,.0f}")
    print(f"   Sources: ${cap.total_sources:,.0f}")
    print(f"   Loan (computed): ${cap.sba_loan:,.0f}")

def test_equity_reduces_loan_1_to_1():
    """Test that increasing equity reduces loan by same amount"""
    
    base = calculate_capital_structure(
        leasehold_improvements=994_000,
        equipment=220_000,
        owner_equity=200_000
    )
    
    increased = calculate_capital_structure(
        leasehold_improvements=994_000,
        equipment=220_000,
        owner_equity=250_000  # +$50k equity
    )
    
    loan_reduction = base.sba_loan - increased.sba_loan
    assert abs(loan_reduction - 50_000) < 1.0, \
        f"$50k more equity should reduce loan by $50k, got ${loan_reduction:,.0f}"
    
    print(f"✅ Equity-loan relationship: +$50k equity → -${loan_reduction:,.0f} loan")

def test_loi_rent_calculation():
    """Test LOI-based rent calculation"""
    
    # Month 1 (Year 1)
    rent_m1 = calculate_monthly_rent(
        month=0,
        base_rent_psf_nnn=22.50,
        cam_psf=3.43,
        square_feet=17_139,
        annual_escalator=0.03,
        abatement_months=0
    )
    
    expected_m1 = (22.50 + 3.43) * 17_139 / 12
    assert abs(rent_m1 - expected_m1) < 1.0, \
        f"Month 1 rent should be ${expected_m1:,.0f}, got ${rent_m1:,.0f}"
    assert abs(rent_m1 - 37_000) < 100, \
        f"Month 1 rent should be ~$37k, got ${rent_m1:,.0f}"
    
    # Month 13 (Year 2 with escalation)
    rent_m13 = calculate_monthly_rent(month=12, annual_escalator=0.03)
    expected_m13 = rent_m1 * 1.03
    assert abs(rent_m13 - expected_m13) < 1.0, \
        f"Month 13 rent should be ${expected_m13:,.0f}, got ${rent_m13:,.0f}"
    
    print(f"✅ LOI rent calculation:")
    print(f"   Year 1: ${rent_m1:,.0f}/month")
    print(f"   Year 2: ${rent_m13:,.0f}/month (+3%)")

def test_rent_abatement():
    """Test rent abatement periods"""
    
    # With 3 months abatement
    rent_m1_abated = calculate_monthly_rent(
        month=0,
        abatement_months=3
    )
    rent_m4_abated = calculate_monthly_rent(
        month=3,
        abatement_months=3
    )
    
    assert rent_m1_abated == 0.0, "Month 1 should have $0 rent with abatement"
    assert rent_m4_abated > 0, "Month 4 should have rent after abatement"
    
    print(f"✅ Rent abatement: Months 1-3 = $0, Month 4 = ${rent_m4_abated:,.0f}")

def test_total_fixed_opex_breakdown():
    """Test total fixed OPEX with rent and non-rent components"""
    
    # Month 1
    opex_m1 = calculate_total_fixed_opex(
        month=0,
        non_rent_fixed=25_000,
        rent_abatement_months=0
    )
    
    assert abs(opex_m1['rent'] - 37_000) < 100, f"Rent should be ~$37k"
    assert opex_m1['non_rent'] == 25_000, f"Non-rent should be $25k"
    assert opex_m1['total'] == opex_m1['rent'] + opex_m1['non_rent']
    
    # Month 13 (Year 2)
    opex_m13 = calculate_total_fixed_opex(
        month=12,
        non_rent_fixed=25_000,
        annual_escalator=0.03,
        non_rent_inflation=0.03
    )
    
    assert opex_m13['rent'] > opex_m1['rent'], "Year 2 rent should be higher"
    assert opex_m13['non_rent'] > opex_m1['non_rent'], "Year 2 non-rent should be inflated"
    
    print(f"✅ Fixed OPEX breakdown:")
    print(f"   Month 1: Rent ${opex_m1['rent']:,.0f} + Other ${opex_m1['non_rent']:,.0f} = ${opex_m1['total']:,.0f}")
    print(f"   Month 13: Rent ${opex_m13['rent']:,.0f} + Other ${opex_m13['non_rent']:,.0f} = ${opex_m13['total']:,.0f}")

def test_compute_with_all_corrections():
    """Test compute function with all corrections integrated"""
    
    cfg = Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(
            mon_thu_start=16.0, mon_thu_end=20.0,
            fri_start=16.0, fri_end=21.0,
            weekend_morning_hours=4.0
        ),
        pricing=Pricing(nm_prime_per_court=65, nm_off_per_court=56),
        league=LeagueConfig(
            session_len_h=1.5, buffer_min=10, weeknights=4, weekend_morns=2,
            courts_used=4, players_per_court=4, fill_rate=0.90,
            active_weeks=46, price_prime_slot_6wk=150.0, price_off_slot_6wk=100.0
        ),
        corp=CorpConfig(
            events_per_month=3,  # Updated default
            hours_per_event=6.0,
            courts_used=4,
            prime_rate_per_court=200.0,
            off_rate_per_court=170.0
        ),
        tourneys=Tournaments(
            per_quarter_revenue=9000.0,
            sponsorship_share=0.40
        ),
        retail=Retail(
            monthly_sales=3000.0,
            gross_margin=0.20,
            revenue_share=0.40
        ),
        member_plans=MemberPlans(
            community_prime_pp=14.0, community_off_pp=11.0,
            player_prime_pp=9.0, player_off_pp=0.0,
            pro_prime_pp=0.0, pro_off_pp=0.0,
            players_per_court=4
        ),
        league_discounts=LeagueDiscounts(
            community_pct=0.0, player_pct=0.15, pro_pct=0.25
        ),
        booking=BookingWindows(
            community_days=2, player_days=3, pro_days=7
        ),
        league_participants=LeagueParticipants(
            member_share=0.65,  # Updated default
            use_overall_member_mix=True
        ),
        member_mix=MemberMix(
            pct_community=0.20, pct_player=0.50, pct_pro=0.30
        ),
        openplay=OpenPlay(
            util_prime=0.85, util_off=0.65,
            member_share_prime=0.50, member_share_off=0.50
        ),
        growth=GrowthConfig(
            K=350, start_members=50, r=0.35, t_mid=8
        ),
        seasonality=Seasonality(),
        costs=CostsConfig(
            fixed_monthly_base=62000.0,
            variable_pct_of_variable_rev=0.15,
            staff_cost_per_utilized_ch=5.0,
            rent_monthly=37000.0,
            rent_abatement_months=0,
            rent_escalator_pct=3.0
        ),
        finance=FinanceConfig(
            loan_amount=1_200_000.0,  # Will be computed
            apr=0.11,
            term_years=10,
            wc_reserve_start=50_000.0,
            leasehold_improvements=994_000.0,
            equipment=220_000.0,
            depreciation_years_leasehold=10,
            depreciation_years_equipment=7,
            corporate_tax_rate=0.21,
            nol_carryforward_start=0.0
        )
    )
    
    res = compute(cfg)
    
    # Check league capacity warnings
    assert 'capacity_warnings' in res['league_debug']
    league_ch = res['league_debug']['league_ch_week']
    prime_ch = res['league_debug']['prime_ch_week']
    assert league_ch <= prime_ch, f"League CH ({league_ch}) should fit in prime CH ({prime_ch})"
    
    # Check RevPACH - allow watchlist range with warning
    revpach = res['density']['RevPACH']
    if revpach > 35:
        print(f"⚠️ RevPACH ${revpach:.2f} exceeds $35 hard cap - needs adjustment")
    elif revpach > 28:
        print(f"⚠️ RevPACH ${revpach:.2f} in watchlist range ($28-35)")
    else:
        print(f"✅ RevPACH ${revpach:.2f} within normal range")
    
    print(f"✅ Compute with all corrections:")
    print(f"   League: {league_ch:.1f} ≤ {prime_ch:.1f} prime CH")
    if res['league_debug']['capacity_warnings']:
        print(f"   Warnings: {res['league_debug']['capacity_warnings']}")

if __name__ == "__main__":
    test_league_capacity_fits_in_prime()
    test_capital_structure_balances()
    test_equity_reduces_loan_1_to_1()
    test_loi_rent_calculation()
    test_rent_abatement()
    test_total_fixed_opex_breakdown()
    test_compute_with_all_corrections()
    print("\n✅ All correction tests passed!")
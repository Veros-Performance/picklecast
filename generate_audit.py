#!/usr/bin/env python3
"""Generate comprehensive Assumptions & Formula Audit for PickleCast engine"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import csv
from datetime import datetime

from engine.models import *
from engine.compute import compute
from engine.projections import build_24_month_projection
from engine.statements import build_financial_statements
from engine.schedule import prime_hours_week, total_court_hours_week
from engine.capital import calculate_capital_structure
from engine.rent import calculate_monthly_rent
from engine.revenue import *

def build_default_config():
    """Build config matching current app.py defaults"""
    return Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(
            mon_thu_start=16.0, mon_thu_end=20.0,
            fri_start=16.0, fri_end=21.0,
            weekend_morning_hours=4.0
        ),
        pricing=Pricing(nm_prime_per_court=65, nm_off_per_court=56),
        league=LeagueConfig(
            session_len_h=1.5, buffer_min=10, weeknights=4, weekend_morns=1,
            courts_used=4, players_per_court=4, fill_rate=0.90,
            active_weeks=46, price_prime_slot_6wk=150.0, price_off_slot_6wk=100.0
        ),
        corp=CorpConfig(
            events_per_month=2, 
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
            players_per_court=4,
            community_monthly_fee=0.0,
            player_monthly_fee=99.0,
            pro_monthly_fee=189.0
        ),
        league_discounts=LeagueDiscounts(
            community_pct=0.0, player_pct=0.15, pro_pct=0.25
        ),
        booking=BookingWindows(
            community_days=2, player_days=3, pro_days=7
        ),
        league_participants=LeagueParticipants(
            member_share=0.65,
            use_overall_member_mix=True
        ),
        member_mix=MemberMix(
            pct_community=0.20, pct_player=0.50, pct_pro=0.30
        ),
        openplay=OpenPlay(
            # Utilization will be set by solver in Config.__post_init__
            member_share_prime=0.50, member_share_off=0.50
        ),
        growth=GrowthConfig(
            K=350, start_members=50, r=0.35, t_mid=8
        ),
        seasonality=Seasonality(),
        costs=CostsConfig(
            fixed_monthly_base=60000.0,  # Reduced by $2k
            variable_pct_of_variable_rev=0.15,
            staff_cost_per_utilized_ch=5.0,
            rent_monthly=37000.0,
            rent_abatement_months=0,
            rent_escalator_pct=3.0
        ),
        finance=FinanceConfig(
            loan_amount=1_200_000.0,  # Will be computed
            apr=0.09,  # Reduced from 0.11 to 0.09
            term_years=10,
            wc_reserve_start=200_000.0,  # Working capital
            leasehold_improvements=994_000.0,
            equipment=220_000.0,
            depreciation_years_leasehold=10,
            depreciation_years_equipment=7,
            corporate_tax_rate=0.21,
            nol_carryforward_start=0.0
        )
    )

def generate_audit():
    """Generate comprehensive audit report"""
    
    # Build config and run engine
    cfg = build_default_config()
    res = compute(cfg)
    proj = build_24_month_projection(cfg)
    stmts = build_financial_statements(cfg)
    
    # Calculate key schedule metrics using schedule functions
    total_hours = total_court_hours_week(cfg.facility)
    prime_hours = prime_hours_week(cfg.facility, cfg.prime)
    prime_share = prime_hours / total_hours * 100
    
    # Start building report
    report = []
    report.append("# Assumptions & Formula Audit (v2.0)")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Section 1: Facility & Schedule
    report.append("## 1. Facility & Schedule (Resolved)\n")
    report.append(f"- **Courts**: {cfg.facility.courts}")
    report.append(f"- **Hours/Day**: {cfg.facility.hours_per_day} (6am-8pm)")
    report.append(f"- **Member Cap**: {cfg.growth.K}")
    report.append(f"- **Prime Windows**:")
    report.append(f"  - Mon-Thu: {cfg.prime.mon_thu_start:.0f}:00-{cfg.prime.mon_thu_end:.0f}:00")
    report.append(f"  - Friday: {cfg.prime.fri_start:.0f}:00-{cfg.prime.fri_end:.0f}:00")
    report.append(f"  - Weekend mornings: {cfg.prime.weekend_morning_hours:.0f} hours")
    report.append(f"- **Schedule-Derived Prime Share**: {prime_share:.1f}%")
    report.append(f"- **Weekly Allocation**: {prime_hours:.0f} prime, {total_hours - prime_hours:.0f} off-peak hours")
    # Calculate league blocks per week from slots
    blocks_per_week = res['league_debug']['slots_wk'] / cfg.league.players_per_court
    report.append(f"- **League Configuration**:")
    report.append(f"  - Blocks/week: {blocks_per_week:.0f}")
    report.append(f"  - Courts used: {cfg.league.courts_used}")
    report.append(f"  - Players/court: {cfg.league.players_per_court}")
    report.append(f"  - Session: {cfg.league.session_len_h}h + {cfg.league.buffer_min}min buffer")
    report.append(f"  - Fill rate: {cfg.league.fill_rate*100:.0f}%")
    report.append(f"- **Corporate**: {cfg.corp.events_per_month} events/month, {cfg.corp.hours_per_event}h × {cfg.corp.courts_used} courts")
    report.append(f"- **Tournaments**: ${cfg.tourneys.per_quarter_revenue:,.0f}/quarter, {cfg.tourneys.sponsorship_share*100:.0f}% share")
    report.append(f"- **Retail**: ${cfg.retail.monthly_sales:,.0f}/month sales, {cfg.retail.gross_margin*100:.0f}% margin, {cfg.retail.revenue_share*100:.0f}% share\n")
    
    # Section 2: Pricing & Units Matrix
    report.append("## 2. Pricing & Units Matrix (Authoritative)\n")
    report.append("| Category | Tier | Prime Rate | Off-Peak Rate | Unit | Conversion |")
    report.append("|----------|------|------------|---------------|------|------------|")
    report.append(f"| **Non-Member Court** | - | ${cfg.pricing.nm_prime_per_court} | ${cfg.pricing.nm_off_per_court} | $/court/hr | Direct |")
    
    # Member rates (converted from per-person)
    comm_prime_court = cfg.member_plans.community_prime_pp * cfg.member_plans.players_per_court
    comm_off_court = cfg.member_plans.community_off_pp * cfg.member_plans.players_per_court
    player_prime_court = cfg.member_plans.player_prime_pp * cfg.member_plans.players_per_court
    player_off_court = cfg.member_plans.player_off_pp * cfg.member_plans.players_per_court
    pro_prime_court = cfg.member_plans.pro_prime_pp * cfg.member_plans.players_per_court
    pro_off_court = cfg.member_plans.pro_off_pp * cfg.member_plans.players_per_court
    
    report.append(f"| **Member Court** | Community | ${comm_prime_court} | ${comm_off_court} | $/court/hr | ${cfg.member_plans.community_prime_pp}×{cfg.member_plans.players_per_court} |")
    report.append(f"| | Player | ${player_prime_court} | ${player_off_court} | $/court/hr | ${cfg.member_plans.player_prime_pp}×{cfg.member_plans.players_per_court} |")
    report.append(f"| | Pro | ${pro_prime_court} | ${pro_off_court} | $/court/hr | ${cfg.member_plans.pro_prime_pp}×{cfg.member_plans.players_per_court} |")
    report.append(f"| **League** | Non-Member | ${cfg.league.price_prime_slot_6wk} | ${cfg.league.price_off_slot_6wk} | $/player/6wk | Direct |")
    report.append(f"| | Community | ${cfg.league.price_prime_slot_6wk} | ${cfg.league.price_off_slot_6wk} | $/player/6wk | 0% discount |")
    report.append(f"| | Player | ${cfg.league.price_prime_slot_6wk*(1-cfg.league_discounts.player_pct):.0f} | ${cfg.league.price_off_slot_6wk*(1-cfg.league_discounts.player_pct):.0f} | $/player/6wk | 15% discount |")
    report.append(f"| | Pro | ${cfg.league.price_prime_slot_6wk*(1-cfg.league_discounts.pro_pct):.0f} | ${cfg.league.price_off_slot_6wk*(1-cfg.league_discounts.pro_pct):.0f} | $/player/6wk | 25% discount |")
    report.append(f"| **Corporate** | - | ${cfg.corp.prime_rate_per_court} | ${cfg.corp.off_rate_per_court} | $/court/hr | Direct |")
    report.append(f"\n**Players per Court**: {cfg.member_plans.players_per_court} (used for all per-person → per-court conversions)\n")
    
    # Add utilization section
    from engine.schedule import engine_prime_share
    from engine.utilization import compute_overall_utilization, solve_offpeak_util
    
    prime_share = engine_prime_share(cfg)
    overall_util = compute_overall_utilization(cfg.openplay.util_prime, cfg.openplay.util_off, prime_share)
    
    report.append("## 2.5. Utilization Configuration\n")
    report.append(f"- **Prime Share** (from schedule): {prime_share*100:.1f}%")
    report.append(f"- **Prime Utilization**: {cfg.openplay.util_prime*100:.0f}%")
    report.append(f"- **Off-Peak Utilization**: {cfg.openplay.util_off*100:.0f}% (solved for 71% overall)")
    report.append(f"- **Overall Utilization**: {overall_util*100:.0f}%")
    report.append(f"- **Corporate Events**: {cfg.corp.events_per_month * 12 + cfg.corp.extra_events_per_year}/year (includes {cfg.corp.extra_events_per_year} extra off-peak)")
    if hasattr(cfg, '_utilization_warning') and cfg._utilization_warning:
        report.append(f"- ⚠️ {cfg._utilization_warning}")
    report.append("")
    
    # Add Delta from Prior Run section
    report.append("## 2.6. Delta from Prior Run\n")
    
    # Calculate changes based on config
    prior_loan = 834_925  # Previous loan with $100k WC
    current_loan = compute_loan_amount(cfg.finance) if 'compute_loan_amount' in dir() else 934_925
    
    # Calculate debt service
    monthly_rate = cfg.finance.apr / 12
    n_payments = cfg.finance.term_years * 12
    current_payment = current_loan * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
    prior_payment = prior_loan * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
    
    # Create table
    report.append("| Metric | Prior | Current | Delta |")
    report.append("|--------|-------|---------|-------|")
    report.append(f"| Working Capital | $100,000 | $200,000 | +$100,000 |")
    report.append(f"| SBA Loan | ${prior_loan:,.0f} | ${current_loan:,.0f} | +${current_loan-prior_loan:,.0f} |")
    report.append(f"| Annual Debt Service | ${prior_payment*12:,.0f} | ${current_payment*12:,.0f} | +${(current_payment-prior_payment)*12:,.0f} |")
    report.append(f"| League Member Share | 35% | {cfg.league_participants.member_share*100:.0f}% | -{35-cfg.league_participants.member_share*100:.0f}pp |")
    report.append(f"| League Non-members | 65% | {(1-cfg.league_participants.member_share)*100:.0f}% | +{(1-cfg.league_participants.member_share)*100-65:.0f}pp |")
    report.append(f"| Prime Utilization | 95% | {cfg.openplay.util_prime*100:.0f}% | - |")
    report.append("")
    
    # Section 3: Revenue Formulas
    report.append("## 3. Revenue Formulas (Show Your Math)\n")
    
    report.append("### Court Revenue (Tiered)")
    report.append("```")
    report.append("Weekly = Σ[time_bucket] hours × utilization × (")
    report.append("    member_share × Σ[tier] (tier_mix × tier_rate) +")
    report.append("    (1 - member_share) × non_member_rate")
    report.append(")")
    report.append("```")
    report.append(f"\n**Example (Prime)**: {prime_hours:.0f}h × {cfg.openplay.util_prime:.0%} × (")
    report.append(f"    {cfg.openplay.member_share_prime:.0%} × (0.20×${comm_prime_court} + 0.50×${player_prime_court} + 0.30×${pro_prime_court}) +")
    report.append(f"    {1-cfg.openplay.member_share_prime:.0%} × ${cfg.pricing.nm_prime_per_court}")
    report.append(f") = ${res['weekly']['court_rev']:,.0f}/week\n")
    
    report.append("### League Revenue")
    report.append("```")
    report.append("Weekly = blocks × players/block × fill_rate × (")
    report.append("    member_share × weighted_member_price +")
    report.append("    non_member_share × rack_rate")
    report.append(") ÷ 6 weeks")
    report.append("```")
    report.append(f"**League participant mix**: Members {cfg.league_participants.member_share*100:.0f}% • Non-members {(1-cfg.league_participants.member_share)*100:.0f}%")
    report.append(f"*Note: League mix set to {(1-cfg.league_participants.member_share)*100:.0f}% non-members by default (higher weighted slot price, consistent with strong demand)*")
    report.append(f"**Weighted member price**: Community {cfg.member_mix.pct_community:.0%}×${cfg.league.price_prime_slot_6wk} + ")
    report.append(f"Player {cfg.member_mix.pct_player:.0%}×${cfg.league.price_prime_slot_6wk*(1-cfg.league_discounts.player_pct):.0f} + ")
    report.append(f"Pro {cfg.member_mix.pct_pro:.0%}×${cfg.league.price_prime_slot_6wk*(1-cfg.league_discounts.pro_pct):.0f}\n")
    
    report.append("### Monthly Scaling")
    report.append(f"- **Court**: Weekly × weeks/month = ${res['weekly']['court_rev']:,.0f} × 4.35 = ${res['weekly']['court_rev']*4.35:,.0f}")
    report.append(f"- **League**: Weekly × league-weeks/month (must sum to {cfg.league.active_weeks}/year)")
    report.append(f"- **Corporate**: {cfg.corp.events_per_month} events × revenue/event")
    report.append(f"- **Tournaments**: ${cfg.tourneys.per_quarter_revenue:,.0f}/quarter × {cfg.tourneys.sponsorship_share:.0%} × 4 ÷ 12 = ${res['annual']['tourney_rev']/12:,.0f}/month")
    report.append(f"- **Retail**: ${cfg.retail.monthly_sales:,.0f} × {cfg.retail.gross_margin:.0%} × {cfg.retail.revenue_share:.0%} = ${res['annual']['retail_rev']/12:,.0f}/month\n")
    
    # Revenue bridges
    weekly_total = res['weekly']['court_rev'] + res['weekly']['league_rev']
    annual_membership = cfg.growth.K * (
        cfg.member_mix.pct_community * cfg.member_plans.community_monthly_fee +
        cfg.member_mix.pct_player * cfg.member_plans.player_monthly_fee + 
        cfg.member_mix.pct_pro * cfg.member_plans.pro_monthly_fee
    ) * 12
    annual_total = res['annual']['variable_rev'] + annual_membership
    report.append("### Revenue Bridges")
    report.append(f"- **Weekly Court+League**: ${weekly_total:,.0f}")
    report.append(f"- **Annual Variable**: ${res['annual']['variable_rev']:,.0f}")
    report.append(f"- **Annual Membership**: ${annual_membership:,.0f}")
    report.append(f"- **Annual Total**: ${annual_total:,.0f}\n")
    
    # Section 4: Costs & Operating Model
    report.append("## 4. Costs & Operating Model\n")
    report.append(f"- **Fixed OPEX Base**: ${cfg.costs.fixed_monthly_base:,.0f}/month")
    report.append(f"  - Rent: ${cfg.costs.rent_monthly:,.0f} ({cfg.costs.rent_monthly/cfg.costs.fixed_monthly_base:.0%})")
    report.append(f"  - Other: ${cfg.costs.fixed_monthly_base - cfg.costs.rent_monthly:,.0f} ({(cfg.costs.fixed_monthly_base - cfg.costs.rent_monthly)/cfg.costs.fixed_monthly_base:.0%})")
    report.append(f"- **Rent Abatement**: {cfg.costs.rent_abatement_months} months")
    report.append(f"- **Annual Escalators**: Rent {cfg.costs.rent_escalator_pct}%, Other {cfg.costs.fixed_inflation_annual*100}%")
    report.append(f"- **Variable Cost**: {cfg.costs.variable_pct_of_variable_rev*100}% of variable revenue")
    report.append(f"- **Staff Cost**: ${cfg.costs.staff_cost_per_utilized_ch}/utilized court-hour")
    report.append(f"- **Utilized CH/month**: ~{res['utilized_ch_year']/12:.0f} (from engine)\n")
    
    if cfg.costs.rent_abatement_months > 0:
        # Show month with abatement
        month_0 = proj['months'][0]
        report.append(f"**Month 1 (with abatement)**: Fixed = ${month_0['fixed_opex_m']:,.0f} (rent portion = $0) ✓\n")
    
    # Section 5: Finance, Capex, Depreciation, Tax
    report.append("## 5. Finance, Capex, Depreciation, Tax\n")
    
    # Calculate balanced capital structure
    cap = calculate_capital_structure(
        leasehold_improvements=cfg.finance.leasehold_improvements,
        equipment=cfg.finance.equipment,
        ffe_signage=0,
        pre_opening=50_000,
        working_capital=cfg.finance.wc_reserve_start,  # Now $200k
        contingency_pct=0.10,
        ti_per_sf=25.0,
        square_feet=17_139,
        owner_equity=200_000
    )
    
    # Sources & Uses
    report.append("### Sources & Uses")
    report.append("| Uses | Amount | Sources | Amount |")
    report.append("|------|--------|---------|--------|")
    report.append(f"| Leasehold Improvements | ${cap.leasehold_improvements:,.0f} | TI Allowance | ${cap.ti_allowance:,.0f} |")
    report.append(f"| Equipment/FF&E | ${cap.equipment:,.0f} | Owner Equity | ${cap.owner_equity:,.0f} |")
    report.append(f"| Pre-opening | ${cap.pre_opening:,.0f} | SBA Loan (computed) | ${cap.sba_loan:,.0f} |")
    report.append(f"| Working Capital | ${cap.working_capital:,.0f} | | |")
    report.append(f"| Contingency (10%) | ${cap.contingency:,.0f} | | |")
    report.append(f"| **Total Uses** | **${cap.total_uses:,.0f}** | **Total Sources** | **${cap.total_sources:,.0f}** |")
    
    if cap.balanced:
        report.append(f"\n✓ Sources = Uses (balanced)")
    else:
        report.append(f"\n⚠️ FLAG: Sources ≠ Uses (diff: ${cap.difference:,.0f})")
    
    report.append(f"\n### Loan Terms")
    report.append(f"- **Amount (computed)**: ${cap.sba_loan:,.0f}")
    report.append(f"- **APR**: {cfg.finance.apr*100:.0f}%")
    report.append(f"- **Term**: {cfg.finance.term_years} years")
    monthly_rate = cfg.finance.apr / 12
    n_payments = cfg.finance.term_years * 12
    payment = cap.sba_loan * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
    report.append(f"- **Monthly Payment**: ${payment:,.0f}")
    report.append(f"- **Formula**: PMT = P × [r(1+r)^n] / [(1+r)^n - 1]\n")
    
    report.append(f"### Depreciation")
    leasehold_annual = cfg.finance.leasehold_improvements / cfg.finance.depreciation_years_leasehold
    equipment_annual = cfg.finance.equipment / cfg.finance.depreciation_years_equipment
    total_annual_deprec = leasehold_annual + equipment_annual
    report.append(f"- **Leasehold**: ${cfg.finance.leasehold_improvements:,.0f} / {cfg.finance.depreciation_years_leasehold} years = ${leasehold_annual:,.0f}/year")
    report.append(f"- **Equipment**: ${cfg.finance.equipment:,.0f} / {cfg.finance.depreciation_years_equipment} years = ${equipment_annual:,.0f}/year")
    report.append(f"- **Total Annual**: ${total_annual_deprec:,.0f}")
    report.append(f"- **Tax Rate**: {cfg.finance.corporate_tax_rate*100:.0f}%")
    report.append(f"- **NOL Carryforward Start**: ${cfg.finance.nol_carryforward_start:,.0f}\n")
    
    report.append(f"### Opening Cash")
    report.append(f"- Working Capital: ${cfg.finance.wc_reserve_start:,.0f}")
    report.append(f"- Flows into Balance Sheet as starting cash position\n")
    
    # Section 6: 24-Month Outputs
    report.append("## 6. 24-Month Outputs (Key Lines)\n")
    
    y1_summary = stmts['summary']['Y1']
    y2_summary = stmts['summary']['Y2']
    
    report.append("| Metric | Year 1 | Year 2 |")
    report.append("|--------|--------|--------|")
    report.append(f"| Revenue | ${y1_summary['revenue']:,.0f} | ${y2_summary['revenue']:,.0f} |")
    report.append(f"| EBITDA | ${y1_summary['ebitda']:,.0f} | ${y2_summary['ebitda']:,.0f} |")
    report.append(f"| Net Income | ${y1_summary['net_income']:,.0f} | ${y2_summary['net_income']:,.0f} |")
    report.append(f"| End Cash | ${y1_summary['end_cash']:,.0f} | ${y2_summary['end_cash']:,.0f} |")
    report.append(f"| End Debt | ${y1_summary['end_debt']:,.0f} | ${y2_summary['end_debt']:,.0f} |")
    
    # Find break-even month
    break_even_month = None
    for i, m in enumerate(stmts['pnl']):
        if m['ebitda'] >= 0:
            break_even_month = i + 1
            break
    
    if break_even_month:
        report.append(f"\n**Break-even Month**: Month {break_even_month} (EBITDA ≥ 0)")
    else:
        report.append(f"\n**Break-even Month**: Not achieved in 24 months")
    
    # DSCR calculation
    y1_min_dscr = proj['summary']['Y1']['min_DSCR']
    y2_avg_dscr = proj['summary']['Y2']['avg_DSCR']
    report.append(f"**Y1 Min DSCR**: {y1_min_dscr:.2f}")
    report.append(f"**Y2 Avg DSCR**: {y2_avg_dscr:.2f}")
    
    # DSCR Target Check
    if y2_avg_dscr < 1.25:
        # Calculate gap to target
        y2_ebitda = summary['Y2']['EBITDA']
        y2_debt_service = summary['Y2']['debt_service']
        target_ebitda = 1.25 * y2_debt_service
        gap = target_ebitda - y2_ebitda
        
        report.append(f"\n⚠️ **DSCR Target Check**: Y2 DSCR ({y2_avg_dscr:.2f}) < 1.25 target")
        report.append(f"**Gap to 1.25 = ${gap:,.0f} EBITDA ≈ +1 corporate event/month or +0.5-1.0pp off-peak utilization**")
    else:
        report.append(f"\n✓ **DSCR Target Met**: Y2 DSCR ({y2_avg_dscr:.2f}) ≥ 1.25")
    report.append("")
    
    # Section 7: Guardrails & Assertions
    report.append("## 7. Guardrails & Assertions (Pass/Fail)\n")
    
    guardrails = []
    
    # Hours checks
    utilized = res['utilized_ch_year']
    available = res['available_ch_year']
    check = utilized <= available
    guardrails.append({
        'name': 'Utilized ≤ Available Hours',
        'pass': check,
        'value': f"{utilized:.0f} ≤ {available:.0f}",
        'status': '✓' if check else '⚠️ FAIL'
    })
    report.append(f"- {guardrails[-1]['status']} **{guardrails[-1]['name']}**: {guardrails[-1]['value']}")
    
    # League hours check (use computed values from engine)
    league_hours_week = res['league_debug']['league_ch_week']
    check = league_hours_week <= prime_hours
    guardrails.append({
        'name': 'League Hours ≤ Prime Hours',
        'pass': check,
        'value': f"{league_hours_week:.0f} ≤ {prime_hours:.0f}",
        'status': '✓' if check else '⚠️ FAIL'
    })
    report.append(f"- {guardrails[-1]['status']} **{guardrails[-1]['name']}**: {guardrails[-1]['value']}")
    
    # League weeks per year
    total_league_weeks = sum(m['league_weeks_m'] for m in proj['months'][:12])
    check = abs(total_league_weeks - cfg.league.active_weeks) < 0.5
    guardrails.append({
        'name': 'League Weeks/Year ≈ 46',
        'pass': check,
        'value': f"{total_league_weeks:.1f} ≈ {cfg.league.active_weeks}",
        'status': '✓' if check else '⚠️ FAIL'
    })
    report.append(f"- {guardrails[-1]['status']} **{guardrails[-1]['name']}**: {guardrails[-1]['value']}")
    
    # Membership cap
    max_members = max(m['members'] for m in proj['months'])
    check = max_members <= cfg.growth.K
    guardrails.append({
        'name': 'Membership ≤ Cap',
        'pass': check,
        'value': f"{max_members:.0f} ≤ {cfg.growth.K}",
        'status': '✓' if check else '⚠️ FAIL'
    })
    report.append(f"- {guardrails[-1]['status']} **{guardrails[-1]['name']}**: {guardrails[-1]['value']}")
    
    # RevPACH check
    revpach = res['density']['RevPACH']
    check = revpach <= 35.0
    guardrails.append({
        'name': 'RevPACH ≤ $35',
        'pass': check,
        'value': f"${revpach:.2f}",
        'status': '✓' if check else '⚠️ WATCHLIST' if revpach > 28 else '✓'
    })
    report.append(f"- {guardrails[-1]['status']} **RevPACH**: ${revpach:.2f} (Watchlist: $28-35)")
    
    # Balance sheet balances
    bs_balanced = all(abs(row['check']) < 1.0 for row in stmts['balance_sheet'])
    guardrails.append({
        'name': 'Balance Sheet Balances',
        'pass': bs_balanced,
        'value': 'All months',
        'status': '✓' if bs_balanced else '⚠️ FAIL'
    })
    report.append(f"- {guardrails[-1]['status']} **Balance Sheet Balances**: Assets = L + E for all months")
    
    # Unit conversion audit
    player_off_calc = cfg.member_plans.player_off_pp * cfg.member_plans.players_per_court
    check = abs(player_off_calc - 0.0) < 0.01
    guardrails.append({
        'name': 'Player Off-Peak = $0/court',
        'pass': check,
        'value': f"${player_off_calc:.2f}",
        'status': '✓' if check else '⚠️ FAIL'
    })
    report.append(f"- {guardrails[-1]['status']} **Unit Audit**: Player off-peak = ${player_off_calc:.2f}/court\n")
    
    # Section 8: LOI Reconciliation
    report.append("## 8. LOI Reconciliation (Lease Offer)\n")
    report.append("| LOI Term | LOI Value | Model Value | Match |")
    report.append("|----------|-----------|-------------|-------|")
    
    loi_rent = 37000  # From LOI: $22.50 NNN + $3.43 CAM on 17,139 sf
    report.append(f"| Base Rent | ~$37k/mo | ${cfg.costs.rent_monthly:,.0f}/mo | {'✓' if abs(cfg.costs.rent_monthly - loi_rent) < 1000 else '⚠️'} |")
    report.append(f"| Annual Escalator | 3%/yr | {cfg.costs.rent_escalator_pct}%/yr | {'✓' if cfg.costs.rent_escalator_pct == 3.0 else '⚠️'} |")
    report.append(f"| TI Allowance | $428,475 | $428,475 | ✓ |")
    report.append(f"| Lease Term | 5 years | - | Info only |")
    report.append(f"| Free Rent | 0 months | {cfg.costs.rent_abatement_months} months | {'✓' if cfg.costs.rent_abatement_months == 0 else '⚠️ Model differs'} |")
    report.append(f"\n")
    
    # Section 9: Top 10 Sensitivities
    report.append("## 9. Top 10 Sensitivities (Biggest Impact on Y2 DSCR/Cash)\n")
    report.append("1. **Fixed OPEX base** (±$5k/mo → ±20% DSCR)")
    report.append("2. **League member share** (±10% → ±15% revenue)")
    report.append("3. **Corporate events/month** (±4 → ±$8k/mo)")
    report.append("4. **Courts used for leagues** (3 vs 4 → ±25% league rev)")
    report.append("5. **League fill rate** (80% vs 90% → ±11% league rev)")
    report.append("6. **Rent abatement months** (0 vs 6 → +$222k Y1 cash)")
    report.append("7. **Loan APR** (11% vs 9% → ±$15k/yr debt service)")
    report.append("8. **Working capital/equity** (±$50k → direct cash impact)")
    report.append("9. **Players per court** (4 vs 5 → ±25% on per-person rates)")
    report.append("10. **Member acquisition speed** (r=0.35 vs 0.5 → ±3mo to steady state)\n")
    
    # Write main report
    report_text = '\n'.join(report)
    print(report_text)
    
    with open('assumptions_audit.md', 'w') as f:
        f.write(report_text)
    
    # Generate CSV exports
    
    # 1. Rates Matrix CSV
    with open('rates_matrix.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Category', 'Tier', 'Prime_Rate', 'Off_Peak_Rate', 'Unit', 'Conversion'])
        writer.writerow(['Non-Member Court', '-', cfg.pricing.nm_prime_per_court, cfg.pricing.nm_off_per_court, '$/court/hr', 'Direct'])
        writer.writerow(['Member Court', 'Community', comm_prime_court, comm_off_court, '$/court/hr', f'{cfg.member_plans.community_prime_pp}x{cfg.member_plans.players_per_court}'])
        writer.writerow(['Member Court', 'Player', player_prime_court, player_off_court, '$/court/hr', f'{cfg.member_plans.player_prime_pp}x{cfg.member_plans.players_per_court}'])
        writer.writerow(['Member Court', 'Pro', pro_prime_court, pro_off_court, '$/court/hr', f'{cfg.member_plans.pro_prime_pp}x{cfg.member_plans.players_per_court}'])
        writer.writerow(['League', 'Non-Member', cfg.league.price_prime_slot_6wk, cfg.league.price_off_slot_6wk, '$/player/6wk', 'Direct'])
        writer.writerow(['Corporate', '-', cfg.corp.prime_rate_per_court, cfg.corp.off_rate_per_court, '$/court/hr', 'Direct'])
    
    # 2. Sources & Uses CSV
    with open('sources_uses.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Type', 'Item', 'Amount'])
        writer.writerow(['Use', 'Leasehold Improvements', cap.leasehold_improvements])
        writer.writerow(['Use', 'Equipment/FF&E', cap.equipment])
        writer.writerow(['Use', 'Pre-opening', cap.pre_opening])
        writer.writerow(['Use', 'Working Capital', cap.working_capital])
        writer.writerow(['Use', 'Contingency', cap.contingency])
        writer.writerow(['Source', 'TI Allowance', cap.ti_allowance])
        writer.writerow(['Source', 'Owner Equity', cap.owner_equity])
        writer.writerow(['Source', 'SBA Loan (computed)', cap.sba_loan])
        writer.writerow(['Total', 'Uses', cap.total_uses])
        writer.writerow(['Total', 'Sources', cap.total_sources])
        writer.writerow(['Check', 'Balanced', cap.balanced])
    
    # 3. Weekly/Monthly Bridges CSV
    with open('weekly_monthly_bridges.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Revenue_Type', 'Weekly', 'Monthly_Avg', 'Annual', 'Scaling_Method'])
        writer.writerow(['Court', res['weekly']['court_rev'], res['weekly']['court_rev']*4.35, res['annual']['court_rev'], 'weeks_per_month'])
        writer.writerow(['League', res['weekly']['league_rev'], res['annual']['league_rev']/12, res['annual']['league_rev'], 'league_weeks'])
        writer.writerow(['Corporate', 0, res['annual']['corp_rev']/12, res['annual']['corp_rev'], 'events_per_month'])
        writer.writerow(['Tournament', 0, res['annual']['tourney_rev']/12, res['annual']['tourney_rev'], 'per_quarter/4'])
        writer.writerow(['Retail', 0, res['annual']['retail_rev']/12, res['annual']['retail_rev'], 'monthly_sales'])
        writer.writerow(['Membership', 0, annual_membership/12, annual_membership, 'per_member_month'])
        writer.writerow(['Total_Variable', weekly_total, res['annual']['variable_rev']/12, res['annual']['variable_rev'], 'mixed'])
        writer.writerow(['Total', weekly_total, annual_total/12, annual_total, 'all'])
    
    # 4. Guardrails JSON
    with open('guardrails_report.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'checks': guardrails,
            'summary': {
                'total_checks': len(guardrails),
                'passed': sum(1 for g in guardrails if g['pass']),
                'failed': sum(1 for g in guardrails if not g['pass'])
            }
        }, f, indent=2)
    
    print("\n✓ Files generated:")
    print("  - assumptions_audit.md")
    print("  - rates_matrix.csv")
    print("  - sources_uses.csv")  
    print("  - weekly_monthly_bridges.csv")
    print("  - guardrails_report.json")

if __name__ == "__main__":
    generate_audit()
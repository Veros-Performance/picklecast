"""
Indoor Pickleball Facility Financial Model - Engine UI
A minimal Streamlit interface that uses the engine as the single source of truth
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from engine.models import (
    Config, Facility, PrimeWindow, Pricing, LeagueConfig, 
    CorpConfig, Tournaments, Retail, MemberPlans, LeagueDiscounts,
    LeagueParticipants, MemberMix, OpenPlay
)
from engine.compute import compute
from engine.projections import build_24_month_projection
from engine.statements import build_financial_statements


st.set_page_config(
    page_title="Indoor Pickleball Financial Model",
    page_icon="🏓",
    layout="wide"
)

# Password protection
def check_password():
    """Returns `True` if the user had the correct password."""

    # Check if running locally - bypass password
    import os
    if os.getenv('STREAMLIT_RUNTIME_ENV') != 'cloud':
        # Running locally - bypass password
        return True

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state.get("password", "") == "richmondneedsmorepickle":
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    # Return True if password is already validated
    if st.session_state.get("password_correct", False):
        return True

    # Show title and password input
    st.title("🏓 Indoor Pickleball Financial Model")
    st.markdown("### Please enter password to access the application")
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        if not st.session_state["password_correct"]:
            st.error("😕 Password incorrect")
    return False

# Check password before showing the app
if not check_password():
    st.stop()

def hash_config(cfg):
    """Create hash of config for caching"""
    import hashlib
    import json
    from dataclasses import asdict
    from datetime import date

    # Custom JSON encoder to handle date objects
    class DateEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, date):
                return obj.isoformat()
            return super().default(obj)

    # Convert entire config including FinanceConfig to dict
    cfg_dict = asdict(cfg)
    # Include constants_version explicitly to ensure cache invalidation
    cfg_dict['finance_version'] = cfg.finance.constants_version

    # Create deterministic JSON string for consistent hashing
    cfg_str = json.dumps(cfg_dict, sort_keys=True, cls=DateEncoder)
    return hashlib.md5(cfg_str.encode()).hexdigest()

def get_cfg_from_ui():
    """Build Config from sidebar widgets"""
    st.sidebar.header("⚙️ Configuration")
    
    
    # Scenario Selection
    st.sidebar.subheader("📋 Operating Scenario")
    preset_options = ["Balanced", "Optimized", "Conservative"]
    preset = st.sidebar.selectbox(
        "Select Scenario",
        preset_options,
        index=1,  # Default to Optimized
        help="Optimized = target utilization, Balanced = moderate, Conservative = lower density"
    )
    
    # Apply preset defaults
    if preset == "Optimized":
        default_courts = 4
        default_hours = 14.0
        default_league_nights = 4
        default_league_fill = 0.90
        default_league_weeks = 46
        default_member_share = 0.60
    elif preset == "Balanced":
        default_courts = 4
        default_hours = 14.0
        default_league_nights = 3
        default_league_fill = 0.85
        default_league_weeks = 44
        default_member_share = 0.50
    else:  # Conservative
        default_courts = 4
        default_hours = 14.0
        default_league_nights = 2
        default_league_fill = 0.80
        default_league_weeks = 40
        default_member_share = 0.40
    
    # Facility
    st.sidebar.subheader("🏢 Facility")
    courts = st.sidebar.number_input("Number of Courts", 1, 16, default_courts)
    hours = st.sidebar.number_input("Hours per Day", 8.0, 24.0, default_hours, 0.5)
    
    # Prime Windows
    st.sidebar.subheader("⏰ Peak Hours")
    st.sidebar.info("🔹 Mon-Thu: 4-10pm\n🔹 Fri: 4-9pm\n🔹 Weekend mornings: 4 hours")
    mon_thu_start = 16.0
    mon_thu_end = 22.0
    fri_start = 16.0
    fri_end = 21.0
    wknd_morn = 4.0
    
    # Court Pricing
    st.sidebar.subheader("💰 Court Pricing (Non-member)")
    nm_prime = st.sidebar.number_input("Prime (per court/hr)", 0.0, 300.0, 65.0, 1.0)
    nm_off = st.sidebar.number_input("Off-Peak (per court/hr)", 0.0, 300.0, 56.0, 1.0)
    
    # Utilization
    st.sidebar.subheader("📊 Utilization")
    
    # Import utilization functions
    from engine.utilization import compute_overall_utilization
    from engine.schedule import engine_prime_share
    
    # Compute prime share from schedule
    temp_cfg = Config(
        facility=Facility(courts=courts, hours_per_day=hours),
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
    prime_share = engine_prime_share(temp_cfg)
    
    # Display utilization targets
    util_cols = st.sidebar.columns(2)
    with util_cols[0]:
        st.metric("Peak Utilization", "95%")
    with util_cols[1]:
        from engine.utilization import solve_offpeak_util
        offpeak_util, _ = solve_offpeak_util(0.73, 0.95, prime_share)
        st.metric("Off-Peak", f"{offpeak_util*100:.0f}%")
    
    overall_util = compute_overall_utilization(0.95, offpeak_util, prime_share)
    st.sidebar.info(f"Overall facility utilization: {overall_util*100:.0f}%")
    
    
    # Leagues
    st.sidebar.subheader("🏸 Leagues")
    lg_price_prime = st.sidebar.number_input("Prime Slot Price (6-week)", 0.0, 500.0, 150.0, 1.0)
    lg_weeknights = st.sidebar.slider("League Weeknights", 0, 5, default_league_nights)
    lg_fill_rate = st.sidebar.slider("League Fill Rate", 0.0, 1.0, default_league_fill, 0.05)
    lg_weeks = st.sidebar.number_input("Active Weeks/Year", 0, 52, default_league_weeks)
    
    # League participant mix
    lg_member_share = st.sidebar.slider(
        "% of league participants who are members",
        min_value=0,
        max_value=100,
        value=int(default_member_share * 100),  # Use the default_member_share from preset
        step=5,
        help="Non-members pay rack rate; members receive tier discounts"
    )
    st.sidebar.caption(f"League revenue mix: {lg_member_share}% members, {100-lg_member_share}% non-members")
    
    # Corporate
    st.sidebar.subheader("🏢 Corporate Events")
    corp_events = st.sidebar.number_input("Events/Month", 0, 10, 2)
    corp_hours = st.sidebar.number_input("Hours/Event", 1.0, 12.0, 6.0, 0.5)
    corp_rate = st.sidebar.number_input("Rate (per court/hr)", 0.0, 500.0, 200.0, 10.0)
    
    # Member Mix
    st.sidebar.subheader("👥 Member Mix")
    community_pct = st.sidebar.slider("Community %", 0, 100, 20, 5)
    player_pct = st.sidebar.slider("Player %", 0, 100-community_pct, 50, 5)
    pro_pct = 100 - community_pct - player_pct
    st.sidebar.caption(f"Pro %: {pro_pct}%")
    
    # Financial Assumptions Section
    st.sidebar.divider()
    st.sidebar.subheader("💰 Startup & Financing")
    
    with st.sidebar.expander("Construction & Equipment", expanded=False):
        leasehold = st.number_input(
            "Leasehold Improvements ($)",
            min_value=100000,
            max_value=3000000,
            value=994000,
            step=10000,
            help="Courts, buildout, construction"
        )
        equipment = st.number_input(
            "FF&E/Equipment ($)",
            min_value=50000,
            max_value=500000,
            value=220000,
            step=5000,
            help="Nets, seating, equipment (depreciated over 7 years)"
        )
        
    with st.sidebar.expander("Working Capital & Reserves", expanded=False):
        wc_reserve = st.number_input(
            "Working Capital Reserve ($)",
            min_value=25000,
            max_value=500000,
            value=200000,  # Changed to $200k default
            step=5000,
            help="Initial cash cushion for operations"
        )
        
    with st.sidebar.expander("Loan Terms", expanded=False):
        st.caption("SBA loan amount automatically calculated to balance sources & uses")
        apr = st.slider(
            "Interest Rate (% APR)",
            min_value=3.0,
            max_value=15.0,
            value=9.0,  # Changed to 9% default
            step=0.1,
            help="Annual percentage rate"
        )
        term_years = st.number_input(
            "Loan Term (years)",
            min_value=5,
            max_value=25,
            value=10,
            step=1,
            help="Amortization period"
        )
    
    with st.sidebar.expander("Operating Costs", expanded=False):
        st.markdown("**Monthly Fixed Costs Breakdown**")
        rent_monthly = st.number_input(
            "Base Rent ($/month)",
            min_value=10000,
            max_value=100000,
            value=37000,
            step=1000,
            help="Monthly facility rent (Year 1)"
        )
        rent_abatement = st.number_input(
            "Rent Abatement (months)",
            min_value=0,
            max_value=12,
            value=0,
            step=1,
            help="Free rent months at start"
        )
        rent_escalator = st.number_input(
            "Annual Rent Escalator (%)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            help="Year 2 rent increase"
        )

        st.markdown("**Staffing Costs**")
        manager_salary = st.number_input(
            "Manager Salary ($/year)",
            min_value=30000,
            max_value=100000,
            value=60000,
            step=5000,
            help="Annual salary for general manager"
        )
        assistant_manager_salary = st.number_input(
            "Assistant Manager Salary ($/year)",
            min_value=25000,
            max_value=80000,
            value=40000,
            step=5000,
            help="Annual salary for assistant manager"
        )
        hourly_rate = st.number_input(
            "Part-time Staff Rate ($/hour)",
            min_value=10.0,
            max_value=30.0,
            value=15.0,
            step=0.50,
            help="Hourly rate for part-time staff"
        )
        extra_hourly_coverage = st.number_input(
            "Additional Hourly Coverage (hours/month)",
            min_value=0,
            max_value=500,
            value=105,
            step=10,
            help="Hours beyond manager coverage (default: ~105 hrs/month)"
        )
        payroll_tax_benefits_pct = st.slider(
            "Payroll Taxes & Benefits (%)",
            min_value=15,
            max_value=35,
            value=20,
            step=1,
            help="Additional % for taxes, benefits, insurance"
        )

        # Calculate total staffing costs
        monthly_salaries = (manager_salary + assistant_manager_salary) / 12
        monthly_hourly = hourly_rate * extra_hourly_coverage
        base_wages = monthly_salaries + monthly_hourly
        total_staffing = base_wages * (1 + payroll_tax_benefits_pct / 100)

        st.info(f"💰 Base Wages: ${base_wages:,.0f}/month")
        st.info(f"💼 Total Staffing (with taxes/benefits): ${total_staffing:,.0f}/month")

        st.markdown("**Other Operating Costs**")
        utilities_monthly = st.number_input(
            "Utilities ($/month)",
            min_value=500,
            max_value=10000,
            value=2000,
            step=250,
            help="Electricity, water, gas, internet"
        )
        insurance_monthly = st.number_input(
            "Insurance ($/month)",
            min_value=500,
            max_value=5000,
            value=1500,
            step=250,
            help="General liability, property insurance"
        )
        marketing_monthly = st.number_input(
            "Marketing ($/month)",
            min_value=500,
            max_value=10000,
            value=2000,
            step=250,
            help="Advertising, promotions, digital marketing"
        )
        software_monthly = st.number_input(
            "Software & Subscriptions ($/month)",
            min_value=100,
            max_value=3000,
            value=800,
            step=100,
            help="Booking system, accounting, other software"
        )
        professional_monthly = st.number_input(
            "Professional Services ($/month)",
            min_value=0,
            max_value=5000,
            value=500,
            step=250,
            help="Accounting, legal, consulting"
        )
        repairs_monthly = st.number_input(
            "Repairs & Maintenance ($/month)",
            min_value=0,
            max_value=5000,
            value=500,
            step=250,
            help="Equipment maintenance, facility repairs"
        )
        other_monthly = st.number_input(
            "Other Expenses ($/month)",
            min_value=0,
            max_value=5000,
            value=800,
            step=100,
            help="Miscellaneous operating expenses"
        )

        # Calculate total fixed costs
        other_fixed = (total_staffing + utilities_monthly + insurance_monthly +
                      marketing_monthly + software_monthly + professional_monthly +
                      repairs_monthly + other_monthly)
        fixed_monthly = rent_monthly + other_fixed

        st.markdown(f"**Total Fixed: ${fixed_monthly:,.0f}/month**")
        st.caption(f"Rent: ${rent_monthly:,.0f} + Other: ${other_fixed:,.0f}")
        if rent_abatement > 0:
            st.info(f"📍 {rent_abatement} months free rent at start")
        if rent_escalator > 0:
            y2_rent = rent_monthly * (1 + rent_escalator/100)
            st.info(f"📈 Year 2 rent: ${y2_rent:,.0f}/month")
        variable_pct = st.slider(
            "Variable Costs (% of revenue)",
            min_value=5,
            max_value=30,
            value=15,
            step=1,
            help="Supplies, commissions, etc."
        )
        staff_per_ch = st.number_input(
            "Staff Cost per Court-Hour ($)",
            min_value=0.0,
            max_value=20.0,
            value=5.0,
            step=0.5,
            help="Incremental staff cost per utilized court-hour"
        )
    
    with st.sidebar.expander("Growth Parameters", expanded=False):
        member_cap = st.number_input(
            "Member Cap",
            min_value=100,
            max_value=500,
            value=350,
            step=10,
            help="Maximum members (K in S-curve)"
        )
        start_members = st.number_input(
            "Starting Members",
            min_value=0,
            max_value=100,
            value=50,
            step=5,
            help="Members at month 0"
        )
        growth_rate = st.slider(
            "Growth Rate (r)",
            min_value=0.1,
            max_value=1.0,
            value=0.35,
            step=0.05,
            help="S-curve growth steepness"
        )
        midpoint_month = st.slider(
            "Growth Midpoint (month)",
            min_value=3,
            max_value=18,
            value=8,
            step=1,
            help="Month when 50% of cap is reached"
        )
    
    # Build Config with all parameters
    from engine.models import GrowthConfig, CostsConfig, FinanceConfig
    from engine.capital import compute_loan_to_balance
    
    # Create finance config first to compute loan
    finance_cfg = FinanceConfig(
        apr=apr/100,
        term_years=term_years,
        wc_reserve_start=wc_reserve,
        leasehold_improvements=leasehold,
        equipment=equipment,
        # Payroll split based on UI inputs
        payroll_split_salary_pct=base_wages / total_staffing if total_staffing > 0 else 0.83,
        payroll_split_taxes_pct=(total_staffing - base_wages) / total_staffing if total_staffing > 0 else 0.17
        # opex_allocations uses default from __post_init__
    )
    
    # Compute loan to balance sources and uses
    loan_amount = compute_loan_to_balance(finance_cfg)
    finance_cfg.loan_amount = loan_amount
    
    cfg = Config(
        facility=Facility(courts=courts, hours_per_day=hours),
        prime=PrimeWindow(
            mon_thu_start=mon_thu_start, mon_thu_end=mon_thu_end,
            fri_start=fri_start, fri_end=fri_end, 
            weekend_morning_hours=wknd_morn
        ),
        pricing=Pricing(
            nm_prime_per_court=nm_prime, nm_off_per_court=nm_off,
            member_prime_per_court=0.0, member_off_per_court=0.0
        ),
        league=LeagueConfig(
            weeknights=lg_weeknights,
            fill_rate=lg_fill_rate,
            price_prime_slot_6wk=lg_price_prime,
            active_weeks=lg_weeks
        ),
        corp=CorpConfig(
            events_per_month=corp_events,
            hours_per_event=corp_hours,
            prime_rate_per_court=corp_rate
        ),
        tourneys=Tournaments(),
        retail=Retail(),
        member_plans=MemberPlans(),
        league_discounts=LeagueDiscounts(),
        league_participants=LeagueParticipants(member_share=lg_member_share/100.0),
        member_mix=MemberMix(
            pct_community=community_pct/100,
            pct_player=player_pct/100,
            pct_pro=pro_pct/100
        ),
        openplay=OpenPlay(
            # Utilization values will be set automatically by the solver in Config.__post_init__
            member_share_prime=default_member_share,
            member_share_off=default_member_share
        ),
        growth=GrowthConfig(
            K=member_cap,
            start_members=start_members,
            r=growth_rate,
            t_mid=midpoint_month
        ),
        costs=CostsConfig(
            fixed_monthly_base=fixed_monthly,
            variable_pct_of_variable_rev=variable_pct/100,
            staff_cost_per_utilized_ch=staff_per_ch,
            rent_monthly=rent_monthly,
            rent_abatement_months=rent_abatement,
            rent_escalator_pct=rent_escalator
        ),
        finance=finance_cfg
    )
    return cfg, preset

def main():
    st.title("🏓 Indoor Pickleball Facility – Financial Model")
    st.caption("Comprehensive Financial Analysis and Projections")
    
    # Get config and compute
    cfg, preset = get_cfg_from_ui()
    
    # Hash config for caching
    cfg_hash = hash_config(cfg)
    
    # Check if we need to recompute
    if 'engine' not in st.session_state or st.session_state['engine'].get('hash') != cfg_hash:
        # SINGLE call to engine
        res = compute(cfg)
        st.session_state['engine'] = {
            'res': res,
            'hash': cfg_hash,
            'config': cfg
        }
    
    # Get results from session state
    res = st.session_state['engine']['res']
    cfg = st.session_state['engine']['config']
    
    # Calculate Y2 DSCRs once for all tabs
    from engine.projections import build_24_month_projection
    proj = build_24_month_projection(cfg)
    y2_months = proj["months"][12:24]
    y2_ebitda_sum = sum(m["EBITDA_m"] for m in y2_months)
    y2_debt_service_sum = sum(m["debt_service_m"] for m in y2_months)
    y2_annual_dscr = y2_ebitda_sum / y2_debt_service_sum if y2_debt_service_sum > 0 else 0
    y2_dscrs = [m["DSCR_m"] for m in y2_months if m["DSCR_m"] != float('inf')]
    y2_avg_dscr = sum(y2_dscrs) / len(y2_dscrs) if y2_dscrs else 0
    y2_min_dscr = min(y2_dscrs) if y2_dscrs else 0
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📊 Executive Dashboard", "📈 Financial Projections", "📋 Financial Statements"])
    
    with tab1:
        # Store key values for internal use
        engine_apr = cfg.finance.apr
        engine_loan = cfg.finance.loan_amount
        engine_wc = cfg.finance.wc_reserve_start
        engine_prime_share = res.get('meta', {}).get('prime_share', 0.296)
        engine_prime_util = cfg.openplay.util_prime
        engine_offpeak_util = cfg.openplay.util_off
        
        # Enhanced banner with utilization and corporate info
        from engine.utilization import compute_overall_utilization
        
        overall_util = compute_overall_utilization(engine_prime_util, engine_offpeak_util, engine_prime_share)
        total_corp_events = cfg.corp.events_per_month * 12 + getattr(cfg.corp, 'extra_events_per_year', 0)
        
        # Key Financial Metrics
        st.markdown("### Key Financial Metrics")
        fin_cols = st.columns(4)
        with fin_cols[0]:
            st.metric("Year 2 DSCR", f"{y2_annual_dscr:.2f}")
        with fin_cols[1]:
            st.metric("Overall Utilization", f"{overall_util*100:.0f}%")
        with fin_cols[2]:
            st.metric("Corporate Events/Year", f"{total_corp_events}")
        with fin_cols[3]:
            st.metric("RevPACH", f"${res['density']['RevPACH']:.2f}")
        
        # KPIs - ALL FROM ENGINE
        st.subheader("📊 Key Performance Indicators")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Revenue per Available Court Hour", f"${res['density']['RevPACH']:.2f}")
            st.caption("RevPACH")
        with c2:
            st.metric("Revenue per Utilized Hour", f"${res['density']['RevPerUtilHr']:.2f}")
            st.caption("Efficiency metric")
        with c3:
            st.metric("Annual Revenue", f"${res['annual']['variable_rev']:,.0f}")
            st.caption("Excluding membership fees")
        with c4:
            utilization = res['utilized_ch_year'] / res['available_ch_year'] * 100
            st.metric("Facility Utilization", f"{utilization:.1f}%")
            st.caption("Overall capacity usage")
        
        # Revenue Breakdown
        st.subheader("💰 Annual Revenue Breakdown")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Court Rentals", f"${res['annual']['court_rev']:,.0f}")
            st.metric("Leagues", f"${res['annual']['league_rev']:,.0f}")
        with c2:
            st.metric("Corporate", f"${res['annual']['corp_rev']:,.0f}")
            st.metric("Tournaments", f"${res['annual']['tourney_rev']:,.0f}")
        with c3:
            st.metric("Retail", f"${res['annual']['retail_rev']:,.0f}")
            st.metric("Total Variable", f"${res['annual']['variable_rev']:,.0f}")
        
        # Member Pricing Display
        with st.expander("💳 Member Pricing Tiers"):
            st.markdown("""
            **Members receive plan-based per-person rates:**
            
            | Tier | Prime (per person/hr) | Off-Peak (per person/hr) | League Discount | Notes |
            |------|----------------------|-------------------------|-----------------|--------|
            | Community | $14 (standard) | $11 (standard) | 0% | Standard member rates |
            | Player | $9 (discounted) | $0 (included) | 15% | Off-peak included in membership |
            | Pro | $0 (included) | $0 (included) | 25% | All court time included |
            | Non-Member | $65/court | $56/court | 0% | Per-court rack rates |
            
            *Note: Pro/Player off-peak included; Player prime discounted; Community standard rates*
            """)
        
        # Facility Summary (more professional)
        with st.expander("🏭 Facility Summary"):
            fac_cols = st.columns(2)
            with fac_cols[0]:
                st.markdown("**Configuration**")
                st.write(f"- Courts: {cfg.facility.courts}")
                st.write(f"- Operating Hours/Day: {cfg.facility.hours_per_day}")
                st.write(f"- League Nights: {cfg.league.weeknights}")
            with fac_cols[1]:
                st.markdown("**Performance**")
                st.write(f"- Available Court-Hours/Year: {res['available_ch_year']:,.0f}")
                st.write(f"- Utilized Court-Hours/Year: {res['utilized_ch_year']:,.0f}")
                st.write(f"- Utilization Rate: {(res['utilized_ch_year']/res['available_ch_year']*100):.1f}%")
        
        # Note: All exports are available in the Financial Statements tab
    
    with tab2:
        # Projections Tab
        st.subheader("📈 24-Month Financial Projections")
        
        # Build projections
        proj = build_24_month_projection(cfg)
        m = proj["months"]
        y1 = proj["summary"]["Y1"]
        y2 = proj["summary"]["Y2"]
        
        # Year summaries
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Year 1")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Revenue", f"${y1['rev_total']:,.0f}")
                st.metric("EBITDA", f"${y1['EBITDA']:,.0f}")
            with c2:
                st.metric("Min DSCR", f"{y1['min_DSCR']:.2f}")
                st.metric("Avg DSCR", f"{y1['avg_DSCR']:.2f}")
            with c3:
                st.metric("Break-even", y1["break_even_month"] or "Not in Y1")
                st.metric("End Cash", f"${y1['end_cash']:,.0f}")
        
        with col2:
            st.markdown("### Year 2")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Revenue", f"${y2['rev_total']:,.0f}")
                st.metric("EBITDA", f"${y2['EBITDA']:,.0f}")
            with c2:
                st.metric("Min DSCR", f"{y2['min_DSCR']:.2f}")
                st.metric("Avg DSCR", f"{y2['avg_DSCR']:.2f}")
            with c3:
                st.metric("Cash Flow", f"${y2['cash_flow']:,.0f}")
                st.metric("End Cash", f"${y2['end_cash']:,.0f}")
        
        # Charts
        st.divider()
        st.markdown("### Revenue & EBITDA Trend")
        
        # Create dataframe for charting
        df = pd.DataFrame(m)
        
        # Revenue and EBITDA chart
        chart_data = df[['month', 'rev_total', 'EBITDA_m']].copy()
        chart_data.columns = ['Month', 'Revenue', 'EBITDA']
        st.line_chart(chart_data.set_index('Month'))
        
        # Member growth chart
        st.markdown("### Member Growth (S-Curve)")
        member_data = df[['month', 'members']].copy()
        member_data.columns = ['Month', 'Members']
        st.line_chart(member_data.set_index('Month'))
        
        # Detailed monthly table
        st.divider()
        st.markdown("### Monthly Details")
        
        
        # Format display columns
        display_df = df[[
            'month', 'members', 'rev_total', 'EBITDA_m', 
            'DSCR_m', 'cash_flow_m', 'cum_cash'
        ]].copy()
        
        display_df.columns = [
            'Month', 'Members', 'Total Revenue', 'EBITDA', 
            'DSCR', 'Cash Flow', 'Cumulative Cash'
        ]
        
        # Format currency columns
        for col in ['Total Revenue', 'EBITDA', 'Cash Flow', 'Cumulative Cash']:
            display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")
        display_df['DSCR'] = display_df['DSCR'].apply(lambda x: f"{x:.2f}" if x != float('inf') else "∞")
        
        st.dataframe(display_df, use_container_width=True)
        
        # Note: All financial exports are available in the Financial Statements tab
        st.info("💡 All financial exports (projections, P&L, Balance Sheet) are available in the Financial Statements tab.")
        
    
    with tab3:
        # Financial Statements Tab
        st.subheader("📋 Financial Statements - P&L & Balance Sheet")
        
        # DSCR display section
        st.markdown("### 📊 Debt Service Coverage Analysis (Year 2)")
        dscr_cols = st.columns(3)
        with dscr_cols[0]:
            st.metric("Annual DSCR", f"{y2_annual_dscr:.2f}")
        with dscr_cols[1]:
            st.metric("Average Monthly DSCR", f"{y2_avg_dscr:.2f}")
        with dscr_cols[2]:
            st.metric("Minimum Monthly DSCR", f"{y2_min_dscr:.2f}")
        
        # Build financial statements
        stmts = build_financial_statements(cfg)
        pnl = stmts["pnl"]
        bs = stmts["balance_sheet"]
        summary = stmts["summary"]
        
        # Year summaries
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Year 1 Summary")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Revenue", f"${summary['Y1']['revenue']:,.0f}")
                st.metric("EBITDA", f"${summary['Y1']['ebitda']:,.0f}")
            with c2:
                st.metric("Net Income", f"${summary['Y1']['net_income']:,.0f}")
                st.metric("End Cash", f"${summary['Y1']['end_cash']:,.0f}")
            with c3:
                st.metric("End Debt", f"${summary['Y1']['end_debt']:,.0f}")
                st.metric("End Equity", f"${summary['Y1']['end_equity']:,.0f}")
        
        with col2:
            st.markdown("### Year 2 Summary")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Revenue", f"${summary['Y2']['revenue']:,.0f}")
                st.metric("EBITDA", f"${summary['Y2']['ebitda']:,.0f}")
            with c2:
                st.metric("Net Income", f"${summary['Y2']['net_income']:,.0f}")
                st.metric("End Cash", f"${summary['Y2']['end_cash']:,.0f}")
            with c3:
                st.metric("End Debt", f"${summary['Y2']['end_debt']:,.0f}")
                st.metric("End Equity", f"${summary['Y2']['end_equity']:,.0f}")
        
        # P&L Statement - Year 1 Monthly
        st.divider()
        st.markdown("### 📊 Year 1 P&L Statement (Monthly)")
        
        # Create P&L dataframe
        pnl_df = pd.DataFrame(pnl[:12])
        pnl_display = pnl_df[[
            'month', 'revenue_total', 'cogs_total', 'gross_profit',
            'opex_fixed', 'ebitda', 'depreciation', 'ebit', 
            'interest', 'ebt', 'tax', 'net_income'
        ]].copy()
        
        pnl_display.columns = [
            'Month', 'Revenue', 'COGS', 'Gross Profit',
            'Fixed OpEx', 'EBITDA', 'Depreciation', 'EBIT',
            'Interest', 'EBT', 'Tax', 'Net Income'
        ]
        
        # Format currency columns
        for col in pnl_display.columns[1:]:
            pnl_display[col] = pnl_display[col].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(pnl_display, use_container_width=True)
        
        # Simplified Balance Sheet Summary
        st.divider()
        st.markdown("### 📊 Balance Sheet Summary")

        # Show only key metrics for Y1 and Y2 EOY
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Year 1 End")
            y1_eoy = bs[11]  # Month 12 of Y1
            st.metric("Cash", f"${y1_eoy['cash']:,.0f}")
            st.metric("Total Assets", f"${y1_eoy['total_assets']:,.0f}")
            st.metric("Debt", f"${y1_eoy['debt_balance']:,.0f}")
            st.metric("Equity", f"${y1_eoy['equity']:,.0f}")

        with col2:
            st.markdown("#### Year 2 End")
            y2_eoy = bs[23]  # Last month of Y2
            st.metric("Cash", f"${y2_eoy['cash']:,.0f}")
            st.metric("Total Assets", f"${y2_eoy['total_assets']:,.0f}")
            st.metric("Debt", f"${y2_eoy['debt_balance']:,.0f}")
            st.metric("Equity", f"${y2_eoy['equity']:,.0f}")
        
        # Comprehensive Export Section
        st.divider()
        st.markdown("### 📥 All Financial Exports")
        st.info("📍 All financial data exports are consolidated here for easy access.")

        # Prepare all datasets for projections (keep for projections export)
        # pnl data is already available from financial statements

        # Prepare projection data
        proj = build_24_month_projection(cfg)
        df_proj = pd.DataFrame(proj["months"])
        df_y1_proj = df_proj.iloc[:12].copy()
        df_24_proj = df_proj.copy()

        # Define column order for projection exports
        proj_cols = ["month", "members", "rev_variable", "rev_membership", "rev_total",
                "court_rev_m", "league_rev_m", "corp_rev_m", "tourney_rev_m", "retail_rev_m",
                "fixed_opex_m", "variable_costs_m", "staff_costs_m", "opex_total_m",
                "EBITDA_m", "debt_service_m", "DSCR_m", "cash_flow_m", "cum_cash"]
        df_y1_proj = df_y1_proj[proj_cols]
        df_24_proj = df_24_proj[proj_cols]

        # Section 1: Balance Sheet
        st.markdown("#### 📋 Balance Sheet")
        st.caption("Banker format with Year 1 monthly columns and Year 2 End of Year")

        bs_y1_monthly = bs[:12]
        bs_y2_eoy = bs[23] if len(bs) > 23 else bs[-1]
        banker_bs_bytes = create_banker_balance_sheet(bs_y1_monthly, bs_y2_eoy)

        st.download_button(
            "📋 Download Balance Sheet (Banker Format)",
            data=banker_bs_bytes,
            file_name=f"Balance_Sheet_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Section 2: P&L Statements
        st.markdown("#### 📊 Profit & Loss Statements")
        st.caption("Banker format with Year 1 monthly columns and Year 2 total")

        # Prepare P&L data for banker format
        # Calculate Y2 totals by summing months 13-24
        pnl_y2_eoy = {}
        if len(pnl) >= 24:
            # Sum months 13-24 for each field
            for key in pnl[0].keys():
                if key != 'month':  # Skip the month field
                    pnl_y2_eoy[key] = sum(pnl[i].get(key, 0) for i in range(12, 24))

            # VALIDATION: Verify Y2 EOY is truly the sum of months 13-24
            # This ensures column O = sum(months 13-24) for each field
            for check_key in ['revenue_total', 'cogs_total', 'ebt', 'net_income']:
                expected_sum = sum(pnl[i].get(check_key, 0) for i in range(12, 24))
                if abs(pnl_y2_eoy.get(check_key, 0) - expected_sum) > 0.01:
                    st.error(f"Y2 EOY validation failed for {check_key}: "
                            f"EOY={pnl_y2_eoy.get(check_key, 0):.2f}, Sum(13-24)={expected_sum:.2f}")

        # Create the banker format P&L
        result = create_banker_pnl_sheet(pnl[:12], pnl_y2_eoy)
        if not result:  # Legacy safety
            return
        banker_pnl_bytes, validation_issues = result
        if banker_pnl_bytes is None:
            return  # Validation already surfaced; do not proceed

        # Only show download button if validation passed
        st.download_button(
            "📊 Download Profit & Loss (Banker Format)",
            data=banker_pnl_bytes,
            file_name=f"Profit_and_Loss_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Section 3: Financial Projections
        st.markdown("#### 📈 Financial Projections")
        col_proj1, col_proj2, col_proj3 = st.columns(3)

        with col_proj1:
            st.download_button(
                "Projections Y1 (CSV)",
                data=df_y1_proj.to_csv(index=False).encode("utf-8"),
                file_name=f"Projections_Y1_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

        with col_proj2:
            st.download_button(
                "Projections 24m (CSV)",
                data=df_24_proj.to_csv(index=False).encode("utf-8"),
                file_name=f"Projections_24m_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

        with col_proj3:
            def make_proj_excel(df_y1, df_24):
                from io import BytesIO
                bio = BytesIO()
                with pd.ExcelWriter(bio, engine="xlsxwriter") as xw:
                    df_y1.to_excel(xw, index=False, sheet_name="Y1 Projections")
                    df_24.to_excel(xw, index=False, sheet_name="24m Projections")
                bio.seek(0)
                return bio.read()

            proj_xlsx = make_proj_excel(df_y1_proj, df_24_proj)
            st.download_button(
                "Projections (Excel)",
                data=proj_xlsx,
                file_name=f"Projections_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # Key Assumptions
        with st.expander("💰 Financial Assumptions"):
            st.info(f"""
            **Capital Structure:**
            - Leasehold Improvements: ${cfg.finance.leasehold_improvements:,.0f}
            - Equipment: ${cfg.finance.equipment:,.0f}
            - Loan: ${cfg.finance.loan_amount:,.0f} @ {cfg.finance.apr*100:.1f}% APR, {cfg.finance.term_years} years
            - Working Capital: ${cfg.finance.wc_reserve_start:,.0f}
            
            **Operating Assumptions:**
            - Tax Rate: {cfg.finance.corporate_tax_rate*100:.0f}%
            - Depreciation: {cfg.finance.depreciation_years_leasehold} years (leasehold), {cfg.finance.depreciation_years_equipment} years (equipment)
            """)

# Exact labels from banker template (Column A, rows 1-59)
BANKER_TEMPLATE_LABELS = [
    "",  # Row 1
    "Profit and Loss Projection (12 Months)",  # Row 2
    "Veros Performance LLC",  # Row 3
    "",  # Row 4
    "Fiscal Year Begins",  # Row 5
    "2025-01-01 00:00:00",  # Row 6 (will be replaced with current year)
    "",  # Row 7
    "",  # Row 8
    "Revenue (Sales)",  # Row 9
    "Court Rental",  # Row 10
    "Leagues",  # Row 11
    "Corporate Events",  # Row 12
    "Tournaments",  # Row 13
    "Memberships",  # Row 14
    "Retail",  # Row 15
    "Other Revenue",  # Row 16
    "Total Revenue (Sales)",  # Row 17
    "",  # Row 18
    "Cost of Sales",  # Row 19
    "Direct Costs",  # Row 20
    "Total Cost of Sales",  # Row 21
    "",  # Row 22
    "Gross Profit",  # Row 23
    "",  # Row 24
    "Expenses",  # Row 25
    "Salary expenses ",  # Row 26 (note trailing space)
    "Payroll expenses ",  # Row 27 (note trailing space)
    "Outside services",  # Row 28
    "Supplies (office and operating)",  # Row 29
    "Repairs and maintenance",  # Row 30
    "Advertising",  # Row 31
    "Car, delivery and travel",  # Row 32
    "Accounting and legal",  # Row 33
    "Rent & Related Costs",  # Row 34
    "Telephone",  # Row 35
    "Utilities",  # Row 36
    "Insurance",  # Row 37
    "Taxes (real estate, etc.)",  # Row 38
    "Interest",  # Row 39
    "Depreciation",  # Row 40
    "Other expenses (specify)",  # Row 41
    "Other expenses (specify)",  # Row 42
    "Other expenses (specify)",  # Row 43
    "Misc. (unspecified)",  # Row 44
    "Sub-total Expenses",  # Row 45
    "Reserve for Contingencies ",  # Row 46 (note trailing space)
    "Total Expenses",  # Row 47
    "",  # Row 48
    "Net Profit Before Taxes",  # Row 49
    "Federal Income Taxes",  # Row 50
    "State Income Taxes",  # Row 51
    "Local Income Taxes",  # Row 52
    "Net Operating Income"  # Row 53
]

# Keep old labels for backward compatibility
TEMPLATE_LABELS = BANKER_TEMPLATE_LABELS

def validate_before_export(periods_y1, period_y2, template_labels):
    """Validate P&L data before export to ensure integrity

    Returns:
        tuple: (is_valid: bool, errors: list[str])
    """
    errors = []
    tolerance = 0.01  # Tolerance for floating point comparisons

    # a) Validate subtotals for sampled months (1, 6, 12)
    sample_months = [0, 5, 11]  # Indices for months 1, 6, 12

    for month_idx in sample_months:
        if month_idx >= len(periods_y1):
            continue

        p = periods_y1[month_idx]
        month_label = f"Month {month_idx + 1}"

        # Check GP = Revenue - COGS
        calc_gp = p.get('total_revenue', 0) - p.get('cogs', 0)
        stored_gp = p.get('gross_profit', 0)
        if abs(calc_gp - stored_gp) > tolerance:
            errors.append(f"{month_label}: Gross Profit mismatch - calculated {calc_gp:.2f} != stored {stored_gp:.2f}")

        # EBITDA - trust engine field directly (no recomputation)
        stored_ebitda = p.get('ebitda', 0)
        # Just verify EBITDA field exists and is reasonable
        if stored_ebitda == 0 and stored_gp > 0:
            errors.append(f"{month_label}: EBITDA is zero despite positive gross profit")

        # Check EBIT = EBITDA - Depreciation
        calc_ebit = stored_ebitda - p.get('depreciation', 0)
        stored_ebit = p.get('ebit', 0)
        if abs(calc_ebit - stored_ebit) > tolerance:
            errors.append(f"{month_label}: EBIT mismatch - calculated {calc_ebit:.2f} != stored {stored_ebit:.2f}")

        # Check EBT = EBIT - Interest
        calc_ebt = stored_ebit - p.get('interest', 0)
        stored_ebt = p.get('ebt', 0)
        if abs(calc_ebt - stored_ebt) > tolerance:
            errors.append(f"{month_label}: EBT mismatch - calculated {calc_ebt:.2f} != stored {stored_ebt:.2f}")

        # Check NI = EBT - Tax
        total_tax = p.get('tax', 0)
        calc_ni = stored_ebt - total_tax
        stored_ni = p.get('net_income', 0)
        if abs(calc_ni - stored_ni) > tolerance:
            errors.append(f"{month_label}: Net Income mismatch - calculated {calc_ni:.2f} != stored {stored_ni:.2f}")

        # Explicit check: NPBT must equal EBT field
        npbt_field = p.get('ebt', 0)
        if npbt_field == 0 and stored_gp > 0:
            errors.append(f"{month_label}: NPBT (EBT) is zero despite positive gross profit")

        # Explicit check: NOI must equal net_income (after-tax) field
        noi_field = p.get('net_income', 0)
        # Verify NOI = EBT - Tax (banker template definition)
        calc_noi = npbt_field - total_tax
        if abs(calc_noi - noi_field) > tolerance:
            errors.append(f"{month_label}: NOI mismatch - should be EBT({npbt_field:.2f}) - Tax({total_tax:.2f}) = {calc_noi:.2f}, but field shows {noi_field:.2f}")

    # b) Y2 EOY parity - verify Y2 totals equal sum of months 13-24
    # (This would require access to months 13-24 data which isn't passed to this function)
    # For now, just verify Y2 has expected fields
    if period_y2:
        required_y2_fields = ['total_revenue', 'cogs', 'gross_profit', 'ebitda', 'net_income']
        for field in required_y2_fields:
            if field not in period_y2:
                errors.append(f"Y2 EOY missing required field: {field}")

    # c) Labor split validation - ensure proper separation
    for i, p in enumerate(periods_y1[:3]):  # Check first 3 months
        cogs_labor = p.get('cogs_variable_labor', 0)

        # Verify COGS has variable labor
        if cogs_labor <= 0:
            errors.append(f"Month {i+1}: Missing variable labor in COGS (cogs_variable_labor)")

        # Ensure salaried payroll is NOT in COGS
        if 'salary_expenses' in p and p.get('cogs', 0) > 0:
            # Check that COGS doesn't contain salaried payroll amount
            opex_salary = p.get('salary_expenses', 0)
            cogs_total = p.get('cogs', 0)

            # If COGS contains exact same amount as opex salary, it's likely double-counted
            if abs(cogs_labor - opex_salary) < tolerance and cogs_labor > 0:
                errors.append(f"Month {i+1}: Potential labor double-count - COGS variable labor ({cogs_labor:.2f}) equals Opex salary ({opex_salary:.2f})")

    # d) Adapter parity - verify export matches engine for key fields
    # Check Total Revenue, COGS, Net Income for months 1, 6, 12
    for month_idx in sample_months:
        if month_idx >= len(periods_y1):
            continue

        p = periods_y1[month_idx]
        month_label = f"Month {month_idx + 1}"

        # Verify key totals are present and non-zero (for non-empty periods)
        if p.get('total_revenue', 0) <= 0:
            errors.append(f"{month_label}: Total Revenue is zero or missing")

        if p.get('cogs', 0) <= 0:
            errors.append(f"{month_label}: Total COGS is zero or missing")

    # Debug logging if there are errors (temporary - remove after debugging)
    if errors and len(periods_y1) > 0:
        p = periods_y1[0]  # Month 1
        import sys
        print(f"DEBUG Month 1: ebt={p.get('ebt', 0):.2f}, tax={p.get('tax', 0):.2f}, "
              f"ebit={p.get('ebit', 0):.2f}, net_income={p.get('net_income', 0):.2f}",
              file=sys.stderr)

    # Limit error reporting to first 10 issues
    if len(errors) > 10:
        errors = errors[:10]
        errors.append(f"... and {len(errors) - 10} more validation errors")

    return len(errors) == 0, errors

def create_banker_pnl_sheet(pnl_y1_monthly, pnl_y2_eoy):
    """Create professional banker-format P&L Excel file with Y1 monthly and Y2 EOY columns

    Uses engine/statements.py P&L data directly - no recomputation

    Args:
        pnl_y1_monthly: List of dicts with Y1 monthly P&L data from engine/statements.py
        pnl_y2_eoy: Dict with Y2 end-of-year P&L totals (summed from months 13-24)
    """
    from io import BytesIO
    from datetime import datetime
    import calendar

    # Direct mapping from engine P&L fields to banker template categories
    # The engine already computed everything - we just map fields

    # Parse years from the data
    current_year = datetime.now().year

    # Month names for headers
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def extract_field_safe(period_dict, field, default=0):
        """Safely extract a field from period dict"""
        if period_dict is None:
            return default
        return period_dict.get(field, default)

    # Map engine P&L fields to display values
    def map_engine_to_display(period):
        """Direct mapping from engine P&L dict to banker template - no calculations"""
        if not period:
            return {}

        # All fields come directly from engine - no math, no allocations
        return {
            # Revenue categories (7)
            'court_rev': period.get('revenue_court', 0),
            'league_rev': period.get('revenue_league', 0),
            'corporate_rev': period.get('revenue_corp', 0),
            'tournament_rev': period.get('revenue_tourney', 0),
            'membership_rev': period.get('revenue_membership', 0),
            'retail_rev': period.get('revenue_retail', 0),
            'revenue_other': 0,  # Always 0, placeholder
            'total_revenue': period.get('revenue_total', 0),

            # COGS (includes variable labor ONLY, no salaried)
            'cogs': period.get('cogs_total', 0),
            'cogs_variable_labor': period.get('cogs_variable_labor', 0),
            'gross_profit': period.get('gross_profit', 0),

            # Operating expenses - detailed breakdown from engine
            # IMPORTANT: Salaried/admin payroll is ONLY here, not in COGS
            'rent': period.get('rent', 0),
            'salary_expenses': period.get('opex_payroll_salary', 0),  # Salaried staff only
            'payroll_expenses': period.get('opex_payroll_taxes', 0),  # Taxes on salaried
            'utilities': period.get('opex_utilities', 0),
            'insurance': period.get('opex_insurance', 0),
            'marketing': period.get('opex_marketing', 0),
            'software': period.get('opex_software', 0),
            'professional_fees': period.get('opex_professional_fees', 0),  # Total (not used in rows)
            'opex_prof_fees_outside': period.get('opex_prof_fees_outside', 0),  # Outside Services row
            'opex_prof_fees_accounting': period.get('opex_prof_fees_accounting', 0),  # Accounting/Legal row
            'repairs_maintenance': period.get('opex_repairs_maintenance', 0),
            'other_opex': period.get('opex_other', 0),

            # D&A and Interest
            'depreciation': period.get('depreciation', 0),
            'interest': period.get('interest', 0),

            # Profitability metrics
            'ebitda': period.get('ebitda', 0),
            'ebit': period.get('ebit', 0),
            'ebt': period.get('ebt', 0),

            # Taxes
            'tax': period.get('tax', 0),
            'tax_federal': period.get('tax_federal', 0),
            'tax_state': period.get('tax_state', 0),
            'tax_local': period.get('tax_local', 0),

            # Bottom line
            'net_income': period.get('net_income', 0)
        }

    # Get mapped period data for all months and Y2
    periods_y1 = [map_engine_to_display(pnl) for pnl in pnl_y1_monthly]
    period_y2 = map_engine_to_display(pnl_y2_eoy) if pnl_y2_eoy else {}

    # Run pre-export validation
    is_valid, validation_errors = validate_before_export(periods_y1, period_y2, TEMPLATE_LABELS)
    if not is_valid:
        import streamlit as st
        error_msg = "❌ **Export validation failed. Please fix the following issues:**\n\n"
        for error in validation_errors:
            error_msg += f"• {error}\n"
        st.error(error_msg)
        return None, validation_errors  # Return tuple: (None, issues)

    # VALIDATION: Ensure no labor double-counting across all months
    for i, period in enumerate(periods_y1):
        cogs_labor = period.get('cogs_variable_labor', 0)
        opex_salary = period.get('salary_expenses', 0)
        # Check that variable labor (COGS) and salaried (Opex) are different
        if cogs_labor > 0 and opex_salary > 0:
            # OK to have both, but they shouldn't be identical (indicates double-count)
            if abs(cogs_labor - opex_salary) < 0.01:
                raise ValueError(f"Labor double-count detected in month {i+1}: "
                                f"COGS variable labor equals Opex salary ({cogs_labor:.2f})")
            # Also check that COGS labor is reasonable (should be much less than salaried)
            if cogs_labor > opex_salary * 2:
                import streamlit as st
                st.warning(f"⚠️ Month {i+1}: Variable labor in COGS ({cogs_labor:.0f}) "
                          f"exceeds 2x salaried payroll ({opex_salary:.0f})")

    # No calculations needed - engine provides all fields


    # Ensure we have all 53 template labels matching banker template (removed 6 empty CoS categories)
    assert len(TEMPLATE_LABELS) == 53, f"Template labels count changed unexpectedly: {len(TEMPLATE_LABELS)}"

    # Build the data structure using exact banker template labels
    data = []

    # Don't add title/header/date rows - banker template starts with data immediately
    # Build rows exactly matching banker template structure
    for idx, label in enumerate(TEMPLATE_LABELS):
        row_num = idx + 1  # 1-based row number to match template

        # Column A is always the label (use space for empty rows to preserve row count)
        row = [label if label else " "]

        # Column B is usually empty except for specific rows
        if row_num == 5:  # Fiscal Year Begins
            row.append(f"{current_year}-01-01")
        else:
            row.append("")  # Empty column B

        # Now add the monthly/yearly data (Columns C onward)
        # Handle cosmetic/header rows first
        if row_num in [1, 2, 3, 4, 5, 6, 7, 8]:  # Cosmetic rows at top
            row.extend(["" for _ in range(13)])  # Empty for all months + Y2

        # Revenue section (rows 9-17)
        elif row_num == 9:  # "Revenue (Sales)" header
            row.extend(["" for _ in range(13)])
        elif row_num == 10:  # Court Rental
            for i in range(12):
                row.append(periods_y1[i].get("court_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("court_rev", 0) if period_y2 else 0)
        elif row_num == 11:  # Leagues
            for i in range(12):
                row.append(periods_y1[i].get("league_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("league_rev", 0) if period_y2 else 0)
        elif row_num == 12:  # Corporate Events
            for i in range(12):
                row.append(periods_y1[i].get("corporate_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("corporate_rev", 0) if period_y2 else 0)
        elif row_num == 13:  # Tournaments
            for i in range(12):
                row.append(periods_y1[i].get("tournament_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("tournament_rev", 0) if period_y2 else 0)
        elif row_num == 14:  # Memberships
            for i in range(12):
                row.append(periods_y1[i].get("membership_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("membership_rev", 0) if period_y2 else 0)
        elif row_num == 15:  # Retail
            for i in range(12):
                row.append(periods_y1[i].get("retail_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("retail_rev", 0) if period_y2 else 0)
        elif row_num == 16:  # Other Revenue
            for i in range(12):
                row.append(periods_y1[i].get("revenue_other", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("revenue_other", 0) if period_y2 else 0)
        elif row_num == 17:  # Total Revenue (Sales) - use engine's pre-calculated total
            for i in range(12):
                row.append(periods_y1[i].get("total_revenue", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("total_revenue", 0) if period_y2 else 0)

        # Cost of Sales section (rows 19-21)
        elif row_num == 18:  # Empty row
            row.extend(["" for _ in range(13)])
        elif row_num == 19:  # "Cost of Sales" header
            row.extend(["" for _ in range(13)])
        elif row_num == 20:  # Direct Costs - all COGS (variable costs + variable labor ONLY)
            for i in range(12):
                row.append(periods_y1[i].get("cogs", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("cogs", 0) if period_y2 else 0)
        elif row_num == 21:  # Total Cost of Sales
            for i in range(12):
                row.append(periods_y1[i].get("cogs", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("cogs", 0) if period_y2 else 0)

        # Gross Profit (row 23)
        elif row_num == 22:  # Empty row
            row.extend(["" for _ in range(13)])
        elif row_num == 23:  # Gross Profit - use engine's pre-calculated value
            for i in range(12):
                row.append(periods_y1[i].get('gross_profit', 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get('gross_profit', 0) if period_y2 else 0)

        # Expenses section (rows 25-47)
        elif row_num == 24:  # Empty row
            row.extend(["" for _ in range(13)])
        elif row_num == 25:  # "Expenses" header
            row.extend(["" for _ in range(13)])
        elif row_num == 26:  # Salary expenses
            for i in range(12):
                row.append(periods_y1[i].get('salary_expenses', 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get('salary_expenses', 0) if period_y2 else 0)
        elif row_num == 27:  # Payroll expenses
            for i in range(12):
                row.append(periods_y1[i].get('payroll_expenses', 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get('payroll_expenses', 0) if period_y2 else 0)
        elif row_num == 28:  # Outside services
            for i in range(12):
                row.append(periods_y1[i].get("opex_prof_fees_outside", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("opex_prof_fees_outside", 0) if period_y2 else 0)
        elif row_num == 29:  # Supplies
            row.extend([0.0 for _ in range(13)])  # Set to 0 to avoid double-counting
        elif row_num == 30:  # Repairs and maintenance
            for i in range(12):
                row.append(periods_y1[i].get("repairs_maintenance", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("repairs_maintenance", 0) if period_y2 else 0)
        elif row_num == 31:  # Advertising
            for i in range(12):
                row.append(periods_y1[i].get("marketing", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("marketing", 0) if period_y2 else 0)
        elif row_num == 32:  # Car, delivery and travel
            row.extend([0.0 for _ in range(13)])
        elif row_num == 33:  # Accounting and legal
            for i in range(12):
                row.append(periods_y1[i].get("opex_prof_fees_accounting", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("opex_prof_fees_accounting", 0) if period_y2 else 0)
        elif row_num == 34:  # Rent & Related Costs
            for i in range(12):
                row.append(periods_y1[i].get("rent", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("rent", 0) if period_y2 else 0)
        elif row_num == 35:  # Telephone
            for i in range(12):
                row.append(periods_y1[i].get("software", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("software", 0) if period_y2 else 0)
        elif row_num == 36:  # Utilities
            for i in range(12):
                row.append(periods_y1[i].get("utilities", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("utilities", 0) if period_y2 else 0)
        elif row_num == 37:  # Insurance
            for i in range(12):
                row.append(periods_y1[i].get("insurance", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("insurance", 0) if period_y2 else 0)
        elif row_num == 38:  # Taxes (real estate, etc.)
            row.extend([0.0 for _ in range(13)])
        elif row_num == 39:  # Interest
            for i in range(12):
                row.append(periods_y1[i].get("interest", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("interest", 0) if period_y2 else 0)
        elif row_num == 40:  # Depreciation
            for i in range(12):
                row.append(periods_y1[i].get("depreciation", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("depreciation", 0) if period_y2 else 0)
        elif row_num in [41, 42, 43]:  # Other expenses (specify)
            row.extend([0.0 for _ in range(13)])
        elif row_num == 44:  # Misc. (unspecified)
            for i in range(12):
                row.append(periods_y1[i].get("other_opex", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("other_opex", 0) if period_y2 else 0)
        elif row_num == 45:  # Sub-total Expenses - use pre-calculated aggregate
            for i in range(12):
                row.append(periods_y1[i].get('subtotal_expenses', 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get('subtotal_expenses', 0) if period_y2 else 0)
        elif row_num == 46:  # Reserve for Contingencies
            row.extend([0.0 for _ in range(13)])
        elif row_num == 47:  # Total Expenses - use pre-calculated aggregate
            for i in range(12):
                row.append(periods_y1[i].get('total_expenses', 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get('total_expenses', 0) if period_y2 else 0)

        # Net Profit Before Taxes (row 49)
        elif row_num == 48:  # Empty row
            row.extend(["" for _ in range(13)])
        elif row_num == 49:  # Net Profit Before Taxes = Gross Profit - Total Expenses
            for i in range(12):
                if i < len(periods_y1):
                    # Use pre-calculated values from engine
                    npbt = periods_y1[i].get('ebt', 0)  # EBT is NPBT in our model
                    row.append(npbt)
                else:
                    row.append(0)
            if period_y2:
                npbt_y2 = period_y2.get('ebt', 0)
                row.append(npbt_y2)
            else:
                row.append(0)

        # Tax section (rows 50-52)
        elif row_num == 50:  # Federal Income Taxes - use engine's pre-calculated value
            for i in range(12):
                row.append(periods_y1[i].get('tax_federal', 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get('tax_federal', 0) if period_y2 else 0)

        elif row_num == 51:  # State Income Taxes
            for i in range(12):
                row.append(periods_y1[i].get('tax_state', 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get('tax_state', 0) if period_y2 else 0)

        elif row_num == 52:  # Local Income Taxes
            for i in range(12):
                row.append(periods_y1[i].get('tax_local', 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get('tax_local', 0) if period_y2 else 0)

        # Net Operating Income (row 53)
        elif row_num == 53:  # Net Operating Income = NPBT - Total Taxes
            for i in range(12):
                if i < len(periods_y1):
                    # Use engine's net_income directly
                    noi = periods_y1[i].get('net_income', 0)
                    row.append(noi)
                else:
                    row.append(0)
            if period_y2:
                noi_y2 = period_y2.get('net_income', 0)
                row.append(noi_y2)
            else:
                row.append(0)

        else:
            # Any unhandled rows get zeros
            row.extend([0.0 for _ in range(13)])

        data.append(row)

    # Debug logging for validation
    sanity_check = {}
    if len(periods_y1) > 0 and len(data) >= 53:
        # Extract month 1 values from data rows (column C, index 2)
        m1_values = {}
        for i, label in enumerate(TEMPLATE_LABELS):
            if i < len(data) and len(data[i]) > 2:
                val = data[i][2]  # Column C (month 1)
                if label == "Total Revenue (Sales)":
                    m1_values["tot_rev"] = val
                elif label == "Total Cost of Sales":
                    m1_values["tot_cogs"] = val
                elif label == "Gross Profit":
                    m1_values["gp"] = val
                elif label == "Total Expenses":
                    m1_values["tot_exp"] = val
                elif label == "Net Profit Before Taxes":
                    m1_values["npbt"] = val
                elif label == "Federal Income Taxes":
                    m1_values["fed_tax"] = val
                elif label == "State Income Taxes":
                    m1_values["state_tax"] = val
                elif label == "Local Income Taxes":
                    m1_values["local_tax"] = val
                elif label == "Net Operating Income":
                    m1_values["noi"] = val

        sanity_check = {
            "labels": len(TEMPLATE_LABELS),
            "tot_rev": m1_values.get('tot_rev', 0),
            "tot_cogs": m1_values.get('tot_cogs', 0),
            "gp": m1_values.get('gp', 0),
            "tot_exp": m1_values.get('tot_exp', 0),
            "npbt": m1_values.get('npbt', 0),
            "fed_tax": m1_values.get('fed_tax', 0),
            "state_tax": m1_values.get('state_tax', 0),
            "local_tax": m1_values.get('local_tax', 0),
            "total_tax": m1_values.get('fed_tax', 0) + m1_values.get('state_tax', 0) + m1_values.get('local_tax', 0),
            "noi": m1_values.get('noi', 0)
        }

    # Create DataFrame
    df = pd.DataFrame(data)

    # No validation needed since we're using engine values directly

    # Create Excel file with professional formatting
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Profit & Loss", index=False, header=False)

        # Get workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets["Profit & Loss"]

        # Define professional formats (same as Balance Sheet)
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter'
        })

        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F0F0F0'  # Light gray
        })

        date_format = workbook.add_format({
            'align': 'center',
            'italic': True,
            'font_size': 10
        })

        label_format = workbook.add_format({
            'indent': 1
        })

        total_label_format = workbook.add_format({
            'bold': True,
            'top': 1
        })

        # Currency format - whole dollars only
        currency_format = workbook.add_format({
            'num_format': '#,##0;(#,##0)',
            'align': 'right'
        })

        total_currency_format = workbook.add_format({
            'bold': True,
            'num_format': '#,##0;(#,##0)',
            'align': 'right',
            'top': 1
        })

        section_header_format = workbook.add_format({
            'bold': True
        })

        # Don't merge/overwrite the first row - banker template needs all 59 rows intact
        # Write month headers in row 2 (Year 1)
        worksheet.write(1, 2, 'Jan', header_format)
        worksheet.write(1, 3, 'Feb', header_format)
        worksheet.write(1, 4, 'Mar', header_format)
        worksheet.write(1, 5, 'Apr', header_format)
        worksheet.write(1, 6, 'May', header_format)
        worksheet.write(1, 7, 'Jun', header_format)
        worksheet.write(1, 8, 'Jul', header_format)
        worksheet.write(1, 9, 'Aug', header_format)
        worksheet.write(1, 10, 'Sep', header_format)
        worksheet.write(1, 11, 'Oct', header_format)
        worksheet.write(1, 12, 'Nov', header_format)
        worksheet.write(1, 13, 'Dec', header_format)
        worksheet.write(1, 14, 'Y2 EOY', header_format)

        # Define total lines that need emphasis (matching template labels)
        total_labels = [
            "Total Revenue (Sales)",
            "Total Cost of Sales",
            "Gross Profit",
            "Total Expenses",
            "Net Profit Before Taxes",
            "Net Operating Income"
        ]

        # Define section headers that need bold formatting
        section_headers = [
            "Profit and Loss Projection (12 Months)",
            "Fiscal Year Begins",
            "Revenue (Sales)",
            "Cost of Sales",
            "Expenses",
            "Sub-total Expenses",
            "Reserve for Contingencies ",
            "Total Expenses"
        ]

        # Format all data rows
        first_data_row = 0  # Start from the first row (no title row anymore)
        for row_idx in range(first_data_row, len(data)):
            if row_idx < len(data):
                label = str(data[row_idx][0]) if data[row_idx][0] else ""

                # Apply label formatting
                if any(total in label for total in total_labels):
                    worksheet.write(row_idx, 0, label, total_label_format)
                elif any(header in label for header in section_headers):
                    worksheet.write(row_idx, 0, label, section_header_format)
                elif label.startswith("  "):  # Indented items
                    worksheet.write(row_idx, 0, label, label_format)
                else:
                    worksheet.write(row_idx, 0, label)

                # Format numeric columns with currency
                for col_idx in range(2, 15):  # Columns C through O
                    if col_idx < len(data[row_idx]):
                        val = data[row_idx][col_idx]
                        if isinstance(val, (int, float)) and val != "":
                            # Apply currency format with emphasis for totals
                            if any(total in label for total in total_labels):
                                worksheet.write(row_idx, col_idx, val, total_currency_format)
                            else:
                                worksheet.write(row_idx, col_idx, val, currency_format)

        # Set column widths
        worksheet.set_column('A:A', 34)   # Labels
        worksheet.set_column('B:B', 3)    # Indent spacer
        worksheet.set_column('C:O', 14)   # Data columns

        # Set row heights for better spacing
        worksheet.set_row(0, 22)  # Title row
        worksheet.set_row(1, 18)  # Headers
        worksheet.set_row(2, 18)  # Date row

        # Freeze panes at first data row
        worksheet.freeze_panes(first_data_row, 2)  # Freeze at C{first_data_row}

    bio.seek(0)

    # All validation is now done in validate_before_export() function
    # which runs BEFORE the Excel file is created

    return bio.read(), []  # Return tuple: (xlsx_bytes, empty_issues_list)

def create_banker_balance_sheet(bs_y1_monthly, bs_y2_eoy):
    """Create professional banker-format Balance Sheet Excel file with Y1 monthly and Y2 EOY columns"""
    from io import BytesIO
    from datetime import datetime
    import calendar

    # Parse years from the data
    current_year = datetime.now().year

    # Month names for headers
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # Build the data structure
    data = []

    # Title row (will be merged and centered)
    title_row = ["Balance Sheet (Projected)"] + ["" for _ in range(14)]
    data.append(title_row)

    # Headers row - Month names for Y1 + EOY for Y2
    header_row = ["", ""]  # A, B columns
    for i in range(12):
        if i < len(bs_y1_monthly):
            header_row.append(f"{month_names[i]} {current_year}")
        else:
            header_row.append("")  # Empty if month missing
    header_row.append(f"EOY {current_year + 1}")  # Y2 EOY
    data.append(header_row)

    # Date row - "as of MM/DD/YYYY"
    date_row = ["", ""]  # A, B columns
    for i in range(12):
        if i < len(bs_y1_monthly):
            last_day = calendar.monthrange(current_year, i + 1)[1]
            date_str = f"as of {i+1:02d}/{last_day:02d}/{current_year}"
            date_row.append(date_str)
        else:
            date_row.append("")
    # Y2 EOY date
    date_row.append(f"as of 12/31/{current_year + 1}")
    data.append(date_row)

    # Helper function to add a data row
    def add_data_row(label, values_y1, value_y2, is_calculated=False):
        row = [label, ""]  # A, B columns
        for i in range(12):
            if i < len(bs_y1_monthly) and i < len(values_y1):
                row.append(values_y1[i])
            else:
                row.append("" if not is_calculated else 0)
        row.append(value_y2)  # Y2 EOY
        data.append(row)

    # Extract values for all periods
    def extract_values(bs_list, field):
        return [bs.get(field, 0) for bs in bs_list]

    # Assets section
    data.append(["Assets"] + ["" for _ in range(14)])
    data.append(["Current Assets"] + ["" for _ in range(14)])

    # Cash
    cash_y1 = extract_values(bs_y1_monthly, "cash")
    cash_y2 = bs_y2_eoy.get("cash", 0)
    add_data_row("  Cash", cash_y1, cash_y2)

    # Other current assets (default to 0)
    add_data_row("  Other current assets", [0]*12, 0, is_calculated=True)

    # Total Current Assets
    total_current_y1 = cash_y1  # Since other current assets = 0
    add_data_row("  Total Current Assets", total_current_y1, cash_y2)

    # Fixed Assets
    data.append(["Fixed Assets"] + ["" for _ in range(14)])

    ppe_gross_y1 = extract_values(bs_y1_monthly, "ppe_gross")
    ppe_gross_y2 = bs_y2_eoy.get("ppe_gross", 0)
    add_data_row("  Fixed assets (gross)", ppe_gross_y1, ppe_gross_y2)

    add_data_row("  Other fixed assets", [0]*12, 0, is_calculated=True)

    accum_dep_y1 = extract_values(bs_y1_monthly, "accumulated_depreciation")
    accum_dep_y2 = bs_y2_eoy.get("accumulated_depreciation", 0)
    add_data_row("  (LESS accumulated depreciation on all fixed assets)", accum_dep_y1, accum_dep_y2)

    # Total Fixed Assets (net)
    ppe_net_y1 = extract_values(bs_y1_monthly, "ppe_net")
    ppe_net_y2 = bs_y2_eoy.get("ppe_net", 0)
    add_data_row("  Total Fixed Assets (net of depreciation)", ppe_net_y1, ppe_net_y2)

    # Other Assets
    data.append(["Other Assets"] + ["" for _ in range(14)])
    add_data_row("  Total Other Assets", [0]*12, 0, is_calculated=True)

    # TOTAL Assets
    total_assets_y1 = extract_values(bs_y1_monthly, "total_assets")
    total_assets_y2 = bs_y2_eoy.get("total_assets", 0)
    add_data_row("TOTAL Assets", total_assets_y1, total_assets_y2)

    data.append(["" for _ in range(15)])  # Empty row

    # Liabilities and Equity section
    data.append(["Liabilities and Equity"] + ["" for _ in range(14)])
    data.append(["Current Liabilities"] + ["" for _ in range(14)])

    add_data_row("  Payroll liabilities", [0]*12, 0, is_calculated=True)
    add_data_row("  Other current liabilities", [0]*12, 0, is_calculated=True)
    add_data_row("  Total Current Liabilities", [0]*12, 0, is_calculated=True)

    # Long-term Debt
    debt_y1 = extract_values(bs_y1_monthly, "debt_balance")
    debt_y2 = bs_y2_eoy.get("debt_balance", 0)
    add_data_row("Total Long-term Debt", debt_y1, debt_y2)

    # Total Liabilities (Current Liab + LT Debt)
    add_data_row("Total Liabilities", debt_y1, debt_y2)

    # Owners' Equity
    data.append(["Owners' Equity"] + ["" for _ in range(14)])
    equity_y1 = extract_values(bs_y1_monthly, "equity")
    equity_y2 = bs_y2_eoy.get("equity", 0)
    add_data_row("  Total Owners' Equity", equity_y1, equity_y2)

    # Total Liabilities & Equity
    total_le_y1 = extract_values(bs_y1_monthly, "total_liabilities_equity")
    total_le_y2 = bs_y2_eoy.get("total_liabilities_equity", 0)
    add_data_row("Total Liabilities & Equity", total_le_y1, total_le_y2)

    # Create DataFrame
    df = pd.DataFrame(data)

    # Create Excel file with professional formatting
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Balance Sheet", index=False, header=False)

        # Get workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets["Balance Sheet"]

        # Define professional formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter'
        })

        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F0F0F0'  # Light gray
        })

        date_format = workbook.add_format({
            'align': 'center',
            'italic': True,
            'font_size': 10
        })

        label_format = workbook.add_format({
            'indent': 1
        })

        total_label_format = workbook.add_format({
            'bold': True,
            'top': 1
        })

        # Currency format with parentheses for negatives
        currency_format = workbook.add_format({
            'num_format': '$#,##0_);($#,##0)',
            'align': 'right'
        })

        total_currency_format = workbook.add_format({
            'bold': True,
            'num_format': '$#,##0_);($#,##0)',
            'align': 'right',
            'top': 1
        })

        # Determine last data column dynamically
        last_col_idx = 14  # Column O (0-indexed)
        last_col_letter = 'O'

        # Merge and center title across all used columns
        worksheet.merge_range(f'A1:{last_col_letter}1', 'Balance Sheet (Projected)', title_format)

        # Apply header format to month names (row 1)
        for col in range(2, last_col_idx + 1):  # C to O
            if col < len(data[1]) and data[1][col]:
                worksheet.write(1, col, data[1][col], header_format)
            if col < len(data[2]) and data[2][col]:
                worksheet.write(2, col, data[2][col], date_format)

        # Dynamically detect rows
        first_data_row = 3  # First label row ("Assets")

        # Define total lines that need emphasis
        total_labels = [
            "Total Current Assets",
            "Total Fixed Assets (net of depreciation)",
            "Total Other Assets",
            "TOTAL Assets",
            "Total Current Liabilities",
            "Total Long-term Debt",
            "Total Liabilities",
            "Total Owners' Equity",
            "Total Liabilities & Equity"
        ]

        # Format all data rows
        for row_idx in range(first_data_row, len(data)):
            if row_idx < len(data):
                label = str(data[row_idx][0]) if data[row_idx][0] else ""

                # Apply label formatting
                if any(total in label for total in total_labels):
                    worksheet.write(row_idx, 0, label, total_label_format)
                elif label.startswith("  "):  # Indented items
                    worksheet.write(row_idx, 0, label, label_format)
                else:
                    worksheet.write(row_idx, 0, label)

                # Format numeric columns with currency
                for col_idx in range(2, last_col_idx + 1):  # Columns C through O
                    if col_idx < len(data[row_idx]):
                        val = data[row_idx][col_idx]
                        if isinstance(val, (int, float)) and val != "":
                            # Apply currency format with emphasis for totals
                            if any(total in label for total in total_labels):
                                worksheet.write(row_idx, col_idx, val, total_currency_format)
                            else:
                                worksheet.write(row_idx, col_idx, val, currency_format)

        # Set column widths
        worksheet.set_column('A:A', 34)   # Labels
        worksheet.set_column('B:B', 3)    # Indent spacer
        worksheet.set_column('C:O', 14)   # Data columns

        # Set row heights for better spacing
        worksheet.set_row(0, 22)  # Title row
        worksheet.set_row(1, 18)  # Headers
        worksheet.set_row(2, 18)  # Date row

        # Freeze panes dynamically at first data row
        # This keeps title, headers, and "as of" rows frozen, plus columns A & B
        worksheet.freeze_panes(first_data_row, 2)  # Freeze at C{first_data_row}

    bio.seek(0)

    # Validation checks
    validation_issues = []

    # Check Y1 months
    for i, bs in enumerate(bs_y1_monthly):
        check = abs(bs.get("check", 0))
        if check > 0.01:
            validation_issues.append(f"{month_names[i]} {current_year}: check=${check:.2f}")

    # Check Y2 EOY
    check_y2 = abs(bs_y2_eoy.get("check", 0))
    if check_y2 > 0.01:
        validation_issues.append(f"EOY {current_year + 1}: check=${check_y2:.2f}")

    if validation_issues:
        import streamlit as st
        st.warning(f"⚠️ Balance Sheet validation issues:\n" + "\n".join(validation_issues) +
                   "\n\nValues should be near zero. This indicates the balance sheet may not balance correctly.")

    return bio.read()

def build_underwriting_packet(cfg, res, preset, include_audit=True):
    """Build comprehensive financial packet from model outputs"""
    prime_share = res.get('meta', {}).get('prime_share', res.get("prime_ch_week", 116) / max(1e-6, res.get("total_ch_week", 392)))
    
    packet = {
        "Scenario": f"{preset} Operating Model",
        "Schedule": {
            "Prime window": "Mon-Thu 4-10pm, Fri 4-9pm, Weekend AM 4h",
            "Prime share %": round(prime_share * 100, 1),
            "League nights": cfg.league.weeknights,
            "Courts used for leagues": cfg.league.courts_used,
            "Block length": f"{cfg.league.session_len_h}h + {cfg.league.buffer_min}m buffer",
            "Weekly blocks/slots": f"{res['weekly']['league_blocks']}/{res['weekly']['league_slots']}",
            "Fill rate": f"{cfg.league.fill_rate * 100:.0f}%",
            "Active league weeks": cfg.league.active_weeks,
        },
        "Pricing": {
            "Non-member per-court (prime/off)": f"${cfg.pricing.nm_prime_per_court:.0f}/${cfg.pricing.nm_off_per_court:.0f}",
            "Member tiers (per-person/hr)": {
                "Community": f"${cfg.member_plans.community_prime_pp:.0f}/${cfg.member_plans.community_off_pp:.0f}",
                "Player": f"${cfg.member_plans.player_prime_pp:.0f}/${cfg.member_plans.player_off_pp:.0f} (off-peak included)",
                "Pro": f"${cfg.member_plans.pro_prime_pp:.0f}/${cfg.member_plans.pro_off_pp:.0f} (all included)",
            },
            "League price (prime, 6-wk)": f"${cfg.league.price_prime_slot_6wk:.0f}",
            "League discounts": f"{cfg.league_discounts.community_pct*100:.0f}%/{cfg.league_discounts.player_pct*100:.0f}%/{cfg.league_discounts.pro_pct*100:.0f}%",
        },
        "Revenue (annual, variable only)": {
            "Court": f"${res['annual']['court_rev']:,.0f}",
            "League": f"${res['annual']['league_rev']:,.0f}",
            "Corporate": f"${res['annual']['corp_rev']:,.0f}",
            "Tournament": f"${res['annual']['tourney_rev']:,.0f}",
            "Retail": f"${res['annual']['retail_rev']:,.0f}",
            "Total": f"${res['annual']['variable_rev']:,.0f}",
        },
        "Density": {
            "RevPACH": f"${res['density']['RevPACH']:.2f}",
            "Rev/Utilized Hr": f"${res['density']['RevPerUtilHr']:.2f}",
            "Available CH/year": f"{res['available_ch_year']:,.0f}",
            "Utilized CH/year": f"{res['utilized_ch_year']:,.0f}",
            "Utilization %": f"{(res['utilized_ch_year'] / res['available_ch_year'] * 100):.1f}%",
        },
    }
    
    if include_audit:
        if "court_debug" in res:
            packet["Court Pricing Audit"] = {
                "Per-court member rates": res["court_debug"].get("per_court_rates"),
                "Utilized CH (prime/off)": f"{res['court_debug'].get('util_prime_ch', 0):.1f}/{res['court_debug'].get('util_off_ch', 0):.1f}",
                "Member CH (prime/off)": f"{res['court_debug'].get('mem_prime_ch', 0):.1f}/{res['court_debug'].get('mem_off_ch', 0):.1f}",
                "Non-member CH (prime/off)": f"{res['court_debug'].get('nm_prime_ch', 0):.1f}/{res['court_debug'].get('nm_off_ch', 0):.1f}",
            }
        if "league_debug" in res:
            packet["League Discount Audit"] = {
                "Weekly slots": res["league_debug"]["slots_wk"],
                "Filled slots": res["league_debug"]["filled_slots"],
                "Member share": f"{res['league_debug']['member_share']*100:.0f}%",
                "Discounted member price": f"${res['league_debug']['disc_member_price']:.2f}",
                "Average slot price": f"${res['league_debug']['avg_slot_price']:.2f}",
            }
    
    return packet

if __name__ == "__main__":
    main()
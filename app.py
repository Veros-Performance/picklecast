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
    # Convert config to dict and hash
    cfg_str = str(vars(cfg))
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
        other_fixed = st.number_input(
            "Other Fixed Costs ($/month)",
            min_value=10000,
            max_value=100000,
            value=25000,
            step=1000,
            help="Payroll, insurance, utilities, etc."
        )
        fixed_monthly = rent_monthly + other_fixed
        st.markdown(f"**Total Fixed: ${fixed_monthly:,.0f}/month**")
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
        equipment=equipment
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

        # Create the banker format P&L
        banker_pnl_bytes = create_banker_pnl_sheet(pnl[:12], pnl_y2_eoy)

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

# Exact labels from banker template (Column A, in order)
TEMPLATE_LABELS = [
    "Revenue (Sales)",
    "Category 1",
    "Category 2",
    "Category 3",
    "Category 4",
    "Category 5",
    "Category 6",
    "Category 7",
    "Total Revenue (Sales)",
    "",  # Empty row
    "Cost of Sales",
    "",  # Empty row
    "Gross Profit",
    "",  # Empty row
    "Operating Expenses",
    "Salaries",
    "Payroll Taxes & Benefits",
    "Rent",
    "Advertising & Marketing",
    "Office Supplies",
    "Utilities",
    "Insurance",
    "Repairs & Maintenance",
    "Professional Fees",
    "Travel",
    "Telephone",
    "Postage & Delivery",
    "Licenses & Permits",
    "Miscellaneous",
    "Total Operating Expenses",
    "",  # Empty row
    "Operating Profit",
    "",  # Empty row
    "Other Income/(Expense)",
    "Interest Income",
    "Interest Expense",
    "Other Income",
    "Other Expense",
    "Total Other Income/(Expense)",
    "",  # Empty row
    "Net Profit Before Taxes",
    "",  # Empty row
    "Income Taxes",
    "Federal Income Tax",
    "State Income Tax",
    "Local Income Tax",
    "",  # Empty row
    "Net Operating Income"
]

def create_banker_pnl_sheet(pnl_y1_monthly, pnl_y2_eoy, mapping_dict=None):
    """Create professional banker-format P&L Excel file with Y1 monthly and Y2 EOY columns

    Computes all totals from raw components - never trusts pre-calculated totals in CSV

    Args:
        pnl_y1_monthly: List of dicts with Y1 monthly P&L data
        pnl_y2_eoy: Dict with Y2 end-of-year P&L totals
        mapping_dict: Optional dict mapping CSV account names to standard categories
    """
    from io import BytesIO
    from datetime import datetime
    import calendar
    import re

    # Parse years from the data
    current_year = datetime.now().year

    # Month names for headers
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def normalize_account_name(name):
        """Normalize account name for matching: lowercase, no punctuation, single spaces"""
        if not name:
            return ""
        # Convert to lowercase
        normalized = str(name).lower()
        # Remove common punctuation
        normalized = re.sub(r'[&/\(\)\-,\.]', ' ', normalized)
        # Collapse multiple spaces to single space
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def map_account_to_category(account_name, mapping_dict=None):
        """Map account name to standard category using explicit mapping or heuristics"""
        normalized = normalize_account_name(account_name)

        # First check explicit mapping if provided
        if mapping_dict and account_name in mapping_dict:
            return mapping_dict[account_name]

        # Revenue heuristics
        if any(term in normalized for term in ['court', 'rental', 'booking']):
            return 'court_rev'
        if any(term in normalized for term in ['league', 'team']):
            return 'league_rev'
        if any(term in normalized for term in ['corporate', 'corp', 'event']):
            return 'corporate_rev'
        if any(term in normalized for term in ['tournament', 'tourney', 'competition']):
            return 'tournament_rev'
        if any(term in normalized for term in ['membership', 'member', 'subscription']):
            return 'membership_rev'
        if any(term in normalized for term in ['retail', 'shop', 'merchandise', 'pro shop']):
            return 'retail_rev'
        if any(term in normalized for term in ['revenue', 'sales', 'income']) and 'other' not in normalized:
            return 'revenue_other'

        # COGS heuristics
        if any(term in normalized for term in ['cogs', 'cost of goods', 'cost of sales', 'inventory cost']):
            return 'cogs'
        if 'merchant fee' in normalized or 'processing fee' in normalized:
            return 'cogs'
        if 'direct labor' in normalized or 'direct cost' in normalized:
            return 'cogs'

        # Operating expense heuristics
        if any(term in normalized for term in ['rent', 'lease', 'occupancy']):
            return 'rent'
        if any(term in normalized for term in ['payroll', 'wage', 'salary', 'staff', 'employee']):
            return 'payroll'
        if any(term in normalized for term in ['utility', 'utilities', 'electric', 'water', 'gas']):
            return 'utilities'
        if any(term in normalized for term in ['insurance', 'liability']):
            return 'insurance'
        if any(term in normalized for term in ['marketing', 'advertising', 'ads', 'promotion']):
            return 'marketing'
        if any(term in normalized for term in ['software', 'subscription', 'saas', 'technology', 'it']):
            return 'software'
        if any(term in normalized for term in ['professional', 'legal', 'accounting', 'consultant']):
            return 'professional_fees'
        if any(term in normalized for term in ['repair', 'maintenance', 'upkeep']):
            return 'repairs_maintenance'
        if any(term in normalized for term in ['admin', 'office', 'general', 'miscellaneous']):
            return 'other_opex'

        # D&A heuristics
        if any(term in normalized for term in ['depreciation', 'amortization']):
            return 'depreciation'

        # Interest heuristics
        if 'interest' in normalized and 'expense' in normalized:
            return 'interest'
        if 'loan' in normalized and 'interest' in normalized:
            return 'interest'

        # Other income/expense
        if 'other income' in normalized or 'non operating income' in normalized:
            return 'other_income'
        if 'other expense' in normalized or 'non operating expense' in normalized:
            return 'other_expense'

        # Tax heuristics
        if any(term in normalized for term in ['tax', 'income tax', 'corporate tax']):
            return 'tax'

        # If we have generic opex terms, put in other_opex
        if any(term in normalized for term in ['expense', 'cost', 'fee']):
            return 'other_opex'

        # Unmapped
        return None

    def compute_period_data(pnl_dict, mapping_dict=None):
        """Compute all derived totals from raw components using smart mapping"""
        # Initialize all categories
        mapped_accounts = {
            'court_rev': 0, 'league_rev': 0, 'corporate_rev': 0,
            'tournament_rev': 0, 'membership_rev': 0, 'retail_rev': 0,
            'revenue_other': 0, 'cogs': 0,
            'rent': 0, 'payroll': 0, 'utilities': 0, 'insurance': 0,
            'marketing': 0, 'software': 0, 'professional_fees': 0,
            'repairs_maintenance': 0, 'other_opex': 0,
            'depreciation': 0, 'interest': 0,
            'other_income': 0, 'other_expense': 0, 'tax': 0
        }

        unmapped = {}

        # Process each account in the period
        for account_name, value in pnl_dict.items():
            if account_name == 'month':  # Skip metadata fields
                continue

            # Try to map the account
            category = map_account_to_category(account_name, mapping_dict)

            if category and category in mapped_accounts:
                mapped_accounts[category] += value
            else:
                # Check if it's already a standard category name
                if account_name in mapped_accounts:
                    mapped_accounts[account_name] += value
                else:
                    unmapped[account_name] = value

        # Extract mapped values
        court_rev = mapped_accounts['court_rev']
        league_rev = mapped_accounts['league_rev']
        corp_rev = mapped_accounts['corporate_rev']
        tourney_rev = mapped_accounts['tournament_rev']
        membership_rev = mapped_accounts['membership_rev']
        retail_rev = mapped_accounts['retail_rev']
        revenue_other = mapped_accounts['revenue_other']

        # Compute total revenue
        total_revenue = court_rev + league_rev + corp_rev + tourney_rev + membership_rev + retail_rev + revenue_other

        # COGS
        cogs = mapped_accounts['cogs']

        # Compute Gross Profit
        gross_profit = total_revenue - cogs

        # Operating expenses
        rent = mapped_accounts['rent']
        payroll = mapped_accounts['payroll']
        utilities = mapped_accounts['utilities']
        insurance = mapped_accounts['insurance']
        marketing = mapped_accounts['marketing']
        software = mapped_accounts['software']
        professional = mapped_accounts['professional_fees']
        repairs = mapped_accounts['repairs_maintenance']
        other_opex = mapped_accounts['other_opex']

        # If we have a fixed_opex field and no detailed breakdown, use it
        if 'fixed_opex' in pnl_dict and (rent + utilities + insurance + marketing + software + professional + repairs + other_opex) == 0:
            fixed_opex = pnl_dict['fixed_opex']
            # Apply standard allocation only as last resort
            rent = fixed_opex * 0.3
            utilities = fixed_opex * 0.15
            insurance = fixed_opex * 0.1
            marketing = fixed_opex * 0.15
            software = fixed_opex * 0.1
            professional = fixed_opex * 0.05
            repairs = fixed_opex * 0.05
            other_opex = fixed_opex * 0.1

        # Compute total operating expenses
        total_opex = rent + payroll + utilities + insurance + marketing + software + professional + repairs + other_opex

        # Compute EBITDA
        ebitda = gross_profit - total_opex

        # Depreciation & Amortization
        depreciation = mapped_accounts['depreciation']

        # Compute EBIT
        ebit = ebitda - depreciation

        # Interest expense (positive magnitude for display)
        interest_expense = mapped_accounts['interest']

        # Other non-interest income/expense
        other_income = mapped_accounts['other_income']
        other_expense = mapped_accounts['other_expense']

        # Total Other Income/(Expense) - signed net value
        # This is negative when expenses (including interest) exceed income
        total_other_net = other_income - other_expense - interest_expense

        # Compute EBT using the signed net
        ebt = ebit + total_other_net

        # Taxes
        tax = mapped_accounts['tax']

        # Compute Net Income
        net_income = ebt - tax

        return {
            # Revenue components
            "court_rev": court_rev,
            "league_rev": league_rev,
            "corporate_rev": corp_rev,
            "tournament_rev": tourney_rev,
            "membership_rev": membership_rev,
            "retail_rev": retail_rev,
            "revenue_other": revenue_other,
            "total_revenue": total_revenue,

            # COGS
            "cogs": cogs,
            "gross_profit": gross_profit,

            # Operating expenses
            "rent": rent,
            "payroll": payroll,
            "utilities": utilities,
            "insurance": insurance,
            "marketing": marketing,
            "software": software,
            "professional_fees": professional,
            "repairs_maintenance": repairs,
            "other_opex": other_opex,
            "total_opex": total_opex,

            # Other items
            "ebitda": ebitda,
            "depreciation": depreciation,
            "ebit": ebit,
            "interest_expense": interest_expense,  # Positive magnitude for display
            "total_other_net": total_other_net,    # Signed net (typically negative)
            "ebt": ebt,
            "tax": tax,
            "net_income": net_income,

            # Metadata
            "unmapped": unmapped
        }

    # Compute period data for all months and Y2
    periods_y1 = [compute_period_data(pnl, mapping_dict) for pnl in pnl_y1_monthly]
    period_y2 = compute_period_data(pnl_y2_eoy, mapping_dict) if pnl_y2_eoy else {}

    # Debug output for first month (remove after validation passes)
    if periods_y1:
        jan = periods_y1[0]
        ebitda_jan = jan.get("gross_profit", 0) - jan.get("total_opex", 0)
        depreciation_jan = jan.get("depreciation", 0)
        op_profit_jan = ebitda_jan - depreciation_jan  # EBIT
        debug = {
            "ebitda": ebitda_jan,
            "depreciation": depreciation_jan,
            "operating_profit_ebit": op_profit_jan,
            "interest_expense": jan.get("interest_expense", 0),
            "total_other_net": jan.get("total_other_net", 0),
            "npbt_written": op_profit_jan + jan.get("total_other_net", 0),
            "ebt_computed": jan.get("ebt", 0),
            "tax": jan.get("tax", 0),
            "net_income": jan.get("net_income", 0),
            "noi_written": (op_profit_jan + jan.get("total_other_net", 0)) - jan.get("tax", 0)
        }
        try:
            import streamlit as st
            st.write({"P&L debug (Jan)": debug})
        except:
            pass  # Not in Streamlit context

    # Build the data structure using exact banker template labels
    data = []

    # Title row (will be merged and centered)
    title_row = ["Profit & Loss (Projected)"] + ["" for _ in range(14)]
    data.append(title_row)

    # Headers row - Month names for Y1 + EOY for Y2
    header_row = ["", ""]  # A, B columns
    for i in range(12):
        if i < len(periods_y1):
            header_row.append(f"{month_names[i]} {current_year}")
        else:
            header_row.append("")  # Empty if month missing
    header_row.append(f"Year {current_year + 1}")  # Y2 full year
    data.append(header_row)

    # Date row - "for the month ended MM/DD/YYYY" or "for the year ended 12/31/YYYY"
    date_row = ["", ""]  # A, B columns
    for i in range(12):
        if i < len(periods_y1):
            last_day = calendar.monthrange(current_year, i + 1)[1]
            date_str = f"for the month ended {i+1:02d}/{last_day:02d}/{current_year}"
            date_row.append(date_str)
        else:
            date_row.append("")
    # Y2 full year date
    date_row.append(f"for the year ended 12/31/{current_year + 1}")
    data.append(date_row)

    # Build rows from TEMPLATE_LABELS
    for label in TEMPLATE_LABELS:
        row = [label, ""]  # A, B columns always

        # Handle each label type
        if label == "":  # Empty rows
            row.extend(["" for _ in range(13)])

        # Revenue categories - map our revenue types to Category 1-7
        elif label == "Category 1":  # Court rental
            for i in range(12):
                row.append(periods_y1[i].get("court_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("court_rev", 0) if period_y2 else 0)
        elif label == "Category 2":  # League
            for i in range(12):
                row.append(periods_y1[i].get("league_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("league_rev", 0) if period_y2 else 0)
        elif label == "Category 3":  # Corporate
            for i in range(12):
                row.append(periods_y1[i].get("corporate_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("corporate_rev", 0) if period_y2 else 0)
        elif label == "Category 4":  # Tournament
            for i in range(12):
                row.append(periods_y1[i].get("tournament_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("tournament_rev", 0) if period_y2 else 0)
        elif label == "Category 5":  # Membership
            for i in range(12):
                row.append(periods_y1[i].get("membership_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("membership_rev", 0) if period_y2 else 0)
        elif label == "Category 6":  # Retail
            for i in range(12):
                row.append(periods_y1[i].get("retail_rev", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("retail_rev", 0) if period_y2 else 0)
        elif label == "Category 7":  # Other revenue (catch-all)
            for i in range(12):
                row.append(periods_y1[i].get("revenue_other", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("revenue_other", 0) if period_y2 else 0)

        # Total Revenue - MUST be the sum of Category 1-7 detail lines
        elif label == "Total Revenue (Sales)":
            for i in range(12):
                if i < len(periods_y1):
                    # Sum ONLY what we write to Categories 1-7
                    total = (periods_y1[i].get("court_rev", 0) +
                            periods_y1[i].get("league_rev", 0) +
                            periods_y1[i].get("corporate_rev", 0) +
                            periods_y1[i].get("tournament_rev", 0) +
                            periods_y1[i].get("membership_rev", 0) +
                            periods_y1[i].get("retail_rev", 0) +
                            periods_y1[i].get("revenue_other", 0))
                    row.append(total)
                else:
                    row.append(0)
            # Y2 total
            if period_y2:
                total_y2 = (period_y2.get("court_rev", 0) +
                           period_y2.get("league_rev", 0) +
                           period_y2.get("corporate_rev", 0) +
                           period_y2.get("tournament_rev", 0) +
                           period_y2.get("membership_rev", 0) +
                           period_y2.get("retail_rev", 0) +
                           period_y2.get("revenue_other", 0))
                row.append(total_y2)
            else:
                row.append(0)

        # Cost of Sales
        elif label == "Cost of Sales":
            for i in range(12):
                row.append(periods_y1[i].get("cogs", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("cogs", 0) if period_y2 else 0)

        # Gross Profit
        elif label == "Gross Profit":
            for i in range(12):
                row.append(periods_y1[i].get("gross_profit", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("gross_profit", 0) if period_y2 else 0)

        # Operating Expenses mapping
        elif label == "Salaries":
            for i in range(12):
                row.append(periods_y1[i].get("payroll", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("payroll", 0) if period_y2 else 0)
        elif label == "Payroll Taxes & Benefits":
            row.extend([0 for _ in range(13)])  # Could map if we had this data
        elif label == "Rent":
            for i in range(12):
                row.append(periods_y1[i].get("rent", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("rent", 0) if period_y2 else 0)
        elif label == "Advertising & Marketing":
            for i in range(12):
                row.append(periods_y1[i].get("marketing", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("marketing", 0) if period_y2 else 0)
        elif label == "Office Supplies":
            row.extend([0 for _ in range(13)])  # Could be part of other_opex
        elif label == "Utilities":
            for i in range(12):
                row.append(periods_y1[i].get("utilities", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("utilities", 0) if period_y2 else 0)
        elif label == "Insurance":
            for i in range(12):
                row.append(periods_y1[i].get("insurance", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("insurance", 0) if period_y2 else 0)
        elif label == "Repairs & Maintenance":
            for i in range(12):
                row.append(periods_y1[i].get("repairs_maintenance", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("repairs_maintenance", 0) if period_y2 else 0)
        elif label == "Professional Fees":
            for i in range(12):
                row.append(periods_y1[i].get("professional_fees", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("professional_fees", 0) if period_y2 else 0)
        elif label == "Travel":
            row.extend([0 for _ in range(13)])
        elif label == "Telephone":
            for i in range(12):
                row.append(periods_y1[i].get("software", 0) * 0.2 if i < len(periods_y1) else 0)  # Part of software/tech
            row.append(period_y2.get("software", 0) * 0.2 if period_y2 else 0)
        elif label == "Postage & Delivery":
            row.extend([0 for _ in range(13)])
        elif label == "Licenses & Permits":
            row.extend([0 for _ in range(13)])
        elif label == "Miscellaneous":
            for i in range(12):
                row.append(periods_y1[i].get("other_opex", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("other_opex", 0) if period_y2 else 0)

        # Total Operating Expenses
        elif label == "Total Operating Expenses":
            for i in range(12):
                row.append(periods_y1[i].get("total_opex", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("total_opex", 0) if period_y2 else 0)

        # Operating Profit (EBIT after D&A - banker convention)
        elif label == "Operating Profit":
            for i in range(12):
                # Operating Profit = Gross Profit - Total Operating Expenses - Depreciation (EBIT)
                if i < len(periods_y1):
                    ebitda = periods_y1[i].get("gross_profit", 0) - periods_y1[i].get("total_opex", 0)
                    depreciation = periods_y1[i].get("depreciation", 0)
                    op_profit = ebitda - depreciation  # This is EBIT
                    row.append(op_profit)
                else:
                    row.append(0)
            if period_y2:
                ebitda_y2 = period_y2.get("gross_profit", 0) - period_y2.get("total_opex", 0)
                depreciation_y2 = period_y2.get("depreciation", 0)
                op_profit_y2 = ebitda_y2 - depreciation_y2  # This is EBIT
                row.append(op_profit_y2)
            else:
                row.append(0)

        # Other Income/Expense items
        elif label == "Interest Income":
            row.extend([0 for _ in range(13)])  # We don't track interest income separately
        elif label == "Interest Expense":
            for i in range(12):
                row.append(periods_y1[i].get("interest_expense", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("interest_expense", 0) if period_y2 else 0)
        elif label == "Other Income":
            row.extend([0 for _ in range(13)])  # Could map if available
        elif label == "Other Expense":
            row.extend([0 for _ in range(13)])  # Could map if available
        elif label == "Total Other Income/(Expense)":
            for i in range(12):
                row.append(periods_y1[i].get("total_other_net", 0) if i < len(periods_y1) else 0)
            row.append(period_y2.get("total_other_net", 0) if period_y2 else 0)

        # Net Profit Before Taxes (EBT)
        elif label == "Net Profit Before Taxes":
            for i in range(12):
                if i < len(periods_y1):
                    # Net Profit Before Taxes = Operating Profit (EBIT) + Total Other Income/(Expense)
                    ebitda = periods_y1[i].get("gross_profit", 0) - periods_y1[i].get("total_opex", 0)
                    depreciation = periods_y1[i].get("depreciation", 0)
                    op_profit = ebitda - depreciation  # This is EBIT
                    npbt = op_profit + periods_y1[i].get("total_other_net", 0)
                    row.append(npbt)
                else:
                    row.append(0)
            if period_y2:
                ebitda_y2 = period_y2.get("gross_profit", 0) - period_y2.get("total_opex", 0)
                depreciation_y2 = period_y2.get("depreciation", 0)
                op_profit_y2 = ebitda_y2 - depreciation_y2  # This is EBIT
                npbt_y2 = op_profit_y2 + period_y2.get("total_other_net", 0)
                row.append(npbt_y2)
            else:
                row.append(0)

        # Tax items
        elif label == "Federal Income Tax":
            for i in range(12):
                row.append(periods_y1[i].get("tax", 0) * 0.7 if i < len(periods_y1) else 0)  # Assume 70% federal
            row.append(period_y2.get("tax", 0) * 0.7 if period_y2 else 0)
        elif label == "State Income Tax":
            for i in range(12):
                row.append(periods_y1[i].get("tax", 0) * 0.25 if i < len(periods_y1) else 0)  # Assume 25% state
            row.append(period_y2.get("tax", 0) * 0.25 if period_y2 else 0)
        elif label == "Local Income Tax":
            for i in range(12):
                row.append(periods_y1[i].get("tax", 0) * 0.05 if i < len(periods_y1) else 0)  # Assume 5% local
            row.append(period_y2.get("tax", 0) * 0.05 if period_y2 else 0)

        # Net Operating Income (Net Income)
        elif label == "Net Operating Income":
            for i in range(12):
                if i < len(periods_y1):
                    # Net Operating Income = Net Profit Before Taxes - All Taxes
                    ebitda = periods_y1[i].get("gross_profit", 0) - periods_y1[i].get("total_opex", 0)
                    depreciation = periods_y1[i].get("depreciation", 0)
                    op_profit = ebitda - depreciation  # This is EBIT
                    npbt = op_profit + periods_y1[i].get("total_other_net", 0)
                    noi = npbt - periods_y1[i].get("tax", 0)
                    row.append(noi)
                else:
                    row.append(0)
            if period_y2:
                ebitda_y2 = period_y2.get("gross_profit", 0) - period_y2.get("total_opex", 0)
                depreciation_y2 = period_y2.get("depreciation", 0)
                op_profit_y2 = ebitda_y2 - depreciation_y2  # This is EBIT
                npbt_y2 = op_profit_y2 + period_y2.get("total_other_net", 0)
                noi_y2 = npbt_y2 - period_y2.get("tax", 0)
                row.append(noi_y2)
            else:
                row.append(0)

        # Section headers (no numbers)
        elif label in ["Revenue (Sales)", "Operating Expenses", "Other Income/(Expense)", "Income Taxes"]:
            row.extend(["" for _ in range(13)])
        else:
            # Default to zeros for any unhandled labels
            row.extend([0 for _ in range(13)])

        data.append(row)

    # Create DataFrame
    df = pd.DataFrame(data)

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

        # Merge and center title
        worksheet.merge_range('A1:O1', 'Profit & Loss (Projected)', title_format)

        # Apply header format to month names (row 1)
        for col in range(2, 15):  # C to O
            if col < len(data[1]) and data[1][col]:
                worksheet.write(1, col, data[1][col], header_format)
            if col < len(data[2]) and data[2][col]:
                worksheet.write(2, col, data[2][col], date_format)

        # Define total lines that need emphasis (matching template labels)
        total_labels = [
            "Total Revenue (Sales)",
            "Gross Profit",
            "Total Operating Expenses",
            "Operating Profit",
            "Total Other Income/(Expense)",
            "Net Profit Before Taxes",
            "Net Operating Income"
        ]

        # Format all data rows
        first_data_row = 3  # First actual data row after headers
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

    # Validation checks using computed values
    validation_issues = []
    tolerance = 0.01

    # Validate Y1 months using banker template terminology
    for i, period in enumerate(periods_y1):
        month = month_names[i] if i < 12 else f"Month {i+1}"

        # Validate Total Revenue (Sales) = sum of revenue categories (including Category 7/other)
        revenue_sum = (period.get("court_rev", 0) + period.get("league_rev", 0) +
                      period.get("corporate_rev", 0) + period.get("tournament_rev", 0) +
                      period.get("membership_rev", 0) + period.get("retail_rev", 0) +
                      period.get("revenue_other", 0))  # Must include Category 7
        revenue_computed = period.get("total_revenue", 0)
        if abs(revenue_sum - revenue_computed) > tolerance:
            validation_issues.append(f"{month}: Total Revenue mismatch (expected {revenue_sum:.2f}, got {revenue_computed:.2f})")

        # Validate Gross Profit = Total Revenue - Cost of Sales
        gp_expected = period["total_revenue"] - period["cogs"]
        gp_computed = period["gross_profit"]
        if abs(gp_expected - gp_computed) > tolerance:
            validation_issues.append(f"{month}: Gross Profit mismatch (expected {gp_expected:.2f}, got {gp_computed:.2f})")

        # Validate Total Operating Expenses = sum of all opex components
        opex_sum = (period.get("payroll", 0) + period.get("rent", 0) + period.get("utilities", 0) +
                    period.get("insurance", 0) + period.get("marketing", 0) + period.get("software", 0) +
                    period.get("professional_fees", 0) + period.get("repairs_maintenance", 0) +
                    period.get("other_opex", 0))
        opex_computed = period["total_opex"]
        if abs(opex_sum - opex_computed) > tolerance:
            validation_issues.append(f"{month}: Total Operating Expenses mismatch (expected {opex_sum:.2f}, got {opex_computed:.2f})")

        # Validate Operating Profit = Gross Profit - Total Operating Expenses - Depreciation (EBIT)
        ebitda = period["gross_profit"] - period["total_opex"]
        depreciation = period.get("depreciation", 0)
        op_profit_expected = ebitda - depreciation  # EBIT
        op_profit_computed = period.get("ebit", ebitda - depreciation)  # Use EBIT if available
        if abs(op_profit_expected - op_profit_computed) > tolerance:
            validation_issues.append(f"{month}: Operating Profit mismatch (expected {op_profit_expected:.2f}, got {op_profit_computed:.2f})")

        # Validate Net Profit Before Taxes = Operating Profit (EBIT) + Total Other Income/(Expense)
        # What we write to the sheet
        npbt_written = op_profit_expected + period["total_other_net"]
        # What the raw data says (should match)
        npbt_computed = period["ebt"]
        if abs(npbt_written - npbt_computed) > tolerance:
            validation_issues.append(f"{month}: Net Profit Before Taxes mismatch (written {npbt_written:.2f}, computed {npbt_computed:.2f})")

        # Validate Net Operating Income = Net Profit Before Taxes - Taxes
        noi_expected = npbt_computed - period["tax"]
        noi_computed = period["net_income"]
        if abs(noi_expected - noi_computed) > tolerance:
            validation_issues.append(f"{month}: Net Operating Income mismatch (expected {noi_expected:.2f}, got {noi_computed:.2f})")

    # Validate Y2 if present (using same banker terminology)
    if period_y2:
        # Validate Total Revenue (Sales) = sum of revenue categories (including Category 7/other)
        revenue_sum_y2 = (period_y2.get("court_rev", 0) + period_y2.get("league_rev", 0) +
                         period_y2.get("corporate_rev", 0) + period_y2.get("tournament_rev", 0) +
                         period_y2.get("membership_rev", 0) + period_y2.get("retail_rev", 0) +
                         period_y2.get("revenue_other", 0))
        revenue_computed_y2 = period_y2.get("total_revenue", 0)
        if abs(revenue_sum_y2 - revenue_computed_y2) > tolerance:
            validation_issues.append(f"Year 2: Total Revenue mismatch (expected {revenue_sum_y2:.2f}, got {revenue_computed_y2:.2f})")

        # Validate Gross Profit
        gp_expected = period_y2["total_revenue"] - period_y2["cogs"]
        gp_computed = period_y2["gross_profit"]
        if abs(gp_expected - gp_computed) > tolerance:
            validation_issues.append(f"Year 2: Gross Profit mismatch (expected {gp_expected:.2f}, got {gp_computed:.2f})")

        # Validate Operating Profit (EBIT)
        ebitda_y2 = period_y2["gross_profit"] - period_y2["total_opex"]
        depreciation_y2 = period_y2.get("depreciation", 0)
        op_profit_expected = ebitda_y2 - depreciation_y2  # EBIT
        op_profit_computed = period_y2.get("ebit", ebitda_y2 - depreciation_y2)
        if abs(op_profit_expected - op_profit_computed) > tolerance:
            validation_issues.append(f"Year 2: Operating Profit mismatch (expected {op_profit_expected:.2f}, got {op_profit_computed:.2f})")

        # Validate Net Profit Before Taxes
        npbt_written = op_profit_expected + period_y2["total_other_net"]
        npbt_computed = period_y2["ebt"]
        if abs(npbt_written - npbt_computed) > tolerance:
            validation_issues.append(f"Year 2: Net Profit Before Taxes mismatch (written {npbt_written:.2f}, computed {npbt_computed:.2f})")

        # Validate Net Operating Income
        noi_expected = period_y2["ebt"] - period_y2["tax"]
        noi_computed = period_y2["net_income"]
        if abs(noi_expected - noi_computed) > tolerance:
            validation_issues.append(f"Year 2: Net Operating Income mismatch (expected {noi_expected:.2f}, got {noi_computed:.2f})")

    if validation_issues:
        import streamlit as st
        st.warning("⚠️ P&L validation issues:\n" + "\n".join(validation_issues))

    return bio.read()

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
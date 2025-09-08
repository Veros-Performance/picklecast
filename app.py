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
        
        # Export Section
        st.divider()
        st.subheader(f"📥 Export Data - {preset} Scenario")
        
        revpach = res["density"]["RevPACH"]
        rev_util = res["density"]["RevPerUtilHr"]
        
        # Professional export mode
        detailed_export = st.checkbox(
            "📋 Include Detailed Analysis", 
            help="Include comprehensive metrics for financial review"
        )
        
        if st.button("📥 Export Financial Data", type="primary"):
            # Build export packet
            packet = build_underwriting_packet(cfg, res, preset, include_audit=detailed_export)
            
            # Create export dataframe
            export_df = pd.DataFrame({
                'Metric': ['RevPACH', 'Rev/Util Hr', 'Annual Variable Revenue', 
                          'Court Revenue', 'League Revenue', 'Corporate Revenue',
                          'Tournament Revenue', 'Retail Revenue', 'Prime Share %',
                          'Utilization %'],
                'Value': [
                    f"${revpach:.2f}",
                    f"${rev_util:.2f}",
                    f"${res['annual']['variable_rev']:,.0f}",
                    f"${res['annual']['court_rev']:,.0f}",
                    f"${res['annual']['league_rev']:,.0f}",
                    f"${res['annual']['corp_rev']:,.0f}",
                    f"${res['annual']['tourney_rev']:,.0f}",
                    f"${res['annual']['retail_rev']:,.0f}",
                    f"{prime_share*100:.1f}%",
                    f"{utilization:.1f}%"
                ]
            })
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"pickleball_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            st.success("✅ Financial data exported successfully")
    
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
        
        # Underwriting Exports
        st.divider()
        st.markdown("### 📊 Underwriting Exports")
        
        # Prepare data for exports
        df_y1 = df.iloc[:12].copy()
        df_24 = df.copy()
        
        # Define column order for clean exports
        cols = ["month", "members", "rev_variable", "rev_membership", "rev_total",
                "court_rev_m", "league_rev_m", "corp_rev_m", "tourney_rev_m", "retail_rev_m",
                "fixed_opex_m", "variable_costs_m", "staff_costs_m", "opex_total_m",
                "EBITDA_m", "debt_service_m", "DSCR_m", "cash_flow_m", "cum_cash"]
        df_y1 = df_y1[cols]
        df_24 = df_24[cols]
        
        # Sanity checks - ensure exports reconcile to summaries
        assert abs(df_y1["rev_total"].sum() - y1["rev_total"]) < 2.0, "Y1 CSV ≠ Y1 summary"
        assert abs(df_24.iloc[12:]["rev_total"].sum() - y2["rev_total"]) < 2.0, "Y2 months ≠ Y2 summary"
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Year-1 (12-month) CSV
            st.download_button(
                "⬇️ Download Year-1 (12-month) CSV",
                data=df_y1.to_csv(index=False).encode("utf-8"),
                file_name=f"veros_Y1_12m_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # 24-Month CSV
            st.download_button(
                "⬇️ Download 24-Month CSV",
                data=df_24.to_csv(index=False).encode("utf-8"),
                file_name=f"veros_24m_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col3:
            # Excel workbook with both tabs
            from io import BytesIO
            
            def make_excel_bytes(df_y1, df_24):
                bio = BytesIO()
                with pd.ExcelWriter(bio, engine="xlsxwriter") as xw:
                    df_y1.to_excel(xw, index=False, sheet_name="Y1 (12m)")
                    df_24.to_excel(xw, index=False, sheet_name="24 Months")
                bio.seek(0)
                return bio.read()
            
            xlsx_bytes = make_excel_bytes(df_y1, df_24)
            st.download_button(
                "⬇️ Download Excel (Y1 & 24m)",
                data=xlsx_bytes,
                file_name=f"veros_underwriting_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # Y1/Y2 Summary export
        st.divider()
        st.markdown("### 📈 Summary Exports")
        
        summary_data = {
            "Metric": [
                "Y1 Revenue", "Y1 EBITDA", "Y1 Min DSCR", "Y1 Avg DSCR", "Y1 End Cash",
                "Y2 Revenue", "Y2 EBITDA", "Y2 Min DSCR", "Y2 Avg DSCR", "Y2 End Cash"
            ],
            "Value": [
                f"${y1['rev_total']:,.0f}", f"${y1['EBITDA']:,.0f}", 
                f"{y1['min_DSCR']:.2f}", f"{y1['avg_DSCR']:.2f}", f"${y1['end_cash']:,.0f}",
                f"${y2['rev_total']:,.0f}", f"${y2['EBITDA']:,.0f}", 
                f"{y2['min_DSCR']:.2f}", f"{y2['avg_DSCR']:.2f}", f"${y2['end_cash']:,.0f}"
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        
        st.download_button(
            "📄 Download Y1/Y2 Summary",
            data=summary_df.to_csv(index=False).encode("utf-8"),
            file_name=f"veros_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    
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
        
        # Balance Sheet - Year 1 Monthly EOM
        st.divider()
        st.markdown("### 📊 Year 1 Balance Sheet (End of Month)")
        
        # Create Balance Sheet dataframe
        bs_df = pd.DataFrame(bs[:12])
        bs_display = bs_df[[
            'month', 'cash', 'ppe_net', 'total_assets',
            'debt_balance', 'equity', 'total_liabilities_equity'
        ]].copy()
        
        bs_display.columns = [
            'Month', 'Cash', 'PPE (Net)', 'Total Assets',
            'Debt', 'Equity', 'Total L&E'
        ]
        
        # Format currency columns
        for col in bs_display.columns[1:]:
            bs_display[col] = bs_display[col].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(bs_display, use_container_width=True)
        
        # Year 2 EOY Balance Sheet
        st.divider()
        st.markdown("### 📊 Year 2 Balance Sheet (End of Year)")
        
        y2_eoy = bs[23]  # Last month of Y2
        y2_bs_data = {
            "Item": ["Cash", "PPE (Net)", "Total Assets", "Debt", "Equity", "Total L&E"],
            "Amount": [
                f"${y2_eoy['cash']:,.0f}",
                f"${y2_eoy['ppe_net']:,.0f}",
                f"${y2_eoy['total_assets']:,.0f}",
                f"${y2_eoy['debt_balance']:,.0f}",
                f"${y2_eoy['equity']:,.0f}",
                f"${y2_eoy['total_liabilities_equity']:,.0f}"
            ]
        }
        y2_bs_df = pd.DataFrame(y2_bs_data)
        st.dataframe(y2_bs_df, use_container_width=True)
        
        # Export Options
        st.divider()
        st.markdown("### 📥 Financial Statement Exports")
        
        # Prepare full datasets for export
        pnl_y1_df = pd.DataFrame(pnl[:12])
        pnl_24m_df = pd.DataFrame(pnl)
        bs_y1_df = pd.DataFrame(bs[:12])
        bs_y2_eoy_df = pd.DataFrame([bs[23]])  # Just Y2 EOY
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # P&L Y1 Monthly CSV
            st.download_button(
                "📊 P&L Y1 Monthly",
                data=pnl_y1_df.to_csv(index=False).encode("utf-8"),
                file_name=f"PnL_Y1_monthly_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # P&L 24-Month CSV
            st.download_button(
                "📊 P&L 24-Month",
                data=pnl_24m_df.to_csv(index=False).encode("utf-8"),
                file_name=f"PnL_24m_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col3:
            # Balance Sheet Y1 Monthly CSV
            st.download_button(
                "📋 BS Y1 Monthly",
                data=bs_y1_df.to_csv(index=False).encode("utf-8"),
                file_name=f"BS_Y1_monthly_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col4:
            # Balance Sheet Y2 EOY CSV
            st.download_button(
                "📋 BS Y2 EOY",
                data=bs_y2_eoy_df.to_csv(index=False).encode("utf-8"),
                file_name=f"BS_Y2_EOY_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        # Combined Excel Workbook
        st.divider()
        from io import BytesIO
        
        def make_financial_excel(pnl_y1, pnl_24m, bs_y1, bs_y2_eoy):
            bio = BytesIO()
            with pd.ExcelWriter(bio, engine="xlsxwriter") as xw:
                pnl_y1.to_excel(xw, index=False, sheet_name="P&L Y1 Monthly")
                pnl_24m.to_excel(xw, index=False, sheet_name="P&L 24 Months")
                bs_y1.to_excel(xw, index=False, sheet_name="BS Y1 Monthly")
                bs_y2_eoy.to_excel(xw, index=False, sheet_name="BS Y2 EOY")
            bio.seek(0)
            return bio.read()
        
        xlsx_bytes = make_financial_excel(pnl_y1_df, pnl_24m_df, bs_y1_df, bs_y2_eoy_df)
        
        st.download_button(
            "📚 Download Complete Financial Statements (Excel)",
            data=xlsx_bytes,
            file_name=f"financial_statements_{datetime.now().strftime('%Y%m%d')}.xlsx",
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
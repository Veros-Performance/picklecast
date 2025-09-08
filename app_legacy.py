"""
LEGACY — READ-ONLY; DO NOT EDIT

Indoor Pickleball Facility Financial Projections for SBA Loan Application
Generates 2-year financial projections with dynamic scenario modeling
Last updated: 2025-09-03

This file is preserved for reference only. All new development should use app.py and the engine.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import io
import hashlib
from dataclasses import dataclass

# Engine imports
from engine.models import Config, Facility, PrimeWindow, Pricing, LeagueConfig, CorpConfig, Tournaments, Retail
from engine.compute import compute

st.set_page_config(
    page_title="Pickleball Facility Projections",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Authentication function
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # You can change this password to whatever you want
        # For production, consider using environment variables or a more secure method
        correct_password_hash = hashlib.sha256("richmondneedsmorepickle".encode()).hexdigest()
        entered_password_hash = hashlib.sha256(st.session_state["password"].encode()).hexdigest()
        
        if entered_password_hash == correct_password_hash:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.markdown("## 🔐 Authentication Required")
        st.text_input(
            "Please enter password to access the financial projections:",
            type="password",
            on_change=password_entered,
            key="password",
            help="Contact administrator for access"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        st.markdown("## 🔐 Authentication Required")
        st.text_input(
            "Please enter password to access the financial projections:",
            type="password",
            on_change=password_entered,
            key="password",
            help="Contact administrator for access"
        )
        st.error("😕 Password incorrect. Please try again.")
        return False
    else:
        # Password correct
        return True

# Constants
NUM_COURTS = 4
HOURS_PER_DAY = 14  # 8 AM to 10 PM typical operation
DAYS_PER_MONTH = 30
# REMOVED: PRIME_TIME_HOURS_RATIO - now derived from schedule via engine
DEPRECIATION_ANNUAL = 132325  # Based on ~$994k leasehold improvements + ~$220k equipment
MEMBER_CAP = 350

# Pricing unit constants
PRICING_UNIT_COURT = "per_court_hour"
LEAGUE_PRICING_UNIT = "per_slot_session"

# Legacy density functions removed - now using engine for all density calculations

# PRICING REGISTRY - Single source of truth for all pricing
pricing = {
    "nm_prime_per_court": 65.0,      # Non-member prime per court hour
    "nm_off_per_court": 56.0,        # Non-member off-peak per court hour
    "member_prime_per_court": 0.0,   # Member prime per court hour (usually free)
    "member_off_per_court": 0.0,     # Member off-peak per court hour (usually free)
    "league_prime_per_slot_6wk": 150.0,  # League prime per player slot for 6 weeks
    "league_off_per_slot_6wk": 100.0,    # League off-peak per player slot for 6 weeks
    "corp_prime_per_court": 200.0,   # Corporate prime per court hour
    "corp_off_per_court": 170.0,     # Corporate off-peak per court hour
}

# Legacy constants for backward compatibility (will migrate these to use pricing dict)
NON_MEMBER_RATE_PRIME_COURT_DEFAULT = pricing["nm_prime_per_court"]
NON_MEMBER_RATE_OFFPEAK_COURT_DEFAULT = pricing["nm_off_per_court"]
LEAGUE_PRICE_PRIME_SLOT_DEFAULT = pricing["league_prime_per_slot_6wk"]
LEAGUE_PRICE_OFFPEAK_SLOT_DEFAULT = pricing["league_off_per_slot_6wk"]

def get_cfg_from_ui(
    prime_start_weekday_val=16.0, prime_end_mon_thu_val=22.0, prime_end_fri_val=21.0,
    weekend_morning_hours_val=4.0, league_session_length_hours_val=1.5, 
    league_buffer_minutes_val=10, league_evenings_per_week_val=4,
    league_weekend_mornings_val=1, courts_used_val=NUM_COURTS,
    league_fill_rate_val=0.9, active_league_weeks_per_year_val=46,
    corporate_frequency_val=2, corporate_hours_per_event_val=6.0,
    corporate_rate_prime_val=200.0, corporate_rate_offpeak_val=170.0,
    tournament_frequency_val=1, tournament_revenue_val=9000.0,
    retail_monthly_sales_val=3000.0, retail_revenue_share_val=0.20,
    retail_gross_margin_pct_val=0.40
):
    """Build a Config from current Streamlit widgets"""
    # Read from existing widgets if they exist; else use defaults that match our assumptions
    courts = NUM_COURTS  # Using the constant 4
    hours_per_day = HOURS_PER_DAY  # Using the constant 14

    # Prime window (aggressive ~37.8%)
    mon_thu_start = prime_start_weekday_val
    mon_thu_end = prime_end_mon_thu_val
    fri_start = prime_start_weekday_val  # Same as weekday start
    fri_end = prime_end_fri_val
    wknd_morn = weekend_morning_hours_val

    # Pricing (per court-hour for non-members; members included in dues)
    nm_prime = pricing["nm_prime_per_court"]
    nm_off = pricing["nm_off_per_court"]

    # Leagues (prime pricing per slot per 6-week session)
    lg_len_h = league_session_length_hours_val
    lg_buffer_m = league_buffer_minutes_val
    lg_nights = league_evenings_per_week_val
    lg_wknd = league_weekend_mornings_val
    lg_courts = courts_used_val
    lg_ppc = 4  # Players per court, default 4
    lg_fill = league_fill_rate_val
    lg_weeks = active_league_weeks_per_year_val
    lg_price_p = pricing["league_prime_per_slot_6wk"]
    lg_price_o = pricing["league_off_per_slot_6wk"]

    # Corporate (assume prime by default)
    corp_events_pm = corporate_frequency_val
    corp_hours_evt = corporate_hours_per_event_val
    corp_courts = courts  # Use all courts for corporate events
    corp_rate_prime = corporate_rate_prime_val
    corp_rate_off = corporate_rate_offpeak_val

    # Tournament & Retail
    t_freq = tournament_frequency_val
    t_rev_evt = tournament_revenue_val
    t_rev_q = t_rev_evt * t_freq  # Revenue per quarter
    t_share = 0.40  # Default 40% sponsorship share
    r_sales = retail_monthly_sales_val
    r_share = retail_revenue_share_val / 100.0 if retail_revenue_share_val > 1 else retail_revenue_share_val  # Convert to fraction if needed
    r_gm = retail_gross_margin_pct_val / 100.0 if retail_gross_margin_pct_val > 1 else retail_gross_margin_pct_val  # Convert to fraction if needed

    cfg = Config(
        facility=Facility(courts=courts, hours_per_day=hours_per_day),
        prime=PrimeWindow(
            mon_thu_start=mon_thu_start, mon_thu_end=mon_thu_end,
            fri_start=fri_start, fri_end=fri_end, weekend_morning_hours=wknd_morn
        ),
        pricing=Pricing(nm_prime_per_court=nm_prime, nm_off_per_court=nm_off,
                        member_prime_per_court=0.0, member_off_per_court=0.0),
        league=LeagueConfig(session_len_h=lg_len_h, buffer_min=lg_buffer_m,
                            weeknights=lg_nights, weekend_morns=lg_wknd,
                            courts_used=lg_courts, players_per_court=lg_ppc,
                            fill_rate=lg_fill, active_weeks=lg_weeks,
                            price_prime_slot_6wk=lg_price_p, price_off_slot_6wk=lg_price_o),
        corp=CorpConfig(prime_rate_per_court=corp_rate_prime, off_rate_per_court=corp_rate_off,
                        events_per_month=corp_events_pm, hours_per_event=corp_hours_evt, courts_used=corp_courts),
        tourneys=Tournaments(per_quarter_revenue=t_rev_q, sponsorship_share=t_share),
        retail=Retail(monthly_sales=r_sales, gross_margin=r_gm, revenue_share=r_share),
    )
    return cfg

# Check authentication before showing the main app
if not check_password():
    st.stop()

st.title("🎾 Indoor Pickleball Facility - SBA Loan Financial Projections [v9-RevPACH-Fix]")
st.markdown("### 2-Year Financial Model for SBA Loan Application")

# Placeholder for banner - will be updated after engine computation
banner_placeholder = st.empty()

# Initialize session state for inputs
if 'inputs' not in st.session_state:
    st.session_state.inputs = {}

# Sidebar for Assumptions
with st.sidebar:
    st.header("📊 Assumptions")
    
    # Debug Mode
    show_debug = st.checkbox(
        "Show Debug Reconciliation",
        value=False,
        help="Display detailed capacity and revenue calculations"
    )
    
    # Facility Constants (Display Only)
    st.subheader("Facility Constants")
    st.info(f"**Number of Courts:** {NUM_COURTS}")
    st.info(f"**Hours per Day:** {HOURS_PER_DAY}")
    st.info(f"**Member Cap:** {MEMBER_CAP}")
    # Prime share is now schedule-driven, shown after engine computation
    
    # Analysis Start Date
    start_date = st.date_input(
        "Analysis Start Date",
        value=date(2026, 8, 1),
        help="The month when the facility will open"
    )
    
    st.divider()
    
    # Court Pricing Model
    st.subheader("Court Pricing Model")
    
    base_prime_rate = st.number_input(
        "Non-Member Rate (Prime) — per court / hr",
        min_value=20.0,
        max_value=200.0,
        value=pricing["nm_prime_per_court"],  # $65/hr PER COURT
        step=5.0,
        help="Peak hours rate for non-members PER COURT HOUR"
    )
    # Update pricing registry
    pricing["nm_prime_per_court"] = base_prime_rate
    
    non_prime_rate = st.number_input(
        "Non-Member Rate (Off-Peak) — per court / hr",
        min_value=20.0,
        max_value=200.0,
        value=pricing["nm_off_per_court"],  # $56/hr PER COURT
        step=5.0,
        help="Off-peak hours rate for non-members PER COURT HOUR"
    )
    # Update pricing registry
    pricing["nm_off_per_court"] = non_prime_rate
    
    st.caption("📋 Court bookings are priced per court per hour. Per-player equivalents shown for context only.")
    st.caption(f"💡 Doubles equivalent: Prime ≈${base_prime_rate/4:.2f}/player, Off-peak ≈${non_prime_rate/4:.2f}/player")
    
    # Member discount calculation
    # Members typically play for free (membership includes court access)
    # or pay a heavily discounted rate
    members_play_free = st.checkbox(
        "Members play free (court access included in membership)",
        value=True,
        help="If unchecked, members pay a discounted court rate"
    )
    
    if members_play_free:
        member_court_rate_prime = 0.0
        member_court_rate_offpeak = 0.0
        st.caption("**Members: Free court access (included in membership)**")
    else:
        member_discount = st.slider(
            "Member Court Rate Discount (%)",
            min_value=0,
            max_value=75,
            value=50,
            help="Percentage discount for members on court rates"
        )
        member_court_rate_prime = base_prime_rate * (1 - member_discount / 100)
        member_court_rate_offpeak = non_prime_rate * (1 - member_discount / 100)
        st.caption(f"**Member Court Rates: Prime ${member_court_rate_prime:.2f}/court/hr, Off-peak ${member_court_rate_offpeak:.2f}/court/hr**")
    
    st.divider()
    
    # Membership Model
    st.subheader("Membership Model")
    
    player_tier_fee = st.number_input(
        "Player Tier Monthly Fee ($)",
        min_value=0.0,
        max_value=500.0,
        value=95.0,
        step=5.0
    )
    
    pro_tier_fee = st.number_input(
        "Pro Tier Monthly Fee ($)",
        min_value=0.0,
        max_value=500.0,
        value=179.0,
        step=5.0
    )
    
    # Monthly Member Count Schedule
    member_schedule_default = "50, 70, 90, 115, 140, 170, 195, 230, 265, 300, 325, 350"  # Capped at 350
    member_schedule_input = st.text_input(
        "Monthly Member Count Schedule (Year 1)",
        value=member_schedule_default,
        help="Enter 12 comma-separated numbers for member count at end of each month"
    )
    
    # Parse member schedule with cap enforcement
    try:
        member_schedule = [min(int(x.strip()), MEMBER_CAP) for x in member_schedule_input.split(',')]
        if len(member_schedule) != 12:
            st.error(f"Please provide exactly 12 member counts (max {MEMBER_CAP} each)")
            member_schedule = [min(x, MEMBER_CAP) for x in [50, 70, 90, 115, 140, 170, 195, 230, 265, 300, 325, 350]]
    except:
        st.error("Invalid member schedule format. Using defaults.")
        member_schedule = [min(x, MEMBER_CAP) for x in [50, 70, 90, 115, 140, 170, 195, 230, 265, 300, 325, 350]]
    
    # Tier Mix Sliders
    st.markdown("**Membership Tier Mix** (Must total 100%)")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        community_pct = st.number_input(
            "Community %",
            min_value=0,
            max_value=100,
            value=20,
            step=5
        )
    
    with col2:
        player_pct = st.number_input(
            "Player %",
            min_value=0,
            max_value=100,
            value=60,
            step=5
        )
    
    with col3:
        pro_pct = st.number_input(
            "Pro %",
            min_value=0,
            max_value=100,
            value=20,
            step=5
        )
    
    total_pct = community_pct + player_pct + pro_pct
    if total_pct != 100:
        st.error(f"⚠️ Tier percentages must total 100% (Currently: {total_pct}%). Calculations paused.")
        st.stop()
    
    st.divider()
    
    # Prime Window & League Schedule
    st.subheader("Prime Window & League Schedule")
    
    # Prime window definition (aggressive)
    prime_start_weekday = st.number_input(
        "Prime Start (Weekdays, 24h)", 
        min_value=0.0, 
        max_value=24.0, 
        value=16.0, 
        step=0.5,
        help="4pm start time for aggressive prime window"
    )
    
    prime_end_mon_thu = st.number_input(
        "Prime End (Mon–Thu, 24h)", 
        min_value=0.0, 
        max_value=24.0, 
        value=22.0, 
        step=0.5,
        help="10pm end time for Monday-Thursday"
    )
    
    prime_end_fri = st.number_input(
        "Prime End (Fri, 24h)", 
        min_value=0.0, 
        max_value=24.0, 
        value=21.0, 
        step=0.5,
        help="9pm end time for Friday"
    )
    
    weekend_morning_hours = st.number_input(
        "Weekend Prime Morning Hours", 
        min_value=0.0, 
        max_value=8.0, 
        value=4.0, 
        step=0.5,
        help="Hours of prime time on weekend mornings (e.g., 8am-12pm = 4 hours)"
    )
    
    st.divider()
    
    # League scheduling inputs
    st.subheader("League Programming")
    
    # Which days actually run leagues (not every night)
    league_evenings_per_week = st.slider(
        "Weeknights with Leagues (Mon–Fri)", 
        min_value=0, 
        max_value=5, 
        value=4,
        help="Number of weekday evenings that run leagues"
    )
    
    league_weekend_mornings = st.slider(
        "Weekend Mornings with Leagues", 
        min_value=0, 
        max_value=2, 
        value=1,
        help="Number of weekend mornings that run leagues"
    )
    
    # League block setup
    league_session_length_hours = st.number_input(
        "League Session Length (hours)", 
        min_value=1.0, 
        max_value=2.0, 
        value=1.5, 
        step=0.25,
        help="90-minute sessions for better experience"
    )
    
    league_buffer_minutes = st.number_input(
        "Buffer Between League Blocks (minutes)", 
        min_value=0, 
        max_value=30, 
        value=10, 
        step=5,
        help="Time between league blocks for transitions"
    )
    
    use_all_courts_for_league = st.checkbox(
        "Use ALL Courts for League Blocks", 
        value=True,
        help="If checked, all courts are used during league blocks"
    )
    
    if not use_all_courts_for_league:
        courts_used = st.slider(
            "Courts Used for League Blocks", 
            min_value=1, 
            max_value=NUM_COURTS, 
            value=NUM_COURTS
        )
    else:
        courts_used = NUM_COURTS
    
    # League pricing (per slot / 6-week session)
    col1, col2 = st.columns(2)
    with col1:
        league_price_offpeak = st.number_input(
            "League Price (Off-Peak, per player, 6 weeks)",
            min_value=0.0,
            max_value=500.0,
            value=pricing["league_off_per_slot_6wk"],  # $100
            step=5.0,
            help="Off-peak league fee per player for full 6-week session"
        )
        # Update pricing registry
        pricing["league_off_per_slot_6wk"] = league_price_offpeak
    
    with col2:
        league_price_prime = st.number_input(
            "League Price (Prime, per player, 6 weeks)",
            min_value=0.0,
            max_value=500.0,
            value=pricing["league_prime_per_slot_6wk"],  # $150
            step=5.0,
            help="Prime-time league fee per player for full 6-week session"
        )
        # Update pricing registry
        pricing["league_prime_per_slot_6wk"] = league_price_prime
    
    st.caption("📋 League fees are per player (per slot) for a 6-week session.")
    
    # For backward compatibility, use prime price as default
    league_price = league_price_prime
    
    # Realism toggles
    league_fill_rate = st.slider(
        "League Fill Rate", 
        min_value=0.5, 
        max_value=1.0, 
        value=0.9, 
        step=0.05,
        help="Percentage of league slots that are filled"
    )
    
    active_league_weeks_per_year = st.slider(
        "Active League Weeks / Year", 
        min_value=40, 
        max_value=52, 
        value=46, 
        step=1,
        help="Weeks per year leagues run (excluding holidays/breaks)"
    )
    
    # Keep these for compatibility but they'll be overridden by schedule
    league_sellthrough = league_fill_rate * 100  # Convert to percentage
    league_scheduling_efficiency = 90  # Default efficiency
    backfill_league_hours = st.checkbox(
        "Backfill unfilled league hours to rentals?",
        value=True,
        help="If checked, unfilled league hours become available for court rentals"
    )
    
    st.divider()
    
    # Corporate Activities
    st.subheader("Corporate Activities")
    
    col1, col2 = st.columns(2)
    with col1:
        corporate_rate_prime = st.number_input(
            "Corporate Prime Rate ($/Hour)",
            min_value=0.0,
            max_value=500.0,
            value=200.0,  # New: $200/hr prime
            step=10.0,
            help="Corporate event rate during prime hours: $200/hr"
        )
    
    with col2:
        corporate_rate_offpeak = st.number_input(
            "Corporate Off-Peak Rate ($/Hour)",
            min_value=0.0,
            max_value=500.0,
            value=170.0,  # New: $170/hr off-peak
            step=10.0,
            help="Corporate event rate during off-peak hours: $170/hr"
        )
    
    corporate_frequency = st.number_input(
        "Corporate Event Frequency (per month)",
        min_value=0,
        max_value=10,
        value=2,  # default 2 for Year 2 planning
        step=1,
        help="Number of corporate team-building events per month"
    )
    
    corporate_hours_per_event = st.number_input(
        "Corporate Event Duration (hours)",
        min_value=0,
        max_value=20,
        value=6,
        step=1,
        help="Average duration of corporate events (hours)"
    )
    
    # Calculate revenue per event based on prime/off-peak split (assume 70% prime for corporate)
    corporate_revenue_per_event = (corporate_hours_per_event * 
                                  (0.7 * corporate_rate_prime + 0.3 * corporate_rate_offpeak))
    
    st.divider()
    
    # Tournament Events
    st.subheader("Tournament Events")
    
    tournament_frequency = st.number_input(
        "Tournament Frequency (per quarter)",
        min_value=0,
        max_value=3,
        value=1,
        step=1,
        help="Number of weekend tournaments per quarter"
    )
    
    tournament_revenue = st.number_input(
        "Tournament Revenue ($ per tournament)",
        min_value=0.0,
        max_value=50000.0,
        value=9000.0,
        step=500.0,
        help="Revenue per tournament event"
    )
    
    tournament_hours = st.number_input(
        "Tournament Utilization (hours per tournament)",
        min_value=0,
        max_value=100,
        value=40,
        step=5,
        help="Total court hours consumed per tournament (weekend)"
    )
    
    st.divider()
    
    # Retail Pop-up Store
    st.subheader("Retail Pop-up Store")
    
    retail_monthly_sales = st.number_input(
        "Retail Monthly Sales ($ gross)",
        min_value=0.0,
        max_value=20000.0,
        value=3000.0,
        step=100.0,
        help="Gross monthly sales from paddle/equipment pop-up store"
    )
    
    retail_revenue_share = st.slider(
        "Revenue Share to Facility (%)",
        min_value=0,
        max_value=50,
        value=20,
        help="Percentage of retail sales kept by facility"
    )
    
    retail_gross_margin_pct = st.slider(
        "Retail Gross Margin on Sales (%)",
        min_value=0, max_value=100, value=40,
        help="Vendor margin on sales; your share applies to profits, not gross sales"
    )
    
    st.divider()
    
    # General Assumptions
    st.subheader("General Assumptions")
    
    # Growth Curve Inputs
    st.markdown("**Growth Curve**")
    col1, col2 = st.columns(2)
    
    with col1:
        start_utilization = st.number_input(
            "Start of Year Utilization (%)",
            min_value=0.0,
            max_value=100.0,
            value=50.0,
            step=5.0,
            help="Utilization at month 1"
        )
    
    with col2:
        end_utilization = st.number_input(
            "End of Year Utilization (%)",
            min_value=0.0,
            max_value=100.0,
            value=80.0,
            step=5.0,
            help="Utilization at month 12"
        )
    
    member_play_ratio_cap = st.slider(
        "Max Member Play Mix (Prime, %)",
        min_value=50, max_value=90, value=70, step=5,
        help="Upper bound on member share of prime-time court hours"
    ) / 100.0
    
    # Non-member demand cap for prime hours
    nonmember_prime_share_max = st.slider(
        "Max Non-Member Share of OPEN Prime Hours (%)",
        min_value=10,
        max_value=40,
        value=25,  # Default 25% max for non-members
        step=5,
        help="Cap on non-member share of prime-time open play hours (after leagues/corporate/tournaments)"
    ) / 100.0
    
    # Seasonal Adjustment Inputs
    st.markdown("**Seasonal Adjustments**")
    
    month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    low_season_months = st.multiselect(
        "Low Season Months",
        options=month_names,
        default=['June', 'July'],
        help="Select months with reduced utilization"
    )
    
    seasonal_dip = st.slider(
        "Seasonal Dip Multiplier (%)",
        min_value=0,
        max_value=50,
        value=15,
        help="Percentage reduction in utilization for selected months"
    )
    
    # Calculate ramp-up percentages with seasonal adjustments
    rampup_percentages = []
    for i in range(12):
        # Linear interpolation for baseline
        baseline = start_utilization + (end_utilization - start_utilization) * (i / 11)
        
        # Apply seasonal adjustment if applicable
        month_idx = (start_date.month + i - 1) % 12
        month_name = month_names[month_idx]
        
        if month_name in low_season_months:
            final_utilization = baseline * (1 - seasonal_dip / 100)
        else:
            final_utilization = baseline
        
        rampup_percentages.append(np.clip(final_utilization / 100, 0, 1))
    
    # Visualization of utilization curve
    st.markdown("**Projected Monthly Utilization**")
    
    # Create month labels for the chart
    chart_months = []
    for i in range(12):
        month_date = start_date + relativedelta(months=i)
        chart_months.append(month_date.strftime("%b"))
    
    # Create a simple bar chart using Plotly
    import plotly.graph_objects as go
    
    fig_util = go.Figure(data=[
        go.Bar(
            x=chart_months,
            y=[p * 100 for p in rampup_percentages],
            marker_color=['lightcoral' if month_names[(start_date.month + i - 1) % 12] in low_season_months 
                         else 'lightblue' for i in range(12)],
            text=[f"{p*100:.1f}%" for p in rampup_percentages],
            textposition='outside'
        )
    ])
    
    fig_util.update_layout(
        height=250,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Month",
        yaxis_title="Utilization %",
        yaxis_range=[0, 100],
        showlegend=False
    )
    
    st.plotly_chart(fig_util, use_container_width=True)
    
    fixed_costs = st.number_input(
        "Total Monthly Fixed Costs ($)",
        min_value=0.0,
        max_value=200000.0,
        value=62000.0,  # Updated to $62,000
        step=1000.0,
        help="Year 1: Rent ~$37k, Payroll/Insurance/Other ~$25k"
    )
    
    rent_abatement_months = st.number_input(
        "Rent Abatement (Free Rent Months)",
        min_value=0,
        max_value=12,
        value=0,  # Changed default from 6 to 0
        step=1,
        help="Number of months with free rent at the beginning of operations"
    )
    
    lease_term_years = st.number_input(
        "Lease Term (Years)",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        help="Length of the lease agreement (for context only)"
    )
    
    annual_rent_escalator = st.number_input(
        "Annual Rent Escalator (%)",
        min_value=0.0,
        max_value=10.0,
        value=3.0,
        step=0.5,
        help="Annual percentage increase in rent"
    )
    
    other_fixed_escalator = st.number_input(
        "Other Fixed Costs Escalator (%)",
        min_value=0.0,
        max_value=10.0,
        value=3.0,
        step=0.5,
        help="Annual percentage increase in non-rent fixed costs (payroll, insurance, etc.)"
    )
    
    # Calculate rent portion (60% of fixed costs)
    base_rent_portion = fixed_costs * 0.60
    base_non_rent_fixed = fixed_costs - base_rent_portion
    
    variable_cost_pct = st.number_input(
        "Variable Costs (% of Revenue)",
        min_value=0.0,
        max_value=50.0,
        value=15.0,
        step=1.0
    )
    
    st.divider()
    
    # Startup Costs & Loan Calculation
    st.subheader("💰 Startup Costs & Loan Calculation")
    
    # Costing Method Selector
    cost_method = st.selectbox(
        "Select Construction Cost Method",
        options=["Fixed Quote Amount", "Estimate per Square Foot"],
        index=0,  # Default to "Fixed Quote Amount"
        help="Choose between a fixed construction quote or square footage estimation"
    )
    
    # A. Construction Cost (conditional based on method)
    st.markdown("**Construction Costs**")
    
    if cost_method == "Fixed Quote Amount":
        calculated_construction_cost = st.number_input(
            "Total Construction Cost ($)",
            min_value=100000.0,
            max_value=5000000.0,
            value=994000.0,  # Default for phased buildout
            step=10000.0,
            help="Fixed construction quote amount"
        )
    else:  # Estimate per Square Foot
        col1, col2 = st.columns(2)
        
        with col1:
            building_sf = st.number_input(
                "Building Square Footage (SF)",
                min_value=1000.0,
                max_value=50000.0,
                value=17139.0,
                step=100.0,
                help="Total square footage of the facility"
            )
        
        with col2:
            cost_per_sf = st.number_input(
                "Construction Cost per SF ($)",
                min_value=50.0,
                max_value=300.0,
                value=97.0,
                step=5.0,
                help="Average construction cost per square foot"
            )
        
        calculated_construction_cost = building_sf * cost_per_sf
        st.info(f"**Calculated Construction Cost:** ${calculated_construction_cost:,.0f}")
    
    # B. Other Itemized Startup Costs
    st.markdown("**Other Startup Costs**")
    
    ffe_cost = st.number_input(
        "FF&E (Furniture, Fixtures, Equipment) ($)",
        min_value=0.0,
        max_value=500000.0,
        value=75000.0,
        step=5000.0,
        help="Courts, nets, seating, equipment, etc."
    )
    
    signage_cost = st.number_input(
        "Signage & Branding ($)",
        min_value=0.0,
        max_value=100000.0,
        value=15000.0,
        step=1000.0,
        help="Interior and exterior signage, branding materials"
    )
    
    preopening_cost = st.number_input(
        "Pre-Opening & Marketing ($)",
        min_value=0.0,
        max_value=500000.0,
        value=66000.0,
        step=5000.0,
        help="Marketing, initial inventory, pre-opening expenses"
    )
    
    working_capital_reserve = st.number_input(
        "Working Capital Reserve ($)",
        min_value=0.0,
        max_value=500000.0,
        value=100000.0,
        step=10000.0,
        help="Operating cash reserve to cover early months negative cash flow"
    )
    
    # C. Project Contingency
    st.markdown("**Project Contingency**")
    contingency_pct = st.slider(
        "Contingency (% of Construction)",
        min_value=0,
        max_value=25,
        value=10,
        help="Buffer for unexpected costs as percentage of construction"
    )
    
    calculated_contingency = calculated_construction_cost * (contingency_pct / 100)
    st.info(f"**Calculated Contingency Amount:** ${calculated_contingency:,.0f}")
    
    # Additional Funding Sources
    st.markdown("**Funding Sources**")
    
    ti_allowance_per_sf = st.number_input(
        "TI Allowance per SF ($)",
        min_value=0.0,
        max_value=100.0,
        value=25.0,
        step=5.0,
        help="Tenant improvement allowance per square foot"
    )
    
    # Calculate total TI allowance based on building size
    # Use a default building size if not in "Estimate per Square Foot" mode
    if cost_method == "Estimate per Square Foot":
        total_ti_allowance = ti_allowance_per_sf * building_sf
    else:
        # Use standard building size for fixed quote method
        default_building_sf = 17139.0
        total_ti_allowance = ti_allowance_per_sf * default_building_sf
    
    st.info(f"**Total TI Allowance:** ${total_ti_allowance:,.0f}")
    
    landlord_allowance = total_ti_allowance  # Use calculated value
    
    owner_equity = st.number_input(
        "Owner Equity Injection ($)",
        min_value=0.0,
        max_value=1000000.0,
        value=200000.0,
        step=10000.0,
        help="Cash equity contribution from owners"
    )
    
    # D. Final Calculated Total
    total_project_cost = (calculated_construction_cost + 
                         ffe_cost + 
                         signage_cost + 
                         preopening_cost + 
                         working_capital_reserve +
                         calculated_contingency)
    
    loan_amount = total_project_cost - landlord_allowance - owner_equity
    
    st.info(f"**Total Project Cost:** ${total_project_cost:,.0f}")
    st.success(f"**Required SBA Loan Amount:** ${loan_amount:,.0f}")
    
    st.divider()
    
    # SBA Loan Terms
    st.subheader("📋 SBA Loan Terms")
    
    interest_rate = st.slider(
        "Interest Rate (%)",
        min_value=1.0,
        max_value=15.0,
        value=9.0,
        step=0.1
    )
    
    loan_term_years = st.number_input(
        "Loan Term (Years)",
        min_value=1,
        max_value=30,
        value=10,
        step=1
    )

# Calculate loan payments
monthly_interest_rate = interest_rate / 100 / 12
num_payments = loan_term_years * 12
if loan_amount > 0 and monthly_interest_rate > 0:
    monthly_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate)**num_payments) / \
                     ((1 + monthly_interest_rate)**num_payments - 1)
else:
    monthly_payment = 0

# Loan amortization schedule with rolling balance
def amort_schedule(loan_amt, r_mo, n):
    """Calculate proper loan amortization with decreasing balance"""
    bal = loan_amt
    sched = []
    pmt = 0 if r_mo == 0 or loan_amt <= 0 else loan_amt * (r_mo * (1+r_mo)**n) / ((1+r_mo)**n - 1)
    for _ in range(n):
        interest = bal * r_mo
        principal = max(pmt - interest, 0)
        bal = max(bal - principal, 0)
        sched.append((principal, interest, pmt, bal))
    return sched

# Generate amortization schedule
amort = amort_schedule(loan_amount, monthly_interest_rate, num_payments)

# Rate audit function to catch unit bleed
def audit_rates(debug_data, pricing):
    """Audit configured vs implied rates to catch unit bleed"""
    audit_results = []
    
    for i, month_data in enumerate(debug_data):
        month = month_data.get('month', f'Month {i+1}')
        
        # Calculate implied rates from revenue and hours
        nm_prime_hours = month_data.get('nm_prime_hours', 0)
        nm_prime_rev = month_data.get('nm_prime_revenue', 0)
        nm_off_hours = month_data.get('nm_offpeak_hours', 0)
        nm_off_rev = month_data.get('nm_offpeak_revenue', 0)
        
        implied_nm_prime = nm_prime_rev / nm_prime_hours if nm_prime_hours > 0 else 0
        implied_nm_off = nm_off_rev / nm_off_hours if nm_off_hours > 0 else 0
        
        # League implied rates
        league_slots = month_data.get('league_slots_filled', 0)
        league_rev = month_data.get('league_revenue', 0)
        implied_league = (league_rev * 6) / league_slots if league_slots > 0 else 0  # Convert to 6-week rate
        
        audit_results.append({
            'Month': month,
            'NM Prime Configured': pricing['nm_prime_per_court'],
            'NM Prime Implied': implied_nm_prime,
            'NM Prime Match': abs(implied_nm_prime - pricing['nm_prime_per_court']) < 0.01,
            'NM Off Configured': pricing['nm_off_per_court'],
            'NM Off Implied': implied_nm_off,
            'NM Off Match': abs(implied_nm_off - pricing['nm_off_per_court']) < 0.01,
            'League Configured': pricing['league_prime_per_slot_6wk'],
            'League Implied': implied_league,
            'League Match': abs(implied_league - pricing['league_prime_per_slot_6wk']) < 1.0,
        })
    
    return audit_results

# Sanity check function
def run_sanity_checks(prime_share, league_share, member_counts, debug_data=None):
    """Run assertions to validate calculations"""
    errors = []
    
    # Check prime share is realistic
    if not (0.15 <= prime_share <= 0.35):
        errors.append(f"Prime share {prime_share*100:.0f}% out of realistic bounds (15-35%)")
    
    # Check league share
    if league_share > 0.80:
        errors.append(f"League share {league_share*100:.0f}% too high (max 80% recommended)")
    
    # Check member cap
    max_members = max(member_counts) if member_counts else 0
    if max_members > MEMBER_CAP:
        errors.append(f"Member count {max_members} exceeds cap {MEMBER_CAP}")
    
    avg_members = sum(member_counts) / len(member_counts) if member_counts else 0
    if avg_members > MEMBER_CAP:
        errors.append(f"Average members {avg_members:.0f} exceeds cap {MEMBER_CAP}")
    
    # Check capacity allocation if debug data provided
    if debug_data:
        for month_data in debug_data:
            # Verify prime hours not over-allocated
            prime_total = month_data.get('prime_hours_total', 0)
            prime_used = (
                month_data.get('league_prime_hours', 0) +
                month_data.get('corp_prime_hours', 0) +
                month_data.get('tourn_prime_hours', 0) +
                month_data.get('open_prime_hours', 0)
            )
            if prime_used > prime_total + 1e-6:
                errors.append(f"Prime hours over-allocated in {month_data.get('month', 'unknown')}: {prime_used:.0f} > {prime_total:.0f}")
    
    return errors

# Call the engine to compute results
cfg = get_cfg_from_ui(
    prime_start_weekday_val=prime_start_weekday,
    prime_end_mon_thu_val=prime_end_mon_thu,
    prime_end_fri_val=prime_end_fri,
    weekend_morning_hours_val=weekend_morning_hours,
    league_session_length_hours_val=league_session_length_hours,
    league_buffer_minutes_val=league_buffer_minutes,
    league_evenings_per_week_val=league_evenings_per_week,
    league_weekend_mornings_val=league_weekend_mornings,
    courts_used_val=courts_used,
    league_fill_rate_val=league_fill_rate,
    active_league_weeks_per_year_val=active_league_weeks_per_year,
    corporate_frequency_val=corporate_frequency,
    corporate_hours_per_event_val=corporate_hours_per_event,
    corporate_rate_prime_val=corporate_rate_prime,
    corporate_rate_offpeak_val=corporate_rate_offpeak,
    tournament_frequency_val=tournament_frequency,
    tournament_revenue_val=tournament_revenue,
    retail_monthly_sales_val=retail_monthly_sales,
    retail_revenue_share_val=retail_revenue_share,
    retail_gross_margin_pct_val=retail_gross_margin_pct
)

# Compute results using the engine with default utilization rates
engine_res = compute(cfg, member_play_ratio=0.6, prime_utilization=0.85, offpeak_utilization=0.51)

# Single source-of-truth helpers from engine
def engine_prime_share(res):
    return res["prime_ch_week"] / max(1e-6, res["total_ch_week"])

def engine_variable_revenue_year(res):
    return float(res["annual"]["variable_rev"])

def engine_available_hours_year(res):
    return float(res["available_ch_year"])

def engine_utilized_hours_year(res):
    return float(res["utilized_ch_year"])  # from engine allocation; must be <= available

# Verify utilized <= available
avail_ch = engine_available_hours_year(engine_res)
util_ch = engine_utilized_hours_year(engine_res)
assert util_ch <= avail_ch + 1e-6, f"Utilized CH exceeds available ({util_ch:.0f} > {avail_ch:.0f})"

# Update banner with engine results
prime_share = engine_prime_share(engine_res)
banner_placeholder.info(f"""
**Revenue Streams:** Memberships • Court Rentals (NM: ${cfg.pricing.nm_prime_per_court:.0f}/${cfg.pricing.nm_off_per_court:.0f}) • Leagues (${cfg.league.price_prime_slot_6wk:.0f}/${cfg.league.price_off_slot_6wk:.0f}) • Corporate (${cfg.corp.prime_rate_per_court:.0f}/${cfg.corp.off_rate_per_court:.0f}) • Tournaments • Retail
**Prime Time:** {prime_share*100:.1f}% of hours (schedule-driven, {cfg.prime.mon_thu_start:.0f}-{cfg.prime.mon_thu_end:.0f}pm weekdays + weekend mornings) • Weekly League: {engine_res['weekly']['league_slots']:.0f} slots, {engine_res['weekly']['league_blocks']:.0f} blocks
""".strip())

# Calculate schedule-driven prime hours and league capacity
# 1) Block length with buffer (hours)
block_slot_hours = float(league_session_length_hours) + float(league_buffer_minutes) / 60.0
# Expect ~1.6667 for 90m + 10m

# 2) Prime windows (hours per night)
weekday_window_mon_thu = max(0.0, prime_end_mon_thu - prime_start_weekday)   # expect 6.0
weekday_window_fri = max(0.0, prime_end_fri - prime_start_weekday)           # expect 5.0
weekend_window_hours = float(weekend_morning_hours)                          # expect 4.0

# 3) Blocks per night (floor)
blocks_per_mon_thu = math.floor(weekday_window_mon_thu / block_slot_hours) if weekday_window_mon_thu > 0 else 0
blocks_per_fri = math.floor(weekday_window_fri / block_slot_hours) if weekday_window_fri > 0 else 0
blocks_per_weekend = math.floor(weekend_window_hours / block_slot_hours) if weekend_window_hours > 0 else 0

# Nights actually running leagues (inputs)
mon_thu_league_nights = int(min(league_evenings_per_week, 4))
fri_league_nights = int(max(0, league_evenings_per_week - mon_thu_league_nights))
weekend_league_morns = int(league_weekend_mornings)

# 4) Weekly blocks and slots
players_per_court = 4  # doubles

league_blocks_per_week = (
    mon_thu_league_nights * blocks_per_mon_thu +
    fri_league_nights * blocks_per_fri +
    weekend_league_morns * blocks_per_weekend
)

players_per_block = players_per_court * courts_used
weekly_league_slots = league_blocks_per_week * players_per_block
filled_weekly_slots = math.floor(weekly_league_slots * league_fill_rate)

# Revenue recognition
weekly_rev_per_slot = league_price_prime / 6.0  # per 6-week session → per-week
weekly_league_revenue = filled_weekly_slots * weekly_rev_per_slot
annual_league_revenue = weekly_league_revenue * active_league_weeks_per_year

# Prime hours per week (for capacity check)
prime_hours_mon_thu = 4 * weekday_window_mon_thu  # 4 nights
prime_hours_fri = 1 * weekday_window_fri  # 1 night
prime_hours_weekend = weekend_window_hours * 2  # 2 days

prime_court_hours_week = NUM_COURTS * (prime_hours_mon_thu + prime_hours_fri + prime_hours_weekend)
league_court_hours_week = league_blocks_per_week * block_slot_hours * courts_used

# League share of prime (derived from schedule, not fixed)
league_share_prime = min(1.0, league_court_hours_week / max(1e-6, prime_court_hours_week))

# For compatibility, set league_prime_hours_pct based on schedule
league_prime_hours_pct = league_share_prime * 100  # Convert to percentage

# For backward compatibility
prime_hours_total_per_week = prime_court_hours_week
filled_league_slots = filled_weekly_slots

# 5) Assertions (catch unit bugs)
assert abs(block_slot_hours - (league_session_length_hours + league_buffer_minutes/60.0)) < 1e-6, "Block slot hours calculation error"
assert blocks_per_mon_thu >= 0 and blocks_per_fri >= 0 and blocks_per_weekend >= 0, "Blocks per night must be non-negative"

# Sanity for common case:
if (abs(weekday_window_mon_thu - 6.0) < 1e-3 and abs(league_session_length_hours - 1.5) < 1e-3 and league_buffer_minutes == 10):
    assert blocks_per_mon_thu == 3, f"Expected 3 blocks Mon–Thu, got {blocks_per_mon_thu}"
if (abs(weekend_window_hours - 4.0) < 1e-3 and abs(league_session_length_hours - 1.5) < 1e-3 and league_buffer_minutes == 10):
    assert blocks_per_weekend == 2, f"Expected 2 blocks weekend, got {blocks_per_weekend}"

# Capacity identity vs prime court-hours
assert league_court_hours_week <= prime_court_hours_week + 1e-6, f"League court-hours ({league_court_hours_week:.1f}) exceed PRIME capacity ({prime_court_hours_week:.1f})"
assert active_league_weeks_per_year <= 52, f"Active league weeks ({active_league_weeks_per_year}) cannot exceed 52"
assert league_session_length_hours >= 1.0 and league_session_length_hours <= 2.0, "League sessions should be 1-2 hours"

# Helper functions to distribute engine annual totals to monthly
def distribute_league_to_months(annual_total, active_weeks, start_month=1):
    """Distribute annual league revenue to monthly based on active weeks"""
    monthly = [0.0] * 24
    if active_weeks <= 0:
        return monthly
    
    # League runs in 6-week sessions (quarterly)
    # Start in month 2 (index 1)
    sessions_per_year = active_weeks / 6.0
    revenue_per_session = annual_total / sessions_per_year if sessions_per_year > 0 else 0
    
    # Distribute quarterly starting from month 2
    for quarter in range(8):  # 8 quarters in 2 years
        start_idx = start_month + quarter * 3
        if start_idx >= 24:
            break
        # Each quarter gets 2 months of revenue (6 weeks = 1.5 months)
        for month_offset in range(3):
            month_idx = start_idx + month_offset
            if month_idx < 24:
                monthly[month_idx] = revenue_per_session / 1.5  # Spread over 1.5 months
    
    return monthly

def distribute_court_to_months(annual_total, rampup_percentages, member_schedule):
    """Distribute annual court revenue to monthly based on utilization ramp"""
    monthly = []
    year1_total = 0
    
    # Calculate relative weights for each month based on utilization
    for i in range(12):
        if i < len(rampup_percentages):
            weight = rampup_percentages[i]
        else:
            weight = 0.82  # steady state
        year1_total += weight
    
    # Normalize to match annual total
    scale_factor = annual_total / year1_total if year1_total > 0 else 0
    
    for i in range(24):
        if i < 12:
            weight = rampup_percentages[i] if i < len(rampup_percentages) else 0.82
            monthly.append(weight * scale_factor)
        else:
            # Year 2: similar pattern
            monthly.append(0.82 * scale_factor)
    
    return monthly

def distribute_corporate_to_months(annual_total, frequency):
    """Distribute annual corporate revenue to monthly with ramp-up"""
    monthly = []
    year1_events = 0
    
    # Year 1 ramp-up pattern
    for i in range(12):
        if i < 3:
            events = 0
        elif i < 6:
            events = 1
        else:
            events = 2
        year1_events += events
    
    # Year 2: steady state
    year2_events = frequency * 12
    total_events = year1_events + year2_events
    
    if total_events > 0:
        revenue_per_event = annual_total * 2 / total_events  # 2 years of revenue
    else:
        revenue_per_event = 0
    
    for i in range(24):
        if i < 3:
            monthly.append(0)
        elif i < 6:
            monthly.append(revenue_per_event * 1)
        elif i < 12:
            monthly.append(revenue_per_event * 2)
        else:
            monthly.append(revenue_per_event * frequency)
    
    return monthly

# Generate monthly projections
def generate_monthly_projections():
    months = []
    dates = []
    debug_data = []  # Store debug info
    
    for i in range(24):  # 2 years
        current_date = start_date + relativedelta(months=i)
        dates.append(current_date)
        months.append(current_date.strftime("%b %Y"))
    
    # Use member schedule for growth with cap enforcement
    member_counts = []
    for i in range(24):
        if i < 12:
            # Year 1: Use the specified schedule with cap
            members = min(member_schedule[i], MEMBER_CAP)
        else:
            # Year 2: Growth capped at MEMBER_CAP
            year1_end = min(member_schedule[11], MEMBER_CAP)
            growth_factor = 1 + (0.1 * ((i - 11) / 12))  # Linear growth from 100% to 110%
            members = min(year1_end * growth_factor, MEMBER_CAP)
        member_counts.append(members)  # Keep as float for calculations
    
    # Calculate revenues
    membership_revenue = []
    court_rental_revenue = []
    league_revenue = []
    corporate_revenue = []
    tournament_revenue_list = []
    retail_revenue = []
    
    # Track metrics for sanity checks
    utilized_hours_list = []
    variable_revenue_list = []
    vr_per_hour_list = []
    revpach_list = []
    
    # STABILITY PATCH: Sanity band constants
    REVPACH_MIN, REVPACH_MAX = 10.0, 22.0
    VR_MIN, VR_MAX = 35.0, 55.0
    
    # ENGINE INTEGRATION: Get annual totals from engine and distribute to months
    engine_league_annual = float(engine_res["annual"]["league_rev"])
    engine_court_annual = float(engine_res["annual"]["court_rev"])
    engine_corp_annual = float(engine_res["annual"]["corp_rev"])
    engine_tourney_annual = float(engine_res["annual"]["tourney_rev"])
    engine_retail_annual = float(engine_res["annual"]["retail_rev"])
    
    # Distribute engine totals to monthly
    league_monthly_from_engine = distribute_league_to_months(engine_league_annual, active_league_weeks_per_year)
    court_monthly_from_engine = distribute_court_to_months(engine_court_annual, rampup_percentages, member_schedule)
    corp_monthly_from_engine = distribute_corporate_to_months(engine_corp_annual, corporate_frequency)
    
    # Tournament: quarterly distribution
    tourney_monthly_from_engine = [0.0] * 24
    tourney_per_quarter = engine_tourney_annual / 4  # 4 quarters per year
    for i in range(24):
        if (i + 1) % 3 == 0:  # Months 3, 6, 9, 12, etc.
            if i == 2:  # Month 3 - First tournament at 50%
                tourney_monthly_from_engine[i] = tourney_per_quarter * 0.5
            elif i == 5:  # Month 6 - Second tournament at 75%
                tourney_monthly_from_engine[i] = tourney_per_quarter * 0.75
            else:  # Month 9+ - Full revenue
                tourney_monthly_from_engine[i] = tourney_per_quarter
    
    # Retail: constant monthly
    retail_monthly_from_engine = [engine_retail_annual / 12] * 24
    
    # Variable to store current quarter's league revenue
    current_quarter_league_rev = 0.0
    reserved_league_prime_hours_monthly = 0.0
    league_start_idx = 1  # leagues begin in Month 2
    
    for i in range(24):
        # Membership revenue
        members = member_counts[i]
        community_members = members * (community_pct / 100)
        player_members = members * (player_pct / 100)
        pro_members = members * (pro_pct / 100)
        
        monthly_membership = (community_members * 0 +  # Community tier is free
                            player_members * player_tier_fee +
                            pro_members * pro_tier_fee)
        membership_revenue.append(monthly_membership)
        
        # Court rental revenue - using schedule-driven prime hours
        total_court_hours = NUM_COURTS * HOURS_PER_DAY * DAYS_PER_MONTH
        
        # Convert weekly schedule-driven hours to monthly
        weeks_per_month = 4.33  # Average weeks per month
        prime_hours_total = (prime_hours_total_per_week * weeks_per_month) / 7 * 30  # Scale to monthly
        offpeak_hours_total = total_court_hours - prime_hours_total
        
        # Store for debug
        debug_info = {
            'month': months[i] if i < len(months) else f"Month {i+1}",
            'total_court_hours': total_court_hours,
            'prime_share': engine_prime_share(engine_res),
            'prime_hours_total': prime_hours_total,
            'offpeak_hours_total': offpeak_hours_total,
        }
        
        # Deduct corporate event hours from prime hours (using ramp-up schedule)
        if i < 3:  # Months 1-3: No corporate events
            actual_corp_frequency_for_hours = 0
        elif i < 6:  # Months 4-6: 1 event per month
            actual_corp_frequency_for_hours = 1
        elif i < 12:  # Months 7-12: 2 events per month
            actual_corp_frequency_for_hours = 2
        else:  # Year 2: Use the input frequency (default 2)
            actual_corp_frequency_for_hours = min(corporate_frequency, 2)
        
        corporate_prime_hours_used = actual_corp_frequency_for_hours * corporate_hours_per_event
        
        # Deduct tournament hours (tournaments happen quarterly)
        tournament_hours_used = 0
        if (i + 1) % 3 == 0:  # Months 3, 6, 9, 12, 15, 18, 21, 24
            tournament_hours_used = tournament_hours * tournament_frequency
        
        # Calculate tournament allocation between prime and off-peak
        tournament_prime_hours = tournament_hours_used * 0.7  # 70% of tournament hours are prime
        tournament_offpeak_hours = tournament_hours_used * 0.3  # 30% are off-peak
        
        # Prime hours available after corporate and tournament events
        pre_league_prime = max(0, prime_hours_total - corporate_prime_hours_used - tournament_prime_hours)
        
        # Store debug info
        debug_info['corp_prime_hours'] = corporate_prime_hours_used
        debug_info['tourn_prime_hours'] = tournament_prime_hours
        
        # --- League reservation & revenue (quarterly, leagues start Month 2) ---
        if i < league_start_idx:
            # No leagues yet; nothing reserved, no revenue
            reserved_league_prime_hours_monthly = 0.0
            league_rev = 0.0
        else:
            # Compute once at the START of each league quarter and keep constant for 3 months
            if (i - league_start_idx) % 3 == 0:
                # Use schedule-driven league capacity
                # Monthly league court-hours from weekly schedule
                league_court_hours_monthly = (league_court_hours_week * weeks_per_month)
                reserved_league_prime_hours_monthly = league_court_hours_monthly
                
                # Calculate filled slots for this month
                monthly_filled_slots = filled_league_slots * weeks_per_month
                
                # Revenue: Each slot pays full price for 6-week session
                # Recognize 1/2 of session revenue per month (6 weeks = 1.5 months)
                current_quarter_league_rev = monthly_filled_slots * league_price_prime / 1.5
                
                # For backward compatibility
                max_league_capacity = monthly_filled_slots
                
                debug_info['max_league_capacity'] = max_league_capacity

            # Use the same reservation & revenue for months 2–3 of the quarter
            league_rev = current_quarter_league_rev

        # Compute prime hours available for rentals AFTER league reservation this month
        if i < league_start_idx:
            available_prime_hours = pre_league_prime
        else:
            if backfill_league_hours:
                # Only actually used league hours are removed from rental supply
                available_prime_hours = max(0.0, pre_league_prime - reserved_league_prime_hours_monthly)
            else:
                # Conservative: reserve full allocation even if not used
                full_alloc_monthly = (pre_league_prime * (league_prime_hours_pct / 100.0))
                available_prime_hours = max(0.0, pre_league_prime - full_alloc_monthly)
        
        # Store debug info
        debug_info['league_prime_hours'] = reserved_league_prime_hours_monthly
        debug_info['open_prime_hours'] = available_prime_hours
        debug_info['league_slots_filled'] = filled_league_slots if i >= league_start_idx else 0
        debug_info['league_revenue'] = league_rev
        
        # Off-peak hours after tournament usage
        offpeak_hours_after_events = max(0, offpeak_hours_total - tournament_offpeak_hours)
        
        # Calculate utilization
        if i < 12:
            utilization = rampup_percentages[i]
        else:
            # Year 2: Base utilization with seasonal variation
            base_utilization = 0.82  # More realistic steady state
            month_idx = (start_date.month + i - 1) % 12
            month_name = month_names[month_idx]
            
            if month_name in low_season_months:
                utilization = base_utilization * (1 - seasonal_dip / 100)
            else:
                utilization = base_utilization
        utilization = float(np.clip(utilization, 0.0, 1.0))
        
        # Estimate member vs non-member mix (members use more courts)
        member_play_ratio = min(member_play_ratio_cap, members / 1000.0)  # cap + growth-linked
        
        # STABILITY PATCH: Calculate court rental revenue ONLY on remainder hours
        # Assert capacity identity
        if reserved_league_prime_hours_monthly > pre_league_prime + 1e-6:
            st.warning(f"League hours {reserved_league_prime_hours_monthly:.1f} exceed available prime {pre_league_prime:.1f}")
            reserved_league_prime_hours_monthly = pre_league_prime
        
        if available_prime_hours < -1e-6:
            st.warning(f"Negative available prime hours: {available_prime_hours:.1f}")
            available_prime_hours = 0
        
        # Prime time courts - split with demand cap for non-members
        open_prime = available_prime_hours * utilization
        
        # Initial demand split
        nm_prime_demand = open_prime * (1 - member_play_ratio)
        # mem_prime_demand = open_prime * member_play_ratio  # Not used, calculated differently below
        
        # Apply non-member cap on prime hours (safety guardrail)
        nm_prime_ceiling = open_prime * nonmember_prime_share_max
        prime_nonmember_hours = min(nm_prime_demand, nm_prime_ceiling)
        prime_member_hours = max(0.0, open_prime - prime_nonmember_hours)
        
        # Revenue calculation - STRICTLY PER COURT (no player multipliers)
        # Members: if membership includes court access, rate is typically 0
        prime_member_court_revenue = prime_member_hours * member_court_rate_prime  # member_court_rate_prime is 0 if included in membership
        
        # Non-members pay full court rate (per court hour)
        prime_nonmember_revenue = prime_nonmember_hours * base_prime_rate
        
        # Off-peak hours - also split between members and non-members
        offpeak_util = min(1.0, utilization * 0.6)  # Lower utilization in off-peak
        offpeak_member_hours = offpeak_hours_after_events * offpeak_util * member_play_ratio
        offpeak_nonmember_hours = offpeak_hours_after_events * offpeak_util * (1 - member_play_ratio)
        
        debug_info['open_offpeak_hours'] = offpeak_hours_after_events
        
        # Off-peak revenue - STRICTLY PER COURT (no player multipliers)
        offpeak_member_revenue = offpeak_member_hours * member_court_rate_offpeak  # member_court_rate_offpeak is 0 if included in membership
        offpeak_nonmember_revenue = offpeak_nonmember_hours * non_prime_rate
        
        # Store debug revenue info
        debug_info['court_rev_prime'] = prime_member_court_revenue + prime_nonmember_revenue
        debug_info['court_rev_offpeak'] = offpeak_member_revenue + offpeak_nonmember_revenue
        
        total_court_revenue = (prime_member_court_revenue + prime_nonmember_revenue + 
                             offpeak_member_revenue + offpeak_nonmember_revenue)
        
        # Sanity check: revenue shouldn't exceed maximum possible
        max_court_revenue = (
            (prime_member_hours + prime_nonmember_hours) * base_prime_rate +
            (offpeak_member_hours + offpeak_nonmember_hours) * non_prime_rate
        )
        if total_court_revenue > max_court_revenue + 1e-6:
            st.warning(f"Month {i+1}: Court revenue ${total_court_revenue:.0f} exceeds max ${max_court_revenue:.0f}")
        
        # STABILITY PATCH: Ceiling guard for court revenue (no player multipliers)
        max_possible_court_rev = (
            (prime_member_hours + prime_nonmember_hours) * max(base_prime_rate, member_court_rate_prime if 'member_court_rate_prime' in locals() else 0) +
            (offpeak_member_hours + offpeak_nonmember_hours) * max(non_prime_rate, member_court_rate_offpeak if 'member_court_rate_offpeak' in locals() else 0)
        )
        if total_court_revenue > max_possible_court_rev + 1e-6:
            st.warning(f"Court revenue ${total_court_revenue:.0f} exceeds max ${max_possible_court_rev:.0f}")
            total_court_revenue = max_possible_court_rev
        
        court_rental_revenue.append(total_court_revenue)
        
        # Calculate utilized hours for this month
        total_utilized = (
            prime_member_hours + prime_nonmember_hours +
            offpeak_member_hours + offpeak_nonmember_hours +
            reserved_league_prime_hours_monthly +
            corporate_prime_hours_used +
            tournament_hours_used
        )
        utilized_hours_list.append(total_utilized)
        
        # Store hours for rate audit
        debug_info['nm_prime_hours'] = prime_nonmember_hours
        debug_info['nm_offpeak_hours'] = offpeak_nonmember_hours
        debug_info['nm_prime_revenue'] = prime_nonmember_hours * pricing['nm_prime_per_court']
        debug_info['nm_offpeak_revenue'] = offpeak_nonmember_hours * pricing['nm_off_per_court']
        
        # Store debug info with utilization
        debug_info['utilized_hours'] = total_utilized
        debug_info['utilization_rate'] = (total_utilized / total_court_hours * 100) if total_court_hours > 0 else 0
        
        # REMOVED - Legacy RevPACH calculation that was missing corp/tournament revenue
        # RevPACH will be calculated once at the end with all revenue components
        debug_data.append(debug_info)
        
        # ENGINE-BASED: Use pre-calculated monthly values from engine totals
        # Replace legacy calculations with engine-derived monthly values
        league_revenue.append(league_monthly_from_engine[i])
        corporate_revenue.append(corp_monthly_from_engine[i])
        tournament_revenue_list.append(tourney_monthly_from_engine[i])
        retail_revenue.append(retail_monthly_from_engine[i])
        
        # Also replace court rental revenue with engine-derived value
        court_rental_revenue[-1] = court_monthly_from_engine[i]  # Replace the last appended value
        
        # Calculate variable revenue metrics for sanity checks - USE ENGINE VALUES
        variable_rev = (
            court_monthly_from_engine[i] + 
            league_monthly_from_engine[i] +
            corp_monthly_from_engine[i] +
            tourney_monthly_from_engine[i] +
            retail_monthly_from_engine[i]
        )
        variable_revenue_list.append(variable_rev)
        
        # Calculate revenue per utilized hour and RevPACH
        vr_per_hour = variable_rev / max(1.0, total_utilized)
        revpach = variable_rev / max(1.0, total_court_hours)
        
        vr_per_hour_list.append(vr_per_hour)
        revpach_list.append(revpach)
        
        # Store in debug_info for consistency
        debug_info['revpach'] = revpach
        debug_info['rev_per_util_hr'] = vr_per_hour
    
    # Calculate staff costs before creating dataframe
    staff_cost_per_hour = 5.0  # $5 per utilized court hour
    staff_costs_list = [hours * staff_cost_per_hour for hours in utilized_hours_list]
    
    # ASSERTIONS: Verify monthly totals match engine annual totals
    league_year1_sum = sum(league_revenue[:12])
    court_year1_sum = sum(court_rental_revenue[:12])
    corp_year1_sum = sum(corporate_revenue[:12])
    tourney_year1_sum = sum(tournament_revenue_list[:12])
    retail_year1_sum = sum(retail_revenue[:12])
    
    # Allow small tolerance for floating point errors
    tolerance = 1.0
    assert abs(league_year1_sum - engine_league_annual) < tolerance, f"League monthly ({league_year1_sum:.0f}) ≠ engine annual ({engine_league_annual:.0f})"
    assert abs(court_year1_sum - engine_court_annual) < tolerance, f"Court monthly ({court_year1_sum:.0f}) ≠ engine annual ({engine_court_annual:.0f})"
    assert abs(corp_year1_sum - engine_corp_annual) < tolerance, f"Corp monthly ({corp_year1_sum:.0f}) ≠ engine annual ({engine_corp_annual:.0f})"
    assert abs(tourney_year1_sum - engine_tourney_annual) < tolerance, f"Tournament monthly ({tourney_year1_sum:.0f}) ≠ engine annual ({engine_tourney_annual:.0f})"
    assert abs(retail_year1_sum - engine_retail_annual) < tolerance, f"Retail monthly ({retail_year1_sum:.0f}) ≠ engine annual ({engine_retail_annual:.0f})"
    
    # Create projections dataframe
    projections = pd.DataFrame({
        'Month': months,
        'Date': dates,
        'Members': member_counts,  # Keep as float for calculations
        'Members_Display': [round(m) for m in member_counts],  # Rounded for display
        'Membership Revenue': membership_revenue,
        'Court Rental Revenue': court_rental_revenue,
        'League Revenue': league_revenue,
        'Corporate Revenue': corporate_revenue,
        'Tournament Revenue': tournament_revenue_list,
        'Retail Revenue': retail_revenue,
        'Utilized Hours': utilized_hours_list,
        'Variable Revenue': variable_revenue_list,
        'VR per Hour': vr_per_hour_list,
        'RevPACH': revpach_list,
        'Staff Costs': staff_costs_list
    })
    
    # Calculate total revenue and expenses
    projections['Total Revenue'] = (projections['Membership Revenue'] + 
                                   projections['Court Rental Revenue'] + 
                                   projections['League Revenue'] +
                                   projections['Corporate Revenue'] +
                                   projections['Tournament Revenue'] +
                                   projections['Retail Revenue'])
    
    # Apply rent abatement and annual escalators
    fixed_costs_list = []
    for i in range(24):
        # Calculate rent and other fixed costs with annual escalators
        year_num = i // 12  # 0 for Year 1, 1 for Year 2
        if year_num == 0:
            current_rent = base_rent_portion
            current_other_fixed = base_non_rent_fixed
        else:
            # Apply escalators for Year 2
            current_rent = base_rent_portion * (1 + annual_rent_escalator / 100)
            current_other_fixed = base_non_rent_fixed * (1 + other_fixed_escalator / 100)
        
        # Apply rent abatement if applicable
        if i < rent_abatement_months:
            # Free rent period - use non-rent portion only
            month_fixed = current_other_fixed
        else:
            # Normal operations - rent + other fixed costs
            month_fixed = current_rent + current_other_fixed
        
        fixed_costs_list.append(month_fixed)
    
    projections['Fixed Costs'] = fixed_costs_list
    
    # STABILITY PATCH: Variable costs scale with activity-based revenue only
    activity_revenue = [
        projections['Court Rental Revenue'][i] + 
        projections['League Revenue'][i] + 
        projections['Corporate Revenue'][i] + 
        projections['Tournament Revenue'][i]
        for i in range(24)
    ]
    projections['Variable Costs'] = [v * (variable_cost_pct / 100) for v in activity_revenue]
    
    # Staff costs already calculated and included in DataFrame
    projections['Total Operating Costs'] = [
        projections['Fixed Costs'][i] + projections['Variable Costs'][i] + projections['Staff Costs'][i]
        for i in range(24)
    ]
    
    # Loan payments from amortization schedule
    princs, intrs, pmts = [], [], []
    for i in range(24):
        if i < len(amort):
            principal, interest, payment, _ = amort[i]
        else:
            principal, interest, payment = 0, 0, 0
        princs.append(principal)
        intrs.append(interest)
        pmts.append(payment)
    
    projections['Loan Principal'] = princs
    projections['Loan Interest'] = intrs
    projections['Total Debt Service'] = pmts
    
    # Income calculations
    projections['EBITDA'] = projections['Total Revenue'] - projections['Total Operating Costs']
    projections['Cash Flow After Debt Service'] = projections['EBITDA'] - projections['Total Debt Service']
    
    # Add Working Capital Buffer for Year 1 DSCR calculation
    # This represents available cash from the working capital reserve
    working_capital_available = []
    remaining_working_capital = working_capital_reserve
    
    for i in range(24):
        if i < 12 and projections['Cash Flow After Debt Service'].iloc[i] < 0:
            # Use working capital to cover negative cash flow in Year 1
            deficit = abs(projections['Cash Flow After Debt Service'].iloc[i])
            if remaining_working_capital > 0:
                buffer_used = min(deficit, remaining_working_capital)
                remaining_working_capital -= buffer_used
                working_capital_available.append(buffer_used)
            else:
                working_capital_available.append(0)
        else:
            working_capital_available.append(0)
    
    projections['Working Capital Buffer'] = working_capital_available
    projections['Adjusted EBITDA for DSCR'] = projections['EBITDA'] + projections['Working Capital Buffer']
    
    # STABILITY PATCH: DSCR computation - both monthly and annual
    projections['DSCR_Operating'] = projections['EBITDA'] / projections['Total Debt Service']
    projections['DSCR_With_WC'] = (projections['EBITDA'] + projections['Working Capital Buffer']) / projections['Total Debt Service']
    projections['DSCR_Operating'] = projections['DSCR_Operating'].replace([np.inf, -np.inf], np.nan)
    projections['DSCR_With_WC'] = projections['DSCR_With_WC'].replace([np.inf, -np.inf], np.nan)
    
    # Calculate annual DSCR metrics
    ebitda_year1 = projections['EBITDA'][:12].sum()
    ebitda_year2 = projections['EBITDA'][12:24].sum()
    debt_service_year1 = projections['Total Debt Service'][:12].sum()
    debt_service_year2 = projections['Total Debt Service'][12:24].sum()
    
    annual_dscr_y1 = ebitda_year1 / debt_service_year1 if debt_service_year1 > 0 else 0
    annual_dscr_y2 = ebitda_year2 / debt_service_year2 if debt_service_year2 > 0 else 0
    
    # Verify league revenue consistency
    annual_league_rev_calc = projections['League Revenue'][:12].sum()
    weekly_league_rev = filled_league_slots * (league_price_prime / 6.0) if 'filled_league_slots' in locals() else 0
    annual_league_rev_expected = weekly_league_rev * 46  # 46 operational weeks
    
    # Add sanity check warnings
    avg_revpach = np.mean(revpach_list)
    avg_vr_per_hour = np.mean([v for v in vr_per_hour_list if v > 0])
    
    if not (REVPACH_MIN <= avg_revpach <= REVPACH_MAX):
        st.warning(f"⚠️ RevPACH ${avg_revpach:.2f} outside expected range (${REVPACH_MIN}-${REVPACH_MAX})")
    
    if not (VR_MIN <= avg_vr_per_hour <= VR_MAX):
        st.warning(f"⚠️ Variable Rev/Utilized Hr ${avg_vr_per_hour:.2f} outside expected range (${VR_MIN}-${VR_MAX})")
    
    # Ending Cash tracker (start with working capital reserve; WC Buffer is a cash OUTFLOW)
    start_cash = working_capital_reserve
    projections['Ending Cash'] = start_cash + (
        projections['Cash Flow After Debt Service'] - projections['Working Capital Buffer']
    ).cumsum()

    # Track remaining working capital reserve (cannot go below zero)
    projections['Remaining WC Reserve'] = np.maximum(
        0.0,
        working_capital_reserve - projections['Working Capital Buffer'].cumsum()
    )
    
    # Keep legacy DSCR for backward compatibility (uses With WC)
    projections['DSCR'] = projections['DSCR_With_WC']
    
    # Run sanity checks
    errors = run_sanity_checks(
        engine_prime_share(engine_res),
        league_prime_hours_pct / 100,
        member_counts,
        debug_data
    )
    
    if errors:
        for error in errors:
            st.error(f"⚠️ {error}")
    
    # Compute unified density metrics using single source of truth
    # Get annual totals for density calculation
    court_rev_year = projections['Court Rental Revenue'][:12].sum()
    league_rev_year = projections['League Revenue'][:12].sum()
    corp_rev_year = projections['Corporate Revenue'][:12].sum()
    tourney_rev_year = projections['Tournament Revenue'][:12].sum()
    retail_rev_year = projections['Retail Revenue'][:12].sum()
    
    # Calculate weekly court-hours from monthly averages
    avg_utilized_hours_monthly = np.mean(utilized_hours_list[:12])
    open_ch_wk = (avg_utilized_hours_monthly / 4.33)  # Monthly to weekly
    league_ch_wk = league_blocks_per_week * block_slot_hours * NUM_COURTS if 'league_blocks_per_week' in locals() else 0
    corp_ch_wk = corporate_frequency * 2.0 * NUM_COURTS / 4.33  # Assuming 2-hour events
    tourney_ch_wk = tournament_frequency * 4.0 * NUM_COURTS / 12.0  # Quarterly tournaments
    
    # Split open play into prime and off-peak using engine schedule
    open_prime_ch_wk = open_ch_wk * engine_prime_share(engine_res)
    open_offpeak_ch_wk = open_ch_wk * (1 - engine_prime_share(engine_res))
    
    # Create density state
    ds = DensityState(
        courts=NUM_COURTS,
        hours_open_per_day=HOURS_PER_DAY,
        open_prime_ch_wk=open_prime_ch_wk,
        open_offpeak_ch_wk=open_offpeak_ch_wk,
        league_ch_wk=league_ch_wk,
        corp_ch_wk=corp_ch_wk,
        tourney_ch_wk=tourney_ch_wk,
        court_rev_year=court_rev_year,
        league_rev_year=league_rev_year,
        corp_rev_year=corp_rev_year,
        tourney_rev_year=tourney_rev_year,
        retail_rev_year=retail_rev_year,
        active_league_weeks_per_year=46,
        weeks_per_year_equiv=52.0
    )
    
    # Compute density metrics
    density_metrics = compute_density(ds)
    
    # STABILITY PATCH: Return additional metrics for debug panel
    stability_metrics = {
        'revpach_list': revpach_list,
        'vr_per_hour_list': vr_per_hour_list,
        'REVPACH_MIN': REVPACH_MIN,
        'REVPACH_MAX': REVPACH_MAX,
        'VR_MIN': VR_MIN,
        'VR_MAX': VR_MAX,
        'annual_dscr_y1': annual_dscr_y1,
        'annual_dscr_y2': annual_dscr_y2,
        'annual_league_rev_calc': annual_league_rev_calc,
        'annual_league_rev_expected': annual_league_rev_expected,
        'density_metrics': density_metrics
    }
    
    return projections, debug_data, stability_metrics

# Generate projections
projections_df, debug_data, stability_metrics = generate_monthly_projections()

# Display key metrics using unified density calculations
st.subheader("📊 Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

with col1:
    # Use engine for variable revenue + membership for total
    var_rev_y1 = engine_variable_revenue_year(engine_res)
    membership_revenue_y1 = projections_df.iloc[:12]['Membership Revenue'].sum()
    total_revenue_y1 = var_rev_y1 + membership_revenue_y1
    st.metric("Year 1 Revenue", f"${total_revenue_y1:,.0f}")
    st.caption(f"Variable: ${var_rev_y1:,.0f}")

with col2:
    year1_ebitda = projections_df.iloc[:12]['EBITDA'].sum()
    st.metric("Year 1 EBITDA", f"${year1_ebitda:,.0f}")

with col3:
    # Use engine density metrics - single source of truth
    revpach_engine = engine_res['density']['RevPACH']
    st.metric("RevPACH (Engine)", f"${revpach_engine:.2f}")

with col4:
    # Use engine density metrics - single source of truth
    rev_util_engine = engine_res['density']['RevPerUtilHr']
    st.metric("Rev/Util Hr (Engine)", f"${rev_util_engine:.2f}")

# Add cache clear button
if st.button("🔄 Recompute Metrics"):
    try:
        st.cache_data.clear()
    except Exception:
        pass
    st.rerun()

# Add Audit expander to display engine results
with st.expander("🔍 Audit (Engine)", expanded=False):
    prime_share_engine = engine_res["prime_ch_week"] / max(1e-6, engine_res["total_ch_week"])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Allocation & Schedule**")
        st.write({
            "Prime Share (%)": f"{prime_share_engine*100:.1f}",
            "Weekly Allocation (CH)": engine_res["alloc_weekly"],
            "Available CH (yr)": f"{engine_res['available_ch_year']:,.0f}",
            "Utilized CH (yr)": f"{engine_res['utilized_ch_year']:,.0f}",
        })
    
    with col2:
        st.markdown("**Weekly Results**")
        st.write({
            "League blocks": engine_res["weekly"]["league_blocks"],
            "League slots": engine_res["weekly"]["league_slots"],
            "League rev": f"${engine_res['weekly']['league_rev']:,.2f}",
            "Court rev": f"${engine_res['weekly']['court_rev']:,.2f}",
        })
    
    with col3:
        st.markdown("**Annual Revenue**")
        st.write({
            "League": f"${engine_res['annual']['league_rev']:,.0f}",
            "Court": f"${engine_res['annual']['court_rev']:,.0f}",
            "Corp": f"${engine_res['annual']['corp_rev']:,.0f}",
            "Tourney": f"${engine_res['annual']['tourney_rev']:,.0f}",
            "Retail": f"${engine_res['annual']['retail_rev']:,.0f}",
            "Total Variable": f"${engine_res['annual']['variable_rev']:,.0f}",
        })
    
    # Display density metrics
    st.markdown("**Density Metrics**")
    st.write({
        "RevPACH": f"${engine_res['density']['RevPACH']:.2f}",
        "Rev/Utilized Hour": f"${engine_res['density']['RevPerUtilHr']:.2f}",
    })
    
    # Display pricing
    st.markdown("**Pricing Configuration**")
    st.write({
        "NM per-court (prime/off)": f"${cfg.pricing.nm_prime_per_court:.0f} / ${cfg.pricing.nm_off_per_court:.0f}",
        "League per-slot 6wk (prime/off)": f"${cfg.league.price_prime_slot_6wk:.0f} / ${cfg.league.price_off_slot_6wk:.0f}",
        "Corp per-court (prime/off)": f"${cfg.corp.prime_rate_per_court:.0f} / ${cfg.corp.off_rate_per_court:.0f}",
    })

# Display debug panel if enabled
if show_debug:
    with st.expander("🔍 Debug Reconciliation Panel", expanded=True):
        debug_month = st.selectbox(
            "Select Month to Debug",
            options=range(24),
            format_func=lambda x: projections_df.iloc[x]['Month']
        )
        
        debug_info = debug_data[debug_month] if debug_month < len(debug_data) else {}
        
        # Create tabs for different debug views
        tab1, tab2, tab3 = st.tabs(["Hour Allocation", "Revenue Breakdown", "Rate Audit"])
        
        with tab1:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Hour Allocation**")
                st.metric("Total Court Hours", f"{debug_info.get('total_court_hours', 0):.0f}")
                st.metric("Prime Share", f"{debug_info.get('prime_share', 0)*100:.1f}%")
                st.metric("Prime Hours Total", f"{debug_info.get('prime_hours_total', 0):.0f}")
                st.metric("Off-Peak Hours Total", f"{debug_info.get('offpeak_hours_total', 0):.0f}")
            
            with col2:
                st.markdown("**Prime Time Usage**")
                st.metric("League Hours", f"{debug_info.get('league_prime_hours', 0):.0f}")
                st.metric("Corporate Hours", f"{debug_info.get('corp_prime_hours', 0):.0f}")
                st.metric("Tournament Hours", f"{debug_info.get('tourn_prime_hours', 0):.0f}")
                st.metric("Open Play Hours", f"{debug_info.get('open_prime_hours', 0):.0f}")
            
            with col3:
                st.markdown("**Revenue Breakdown**")
                st.metric("Court Rev (Prime)", f"${debug_info.get('court_rev_prime', 0):,.0f}")
                st.metric("Court Rev (Off-Peak)", f"${debug_info.get('court_rev_offpeak', 0):,.0f}")
                st.metric("League Capacity", f"{debug_info.get('max_league_capacity', 0):.0f} players")
                
            # Capacity check
        prime_allocated = (
            debug_info.get('league_prime_hours', 0) +
            debug_info.get('corp_prime_hours', 0) +
            debug_info.get('tourn_prime_hours', 0) +
            debug_info.get('open_prime_hours', 0)
        )
        prime_total = debug_info.get('prime_hours_total', 0)
        
        if prime_total > 0:
            utilization_pct = (prime_allocated / prime_total) * 100
            st.progress(min(utilization_pct / 100, 1.0))
            st.caption(f"Prime Time Utilization: {utilization_pct:.1f}% ({prime_allocated:.0f} / {prime_total:.0f} hours)")
        
            if prime_allocated > prime_total + 1e-6:
                st.error("⚠️ WARNING: Prime hours over-allocated!")
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Monthly Revenue Sources**")
                st.metric("Court Rental", f"${projections_df.iloc[debug_month]['Court Rental Revenue']:,.0f}")
                st.metric("League", f"${projections_df.iloc[debug_month]['League Revenue']:,.0f}")
                st.metric("Membership", f"${projections_df.iloc[debug_month]['Membership Revenue']:,.0f}")
            with col2:
                st.markdown("**Key Metrics**")
                st.metric("RevPACH", f"${projections_df.iloc[debug_month]['RevPACH']:.2f}")
                st.metric("VR per Hour", f"${projections_df.iloc[debug_month]['VR per Hour']:.2f}")
                st.metric("Total Revenue", f"${projections_df.iloc[debug_month]['Total Revenue']:,.0f}")
        
        with tab3:
            st.markdown("**Rate Audit - Configured vs Implied Rates**")
            audit_results = audit_rates(debug_data, pricing)
            if audit_results and debug_month < len(audit_results):
                audit = audit_results[debug_month]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Non-Member Prime Rate**")
                    st.metric("Configured", f"${audit['NM Prime Configured']:.2f}")
                    st.metric("Implied", f"${audit['NM Prime Implied']:.2f}")
                    if audit['NM Prime Match']:
                        st.success("✅ Rates match")
                    else:
                        st.error(f"⚠️ Unit bleed detected: ${abs(audit['NM Prime Implied'] - audit['NM Prime Configured']):.2f}")
                    
                    st.markdown("**Non-Member Off-Peak Rate**")
                    st.metric("Configured", f"${audit['NM Off Configured']:.2f}")
                    st.metric("Implied", f"${audit['NM Off Implied']:.2f}")
                    if audit['NM Off Match']:
                        st.success("✅ Rates match")
                    else:
                        st.error(f"⚠️ Unit bleed detected: ${abs(audit['NM Off Implied'] - audit['NM Off Configured']):.2f}")
                
                with col2:
                    st.markdown("**League Rate (6-week session)**")
                    st.metric("Configured", f"${audit['League Configured']:.2f}")
                    st.metric("Implied", f"${audit['League Implied']:.2f}")
                    if audit['League Match']:
                        st.success("✅ Rates match")
                    else:
                        st.warning(f"⚠️ Variance: ${abs(audit['League Implied'] - audit['League Configured']):.2f}")
        
        # STABILITY PATCH: Display key sanity metrics - ENGINE VALUES
        st.divider()
        st.markdown("### 📊 Stability Metrics (Engine)")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("**RevPACH (Engine)**")
            revpach_engine = engine_res['density']['RevPACH']
            REVPACH_MIN = 10.0
            REVPACH_MAX = 22.0
            color = "🟢" if REVPACH_MIN <= revpach_engine <= REVPACH_MAX else "🔴"
            st.metric(f"{color} Engine", f"${revpach_engine:.2f}")
            st.caption(f"Target: ${REVPACH_MIN}-${REVPACH_MAX}")
        
        with col2:
            st.markdown("**Rev/Utilized Hr (Engine)**")
            rev_util_engine = engine_res['density']['RevPerUtilHr']
            VR_MIN = 35.0
            VR_MAX = 55.0
            color = "🟢" if VR_MIN <= rev_util_engine <= VR_MAX else "🔴"
            st.metric(f"{color} Engine", f"${rev_util_engine:.2f}")
            st.caption(f"Target: ${VR_MIN}-${VR_MAX}")
        
        with col3:
            st.markdown("**Prime Share (Schedule)**")
            prime_share_pct = engine_prime_share(engine_res) * 100
            st.metric("From Schedule", f"{prime_share_pct:.1f}%")
            st.caption("Derived from prime windows")
        
        with col4:
            st.markdown("**Annual DSCR Y2**")
            annual_dscr_y2 = stability_metrics['annual_dscr_y2']
            st.metric("Operating", f"{annual_dscr_y2:.2f}")
            st.caption("Target: ≥1.25")
        
        # League revenue consistency check
        annual_league_rev_calc = stability_metrics['annual_league_rev_calc']
        annual_league_rev_expected = stability_metrics['annual_league_rev_expected']
        if abs(annual_league_rev_calc - annual_league_rev_expected) > 100:
            st.warning(f"⚠️ League Revenue Mismatch: Monthly sum ${annual_league_rev_calc:,.0f} vs Weekly calc ${annual_league_rev_expected:,.0f}")
        else:
            st.success("✅ Capacity constraints satisfied")
            
        # Add sanity checks section
        st.divider()
        st.markdown("**Schedule-Driven League Details**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Prime Windows & Schedule**")
            st.metric("Mon-Thu Window", f"{weekday_window_mon_thu:.1f}h/night")
            st.metric("Friday Window", f"{weekday_window_fri:.1f}h/night")
            st.metric("Weekend AM Window", f"{weekend_window_hours:.1f}h/day")
            st.metric("Block Slot Hours", f"{block_slot_hours:.3f}h")
            st.metric("Mon-Thu League Nights", f"{mon_thu_league_nights}")
            st.metric("Fri League Nights", f"{fri_league_nights}")
            st.metric("Weekend League Mornings", f"{weekend_league_morns}")
            
        with col2:
            st.markdown("**League Blocks**")
            st.metric("Blocks/Mon-Thu", f"{blocks_per_mon_thu}")
            st.metric("Blocks/Fri", f"{blocks_per_fri}")
            st.metric("Blocks/Weekend", f"{blocks_per_weekend}")
            st.metric("Total Blocks/Week", f"{league_blocks_per_week}")
            st.metric("Players/Block", f"{players_per_block}")
            st.metric("Courts Used", f"{courts_used}")
            st.metric("League Court-Hours/Week", f"{league_court_hours_week:.1f}")
                
        with col3:
            st.markdown("**League Capacity & Revenue**")
            st.metric("Weekly Slots", f"{weekly_league_slots:.0f}")
            st.metric("Filled Weekly Slots", f"{filled_weekly_slots:.0f}")
            st.metric("Fill Rate", f"{league_fill_rate:.0%}")
            st.metric("Weekly Revenue", f"${weekly_league_revenue:,.0f}")
            st.metric("Annual Revenue", f"${annual_league_revenue:,.0f}")
            st.metric("League Share of Prime", f"{league_share_prime:.1%}")
            st.metric("Price per Slot", f"${league_price_prime:.0f}")
        
        st.divider()
        st.markdown("**Units & Pricing (Debug)**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Court Pricing**")
            st.metric("Unit", "Per Court Hour")
            st.metric("Prime Rate", f"${base_prime_rate:.0f}/court/hr")
            st.metric("Off-Peak Rate", f"${non_prime_rate:.0f}/court/hr")
            
        with col2:
            st.markdown("**League Pricing**")
            st.metric("Unit", "Per Slot (6-week Session)")
            st.metric("Prime Price", f"${league_price_prime:.0f}/slot")
            st.metric("Off-Peak Price", f"${league_price_offpeak:.0f}/slot")
                
        with col3:
            st.markdown("**Metrics**")
            st.metric("Non-Member Cap", f"{nonmember_prime_share_max*100:.0f}%")
            revpach = debug_info.get('revpach', 0)
            st.metric("RevPACH", f"${revpach:.2f}")
            rev_per_util_hr = debug_info.get('rev_per_util_hr', 0)
            st.metric("Rev/Util Hr", f"${rev_per_util_hr:.2f}")
            
        # Sanity check warnings
        PACH_MIN, PACH_MAX = 10.0, 22.0
        VR_MIN, VR_MAX = 35.0, 55.0
        if not (PACH_MIN <= revpach <= PACH_MAX):
            st.warning(f"⚠️ RevPACH ${revpach:.2f} outside expected range ${PACH_MIN}-${PACH_MAX}")
        if not (VR_MIN <= rev_per_util_hr <= VR_MAX):
            st.warning(f"⚠️ Rev/Utilized Hour ${rev_per_util_hr:.2f} outside expected range ${VR_MIN}-${VR_MAX}")

# Calculate key metrics
year1_revenue = projections_df.iloc[:12]['Total Revenue'].sum()
year1_cash_flow = projections_df.iloc[:12]['Cash Flow After Debt Service'].sum()
year1_avg_dscr = projections_df.iloc[:12]['DSCR'].mean(skipna=True)  # Skip NaN values

# Year 1 DSCRs (Operating vs With WC)
year1_dscr_oper_avg = projections_df.iloc[:12]['DSCR_Operating'].mean(skipna=True)
year1_dscr_oper_min = projections_df.iloc[:12]['DSCR_Operating'].replace(0, np.nan).dropna().min()

year1_dscr_wc_avg = projections_df.iloc[:12]['DSCR_With_WC'].mean(skipna=True)
year1_dscr_wc_min = projections_df.iloc[:12]['DSCR_With_WC'].replace(0, np.nan).dropna().min()

# Year 1 Ending Cash stats
year1_min_ending_cash = projections_df.iloc[:12]['Ending Cash'].min()

# Calculate minimum DSCR excluding zero/NaN months
year1_dscr_min = projections_df.iloc[:12]['DSCR'].replace(0, np.nan).dropna().min()
if pd.isna(year1_dscr_min):
    year1_dscr_min = 0  # Default if all months are NaN

# Find break-even month (when cash flow after debt service turns positive)
breakeven_month = None
for idx, row in projections_df.iterrows():
    if row['Cash Flow After Debt Service'] > 0:
        breakeven_month = row['Month']
        break

# Main display area
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Year 1 Total Revenue", f"${year1_revenue:,.0f}")

with col2:
    st.metric("Year 1 Cash Flow", f"${year1_cash_flow:,.0f}")

with col3:
    st.metric("Break-Even Month", breakeven_month if breakeven_month else "Not in 24 months")

with col4:
    st.metric("Avg Y1 DSCR (Op)", f"{year1_dscr_oper_avg:.2f}" if not np.isnan(year1_dscr_oper_avg) else "N/A")

with col5:
    st.metric("Min Y1 DSCR (Op)", f"{year1_dscr_oper_min:.2f}" if not np.isnan(year1_dscr_oper_min) else "N/A")

with col6:
    st.metric("Min Y1 Ending Cash", f"${year1_min_ending_cash:,.0f}")

year1_min_wc = projections_df.iloc[:12]['Remaining WC Reserve'].min() if 'Remaining WC Reserve' in projections_df.columns else np.nan
st.metric("Min Y1 WC Reserve", f"${year1_min_wc:,.0f}" if not np.isnan(year1_min_wc) else "N/A")

st.caption("Note: Lenders typically assess Operating DSCR (EBITDA / Debt Service). We show DSCR with Working-Capital Buffer for visibility into cash coverage during ramp-up.")

st.divider()

# Sanity Panel with Guardrails
with st.expander("🛡️ Sanity Checks & Guardrails", expanded=False):
    # Calculate average metrics
    avg_vr_per_hour = projections_df['VR per Hour'].mean()
    avg_revpach = projections_df['RevPACH'].mean()
    avg_utilized_hours = projections_df['Utilized Hours'].mean()
    total_court_hours_monthly = NUM_COURTS * HOURS_PER_DAY * DAYS_PER_MONTH
    avg_utilization = (avg_utilized_hours / total_court_hours_monthly) * 100
    
    # Expected bands
    VR_MIN, VR_MAX = 35.0, 55.0
    PACH_MIN, PACH_MAX = 10.0, 22.0
    
    # Check for warnings
    warn_msgs = []
    if not (VR_MIN <= avg_vr_per_hour <= VR_MAX):
        warn_msgs.append(f"⚠️ Variable Rev / Utilized Hr = ${avg_vr_per_hour:.2f} (expected ${VR_MIN}-{VR_MAX})")
    
    if not (PACH_MIN <= avg_revpach <= PACH_MAX):
        warn_msgs.append(f"⚠️ RevPACH = ${avg_revpach:.2f} (expected ${PACH_MIN}-{PACH_MAX})")
    
    # Check membership revenue ceiling
    avg_members = projections_df['Members'].mean()
    if avg_members > MEMBER_CAP:
        warn_msgs.append(f"⚠️ Average members {avg_members:.0f} exceeds cap {MEMBER_CAP}")
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Avg VR/Utilized Hour", f"${avg_vr_per_hour:.2f}")
        st.caption(f"Expected: ${VR_MIN}-${VR_MAX}")
    
    with col2:
        st.metric("Avg RevPACH", f"${avg_revpach:.2f}")
        st.caption(f"Expected: ${PACH_MIN}-${PACH_MAX}")
    
    with col3:
        st.metric("Avg Utilization", f"{avg_utilization:.1f}%")
        st.caption(f"Non-Member Prime Cap: {nonmember_prime_share_max*100:.0f}%")
    
    # Display warnings or success
    if warn_msgs:
        for msg in warn_msgs:
            st.warning(msg)
    else:
        st.success("✅ All sanity checks passed - metrics within expected bands")
    
    # Additional info
    st.info(f"""
    **Guardrails Active:**
    - Non-member prime hours capped at {nonmember_prime_share_max*100:.0f}% of open prime
    - Member cap enforced at {MEMBER_CAP}
    - Prime time derived from schedule: {engine_prime_share(engine_res)*100:.1f}%
    - League allocation: {league_prime_hours_pct}% of prime hours
    """)

st.divider()

# Year 1 Monthly Projections Table
st.subheader("📅 Year 1 Monthly Financial Projections")

year1_df = projections_df.iloc[:12].copy()
year1_display = year1_df[['Month', 'Members_Display', 'Membership Revenue', 'Court Rental Revenue',
                          'League Revenue', 'Corporate Revenue', 'Tournament Revenue', 'Retail Revenue',
                          'Total Revenue', 'Total Operating Costs',
                          'Total Debt Service', 'Cash Flow After Debt Service',
                          'DSCR_Operating', 'DSCR_With_WC', 'Ending Cash', 'Remaining WC Reserve']]
year1_display = year1_display.rename(columns={'Members_Display': 'Members',
                                              'DSCR_Operating': 'DSCR (Op)',
                                              'DSCR_With_WC': 'DSCR (With WC)'})
# Format
currency_cols = ['Membership Revenue','Court Rental Revenue','League Revenue','Corporate Revenue',
                 'Tournament Revenue','Retail Revenue','Total Revenue','Total Operating Costs',
                 'Total Debt Service','Cash Flow After Debt Service','Ending Cash','Remaining WC Reserve']
for col in currency_cols:
    year1_display[col] = year1_display[col].apply(lambda x: f"${x:,.0f}")

for col in ['DSCR (Op)', 'DSCR (With WC)']:
    year1_display[col] = year1_display[col].apply(lambda x: "N/A" if (pd.isna(x) or x == 0) else f"{x:.2f}")

st.dataframe(year1_display.set_index('Month').T, use_container_width=True)

with st.expander("Capacity sanity check (Month 6 example)"):
    idx = min(5, len(projections_df)-1)  # Month 6 = index 5
    # Recompute the key hour components for display only (mirror logic, no side effects)
    total_court_hours = NUM_COURTS * HOURS_PER_DAY * DAYS_PER_MONTH
    prime_hours = total_court_hours * engine_prime_share(engine_res)
    # Roughly mirror tournament/corporate for that month (best-effort display; no calc dependency)
    # This is illustrative; it won't affect the model.
    st.write(f"Prime hours baseline: {prime_hours:,.0f} hrs")
    st.write("Then minus: corporate and tournament prime hours; minus fixed league reservation (if active); remainder is rental supply.")
    st.caption("This is an illustrative snapshot for reviewers; see main model for actual monthly math.")

# 2-Year Annual Summary
st.subheader("📊 2-Year Annual Summary")

# Select only numeric columns for summation
numeric_cols = projections_df.select_dtypes(include=[np.number]).columns
year1_summary = projections_df.iloc[:12][numeric_cols].sum()
year2_summary = projections_df.iloc[12:24][numeric_cols].sum()

summary_data = {
    'Metric': ['Total Revenue','Membership Revenue','Court Rental Revenue','League Revenue',
               'Corporate Revenue','Tournament Revenue','Retail Revenue',
               'Total Operating Costs','EBITDA','Total Debt Service','Cash Flow After Debt Service',
               'Avg Monthly Members','Avg DSCR (Op)','Avg DSCR (With WC)'],
    'Year 1': [
        f"${year1_summary['Total Revenue']:,.0f}",
        f"${year1_summary['Membership Revenue']:,.0f}",
        f"${year1_summary['Court Rental Revenue']:,.0f}",
        f"${year1_summary['League Revenue']:,.0f}",
        f"${year1_summary['Corporate Revenue']:,.0f}",
        f"${year1_summary['Tournament Revenue']:,.0f}",
        f"${year1_summary['Retail Revenue']:,.0f}",
        f"${year1_summary['Total Operating Costs']:,.0f}",
        f"${year1_summary['EBITDA']:,.0f}",
        f"${year1_summary['Total Debt Service']:,.0f}",
        f"${year1_summary['Cash Flow After Debt Service']:,.0f}",
        f"{round(projections_df.iloc[:12]['Members'].mean())}",
        f"{year1_dscr_oper_avg:.2f}" if not np.isnan(year1_dscr_oper_avg) else "N/A",
        f"{year1_dscr_wc_avg:.2f}" if not np.isnan(year1_dscr_wc_avg) else "N/A",
    ],
    'Year 2': [
        f"${year2_summary['Total Revenue']:,.0f}",
        f"${year2_summary['Membership Revenue']:,.0f}",
        f"${year2_summary['Court Rental Revenue']:,.0f}",
        f"${year2_summary['League Revenue']:,.0f}",
        f"${year2_summary['Corporate Revenue']:,.0f}",
        f"${year2_summary['Tournament Revenue']:,.0f}",
        f"${year2_summary['Retail Revenue']:,.0f}",
        f"${year2_summary['Total Operating Costs']:,.0f}",
        f"${year2_summary['EBITDA']:,.0f}",
        f"${year2_summary['Total Debt Service']:,.0f}",
        f"${year2_summary['Cash Flow After Debt Service']:,.0f}",
        f"{round(projections_df.iloc[12:24]['Members'].mean())}",
        f"{projections_df.iloc[12:24]['DSCR_Operating'].mean(skipna=True):.2f}",
        f"{projections_df.iloc[12:24]['DSCR_With_WC'].mean(skipna=True):.2f}",
    ]
}

summary_df = pd.DataFrame(summary_data)
st.dataframe(summary_df.set_index('Metric'), use_container_width=True)

st.divider()

# Visualizations
st.subheader("📈 Financial Visualizations")

col1, col2 = st.columns(2)

with col1:
    # Monthly Revenue by Stream
    fig_revenue = go.Figure()
    fig_revenue.add_trace(go.Scatter(
        x=projections_df['Month'],
        y=projections_df['Membership Revenue'],
        mode='lines',
        name='Membership',
        stackgroup='one',
        line=dict(color='#1f77b4')
    ))
    fig_revenue.add_trace(go.Scatter(
        x=projections_df['Month'],
        y=projections_df['Court Rental Revenue'],
        mode='lines',
        name='Court Rental',
        stackgroup='one',
        line=dict(color='#ff7f0e')
    ))
    fig_revenue.add_trace(go.Scatter(
        x=projections_df['Month'],
        y=projections_df['League Revenue'],
        mode='lines',
        name='League',
        stackgroup='one',
        line=dict(color='#2ca02c')
    ))
    fig_revenue.add_trace(go.Scatter(
        x=projections_df['Month'],
        y=projections_df['Corporate Revenue'],
        mode='lines',
        name='Corporate',
        stackgroup='one',
        line=dict(color='#d62728')
    ))
    fig_revenue.add_trace(go.Scatter(
        x=projections_df['Month'],
        y=projections_df['Tournament Revenue'],
        mode='lines',
        name='Tournament',
        stackgroup='one',
        line=dict(color='#9467bd')
    ))
    fig_revenue.add_trace(go.Scatter(
        x=projections_df['Month'],
        y=projections_df['Retail Revenue'],
        mode='lines',
        name='Retail',
        stackgroup='one',
        line=dict(color='#8c564b')
    ))
    fig_revenue.update_layout(
        title="Monthly Revenue by Stream",
        xaxis_title="Month",
        yaxis_title="Revenue ($)",
        hovermode='x unified',
        showlegend=True,
        height=400
    )
    st.plotly_chart(fig_revenue, use_container_width=True)

with col2:
    # Monthly Profitability
    fig_profit = go.Figure()
    fig_profit.add_trace(go.Bar(
        x=projections_df['Month'],
        y=projections_df['Total Revenue'],
        name='Total Revenue',
        marker_color='green'
    ))
    fig_profit.add_trace(go.Bar(
        x=projections_df['Month'],
        y=-projections_df['Total Operating Costs'],
        name='Operating Costs',
        marker_color='red'
    ))
    fig_profit.add_trace(go.Scatter(
        x=projections_df['Month'],
        y=projections_df['Cash Flow After Debt Service'],
        mode='lines+markers',
        name='Cash Flow After Debt Service',
        marker_color='blue',
        line=dict(width=3)
    ))
    fig_profit.update_layout(
        title="Monthly Profitability Analysis",
        xaxis_title="Month",
        yaxis_title="Amount ($)",
        hovermode='x unified',
        showlegend=True,
        height=400
    )
    st.plotly_chart(fig_profit, use_container_width=True)

# Member Growth Chart
st.subheader("👥 Member Growth Trajectory")
fig_members = go.Figure()
fig_members.add_trace(go.Scatter(
    x=projections_df['Month'],
    y=projections_df['Members_Display'],  # Use rounded values for display
    mode='lines+markers',
    name='Total Members',
    line=dict(color='purple', width=3),
    marker=dict(size=8)
))
fig_members.update_layout(
    xaxis_title="Month",
    yaxis_title="Number of Members",
    hovermode='x unified',
    height=350
)
st.plotly_chart(fig_members, use_container_width=True)

st.divider()

# Export Functionality with Guardrails - ENGINE ONLY
st.subheader("💾 Export Financial Projections")

# Use engine metrics for export check - SINGLE SOURCE OF TRUTH
var_rev = engine_variable_revenue_year(engine_res)
avail_ch = engine_available_hours_year(engine_res)
util_ch = engine_utilized_hours_year(engine_res)
revpach_engine = engine_res["density"]["RevPACH"]
rev_util_engine = engine_res["density"]["RevPerUtilHr"]

# Verify utilized <= available
assert util_ch <= avail_ch + 1e-6, f"Utilized CH exceeds available ({util_ch:.0f} > {avail_ch:.0f})"

# Export guardrails using engine results
export_blocked = False
export_warnings = []

if revpach_engine > 25.0:
    export_warnings.append(f"RevPACH (${revpach_engine:.2f}) exceeds $25/hr limit")
    export_blocked = True

if rev_util_engine > 60.0:
    export_warnings.append(f"Rev/Utilized Hour (${rev_util_engine:.2f}) exceeds $60/hr limit")
    export_blocked = True

if export_blocked:
    st.error("⚠️ Export blocked due to unrealistic metrics:")
    for warning in export_warnings:
        st.warning(warning)
    st.info(f"""
    **Metric Breakdown (Engine):**
    - RevPACH: ${revpach_engine:.2f}
    - Rev/Utilized Hr: ${rev_util_engine:.2f}
    - Variable Revenue/Year: ${var_rev:,.0f}
    - Available Court-Hours/Year: {avail_ch:,.0f}
    - Utilized Court-Hours/Year: {util_ch:,.0f}
    - Prime Share: {engine_prime_share(engine_res)*100:.1f}%
    """)
    st.info("Please adjust your assumptions to bring metrics within reasonable ranges before exporting.")
else:
    st.success(f"✅ Metrics within acceptable range (RevPACH: ${revpach_engine:.2f}, Rev/Util Hr: ${rev_util_engine:.2f})")
    st.caption(f"Engine Values - Variable Revenue/Year: ${var_rev:,.0f}, Prime Share: {engine_prime_share(engine_res)*100:.1f}%")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Monthly projections CSV
            monthly_csv = projections_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Monthly Projections (CSV)",
                data=monthly_csv,
                file_name=f"pickleball_monthly_projections_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Annual summary CSV
            annual_csv = summary_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Annual Summary (CSV)",
                data=annual_csv,
                file_name=f"pickleball_annual_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# Footer with loan details
st.divider()
st.caption(f"""
**Loan Details:** ${loan_amount:,.0f} at {interest_rate}% for {loan_term_years} years | 
**Monthly Payment:** ${monthly_payment:,.2f} | 
**Total Interest:** ${(monthly_payment * num_payments - loan_amount):,.2f}
""")

# Validation assertions for new defaults
if __name__ == "__main__":
    # These assertions validate the new default values are properly set
    # Validation: Check new non-member pricing defaults
    assert base_prime_rate == NON_MEMBER_RATE_PRIME_COURT_DEFAULT, f"Expected non-member prime rate to be {NON_MEMBER_RATE_PRIME_COURT_DEFAULT}, got {base_prime_rate}"
    assert non_prime_rate == NON_MEMBER_RATE_OFFPEAK_COURT_DEFAULT, f"Expected non-member off-peak rate to be {NON_MEMBER_RATE_OFFPEAK_COURT_DEFAULT}, got {non_prime_rate}"
    # Schedule-driven league allocation - percentage varies based on inputs
    # assert league_prime_hours_pct == 60, f"Expected prime-time league allocation to be 60%, got {league_prime_hours_pct}%"
    assert league_price_offpeak == LEAGUE_PRICE_OFFPEAK_SLOT_DEFAULT, f"Expected off-peak league price to be {LEAGUE_PRICE_OFFPEAK_SLOT_DEFAULT}, got {league_price_offpeak}"
    assert league_price_prime == LEAGUE_PRICE_PRIME_SLOT_DEFAULT, f"Expected prime league price to be {LEAGUE_PRICE_PRIME_SLOT_DEFAULT}, got {league_price_prime}"
    assert corporate_rate_prime == 200.0, f"Expected corporate prime rate to be 200.0, got {corporate_rate_prime}"
    assert corporate_rate_offpeak == 170.0, f"Expected corporate off-peak rate to be 170.0, got {corporate_rate_offpeak}"
    
    # Sanity check on league pricing
    assert league_price_prime >= 0 and league_price_offpeak >= 0, "League prices must be non-negative"
    if league_price_offpeak > league_price_prime:
        st.info(f"Note: Off-peak league price (${league_price_offpeak:.0f}) exceeds prime (${league_price_prime:.0f}). This is allowed but uncommon.")
    
    # Validate per-player calculations (for display only - doesn't affect revenue)
    expected_per_player_prime = NON_MEMBER_RATE_PRIME_COURT_DEFAULT / 4
    expected_per_player_offpeak = NON_MEMBER_RATE_OFFPEAK_COURT_DEFAULT / 4
    actual_per_player_prime = base_prime_rate / 4
    actual_per_player_offpeak = non_prime_rate / 4
    assert abs(actual_per_player_prime - expected_per_player_prime) < 0.01, f"Prime per-player should be ~${expected_per_player_prime:.2f}, got ${actual_per_player_prime:.2f}"
    assert abs(actual_per_player_offpeak - expected_per_player_offpeak) < 0.01, f"Off-peak per-player should be ~${expected_per_player_offpeak:.2f}, got ${actual_per_player_offpeak:.2f}"
    
    # Validate pricing units
    # Pricing unit assertions - constants are now defined at top
    
    # Guard against unit cross-contamination
    # Court rates should be in reasonable per-court range ($20-$200)
    assert 20 <= base_prime_rate <= 200, f"Court prime rate ${base_prime_rate} outside reasonable range"
    assert 20 <= non_prime_rate <= 200, f"Court off-peak rate ${non_prime_rate} outside reasonable range"
    # League prices should be in reasonable per-slot range ($50-$300 for 6 weeks)
    assert 50 <= league_price_prime <= 300, f"League prime price ${league_price_prime} outside reasonable range"
    assert 50 <= league_price_offpeak <= 300, f"League off-peak price ${league_price_offpeak} outside reasonable range"
    
    # Validate non-member prime share cap
    assert 0.10 <= nonmember_prime_share_max <= 0.40, f"Non-member prime share max should be between 10-40%, got {nonmember_prime_share_max*100:.0f}%"
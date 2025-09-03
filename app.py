"""
Indoor Pickleball Facility Financial Projections for SBA Loan Application
Generates 2-year financial projections with dynamic scenario modeling
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import io
import hashlib

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

# Check authentication before showing the main app
if not check_password():
    st.stop()

st.title("🎾 Indoor Pickleball Facility - SBA Loan Financial Projections")
st.markdown("### 2-Year Financial Model for SBA Loan Application")
st.info("""
**Revenue Streams:** Memberships • Court Rentals • Leagues • Corporate Events • Tournaments • Retail Pop-up Store
""".strip())

# Constants
NUM_COURTS = 4
HOURS_PER_DAY = 14  # 8 AM to 10 PM typical operation
DAYS_PER_MONTH = 30
PRIME_TIME_HOURS_RATIO = 0.5  # 50% of hours are prime time
DEPRECIATION_ANNUAL = 132325  # Based on ~$994k leasehold improvements + ~$220k equipment

# Initialize session state for inputs
if 'inputs' not in st.session_state:
    st.session_state.inputs = {}

# Sidebar for Assumptions
with st.sidebar:
    st.header("📊 Assumptions")
    
    # Facility Constants (Display Only)
    st.subheader("Facility Constants")
    st.info(f"**Number of Courts:** {NUM_COURTS}")
    
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
        "Base Prime-Time Rate ($/Court/Hour)",
        min_value=20.0,
        max_value=150.0,
        value=56.0,
        step=1.0,
        help="The standard rate for prime-time court rental"
    )
    
    non_prime_discount = st.slider(
        "Non-Prime Rate Discount (% from Prime)",
        min_value=0,
        max_value=50,
        value=21,
        help="Percentage discount for non-prime hours"
    )
    non_prime_rate = base_prime_rate * (1 - non_prime_discount / 100)
    st.caption(f"**Non-Prime Rate: ${non_prime_rate:.2f}/hour**")
    
    # Member discount calculation
    standard_per_person_prime = base_prime_rate / 4  # Assuming 4 players per court
    member_prime_discount = st.slider(
        "Player Member Prime Rate Discount (% from Standard)",
        min_value=0,
        max_value=75,
        value=36,
        help="Percentage discount for members during prime time"
    )
    member_prime_rate = standard_per_person_prime * (1 - member_prime_discount / 100)
    st.caption(f"**Member Prime Rate: ${member_prime_rate:.2f}/person/hour**")
    
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
    member_schedule_default = "75, 100, 130, 165, 200, 240, 280, 325, 375, 425, 465, 500"
    member_schedule_input = st.text_input(
        "Monthly Member Count Schedule (Year 1)",
        value=member_schedule_default,
        help="Enter 12 comma-separated numbers for member count at end of each month"
    )
    
    # Parse member schedule
    try:
        member_schedule = [int(x.strip()) for x in member_schedule_input.split(',')]
        if len(member_schedule) != 12:
            st.error("Please provide exactly 12 member counts (one for each month)")
            member_schedule = [75, 100, 130, 165, 200, 240, 280, 325, 375, 425, 465, 500]
    except:
        st.error("Invalid member schedule format. Using defaults.")
        member_schedule = [75, 100, 130, 165, 200, 240, 280, 325, 375, 425, 465, 500]
    
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
    
    # League Programming
    st.subheader("League Programming")
    
    league_price = st.number_input(
        "Standard League Price ($/Person for 6-week session)",
        min_value=0.0,
        max_value=500.0,
        value=99.0,
        step=1.0
    )
    
    league_prime_hours_pct = st.slider(
        "Prime-Time Hours Allocated to Leagues (%)",
        min_value=0,
        max_value=100,
        value=50,
        help="Percentage of prime-time hours reserved for leagues"
    )
    
    league_sellthrough = st.slider(
        "League Sell-Through Rate (%)",
        min_value=0,
        max_value=100,
        value=85,
        help="Percentage of league spots that are filled"
    )
    
    league_scheduling_efficiency = st.slider(
        "League Scheduling Efficiency (%)",
        min_value=50,
        max_value=100,
        value=90,
        help="Efficiency of court scheduling for leagues (accounts for transitions, no-shows, etc.)"
    )
    
    backfill_league_hours = st.checkbox(
        "Backfill unfilled league hours to rentals?",
        value=True,
        help="If checked, unfilled league hours become available for court rentals"
    )
    
    st.divider()
    
    # Corporate Activities
    st.subheader("Corporate Activities")
    
    corporate_frequency = st.number_input(
        "Corporate Event Frequency (per month)",
        min_value=0,
        max_value=10,
        value=2,  # default 2 for Year 2 planning
        step=1,
        help="Number of corporate team-building events per month"
    )
    
    corporate_revenue_per_event = st.number_input(
        "Corporate Event Revenue ($ per event)",
        min_value=0.0,
        max_value=10000.0,
        value=2500.0,
        step=100.0,
        help="Revenue per corporate event"
    )
    
    corporate_hours_per_event = st.number_input(
        "Corporate Event Utilization (prime hours per event)",
        min_value=0,
        max_value=20,
        value=6,
        step=1,
        help="Prime-time court hours consumed per corporate event"
    )
    
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

# Generate monthly projections
def generate_monthly_projections():
    months = []
    dates = []
    
    for i in range(24):  # 2 years
        current_date = start_date + relativedelta(months=i)
        dates.append(current_date)
        months.append(current_date.strftime("%b %Y"))
    
    # Use member schedule for growth
    member_counts = []
    for i in range(24):
        if i < 12:
            # Year 1: Use the specified schedule (already integers)
            members = member_schedule[i]
        else:
            # Year 2: Continue growth to 120% of Year 1 end value
            year1_end = member_schedule[11]
            growth_factor = 1 + (0.2 * ((i - 11) / 12))  # Linear growth from 100% to 120%
            members = year1_end * min(growth_factor, 1.2)
        member_counts.append(members)  # Keep as float for calculations
    
    # Calculate revenues
    membership_revenue = []
    court_rental_revenue = []
    league_revenue = []
    corporate_revenue = []
    tournament_revenue_list = []
    retail_revenue = []
    
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
        
        # Court rental revenue
        total_court_hours = NUM_COURTS * HOURS_PER_DAY * DAYS_PER_MONTH
        prime_hours = total_court_hours * PRIME_TIME_HOURS_RATIO
        non_prime_hours = total_court_hours * (1 - PRIME_TIME_HOURS_RATIO)
        
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
        
        # Calculate tournament allocation between prime and non-prime
        tournament_prime_hours = tournament_hours_used * 0.7  # 70% of tournament hours are prime
        tournament_non_prime_hours = tournament_hours_used * 0.3  # 30% are non-prime
        
        # Prime hours available after corporate and tournament events
        pre_league_prime = max(0, prime_hours - corporate_prime_hours_used - tournament_prime_hours)
        
        # --- League reservation & revenue (quarterly, leagues start Month 2) ---
        if i < league_start_idx:
            # No leagues yet; nothing reserved, no revenue
            reserved_league_prime_hours_monthly = 0.0
            league_rev = 0.0
        else:
            # Compute once at the START of each league quarter and keep constant for 3 months
            if (i - league_start_idx) % 3 == 0:
                # Capacity baseline = PRE-league prime hours * allocation% across the full 3-month session
                session_league_hours = pre_league_prime * (league_prime_hours_pct / 100.0) * 3.0
                # Scheduling efficiency (transitions/no-shows)
                effective_session_hours = session_league_hours * (league_scheduling_efficiency / 100.0)
                # Hours actually run based on sell-through
                run_session_hours = effective_session_hours * (league_sellthrough / 100.0)

                # Fixed monthly reservation (constant for each month of this quarter)
                reserved_league_prime_hours_monthly = run_session_hours / 3.0

                # Revenue: 4 players per court-hour, 6-week program; spread evenly over 3 months
                league_spots = (run_session_hours / 6.0) * 4.0
                current_quarter_league_rev = league_spots * league_price / 3.0

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
        
        # Non-prime hours after tournament usage
        non_prime_hours_after_events = max(0, non_prime_hours - tournament_non_prime_hours)
        
        # Calculate utilization
        if i < 12:
            utilization = rampup_percentages[i]
        else:
            utilization = 0.88  # Steady state at 88% (95% prime, 80% non-prime blended)
        utilization = float(np.clip(utilization, 0.0, 1.0))
        
        # Estimate member vs non-member mix (members use more courts)
        member_play_ratio = min(member_play_ratio_cap, members / 1000.0)  # cap + growth-linked
        
        # Calculate court rental revenue
        # Prime time courts - split between members and non-members
        prime_member_hours = available_prime_hours * utilization * member_play_ratio
        prime_nonmember_hours = available_prime_hours * utilization * (1 - member_play_ratio)
        
        # Members book courts but pay per-person rate (assume avg 3.5 players per court)
        prime_member_court_revenue = prime_member_hours * member_prime_rate * 3.5
        
        # Non-members pay full court rate
        prime_nonmember_revenue = prime_nonmember_hours * base_prime_rate
        
        # Non-prime hours - also split between members and non-members
        non_prime_util = min(1.0, utilization * 0.6)  # Lower utilization in non-prime, capped at 1.0
        non_prime_member_hours = non_prime_hours_after_events * non_prime_util * member_play_ratio
        non_prime_nonmember_hours = non_prime_hours_after_events * non_prime_util * (1 - member_play_ratio)
        
        # Calculate non-prime member rate (scaled down from prime member rate)
        non_prime_discount_factor = non_prime_rate / base_prime_rate
        non_prime_member_rate = member_prime_rate * non_prime_discount_factor
        
        non_prime_member_revenue = non_prime_member_hours * non_prime_member_rate * 3.5
        non_prime_nonmember_revenue = non_prime_nonmember_hours * non_prime_rate
        
        total_court_revenue = (prime_member_court_revenue + prime_nonmember_revenue + 
                             non_prime_member_revenue + non_prime_nonmember_revenue)
        court_rental_revenue.append(total_court_revenue)
        
        # Save monthly league revenue
        league_revenue.append(league_rev)
        
        # Corporate Activities revenue (monthly with ramp-up)
        if i < 3:  # Months 1-3: No corporate events
            actual_corp_frequency = 0
        elif i < 6:  # Months 4-6: 1 event per month
            actual_corp_frequency = 1
        elif i < 12:  # Months 7-12: 2 events per month
            actual_corp_frequency = 2
        else:  # Year 2: Use the input frequency (default 2)
            actual_corp_frequency = min(corporate_frequency, 2)  # Cap at 2 for Year 2
        
        corp_rev = actual_corp_frequency * corporate_revenue_per_event
        corporate_revenue.append(corp_rev)
        
        # Tournament revenue (quarterly with ramp-up)
        if (i + 1) % 3 == 0:  # Months 3, 6, 9, 12, etc.
            base_tourn_rev = tournament_frequency * tournament_revenue
            
            # Apply ramp-up for first year tournaments
            if i == 2:  # Month 3 - First tournament at 50%
                tourn_rev = base_tourn_rev * 0.5
            elif i == 5:  # Month 6 - Second tournament at 75%
                tourn_rev = base_tourn_rev * 0.75
            else:  # Month 9+ - Full revenue
                tourn_rev = base_tourn_rev
        else:
            tourn_rev = 0
        tournament_revenue_list.append(tourn_rev)
        
        # Retail revenue (monthly, profit share; no court hours impact)
        retail_profit = retail_monthly_sales * (retail_gross_margin_pct / 100.0)
        retail_rev = retail_profit * (retail_revenue_share / 100.0)
        retail_revenue.append(retail_rev)
    
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
    projections['Variable Costs'] = projections['Total Revenue'] * (variable_cost_pct / 100)
    projections['Total Operating Costs'] = projections['Fixed Costs'] + projections['Variable Costs']
    
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
    
    # DSCR (Operating) and DSCR (With Working Capital)
    projections['DSCR_Operating'] = projections['EBITDA'] / projections['Total Debt Service']
    projections['DSCR_With_WC'] = (projections['EBITDA'] + projections['Working Capital Buffer']) / projections['Total Debt Service']
    projections['DSCR_Operating'] = projections['DSCR_Operating'].replace([np.inf, -np.inf], np.nan)
    projections['DSCR_With_WC'] = projections['DSCR_With_WC'].replace([np.inf, -np.inf], np.nan)
    
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
    
    return projections

# Generate projections
projections_df = generate_monthly_projections()

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
    prime_hours = total_court_hours * PRIME_TIME_HOURS_RATIO
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

# Export Functionality
st.subheader("💾 Export Financial Projections")

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
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import math

st.set_page_config(
    page_title="Pickleball Financial Model",
    page_icon="🎾",
    layout="wide"
)

st.title("🎾 Pickleball Financial Model")

if 'tsd_simple' not in st.session_state:
    st.session_state.tsd_simple = {
        # Two-tier structure
        'members': 370,
        'non_members': 150,
        'monthly_membership_fee': 68,
        # Per-person hourly rates
        'member_rate': 6,
        'non_member_rate': 10,
        # Early bird rates (per person)
        'early_bird_member_rate': 3.75,
        'early_bird_nonmember_rate': 5,
        # Time allocation
        'early_bird_percentage': 15,
        'regular_time_percentage': 40,
        'prime_time_percentage': 45,
        # Usage assumptions
        'member_hours_per_month': 11,
        'non_member_hours_per_month': 4,
        # Operations
        'hours_per_day': 15,
        'programming_revenue': 38000,
        'ancillary_revenue': 32000
    }

if 'veros_params' not in st.session_state:
    st.session_state.veros_params = {
        'member_scaling': 0.42,
        'market_adjustment': 0.9,
        'startup_ramp': 6
    }

def calculate_tsd_simple_revenue(courts, params, growth_factor=1.0):
    # Third Shot Drop simplified model
    
    # Membership revenue
    membership_revenue = params['members'] * params['monthly_membership_fee'] * growth_factor
    
    # Court time revenue - Members
    member_early_hours = params['members'] * params['member_hours_per_month'] * (params['early_bird_percentage']/100)
    member_regular_hours = params['members'] * params['member_hours_per_month'] * (params['regular_time_percentage']/100)
    member_prime_hours = params['members'] * params['member_hours_per_month'] * (params['prime_time_percentage']/100)
    
    member_court_revenue = (
        member_early_hours * params['early_bird_member_rate'] + 
        member_regular_hours * params['member_rate'] + 
        member_prime_hours * params['member_rate']
    ) * growth_factor
    
    # Court time revenue - Non-Members  
    non_member_early_hours = params['non_members'] * params['non_member_hours_per_month'] * (params['early_bird_percentage']/100)
    non_member_regular_hours = params['non_members'] * params['non_member_hours_per_month'] * (params['regular_time_percentage']/100)
    non_member_prime_hours = params['non_members'] * params['non_member_hours_per_month'] * (params['prime_time_percentage']/100)
    
    non_member_court_revenue = (
        non_member_early_hours * params['early_bird_nonmember_rate'] + 
        non_member_regular_hours * params['non_member_rate'] + 
        non_member_prime_hours * params['non_member_rate']
    ) * growth_factor
    
    total_court_revenue = member_court_revenue + non_member_court_revenue
    
    # Utilization check
    total_hours = (
        params['members'] * params['member_hours_per_month'] +
        params['non_members'] * params['non_member_hours_per_month']
    ) * growth_factor
    
    court_capacity = courts * params['hours_per_day'] * 30  # Monthly available hours
    utilization_rate = min((total_hours / court_capacity) * 100 if court_capacity > 0 else 0, 100.0)
    
    # Programming and ancillary revenue
    programming_revenue = params.get('programming_revenue', 35000) * growth_factor
    ancillary_revenue = params.get('ancillary_revenue', 25000) * growth_factor
    
    total_revenue = membership_revenue + total_court_revenue + programming_revenue + ancillary_revenue
    
    return {
        'membership_revenue': membership_revenue,
        'court_revenue': total_court_revenue,
        'member_court_revenue': member_court_revenue,
        'non_member_court_revenue': non_member_court_revenue,
        'programming': programming_revenue,
        'ancillary': ancillary_revenue,
        'total': total_revenue,
        'utilization_rate': utilization_rate,
        'total_hours': total_hours
    }

def calculate_tsd_revenue(courts, params, growth_factor=1.0):
    # Third Shot Drop hourly-based revenue model
    
    # Calculate blended hourly rates with prime time pricing
    prime_usage = params.get('prime_time_usage', 50) / 100
    off_peak_usage = 1 - prime_usage
    
    # Tier 1 rates
    t1_prime_rate = params['tier1_base_rate'] + params.get('prime_time_premium', 2)
    t1_offpeak_rate = max(params['tier1_base_rate'] - params.get('off_peak_discount', 1), 0)
    t1_blended_rate = (t1_prime_rate * prime_usage) + (t1_offpeak_rate * off_peak_usage)
    
    # Tier 2 & 3 rates (same base rate)
    t2_prime_rate = params['tier2_base_rate'] + params.get('prime_time_premium', 2)
    t2_offpeak_rate = max(params['tier2_base_rate'] - params.get('off_peak_discount', 1), 0)
    t2_blended_rate = (t2_prime_rate * prime_usage) + (t2_offpeak_rate * off_peak_usage)
    
    # Average hours per member per month
    avg_hours = params.get('avg_hours_per_member', 12)
    
    # Calculate revenue components
    membership_revenue = (
        params['tier2_members'] * params['tier2_monthly_fee'] +
        params['tier3_members'] * params['tier3_monthly_fee']
    ) * growth_factor
    
    court_revenue = (
        params['tier1_members'] * avg_hours * t1_blended_rate +
        params['tier2_members'] * avg_hours * t2_blended_rate +
        params['tier3_members'] * avg_hours * t2_blended_rate
    ) * growth_factor
    
    # Utilization check
    total_hours = (
        params['tier1_members'] * avg_hours +
        params['tier2_members'] * avg_hours +
        params['tier3_members'] * avg_hours
    ) * growth_factor
    
    court_capacity = courts * params['hours_per_day'] * 30  # Monthly available hours
    utilization_rate = min((total_hours / court_capacity) * 100 if court_capacity > 0 else 0, 100.0)
    
    # Programming and ancillary revenue
    base_revenue = membership_revenue + court_revenue
    programming_revenue = params.get('programming_revenue', 35000) * growth_factor
    ancillary_revenue = base_revenue * (params.get('ancillary_ratio', 35) / 100)
    
    total_revenue = base_revenue + programming_revenue + ancillary_revenue
    
    return {
        'court_revenue': court_revenue,
        'membership_revenue': membership_revenue,
        'programming': programming_revenue,
        'ancillary': ancillary_revenue,
        'total': total_revenue,
        'utilization_rate': utilization_rate,
        'total_hours': total_hours,
        'blended_rates': {
            'tier1': t1_blended_rate,
            'tier2': t2_blended_rate
        }
    }

tab1, tab2 = st.tabs(["Facility Model Validation", "Veros Projections"])

with tab1:
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.header("Third Shot Drop Model")
        st.markdown("**Courts:** 12 (fixed)")
        
        st.slider(
            "Hours per day", 10, 20, 
            value=st.session_state.tsd_simple['hours_per_day'],
            key='hours_per_day'
        )
        
        st.subheader("Membership Categories")
        
        st.slider(
            "Members", 100, 500, 
            value=st.session_state.tsd_simple['members'],
            key='members',
            help="Pay $68/month + $6/hour"
        )
        
        st.slider(
            "Non-Members/Drop-ins", 50, 300, 
            value=st.session_state.tsd_simple['non_members'],
            key='non_members',
            help="Pay $10/hour only"
        )
        
        st.markdown("**Membership:** $68/month")
        st.markdown("**Member rate:** $6/hour")
        st.markdown("**Non-member rate:** $10/hour")
        
        st.subheader("Time Allocation")
        
        st.slider(
            "Early Bird Usage %", 10, 25, 
            value=st.session_state.tsd_simple['early_bird_percentage'],
            key='early_bird_percentage'
        )
        
        st.slider(
            "Regular Time Usage %", 30, 50, 
            value=st.session_state.tsd_simple['regular_time_percentage'],
            key='regular_time_percentage'
        )
        
        st.slider(
            "Prime Time Usage %", 35, 55, 
            value=st.session_state.tsd_simple['prime_time_percentage'],
            key='prime_time_percentage'
        )
        
        st.caption("Early bird: $15/court (4 people)")
        st.caption("Early bird: $20/court (non-members)")
        
        st.subheader("Usage Assumptions")
        
        st.slider(
            "Member Hours/Month", 8, 20, 
            value=st.session_state.tsd_simple['member_hours_per_month'],
            key='member_hours_per_month'
        )
        
        st.slider(
            "Non-Member Hours/Month", 2, 8, 
            value=st.session_state.tsd_simple['non_member_hours_per_month'],
            key='non_member_hours_per_month'
        )
        
        st.subheader("Additional Revenue")
        
        st.slider(
            "Programming Revenue", 
            min_value=5000, 
            max_value=50000, 
            value=st.session_state.tsd_simple['programming_revenue'],
            step=1000,
            key='programming_revenue',
            help="Tournaments, leagues, clinics, events"
        )
        
        st.slider(
            "Ancillary Revenue", 
            min_value=5000, 
            max_value=40000, 
            value=st.session_state.tsd_simple['ancillary_revenue'],
            step=1000,
            key='ancillary_revenue',
            help="Pro shop, food, equipment"
        )
        
        st.subheader("Growth Curve")
        starting_capacity = st.slider(
            "Starting capacity (%)", 40, 80, 60, 5,
            help="Member count at month 1 as % of current"
        )
        
        st.subheader("Model Comparison")
        st.markdown("**Third Shot Drop (Colorado):**")
        st.markdown("- Members: $68/month + $6/hour")
        st.markdown("- Drop-ins: $10/hour")
        st.markdown("- Prime time: +$2/hour")
        
        st.markdown("**Reference Facility:**")
        st.markdown("- Elite: $119/month")
        st.markdown("- Mid-tier: $49-99/month") 
        st.markdown("- Total Members: 370")
        
        st.subheader("Member Summary")
        total_people = st.session_state.members + st.session_state.non_members
        st.markdown(f"**Total People: {total_people}**")
        st.markdown(f"Members: {st.session_state.members} ({st.session_state.members/total_people*100:.0f}%)")
        st.markdown(f"Non-Members: {st.session_state.non_members} ({st.session_state.non_members/total_people*100:.0f}%)")
    
    with col2:
        st.header("Revenue Validation")
        
        uploaded_file = st.file_uploader(
            "Upload CSV with columns: month, total_revenue, membership_revenue, dropins, programming, ancillary",
            type=['csv']
        )
        
        if uploaded_file is not None:
            actual_data = pd.read_csv(uploaded_file)
            
            predicted_revenues = []
            for month_idx, row in actual_data.iterrows():
                growth_factor = min(starting_capacity/100 + (month_idx * 0.05), 1.0)
                params = {
                    'members': st.session_state.members,
                    'non_members': st.session_state.non_members,
                    'monthly_membership_fee': 68,
                    'member_rate': 6,
                    'non_member_rate': 10,
                    'early_bird_member_rate': 3.75,
                    'early_bird_nonmember_rate': 5,
                    'early_bird_percentage': st.session_state.early_bird_percentage,
                    'regular_time_percentage': st.session_state.regular_time_percentage,
                    'prime_time_percentage': st.session_state.prime_time_percentage,
                    'member_hours_per_month': st.session_state.member_hours_per_month,
                    'non_member_hours_per_month': st.session_state.non_member_hours_per_month,
                    'hours_per_day': st.session_state.hours_per_day,
                    'programming_revenue': st.session_state.programming_revenue,
                    'ancillary_revenue': st.session_state.ancillary_revenue
                }
                pred = calculate_tsd_simple_revenue(12, params, growth_factor)
                predicted_revenues.append(pred)
            
            comparison_data = []
            for i, row in actual_data.iterrows():
                pred = predicted_revenues[i]
                actual_total = row['total_revenue']
                predicted_total = pred['total']
                variance = abs((predicted_total - actual_total) / actual_total * 100)
                
                comparison_data.append({
                    'Month': row['month'],
                    'Actual Revenue': f"${actual_total:,.0f}",
                    'Predicted Revenue': f"${predicted_total:,.0f}",
                    'Variance %': f"{variance:.1f}%",
                    'variance_num': variance
                })
            
            comparison_df = pd.DataFrame(comparison_data)
            
            st.subheader("Revenue Comparison")
            
            def highlight_variance(val):
                if 'Variance %' in val.name:
                    num = float(val.replace('%', ''))
                    if num > 5:
                        return 'color: red'
                    elif num > 3:
                        return 'color: orange'
                    else:
                        return 'color: green'
                return ''
            
            st.dataframe(
                comparison_df[['Month', 'Actual Revenue', 'Predicted Revenue', 'Variance %']],
                use_container_width=True
            )
            
            avg_variance = comparison_df['variance_num'].mean()
            st.metric("Overall Accuracy Score", f"{100 - avg_variance:.1f}%")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=actual_data['month'],
                y=actual_data['total_revenue'],
                mode='lines+markers',
                name='Actual Revenue',
                line=dict(color='blue', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=actual_data['month'],
                y=[pred['total'] for pred in predicted_revenues],
                mode='lines+markers',
                name='Predicted Revenue',
                line=dict(color='red', width=2, dash='dash')
            ))
            fig.update_layout(
                title='Actual vs Predicted Revenue',
                xaxis_title='Month',
                yaxis_title='Revenue ($)',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Revenue Breakdown")
            latest_pred = predicted_revenues[-1]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Membership", f"${latest_pred['membership_revenue']:,.0f}")
            with col2:
                st.metric("Court Time", f"${latest_pred['court_revenue']:,.0f}")
            with col3:
                st.metric("Programming", f"${latest_pred['programming']:,.0f}")
            with col4:
                st.metric("Ancillary", f"${latest_pred['ancillary']:,.0f}")
            
            st.metric("**Total Revenue**", f"${latest_pred['total']:,.0f}", 
                     delta=f"Utilization: {latest_pred['utilization_rate']:.1f}%")
            
            # Show court revenue breakdown
            st.caption(f"Member court revenue: ${latest_pred['member_court_revenue']:,.0f}")
            st.caption(f"Non-member court revenue: ${latest_pred['non_member_court_revenue']:,.0f}")
        
        else:
            st.info("Upload a CSV file to compare actual vs predicted revenue")
            
            st.subheader("Current Model Predictions")
            params = {
                'members': st.session_state.members,
                'non_members': st.session_state.non_members,
                'monthly_membership_fee': 68,
                'member_rate': 6,
                'non_member_rate': 10,
                'early_bird_member_rate': 3.75,
                'early_bird_nonmember_rate': 5,
                'early_bird_percentage': st.session_state.early_bird_percentage,
                'regular_time_percentage': st.session_state.regular_time_percentage,
                'prime_time_percentage': st.session_state.prime_time_percentage,
                'member_hours_per_month': st.session_state.member_hours_per_month,
                'non_member_hours_per_month': st.session_state.non_member_hours_per_month,
                'hours_per_day': st.session_state.hours_per_day,
                'programming_revenue': st.session_state.programming_revenue,
                'ancillary_revenue': st.session_state.ancillary_revenue
            }
            pred = calculate_tsd_simple_revenue(12, params)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Membership", f"${pred['membership_revenue']:,.0f}")
            with col2:
                st.metric("Court Time", f"${pred['court_revenue']:,.0f}")
            with col3:
                st.metric("Programming", f"${pred['programming']:,.0f}")
            with col4:
                st.metric("Ancillary", f"${pred['ancillary']:,.0f}")
            
            st.metric("**Total Revenue**", f"${pred['total']:,.0f}", 
                     delta=f"Utilization: {pred['utilization_rate']:.1f}%")
            
            # Show court revenue breakdown
            st.caption(f"Member court revenue: ${pred['member_court_revenue']:,.0f}")
            st.caption(f"Non-member court revenue: ${pred['non_member_court_revenue']:,.0f}")
            
            # Show September target
            st.info("Target: Reference facility September actual = $115,946")

with tab2:
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.header("Veros Settings")
        st.markdown("**Courts:** 5 (fixed)")
        
        st.subheader("Facility Economics")
        
        facility_sqft = st.slider("Facility Size (sqft)", 12000, 20000, 14000, step=500)
        lease_rate_per_sqft = st.slider("Lease Rate ($/sqft/year)", 15, 30, 20, step=1)
        annual_rent = facility_sqft * lease_rate_per_sqft
        
        annual_utilities = st.slider("Annual Utilities", 30000, 80000, 50000, step=5000)
        annual_insurance = st.slider("Annual Insurance", 15000, 40000, 25000, step=2500)
        annual_staffing = st.slider("Annual Staffing", 150000, 300000, 150000, step=10000)
        
        total_annual_fixed_costs = annual_rent + annual_utilities + annual_insurance + annual_staffing
        monthly_fixed_costs = total_annual_fixed_costs / 12
        
        st.metric("Monthly Fixed Costs", f"${monthly_fixed_costs:,.0f}")
        st.metric("Annual Rent", f"${annual_rent:,.0f}")
        
        st.subheader("Scaling Factors")
        
        base_utilization_boost = st.slider(
            "Small Facility Utilization Boost", 
            1.0, 1.5, 1.25, 
            step=0.05,
            help="Smaller facilities achieve higher utilization per court"
        )
        
        court_scaling_factor = 5 / 12  # Base scaling
        member_scaling_factor = st.slider(
            "Member scaling factor", 
            0.30, 0.60, 
            0.44,
            step=0.02
        )
        
        market_adjustment = st.slider(
            "Market positioning", 
            0.90, 1.30, 1.25, 
            step=0.05,
            help="Premium location and tech advantages"
        )
        
        st.subheader("Growth Parameters")
        
        months_to_peak = st.slider("Months to peak capacity", 6, 24, 12)
        starting_capacity_veros = st.slider("Starting capacity (%)", 20, 60, 40)
        
        st.subheader("Break-Even Analysis")
        monthly_break_even_revenue = monthly_fixed_costs / (1 - 0.25)  # Account for variable costs
        st.metric("Monthly Break-Even Revenue", f"${monthly_break_even_revenue:,.0f}")
        
        # Calculate base revenue from reference facility validation
        performance_params = {
            'members': 370,
            'non_members': 150,
            'monthly_membership_fee': 68,
            'member_rate': 6,
            'non_member_rate': 10,
            'early_bird_member_rate': 3.75,
            'early_bird_nonmember_rate': 5,
            'early_bird_percentage': 15,
            'regular_time_percentage': 40,
            'prime_time_percentage': 45,
            'member_hours_per_month': 11,
            'non_member_hours_per_month': 4,
            'hours_per_day': 15,
            'programming_revenue': 38000,
            'ancillary_revenue': 32000
        }
        base_performance_revenue = calculate_tsd_simple_revenue(12, performance_params)['total']
    
    def calculate_growth_factor(month, months_to_peak, starting_capacity):
        if month <= months_to_peak:
            # S-curve growth to peak
            progress = month / months_to_peak
            growth_factor = starting_capacity/100 + (1 - starting_capacity/100) * (progress ** 1.5)
        else:
            # Maintain peak capacity with slight seasonal variation
            seasonal_factor = 1 + 0.05 * math.sin((month - months_to_peak) * math.pi / 6)
            growth_factor = min(1.0 * seasonal_factor, 1.1)
        
        return growth_factor
    
    with col2:
        st.header("Veros 24-Month Projections")
        
        scaled_params = {
            'members': st.session_state.members,
            'non_members': st.session_state.non_members,
            'monthly_membership_fee': 68,
            'member_rate': 6,
            'non_member_rate': 10,
            'early_bird_member_rate': 3.75,
            'early_bird_nonmember_rate': 5,
            'early_bird_percentage': st.session_state.early_bird_percentage,
            'regular_time_percentage': st.session_state.regular_time_percentage,
            'prime_time_percentage': st.session_state.prime_time_percentage,
            'member_hours_per_month': st.session_state.member_hours_per_month,
            'non_member_hours_per_month': st.session_state.non_member_hours_per_month,
            'hours_per_day': st.session_state.hours_per_day,
            'programming_revenue': st.session_state.programming_revenue,
            'ancillary_revenue': st.session_state.ancillary_revenue
        }
        # Calculate scaled revenue based on all factors
        projections = []
        break_even_month = None
        
        for month in range(1, 25):
            # Calculate growth factor using S-curve
            growth_factor = calculate_growth_factor(month, months_to_peak, starting_capacity_veros)
            
            # Apply all scaling factors to base revenue
            scaled_revenue = (base_performance_revenue * 
                            member_scaling_factor * 
                            market_adjustment * 
                            base_utilization_boost * 
                            growth_factor)
            
            # Fixed costs from facility economics
            fixed_costs = monthly_fixed_costs
            
            # Variable costs (25% of revenue)
            variable_costs = scaled_revenue * 0.25
            total_costs = fixed_costs + variable_costs
            
            net_income = scaled_revenue - total_costs
            
            # Check for break-even
            if net_income > 0 and break_even_month is None:
                break_even_month = month
            
            projections.append({
                'Month': month,
                'Revenue': scaled_revenue,
                'Costs': total_costs,
                'Fixed Costs': fixed_costs,
                'Variable Costs': variable_costs,
                'Net Income': net_income,
                'Growth Factor': growth_factor * 100  # As percentage
            })
        
        projections_df = pd.DataFrame(projections)
        
        # Display break-even status
        if break_even_month:
            st.success(f"✅ Break-even achieved in Month {break_even_month}")
            months_to_break_even = break_even_month
        else:
            st.warning("⚠️ Break-even not achieved within 24 months")
            months_to_break_even = ">24"
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Break-even", f"Month {months_to_break_even}")
        with col2:
            st.metric("Month 6 Revenue", f"${projections_df.iloc[5]['Revenue']:,.0f}")
        with col3:
            st.metric("Month 12 Revenue", f"${projections_df.iloc[11]['Revenue']:,.0f}")
        with col4:
            st.metric("Month 18 Revenue", f"${projections_df.iloc[17]['Revenue']:,.0f}")
        with col5:
            st.metric("Month 24 Revenue", f"${projections_df.iloc[23]['Revenue']:,.0f}")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=projections_df['Month'],
            y=projections_df['Revenue'],
            mode='lines+markers',
            name='Total Revenue',
            line=dict(color='green', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=projections_df['Month'],
            y=projections_df['Costs'],
            mode='lines+markers',
            name='Total Costs',
            line=dict(color='red', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=projections_df['Month'],
            y=projections_df['Net Income'],
            mode='lines+markers',
            name='Net Income',
            line=dict(color='blue', width=2)
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(
            title='Veros Financial Projections with Real Estate Costs',
            xaxis_title='Month',
            yaxis_title='Amount ($)',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Cost Breakdown")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=projections_df['Month'],
            y=projections_df['Fixed Costs'],
            mode='lines',
            name='Fixed Costs',
            line=dict(color='red', width=2)
        ))
        fig2.add_trace(go.Scatter(
            x=projections_df['Month'],
            y=projections_df['Variable Costs'],
            mode='lines',
            name='Variable Costs (25% of Revenue)',
            line=dict(color='orange', width=2)
        ))
        fig2.add_trace(go.Scatter(
            x=projections_df['Month'],
            y=projections_df['Revenue'],
            mode='lines',
            name='Total Revenue',
            line=dict(color='green', width=2, dash='dash')
        ))
        fig2.update_layout(
            title='Revenue vs Cost Structure',
            xaxis_title='Month',
            yaxis_title='Amount ($)',
            height=400
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Growth Trajectory")
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=projections_df['Month'],
                y=projections_df['Growth Factor'],
                mode='lines+markers',
                name='Growth Factor %',
                line=dict(color='purple', width=2)
            ))
            fig3.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="Peak Capacity")
            fig3.update_layout(
                title='S-Curve Growth to Peak',
                xaxis_title='Month',
                yaxis_title='Capacity (%)',
                height=300,
                yaxis=dict(range=[0, 110])
            )
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            st.subheader("Key Metrics")
            st.metric("Peak Monthly Revenue", f"${projections_df['Revenue'].max():,.0f}")
            st.metric("Peak Monthly Profit", f"${projections_df['Net Income'].max():,.0f}")
            st.metric("Total Fixed Costs/Month", f"${monthly_fixed_costs:,.0f}")
            st.metric("Facility Size", f"{facility_sqft:,} sqft")
            st.metric("Lease Rate", f"${lease_rate_per_sqft}/sqft/year")
        
        with st.expander("View Detailed Monthly Projections"):
            display_df = projections_df.copy()
            for col in ['Revenue', 'Fixed Costs', 'Variable Costs', 'Costs', 'Net Income']:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")
            display_df['Growth Factor'] = display_df['Growth Factor'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(display_df, use_container_width=True)
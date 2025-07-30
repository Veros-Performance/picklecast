"""Veros projections tab component."""

import streamlit as st
import pandas as pd
from config.default_params import REFERENCE_FACILITY_PARAMS
from utils.calculations import calculate_tsd_simple_revenue, calculate_growth_factor
from utils.visualizations import (
    create_financial_projections_chart, 
    create_cost_breakdown_chart,
    create_growth_trajectory_chart
)


def render_projections_tab():
    """Render the Veros projections tab."""
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
        base_performance_revenue = calculate_tsd_simple_revenue(12, REFERENCE_FACILITY_PARAMS)['total']
    
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
        
        fig = create_financial_projections_chart(projections_df)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Cost Breakdown")
        fig2 = create_cost_breakdown_chart(projections_df)
        st.plotly_chart(fig2, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Growth Trajectory")
            fig3 = create_growth_trajectory_chart(projections_df)
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
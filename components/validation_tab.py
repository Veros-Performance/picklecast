"""Model validation tab component."""

import streamlit as st
import pandas as pd
from utils.calculations import calculate_tsd_simple_revenue
from utils.visualizations import create_revenue_comparison_chart


def render_validation_tab():
    """Render the model validation tab."""
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
            
            fig = create_revenue_comparison_chart(actual_data, predicted_revenues)
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
    
    return starting_capacity
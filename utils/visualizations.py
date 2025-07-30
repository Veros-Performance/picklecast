"""Visualization utilities for the financial model."""

import plotly.graph_objects as go
import pandas as pd


def create_revenue_comparison_chart(actual_data, predicted_revenues):
    """Create actual vs predicted revenue comparison chart."""
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
    return fig


def create_financial_projections_chart(projections_df):
    """Create financial projections chart with revenue, costs, and net income."""
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
    return fig


def create_cost_breakdown_chart(projections_df):
    """Create cost breakdown chart."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=projections_df['Month'],
        y=projections_df['Fixed Costs'],
        mode='lines',
        name='Fixed Costs',
        line=dict(color='red', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=projections_df['Month'],
        y=projections_df['Variable Costs'],
        mode='lines',
        name='Variable Costs (25% of Revenue)',
        line=dict(color='orange', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=projections_df['Month'],
        y=projections_df['Revenue'],
        mode='lines',
        name='Total Revenue',
        line=dict(color='green', width=2, dash='dash')
    ))
    fig.update_layout(
        title='Revenue vs Cost Structure',
        xaxis_title='Month',
        yaxis_title='Amount ($)',
        height=400
    )
    return fig


def create_growth_trajectory_chart(projections_df):
    """Create growth trajectory chart."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=projections_df['Month'],
        y=projections_df['Growth Factor'],
        mode='lines+markers',
        name='Growth Factor %',
        line=dict(color='purple', width=2)
    ))
    fig.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="Peak Capacity")
    fig.update_layout(
        title='S-Curve Growth to Peak',
        xaxis_title='Month',
        yaxis_title='Capacity (%)',
        height=300,
        yaxis=dict(range=[0, 110])
    )
    return fig
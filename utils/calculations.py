"""Shared calculation functions for financial models."""

import math


def calculate_tsd_simple_revenue(courts, params, growth_factor=1.0):
    """Calculate revenue using the Third Shot Drop simplified model."""
    
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
    """Calculate revenue using the Third Shot Drop hourly-based model."""
    
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


def calculate_growth_factor(month, months_to_peak, starting_capacity):
    """Calculate growth factor using S-curve model."""
    if month <= months_to_peak:
        # S-curve growth to peak
        progress = month / months_to_peak
        growth_factor = starting_capacity/100 + (1 - starting_capacity/100) * (progress ** 1.5)
    else:
        # Maintain peak capacity with slight seasonal variation
        seasonal_factor = 1 + 0.05 * math.sin((month - months_to_peak) * math.pi / 6)
        growth_factor = min(1.0 * seasonal_factor, 1.1)
    
    return growth_factor
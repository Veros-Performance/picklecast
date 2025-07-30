"""Default parameters for the pickleball financial model."""

TSD_SIMPLE_DEFAULTS = {
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

VEROS_DEFAULTS = {
    'member_scaling': 0.42,
    'market_adjustment': 0.9,
    'startup_ramp': 6
}

# Reference facility parameters for base revenue calculation
REFERENCE_FACILITY_PARAMS = {
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
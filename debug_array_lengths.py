#!/usr/bin/env python3
"""Debug script to check array lengths in the app"""

# Simulate the array creation to find length mismatches
months = ['Jan 2025', 'Feb 2025', 'Mar 2025', 'Apr 2025', 'May 2025', 'Jun 2025',
          'Jul 2025', 'Aug 2025', 'Sep 2025', 'Oct 2025', 'Nov 2025', 'Dec 2025',
          'Jan 2026', 'Feb 2026', 'Mar 2026', 'Apr 2026', 'May 2026', 'Jun 2026',
          'Jul 2026', 'Aug 2026', 'Sep 2026', 'Oct 2026', 'Nov 2026', 'Dec 2026']

# These should all be length 24
arrays = {
    'months': 24,
    'dates': 24,
    'member_counts': 24,
    'membership_revenue': 24,
    'court_rental_revenue': 24,
    'league_revenue': 24,
    'corporate_revenue': 24,
    'tournament_revenue_list': 24,
    'retail_revenue': 24,
    'utilized_hours_list': 24,
    'variable_revenue_list': 24,
    'vr_per_hour_list': 24,
    'revpach_list': 24,
    'staff_costs_list': 24
}

print("Expected lengths for all arrays: 24")
print("\nArray names and expected lengths:")
for name, expected_len in arrays.items():
    print(f"  {name:25} : {expected_len}")

print("\nTo debug in the app, add this before the DataFrame creation:")
print("""
    # Debug array lengths
    print(f"months: {len(months)}")
    print(f"dates: {len(dates)}")
    print(f"member_counts: {len(member_counts)}")
    print(f"membership_revenue: {len(membership_revenue)}")
    print(f"court_rental_revenue: {len(court_rental_revenue)}")
    print(f"league_revenue: {len(league_revenue)}")
    print(f"corporate_revenue: {len(corporate_revenue)}")
    print(f"tournament_revenue_list: {len(tournament_revenue_list)}")
    print(f"retail_revenue: {len(retail_revenue)}")
    print(f"utilized_hours_list: {len(utilized_hours_list)}")
    print(f"variable_revenue_list: {len(variable_revenue_list)}")
    print(f"vr_per_hour_list: {len(vr_per_hour_list)}")
    print(f"revpach_list: {len(revpach_list)}")
    print(f"staff_costs_list: {len(staff_costs_list)}")
""")
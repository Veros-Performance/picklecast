#!/usr/bin/env python3
"""Audit script to find where RevPACH inflation is coming from"""

def audit_revpach():
    """Calculate RevPACH from first principles to find the issue"""
    
    print("=" * 70)
    print("REVPACH AUDIT - Finding the source of inflated revenue")
    print("=" * 70)
    
    # Base constants
    courts = 4
    hours_per_day = 14  # 8 AM to 10 PM
    days_per_year = 365
    available_court_hours_year = courts * hours_per_day * days_per_year
    
    print(f"\nFACILITY CAPACITY:")
    print(f"  Courts: {courts}")
    print(f"  Hours/day: {hours_per_day}")
    print(f"  Available court-hours/year: {available_court_hours_year:,}")
    
    # Pricing from registry
    nm_prime_per_court = 65.0
    nm_off_per_court = 56.0
    league_prime_per_slot_6wk = 150.0
    
    print(f"\nPRICING REGISTRY:")
    print(f"  Non-member prime: ${nm_prime_per_court}/court/hr")
    print(f"  Non-member off-peak: ${nm_off_per_court}/court/hr")
    print(f"  League prime: ${league_prime_per_slot_6wk}/player/6wk")
    
    # Time allocation
    prime_share = 0.24  # 24% of hours are prime
    prime_hours_year = available_court_hours_year * prime_share
    offpeak_hours_year = available_court_hours_year * (1 - prime_share)
    
    print(f"\nTIME ALLOCATION:")
    print(f"  Prime hours/year: {prime_hours_year:,.0f} ({prime_share*100:.0f}%)")
    print(f"  Off-peak hours/year: {offpeak_hours_year:,.0f} ({(1-prime_share)*100:.0f}%)")
    
    # League allocation (schedule-driven)
    league_blocks_per_week = 14  # From schedule calculation
    league_block_hours = 1.667  # 90 min + 10 min buffer
    league_court_hours_week = league_blocks_per_week * league_block_hours * courts
    league_weeks_per_year = 46
    league_court_hours_year = league_court_hours_week * league_weeks_per_year
    league_share_of_prime = league_court_hours_year / prime_hours_year
    
    print(f"\nLEAGUE ALLOCATION:")
    print(f"  Blocks/week: {league_blocks_per_week}")
    print(f"  Block duration: {league_block_hours:.3f} hours")
    print(f"  Court-hours/week: {league_court_hours_week:.1f}")
    print(f"  Court-hours/year: {league_court_hours_year:.0f}")
    print(f"  Share of prime: {league_share_of_prime*100:.1f}%")
    
    # Open play hours (remainder after leagues)
    open_prime_hours_year = prime_hours_year - league_court_hours_year
    open_offpeak_hours_year = offpeak_hours_year  # No off-peak leagues
    
    print(f"\nOPEN PLAY HOURS:")
    print(f"  Prime (after leagues): {open_prime_hours_year:,.0f}")
    print(f"  Off-peak: {open_offpeak_hours_year:,.0f}")
    
    # Utilization rates
    prime_utilization = 0.85
    offpeak_utilization = 0.51  # 0.85 * 0.6
    member_play_ratio = 0.6  # 60% members, 40% non-members
    
    print(f"\nUTILIZATION:")
    print(f"  Prime utilization: {prime_utilization*100:.0f}%")
    print(f"  Off-peak utilization: {offpeak_utilization*100:.0f}%")
    print(f"  Member play ratio: {member_play_ratio*100:.0f}%")
    
    # Calculate utilized hours
    utilized_prime = open_prime_hours_year * prime_utilization
    utilized_offpeak = open_offpeak_hours_year * offpeak_utilization
    
    # Split between members and non-members
    nm_prime_hours = utilized_prime * (1 - member_play_ratio)
    member_prime_hours = utilized_prime * member_play_ratio
    nm_offpeak_hours = utilized_offpeak * (1 - member_play_ratio)
    member_offpeak_hours = utilized_offpeak * member_play_ratio
    
    print(f"\nUTILIZED COURT-HOURS BY SEGMENT:")
    print(f"  Non-member prime: {nm_prime_hours:,.0f}")
    print(f"  Member prime: {member_prime_hours:,.0f}")
    print(f"  Non-member off-peak: {nm_offpeak_hours:,.0f}")
    print(f"  Member off-peak: {member_offpeak_hours:,.0f}")
    
    # Court rental revenue (members play free)
    court_rev_nm_prime = nm_prime_hours * nm_prime_per_court
    court_rev_member_prime = member_prime_hours * 0  # Members free
    court_rev_nm_offpeak = nm_offpeak_hours * nm_off_per_court
    court_rev_member_offpeak = member_offpeak_hours * 0  # Members free
    
    total_court_revenue = (court_rev_nm_prime + court_rev_member_prime + 
                          court_rev_nm_offpeak + court_rev_member_offpeak)
    
    print(f"\nCOURT RENTAL REVENUE:")
    print(f"  Non-member prime: ${court_rev_nm_prime:,.0f}")
    print(f"  Member prime: ${court_rev_member_prime:,.0f}")
    print(f"  Non-member off-peak: ${court_rev_nm_offpeak:,.0f}")
    print(f"  Member off-peak: ${court_rev_member_offpeak:,.0f}")
    print(f"  TOTAL COURT REVENUE: ${total_court_revenue:,.0f}")
    
    # Implied rates check
    implied_nm_prime_rate = court_rev_nm_prime / nm_prime_hours if nm_prime_hours > 0 else 0
    implied_nm_off_rate = court_rev_nm_offpeak / nm_offpeak_hours if nm_offpeak_hours > 0 else 0
    
    print(f"\nIMPLIED RATES CHECK:")
    print(f"  Non-member prime: ${implied_nm_prime_rate:.2f} (configured: ${nm_prime_per_court})")
    print(f"  Non-member off-peak: ${implied_nm_off_rate:.2f} (configured: ${nm_off_per_court})")
    
    # League revenue
    weekly_league_slots = 224  # 14 blocks * 16 players
    league_fill_rate = 0.9
    filled_slots_week = weekly_league_slots * league_fill_rate
    weekly_league_rev = filled_slots_week * (league_prime_per_slot_6wk / 6.0)
    annual_league_rev = weekly_league_rev * league_weeks_per_year
    
    print(f"\nLEAGUE REVENUE:")
    print(f"  Slots/week: {weekly_league_slots}")
    print(f"  Filled slots/week: {filled_slots_week:.0f}")
    print(f"  Weekly revenue: ${weekly_league_rev:,.0f}")
    print(f"  ANNUAL LEAGUE REVENUE: ${annual_league_rev:,.0f}")
    
    # Other revenue (estimates)
    membership_revenue = 350 * 40 * 12  # 350 members avg, $40/mo
    corporate_revenue = 50000  # Estimate
    tournament_revenue = 20000  # Estimate
    retail_revenue = 30000  # Estimate
    
    print(f"\nOTHER REVENUE:")
    print(f"  Membership: ${membership_revenue:,.0f}")
    print(f"  Corporate: ${corporate_revenue:,.0f}")
    print(f"  Tournament: ${tournament_revenue:,.0f}")
    print(f"  Retail: ${retail_revenue:,.0f}")
    
    # Total variable revenue
    variable_revenue = (total_court_revenue + annual_league_rev + 
                       corporate_revenue + tournament_revenue + retail_revenue)
    
    # Calculate RevPACH
    revpach = variable_revenue / available_court_hours_year
    
    # Calculate revenue per utilized hour
    total_utilized = (nm_prime_hours + member_prime_hours + 
                     nm_offpeak_hours + member_offpeak_hours + 
                     league_court_hours_year)
    rev_per_util_hr = variable_revenue / total_utilized if total_utilized > 0 else 0
    
    print(f"\n" + "=" * 70)
    print("FINAL METRICS:")
    print("=" * 70)
    print(f"  Total Variable Revenue: ${variable_revenue:,.0f}")
    print(f"  Available Court-Hours: {available_court_hours_year:,}")
    print(f"  Utilized Court-Hours: {total_utilized:,.0f}")
    print(f"  RevPACH: ${revpach:.2f}")
    print(f"  Revenue/Utilized Hour: ${rev_per_util_hr:.2f}")
    
    print(f"\nTARGET RANGES:")
    print(f"  RevPACH target: $10-$22 {'✓' if 10 <= revpach <= 22 else '✗'}")
    print(f"  Rev/Util Hr target: $35-$55 {'✓' if 35 <= rev_per_util_hr <= 55 else '✗'}")
    
    if revpach > 22:
        print(f"\n⚠️  RevPACH is ${revpach:.2f}, which is ${revpach - 22:.2f} above target max")
        print("\nPOSSIBLE CAUSES:")
        print("  1. Court revenue calculation may have player multipliers")
        print("  2. League revenue may be double-counted")
        print("  3. Membership revenue included in variable revenue")
        print("  4. Hours calculation may be wrong")

if __name__ == "__main__":
    audit_revpach()
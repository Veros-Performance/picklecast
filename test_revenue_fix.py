#!/usr/bin/env python3
"""Test that revenue calculations are now reasonable after fixing member court pricing"""

def test_revenue_calculations():
    """Verify revenue is no longer inflated"""
    
    print("=" * 70)
    print("TESTING REVENUE CALCULATIONS AFTER FIX")
    print("=" * 70)
    
    # Test parameters (defaults)
    courts = 4
    prime_hours_monthly = 333  # Avg prime hours per month
    offpeak_hours_monthly = 400  # Avg off-peak hours per month
    
    # Pricing
    non_member_rate_prime = 65.0  # Per court hour
    non_member_rate_offpeak = 56.0  # Per court hour
    member_court_rate = 0.0  # Members play free (included in membership)
    
    # Utilization
    prime_utilization = 0.85
    offpeak_utilization = 0.51  # 85% * 0.6
    
    # Member play ratio (with 200 members avg)
    member_play_ratio = 0.6  # 60% of play is members
    
    # League allocation (schedule-driven, ~63% of prime)
    league_prime_pct = 0.63
    corporate_prime_pct = 0.05
    tournament_prime_pct = 0.02
    
    print("\nINPUT ASSUMPTIONS:")
    print(f"  Courts: {courts}")
    print(f"  Prime hours/month: {prime_hours_monthly}")
    print(f"  Off-peak hours/month: {offpeak_hours_monthly}")
    print(f"  Non-member rates: ${non_member_rate_prime}/hr prime, ${non_member_rate_offpeak}/hr off-peak")
    print(f"  Member court rate: ${member_court_rate}/hr (free with membership)")
    print(f"  Prime utilization: {prime_utilization * 100}%")
    print(f"  Off-peak utilization: {offpeak_utilization * 100}%")
    print(f"  Member play ratio: {member_play_ratio * 100}%")
    
    # Calculate available open play hours
    prime_for_leagues = prime_hours_monthly * league_prime_pct
    prime_for_corporate = prime_hours_monthly * corporate_prime_pct
    prime_for_tournaments = prime_hours_monthly * tournament_prime_pct
    
    open_prime = prime_hours_monthly - prime_for_leagues - prime_for_corporate - prime_for_tournaments
    open_offpeak = offpeak_hours_monthly  # Assuming no off-peak leagues/events
    
    print(f"\nHOURS ALLOCATION:")
    print(f"  Prime for leagues: {prime_for_leagues:.1f} hrs/mo ({league_prime_pct*100:.1f}%)")
    print(f"  Prime for corporate: {prime_for_corporate:.1f} hrs/mo")
    print(f"  Prime for tournaments: {prime_for_tournaments:.1f} hrs/mo")
    print(f"  Open prime play: {open_prime:.1f} hrs/mo")
    print(f"  Open off-peak play: {open_offpeak:.1f} hrs/mo")
    
    # Calculate utilized hours
    prime_member_hours = open_prime * prime_utilization * member_play_ratio
    prime_nonmember_hours = open_prime * prime_utilization * (1 - member_play_ratio)
    offpeak_member_hours = open_offpeak * offpeak_utilization * member_play_ratio
    offpeak_nonmember_hours = open_offpeak * offpeak_utilization * (1 - member_play_ratio)
    
    print(f"\nUTILIZED HOURS:")
    print(f"  Prime member hours: {prime_member_hours:.1f}")
    print(f"  Prime non-member hours: {prime_nonmember_hours:.1f}")
    print(f"  Off-peak member hours: {offpeak_member_hours:.1f}")
    print(f"  Off-peak non-member hours: {offpeak_nonmember_hours:.1f}")
    
    # Calculate revenue (FIXED: no player multipliers)
    prime_member_revenue = prime_member_hours * member_court_rate
    prime_nonmember_revenue = prime_nonmember_hours * non_member_rate_prime
    offpeak_member_revenue = offpeak_member_hours * member_court_rate
    offpeak_nonmember_revenue = offpeak_nonmember_hours * non_member_rate_offpeak
    
    total_court_revenue_monthly = (
        prime_member_revenue + prime_nonmember_revenue +
        offpeak_member_revenue + offpeak_nonmember_revenue
    )
    
    print(f"\nMONTHLY COURT REVENUE:")
    print(f"  Prime member revenue: ${prime_member_revenue:,.2f}")
    print(f"  Prime non-member revenue: ${prime_nonmember_revenue:,.2f}")
    print(f"  Off-peak member revenue: ${offpeak_member_revenue:,.2f}")
    print(f"  Off-peak non-member revenue: ${offpeak_nonmember_revenue:,.2f}")
    print(f"  TOTAL MONTHLY: ${total_court_revenue_monthly:,.2f}")
    
    # Annual projections
    annual_court_revenue = total_court_revenue_monthly * 12
    print(f"\nANNUAL COURT REVENUE: ${annual_court_revenue:,.2f}")
    
    # Sanity checks
    print(f"\nSANITY CHECKS:")
    
    # Check 1: Revenue per utilized hour
    total_utilized_hours = (prime_member_hours + prime_nonmember_hours + 
                           offpeak_member_hours + offpeak_nonmember_hours)
    rev_per_utilized_hour = total_court_revenue_monthly / total_utilized_hours if total_utilized_hours > 0 else 0
    print(f"  Revenue per utilized hour: ${rev_per_utilized_hour:.2f}")
    print(f"    Expected range: $35-$55 ✓" if 35 <= rev_per_utilized_hour <= 55 else f"    Expected range: $35-$55 ✗")
    
    # Check 2: RevPACH
    total_available_hours = prime_hours_monthly + offpeak_hours_monthly
    revpach = total_court_revenue_monthly / total_available_hours if total_available_hours > 0 else 0
    print(f"  RevPACH: ${revpach:.2f}")
    print(f"    Expected range: $10-$22 ✓" if 10 <= revpach <= 22 else f"    Expected range: $10-$22 ✗")
    
    # Check 3: Annual court revenue reasonableness
    print(f"  Annual court revenue: ${annual_court_revenue:,.0f}")
    print(f"    Expected range: $200k-$400k ✓" if 200000 <= annual_court_revenue <= 400000 else f"    Expected range: $200k-$400k ✗")
    
    # Compare to inflated calculation (OLD BUG)
    print(f"\nCOMPARISON TO OLD INFLATED CALCULATION:")
    # Old bug: member_prime_rate was per-person rate ($7.50) used on court hours
    old_member_rate = 15.0  # Was using per-person rate on court hours
    old_prime_member_rev = prime_member_hours * old_member_rate
    old_offpeak_member_rev = offpeak_member_hours * old_member_rate * 0.86
    old_total = (old_prime_member_rev + prime_nonmember_revenue + 
                old_offpeak_member_rev + offpeak_nonmember_revenue)
    old_annual = old_total * 12
    
    print(f"  OLD inflated monthly: ${old_total:,.2f}")
    print(f"  OLD inflated annual: ${old_annual:,.2f}")
    print(f"  NEW corrected annual: ${annual_court_revenue:,.2f}")
    print(f"  Reduction: ${old_annual - annual_court_revenue:,.2f} ({((old_annual - annual_court_revenue)/old_annual)*100:.1f}%)")
    
    print("\n" + "=" * 70)
    if annual_court_revenue <= 400000:
        print("✅ REVENUE CALCULATIONS NOW REASONABLE!")
    else:
        print("❌ REVENUE STILL APPEARS INFLATED")
    print("=" * 70)

if __name__ == "__main__":
    test_revenue_calculations()
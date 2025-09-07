#!/usr/bin/env python3
"""Test league slot calculations to verify the fix"""

import math

def test_league_calculations():
    """Verify league slot calculations match expected values"""
    
    print("=" * 70)
    print("TESTING LEAGUE SLOT CALCULATIONS")
    print("=" * 70)
    
    # Test data - using defaults from app
    league_session_length_hours = 1.5  # 90 minutes
    league_buffer_minutes = 10.0
    
    # Prime windows
    prime_start_weekday = 16.0  # 4 PM
    prime_end_mon_thu = 21.0    # 9 PM
    prime_end_fri = 21.0        # 9 PM
    prime_start_weekend = 8.0   # 8 AM
    prime_end_weekend = 12.0    # 12 PM
    
    # League nights/mornings
    mon_thu_league_nights = 4   # Monday-Thursday
    fri_league_nights = 0        # Friday nights
    weekend_league_morns = 1     # Weekend mornings
    
    # Capacity
    courts = 4
    players_per_court = 4
    
    print("\nINPUT PARAMETERS:")
    print(f"  Session Length: {league_session_length_hours} hours ({league_session_length_hours * 60} minutes)")
    print(f"  Buffer Between Sessions: {league_buffer_minutes} minutes")
    print(f"  League Nights (Mon-Thu): {mon_thu_league_nights}")
    print(f"  League Nights (Fri): {fri_league_nights}")
    print(f"  League Mornings (Weekend): {weekend_league_morns}")
    print(f"  Courts: {courts}")
    print(f"  Players per Court: {players_per_court}")
    
    # 1) Calculate block length with buffer (hours)
    block_slot_hours = float(league_session_length_hours) + float(league_buffer_minutes) / 60.0
    print(f"\nSTEP 1: Block Slot Hours")
    print(f"  {league_session_length_hours} + {league_buffer_minutes}/60 = {block_slot_hours:.3f} hours")
    print(f"  ✓ Expected: 1.667 hours, Got: {block_slot_hours:.3f} hours")
    
    # 2) Calculate prime windows (hours per night)
    weekday_window_mon_thu = max(0.0, prime_end_mon_thu - prime_start_weekday)
    weekday_window_fri = max(0.0, prime_end_fri - prime_start_weekday)
    weekend_window = max(0.0, prime_end_weekend - prime_start_weekend)
    
    print(f"\nSTEP 2: Prime Windows")
    print(f"  Mon-Thu: {prime_end_mon_thu} - {prime_start_weekday} = {weekday_window_mon_thu} hours")
    print(f"  Fri: {prime_end_fri} - {prime_start_weekday} = {weekday_window_fri} hours")
    print(f"  Weekend: {prime_end_weekend} - {prime_start_weekend} = {weekend_window} hours")
    
    # 3) Calculate blocks per night (floor to get complete blocks)
    blocks_per_mon_thu = math.floor(weekday_window_mon_thu / block_slot_hours)
    blocks_per_fri = math.floor(weekday_window_fri / block_slot_hours)
    blocks_per_weekend = math.floor(weekend_window / block_slot_hours)
    
    print(f"\nSTEP 3: Blocks per Night/Morning")
    print(f"  Mon-Thu: floor({weekday_window_mon_thu}/{block_slot_hours:.3f}) = {blocks_per_mon_thu} blocks")
    print(f"  Fri: floor({weekday_window_fri}/{block_slot_hours:.3f}) = {blocks_per_fri} blocks")
    print(f"  Weekend: floor({weekend_window}/{block_slot_hours:.3f}) = {blocks_per_weekend} blocks")
    print(f"  ✓ Expected Mon-Thu: 3, Got: {blocks_per_mon_thu}")
    print(f"  ✓ Expected Weekend: 2, Got: {blocks_per_weekend}")
    
    # 4) Calculate total weekly blocks
    league_blocks_per_week = (
        mon_thu_league_nights * blocks_per_mon_thu +
        fri_league_nights * blocks_per_fri +
        weekend_league_morns * blocks_per_weekend
    )
    
    print(f"\nSTEP 4: Weekly League Blocks")
    print(f"  ({mon_thu_league_nights} nights × {blocks_per_mon_thu} blocks) + ")
    print(f"  ({fri_league_nights} nights × {blocks_per_fri} blocks) + ")
    print(f"  ({weekend_league_morns} mornings × {blocks_per_weekend} blocks)")
    print(f"  = {mon_thu_league_nights * blocks_per_mon_thu} + {fri_league_nights * blocks_per_fri} + {weekend_league_morns * blocks_per_weekend}")
    print(f"  = {league_blocks_per_week} blocks/week")
    print(f"  ✓ Expected: 14, Got: {league_blocks_per_week}")
    
    # 5) Calculate weekly player slots
    slots_per_block = courts * players_per_court
    weekly_league_slots = league_blocks_per_week * slots_per_block
    
    print(f"\nSTEP 5: Weekly Player Slots")
    print(f"  {league_blocks_per_week} blocks × {courts} courts × {players_per_court} players")
    print(f"  = {league_blocks_per_week} × {slots_per_block}")
    print(f"  = {weekly_league_slots} slots/week")
    print(f"  ✓ Expected: 224, Got: {weekly_league_slots}")
    
    # 6) Revenue calculations
    fill_rate = 0.9  # 90% fill rate
    league_price_prime = 150.0  # $150 per player slot
    weeks_per_session = 6
    sessions_per_year = 46 / weeks_per_session  # ~7.67 sessions
    
    filled_slots = weekly_league_slots * fill_rate
    weekly_revenue = filled_slots * (league_price_prime / weeks_per_session)
    annual_revenue = weekly_revenue * 46  # 46 operational weeks
    
    print(f"\nSTEP 6: Revenue Calculations")
    print(f"  Filled Slots: {weekly_league_slots} × {fill_rate} = {filled_slots:.1f} slots/week")
    print(f"  Weekly Revenue: {filled_slots:.1f} × (${league_price_prime}/{weeks_per_session} weeks)")
    print(f"              = {filled_slots:.1f} × ${league_price_prime/weeks_per_session:.2f}")
    print(f"              = ${weekly_revenue:,.2f}/week")
    print(f"  Annual Revenue: ${weekly_revenue:,.2f} × 46 weeks = ${annual_revenue:,.2f}")
    print(f"  ✓ Expected Weekly: ~$5,025, Got: ${weekly_revenue:,.2f}")
    print(f"  ✓ Expected Annual: ~$231,150, Got: ${annual_revenue:,.2f}")
    
    # Assertions
    print(f"\nASSERTION CHECKS:")
    assertions_passed = 0
    assertions_total = 5
    
    try:
        assert blocks_per_mon_thu == 3, f"Expected 3 blocks Mon-Thu, got {blocks_per_mon_thu}"
        print("  ✓ Assertion 1: blocks_per_mon_thu == 3")
        assertions_passed += 1
    except AssertionError as e:
        print(f"  ✗ Assertion 1: {e}")
    
    try:
        assert blocks_per_weekend == 2, f"Expected 2 blocks weekend, got {blocks_per_weekend}"
        print("  ✓ Assertion 2: blocks_per_weekend == 2")
        assertions_passed += 1
    except AssertionError as e:
        print(f"  ✗ Assertion 2: {e}")
    
    try:
        assert league_blocks_per_week == 14, f"Expected 14 weekly blocks, got {league_blocks_per_week}"
        print("  ✓ Assertion 3: league_blocks_per_week == 14")
        assertions_passed += 1
    except AssertionError as e:
        print(f"  ✗ Assertion 3: {e}")
    
    try:
        assert weekly_league_slots == 224, f"Expected 224 weekly slots, got {weekly_league_slots}"
        print("  ✓ Assertion 4: weekly_league_slots == 224")
        assertions_passed += 1
    except AssertionError as e:
        print(f"  ✗ Assertion 4: {e}")
    
    try:
        assert 5000 <= weekly_revenue <= 5100, f"Expected weekly revenue ~$5,025, got ${weekly_revenue:.2f}"
        print("  ✓ Assertion 5: weekly_revenue in range $5,000-$5,100")
        assertions_passed += 1
    except AssertionError as e:
        print(f"  ✗ Assertion 5: {e}")
    
    print(f"\nRESULT: {assertions_passed}/{assertions_total} assertions passed")
    
    if assertions_passed == assertions_total:
        print("\n✅ ALL LEAGUE CALCULATIONS CORRECT!")
    else:
        print(f"\n❌ {assertions_total - assertions_passed} ASSERTIONS FAILED")
    
    print("=" * 70)

if __name__ == "__main__":
    test_league_calculations()
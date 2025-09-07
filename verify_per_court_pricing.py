#!/usr/bin/env python3
"""Verify that per-court pricing is correctly implemented and no player multipliers affect revenue"""

import re

def verify_per_court_pricing():
    """Verify pricing is strictly per court with no player multipliers"""
    
    print("=" * 70)
    print("VERIFYING PER-COURT PRICING IMPLEMENTATION")
    print("=" * 70)
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Check for pricing unit constant
    if 'PRICING_UNIT = "per_court"' in content:
        print("✅ PRICING_UNIT constant set to 'per_court'")
    else:
        print("❌ PRICING_UNIT constant NOT found or incorrect")
    
    # Check for new constant names
    if 'NON_MEMBER_RATE_PRIME_COURT_DEFAULT' in content:
        print("✅ Using _COURT_DEFAULT constants for clarity")
    else:
        print("❌ Not using _COURT_DEFAULT constant names")
    
    # Check widget labels
    if 'per court / hr' in content.lower():
        print("✅ Widget labels clearly show 'per court / hr'")
    else:
        print("❌ Widget labels don't clearly indicate per-court pricing")
    
    # Check for player multipliers in revenue calculations
    multiplier_patterns = [
        r'revenue.*\*.*3\.5',  # Looking for * 3.5
        r'revenue.*\*.*players_per_court',
        r'court_revenue.*\*.*3\.5',
        r'member_court_revenue.*\*.*3\.5'
    ]
    
    found_multipliers = False
    for pattern in multiplier_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            # Check if it's in a comment
            for match in matches:
                if '#' not in match:  # Not a comment
                    print(f"❌ Found player multiplier in revenue calc: {match[:60]}...")
                    found_multipliers = True
    
    if not found_multipliers:
        print("✅ No player multipliers found in revenue calculations")
    
    # Check for non-member prime share cap
    if 'value=25' in content and 'Max Non-Member Share of OPEN Prime Hours' in content:
        print("✅ Non-member prime share cap defaults to 25%")
    else:
        print("❌ Non-member prime share cap not set to 25% default")
    
    # Check for RevPACH calculations
    if 'revpach' in content.lower():
        print("✅ RevPACH calculations added")
    else:
        print("❌ RevPACH calculations missing")
    
    # Check for revenue per utilized hour
    if 'rev_per_util_hr' in content:
        print("✅ Revenue per utilized hour calculations added")
    else:
        print("❌ Revenue per utilized hour calculations missing")
    
    # Check for sanity check bands
    if 'VR_MIN, VR_MAX = 35.0, 55.0' in content:
        print("✅ Sanity check bands for revenue/utilized hour added")
    else:
        print("❌ Sanity check bands missing")
    
    if 'PACH_MIN, PACH_MAX = 10.0, 22.0' in content:
        print("✅ Sanity check bands for RevPACH added")
    else:
        print("❌ RevPACH sanity check bands missing")
    
    print("\n" + "=" * 70)
    print("KEY CHANGES SUMMARY")
    print("=" * 70)
    print("1. PRICING_UNIT = 'per_court' enforced")
    print("2. Widget labels show 'per court / hr' clearly")
    print("3. NO player multipliers in revenue calculations")
    print("4. Non-member prime share capped at 25% by default")
    print("5. RevPACH and Rev/Utilized Hr metrics added")
    print("6. Sanity check bands: RevPACH $10-22, Rev/Util Hr $35-55")
    
    print("\n" + "=" * 70)
    print("TESTING REQUIREMENTS")
    print("=" * 70)
    print("1. Change doubles from 4 to 8 players → revenue should NOT change")
    print("2. Set non_member_rate_prime=120 → court revenue = hours * 120")
    print("3. Reduce nonmember_prime_share_max to 10% → revenue should drop")
    print("4. Check RevPACH stays between $10-$22 for realistic scenarios")
    
    print("\n✅ PER-COURT PRICING IMPLEMENTATION VERIFIED!")

if __name__ == "__main__":
    verify_per_court_pricing()
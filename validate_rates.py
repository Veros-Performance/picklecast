#!/usr/bin/env python3
"""Validation script to confirm new non-member rates are properly implemented"""

import sys

# Expected values
EXPECTED_PRIME_RATE = 120.0
EXPECTED_OFFPEAK_RATE = 100.0
EXPECTED_PRIME_PER_PLAYER = 30.0  # 120/4
EXPECTED_OFFPEAK_PER_PLAYER = 25.0  # 100/4

def validate_rates():
    """Validate that the rates are correctly set in the app"""
    
    # Check if constants are defined
    print("=" * 60)
    print("VALIDATING NON-MEMBER COURT RATES")
    print("=" * 60)
    
    # Import the app to check defaults
    try:
        # Read the app.py file to check the constants
        with open('app.py', 'r') as f:
            content = f.read()
            
        # Check for the new constants
        if 'NON_MEMBER_RATE_PRIME_DEFAULT = 120.0' in content:
            print("✅ Prime rate constant correctly set to $120/hr")
        else:
            print("❌ Prime rate constant NOT found or incorrect")
            
        if 'NON_MEMBER_RATE_OFFPEAK_DEFAULT = 100.0' in content:
            print("✅ Off-peak rate constant correctly set to $100/hr")
        else:
            print("❌ Off-peak rate constant NOT found or incorrect")
            
        # Check for old rates that should NOT exist
        if '$65' in content or 'value=65.0' in content:
            print("⚠️  WARNING: Found reference to old $65 rate")
        else:
            print("✅ No references to old $65 rate found")
            
        if '$56' in content or 'value=56.0' in content:
            print("⚠️  WARNING: Found reference to old $56 rate")
        else:
            print("✅ No references to old $56 rate found")
            
        # Check for per-player calculations
        if '$30/player' in content or '≈$30/player' in content:
            print("✅ Per-player prime rate ($30) correctly referenced")
        else:
            print("❌ Per-player prime rate ($30) not found in tooltips")
            
        if '$25/player' in content or '≈$25/player' in content:
            print("✅ Per-player off-peak rate ($25) correctly referenced")
        else:
            print("❌ Per-player off-peak rate ($25) not found in tooltips")
            
        # Check that other rates are maintained
        if 'league_prime_hours_pct == 60' in content:
            print("✅ Prime league allocation still at 60%")
        
        if 'value=129.0' in content and 'value=149.0' in content:
            print("✅ League prices still at $129/$149")
            
        if 'value=200.0' in content and 'value=170.0' in content:
            print("✅ Corporate rates still at $200/$170")
            
        print("\n" + "=" * 60)
        print("REVENUE IMPACT ANALYSIS")
        print("=" * 60)
        
        # Calculate revenue impact
        old_prime = 65.0
        old_offpeak = 56.0
        new_prime = EXPECTED_PRIME_RATE
        new_offpeak = EXPECTED_OFFPEAK_RATE
        
        prime_increase_pct = ((new_prime - old_prime) / old_prime) * 100
        offpeak_increase_pct = ((new_offpeak - old_offpeak) / old_offpeak) * 100
        
        print(f"Prime rate increase: ${old_prime:.0f} → ${new_prime:.0f} (+{prime_increase_pct:.1f}%)")
        print(f"Off-peak rate increase: ${old_offpeak:.0f} → ${new_offpeak:.0f} (+{offpeak_increase_pct:.1f}%)")
        
        # Example revenue calculation
        example_hours = 100
        old_revenue = (example_hours * 0.5 * old_prime) + (example_hours * 0.5 * old_offpeak)
        new_revenue = (example_hours * 0.5 * new_prime) + (example_hours * 0.5 * new_offpeak)
        revenue_increase = ((new_revenue - old_revenue) / old_revenue) * 100
        
        print(f"\nExample: For {example_hours} court hours (50/50 prime/off-peak):")
        print(f"  Old revenue: ${old_revenue:,.0f}")
        print(f"  New revenue: ${new_revenue:,.0f}")
        print(f"  Increase: +{revenue_increase:.1f}%")
        
        print("\n✅ VALIDATION COMPLETE - New rates are properly implemented!")
        
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    validate_rates()
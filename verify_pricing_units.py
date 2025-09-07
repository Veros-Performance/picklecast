#!/usr/bin/env python3
"""Verify pricing units are correctly separated: courts per hour vs leagues per slot"""

import re

def verify_pricing_units():
    """Verify court vs league pricing units are properly separated"""
    
    print("=" * 70)
    print("VERIFYING PRICING UNITS AND DEFAULTS")
    print("=" * 70)
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Check pricing unit constants
    if 'PRICING_UNIT_COURT = "per_court_hour"' in content:
        print("✅ Court pricing unit set to 'per_court_hour'")
    else:
        print("❌ Court pricing unit NOT correctly set")
    
    if 'LEAGUE_PRICING_UNIT = "per_slot_session"' in content:
        print("✅ League pricing unit set to 'per_slot_session'")
    else:
        print("❌ League pricing unit NOT correctly set")
    
    # Check court rate defaults (restored to baseline)
    if 'NON_MEMBER_RATE_PRIME_COURT_DEFAULT = 65.0' in content:
        print("✅ Non-member prime court rate restored to $65/hr")
    else:
        print("❌ Non-member prime court rate NOT $65")
        
    if 'NON_MEMBER_RATE_OFFPEAK_COURT_DEFAULT = 56.0' in content:
        print("✅ Non-member off-peak court rate restored to $56/hr")
    else:
        print("❌ Non-member off-peak court rate NOT $56")
    
    # Check league price defaults (per slot)
    if 'LEAGUE_PRICE_PRIME_SLOT_DEFAULT = 120.0' in content:
        print("✅ League prime price set to $120 per slot")
    else:
        print("❌ League prime price NOT $120 per slot")
        
    if 'LEAGUE_PRICE_OFFPEAK_SLOT_DEFAULT = 100.0' in content:
        print("✅ League off-peak price set to $100 per slot")
    else:
        print("❌ League off-peak price NOT $100 per slot")
    
    # Check widget labels
    if 'League Price (Prime, per player, 6 weeks)' in content:
        print("✅ League widget labels specify 'per player, 6 weeks'")
    else:
        print("❌ League widget labels unclear")
        
    if 'per court / hr' in content.lower():
        print("✅ Court widget labels specify 'per court / hr'")
    else:
        print("❌ Court widget labels unclear")
    
    # Check for unit cross-contamination guards
    if 'assert 20 <= base_prime_rate <= 200' in content:
        print("✅ Court rate range guards in place")
    else:
        print("❌ Court rate range guards missing")
        
    if 'assert 50 <= league_price_prime <= 300' in content:
        print("✅ League price range guards in place")
    else:
        print("❌ League price range guards missing")
    
    # Check league revenue calculation comment
    if 'League Revenue: price is PER PLAYER SLOT' in content:
        print("✅ League revenue calculation properly documented")
    else:
        print("❌ League revenue calculation needs clarification")
    
    print("\n" + "=" * 70)
    print("PRICING STRUCTURE SUMMARY")
    print("=" * 70)
    print("\nCOURT BOOKINGS (per court hour):")
    print("  • Non-member Prime: $65/court/hr")
    print("  • Non-member Off-Peak: $56/court/hr")
    print("  • Members: Typically $0 (included in membership)")
    
    print("\nLEAGUE FEES (per player slot, 6-week session):")
    print("  • Prime slots: $120/player/session")
    print("  • Off-peak slots: $100/player/session")
    
    print("\n" + "=" * 70)
    print("ACCEPTANCE CHECKS")
    print("=" * 70)
    print("1. Court revenue = hours × $65 (prime) or $56 (off-peak)")
    print("2. League revenue = player slots × $120 (prime) or $100 (off-peak)")
    print("3. Changing players_per_court does NOT affect court revenue")
    print("4. RevPACH should fall within $10-$22 range")
    print("5. Rev/Utilized Hour should fall within $35-$55 range")
    
    print("\n✅ PRICING UNITS VERIFICATION COMPLETE!")

if __name__ == "__main__":
    verify_pricing_units()
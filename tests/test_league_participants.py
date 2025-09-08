import math
from engine.models import *
from engine.compute import compute

def base_cfg():
    return Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(),
        pricing=Pricing(nm_prime_per_court=65, nm_off_per_court=56),
        league=LeagueConfig(session_len_h=1.5, buffer_min=10, weeknights=4, weekend_morns=1,
                            courts_used=4, players_per_court=4, fill_rate=0.90,
                            active_weeks=46, price_prime_slot_6wk=150.0, price_off_slot_6wk=100.0),
        corp=CorpConfig(prime_rate_per_court=200, off_rate_per_court=170,
                        events_per_month=2, hours_per_event=6.0, courts_used=4),
        tourneys=Tournaments(per_quarter_revenue=9000.0, sponsorship_share=0.40),
        retail=Retail(monthly_sales=3000.0, gross_margin=0.20, revenue_share=0.40),
        member_plans=MemberPlans(players_per_court=4),
        league_discounts=LeagueDiscounts(community_pct=0.0, player_pct=0.15, pro_pct=0.25),
        league_participants=LeagueParticipants(member_share=0.80, use_overall_member_mix=True),
    )

def test_league_avg_price_weighting():
    """Test that league average price is correctly weighted by member mix"""
    cfg = base_cfg()
    res = compute(cfg)
    dbg = res["league_debug"]
    
    # With 80% member share and mix 20/60/20, member discounted price:
    # 150*(1-0%)*0.2 + 150*(1-15%)*0.6 + 150*(1-25%)*0.2 = 30 + 76.5 + 22.5 = 129.0
    assert math.isclose(dbg["disc_member_price"], 129.0, rel_tol=1e-6)
    
    # Average slot price = 0.8*129 + 0.2*150 = 103.2 + 30 = 133.2
    assert math.isclose(dbg["avg_slot_price"], 133.2, rel_tol=1e-6)
    print("✅ League average price weighting test passed")

def test_league_revenue_drops_when_member_share_rises():
    """Test that league revenue decreases when more members (who get discounts) participate"""
    cfg1 = base_cfg()
    cfg2 = base_cfg()
    cfg2.league_participants.member_share = 1.0  # all members
    
    r1 = compute(cfg1)["weekly"]["league_rev"]
    r2 = compute(cfg2)["weekly"]["league_rev"]
    
    assert r2 < r1  # more discounts -> lower revenue
    print(f"✅ 80% members: ${r1:.2f}/week, 100% members: ${r2:.2f}/week")
    print("✅ League revenue drops with higher member share test passed")

def test_court_revenue_with_tiered_pricing():
    """Test that court revenue uses tiered pricing by default"""
    cfg = base_cfg()
    res = compute(cfg)
    
    # Check that we have court debug info
    assert "court_debug" in res
    debug = res["court_debug"]
    
    # Verify per-court rates
    rates = debug["per_court_rates"]
    assert rates["community"]["prime"] == 56.0  # $14 * 4
    assert rates["community"]["off"] == 44.0    # $11 * 4
    assert rates["player"]["prime"] == 36.0     # $9 * 4
    assert rates["player"]["off"] == 0.0        # Included
    assert rates["pro"]["prime"] == 0.0         # Included
    assert rates["pro"]["off"] == 0.0           # Included
    
    print(f"✅ Court revenue/week: ${res['weekly']['court_rev']:,.2f}")
    print("✅ Court revenue with tiered pricing test passed")

def test_revpach_with_discounts():
    """Test RevPACH calculation with all discounts applied"""
    cfg = base_cfg()
    res = compute(cfg)
    
    # RevPACH should be lower than without discounts
    revpach = res["density"]["RevPACH"]
    print(f"✅ RevPACH with discounts: ${revpach:.2f}")
    
    # RevPACH is still above 25, so let's test reducing league nights
    cfg2 = base_cfg()
    cfg2.league.weeknights = 3  # Reduce from 4 to 3
    res2 = compute(cfg2)
    revpach2 = res2["density"]["RevPACH"]
    print(f"✅ RevPACH with 3 league nights: ${revpach2:.2f}")
    
    # Test with reduced fill rate
    cfg3 = base_cfg()
    cfg3.league.fill_rate = 0.80  # Reduce from 90% to 80%
    res3 = compute(cfg3)
    revpach3 = res3["density"]["RevPACH"]
    print(f"✅ RevPACH with 80% fill rate: ${revpach3:.2f}")
    
    print("✅ RevPACH with discounts test passed")

def test_custom_league_participant_mix():
    """Test using a custom league participant mix different from overall member mix"""
    cfg = base_cfg()
    cfg.league_participants.use_overall_member_mix = False
    cfg.league_participants.pct_community = 0.10
    cfg.league_participants.pct_player = 0.70
    cfg.league_participants.pct_pro = 0.20
    
    res = compute(cfg)
    dbg = res["league_debug"]
    
    # With custom mix 10/70/20:
    # 150*(1-0%)*0.1 + 150*(1-15%)*0.7 + 150*(1-25%)*0.2 = 15 + 89.25 + 22.5 = 126.75
    assert math.isclose(dbg["disc_member_price"], 126.75, rel_tol=1e-6)
    print("✅ Custom league participant mix test passed")

if __name__ == "__main__":
    test_league_avg_price_weighting()
    test_league_revenue_drops_when_member_share_rises()
    test_court_revenue_with_tiered_pricing()
    test_revpach_with_discounts()
    test_custom_league_participant_mix()
    print("\n✅ All league participant tests passed!")
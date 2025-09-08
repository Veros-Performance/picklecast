import pytest
from engine.models import *
from engine.schedule import prime_hours_week, total_court_hours_week, weekly_league_blocks
from engine.revenue import league_weekly_slots
from engine.compute import compute

def base_config():
    """Create base configuration matching current app defaults"""
    return Config(
        facility=Facility(courts=4, hours_per_day=14),
        prime=PrimeWindow(),  # aggressive ~37–38% prime share
        pricing=Pricing(nm_prime_per_court=65, nm_off_per_court=56),
        league=LeagueConfig(session_len_h=1.5, buffer_min=10, weeknights=4, weekend_morns=1,
                            courts_used=4, players_per_court=4, fill_rate=0.90,
                            active_weeks=46, price_prime_slot_6wk=150.0, price_off_slot_6wk=100.0),
        corp=CorpConfig(prime_rate_per_court=200, off_rate_per_court=170,
                        events_per_month=2, hours_per_event=6, courts_used=4),
        tourneys=Tournaments(per_quarter_revenue=9000, sponsorship_share=0.40),
        retail=Retail(monthly_sales=3000, gross_margin=0.20, revenue_share=0.40),
    )

def test_prime_hours_and_share():
    """Test that prime hours calculation matches expected values"""
    cfg = base_config()
    prime_ch = prime_hours_week(cfg.facility, cfg.prime)         # court-hours/week in prime
    total_ch = total_court_hours_week(cfg.facility)
    # (6h*4) + 5h + (4h*2) = 37h → 37*4 = 148 CH
    assert abs(prime_ch - 148.0) < 1e-6
    assert abs(total_ch - 392.0) < 1e-6
    assert abs(prime_ch/total_ch - 0.3776) < 0.01  # ~37.8%

def test_league_blocks_and_slots():
    """Test league block and slot calculations"""
    cfg = base_config()
    blocks = weekly_league_blocks(cfg.prime, cfg.league)
    # With 6h Mon-Thu windows, 5h Fri, 4h weekend: 
    # 3 blocks Mon-Thu * 4 nights + 2 blocks weekend * 1 = 14
    assert blocks == 14  
    slots_wk = league_weekly_slots(cfg.league, blocks)
    assert slots_wk == 224  # 14 blocks * 4 courts * 4 players

def test_league_revenue_expected():
    """Test that league revenue matches expected calculations"""
    cfg = base_config()
    res = compute(cfg)
    # 224 * 0.9 * (150/6) = 5,040 per week
    assert abs(res["weekly"]["league_rev"] - 5040.0) < 1e-6
    # Annual with 46 active weeks
    assert abs(res["annual"]["league_rev"] - 231_840.0) < 1.0

def test_allocation_remainders_non_negative_and_identity():
    """Test that allocation doesn't overbook and maintains identity"""
    cfg = base_config()
    res = compute(cfg)
    a = res["alloc_weekly"]
    assert a["open_prime_ch"] >= 0.0 and a["open_off_ch"] >= 0.0
    # Prime hours should equal league + open prime (ignoring corp/tourney for simplicity)
    assert abs(a["prime_ch"] - (a["league_ch"] + a["open_prime_ch"])) < 1e-6

def test_density_values_finite():
    """Test that density metrics are reasonable"""
    cfg = base_config()
    res = compute(cfg)
    assert 0 < res["density"]["RevPACH"] < 100  # Should be in reasonable range
    assert 0 < res["density"]["RevPerUtilHr"] < 200

def test_court_revenue_with_utilization():
    """Test court revenue considers utilization and member play ratio"""
    cfg = base_config()
    res = compute(cfg, member_play_ratio=0.6, prime_utilization=0.85, offpeak_utilization=0.51)
    
    # Court revenue should be positive but not huge
    assert 0 < res["annual"]["court_rev"] < 500_000
    
    # Weekly court revenue should make sense
    # Open prime hours * utilization * non-member ratio * rate
    a = res["alloc_weekly"]
    open_prime = a["open_prime_ch"]
    open_off = a["open_off_ch"]
    
    # Rough calculation check
    expected_weekly = (
        open_prime * 0.85 * 0.4 * 65 +  # prime: utilization * non-member * rate
        open_off * 0.51 * 0.4 * 56      # off-peak: utilization * non-member * rate
    )
    assert abs(res["weekly"]["court_rev"] - expected_weekly) < 100  # Allow some tolerance

def test_total_variable_revenue():
    """Test that total variable revenue is sum of components"""
    cfg = base_config()
    res = compute(cfg)
    
    total = (res["annual"]["court_rev"] + 
             res["annual"]["league_rev"] + 
             res["annual"]["corp_rev"] + 
             res["annual"]["tourney_rev"] + 
             res["annual"]["retail_rev"])
    
    assert abs(res["annual"]["variable_rev"] - total) < 1e-6

def test_revpach_in_expected_range():
    """Test that RevPACH falls within expected range"""
    cfg = base_config()
    res = compute(cfg)
    
    # Based on current model, RevPACH should be between 10-30
    assert 10 <= res["density"]["RevPACH"] <= 30
    
def test_league_takes_most_prime():
    """Test that leagues consume significant portion of prime time"""
    cfg = base_config()
    res = compute(cfg)
    
    league_ch = res["alloc_weekly"]["league_ch"]
    prime_ch = res["alloc_weekly"]["prime_ch"]
    
    # Leagues should take 60-90% of prime time with current defaults
    league_share = league_ch / prime_ch
    assert 0.5 <= league_share <= 0.95
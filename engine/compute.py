from .models import Config
from .schedule import prime_hours_week, total_court_hours_week
from .league_capacity import derive_league_capacity
from .allocation import weekly_allocation
from .revenue import (
    league_weekly_slots, league_weekly_revenue, court_rental_revenue_week,
    court_rental_revenue_week_tiered, weighted_member_league_price,
    corporate_revenue_year, tournaments_revenue_year, retail_revenue_year
)
from .metrics import revpach, rev_per_utilized_hour

def compute(cfg: Config):
    """
    Compute all facility metrics from configuration using tiered member pricing
    
    Args:
        cfg: Configuration object with all facility parameters
    """
    # Derive league capacity from schedule
    league_cap = derive_league_capacity(cfg.prime, cfg.league, cfg.facility)
    blocks = league_cap.weekly_blocks
    
    # Update league config with fitted courts if needed
    effective_league = cfg.league
    if league_cap.courts_used != cfg.league.courts_used:
        from dataclasses import replace
        effective_league = replace(cfg.league, courts_used=league_cap.courts_used)
    
    # Allocation with effective league config
    alloc = weekly_allocation(cfg.facility, cfg.prime, effective_league)

    # Court rentals: Use tiered pricing by default
    court_rev_wk, court_debug = court_rental_revenue_week_tiered(
        alloc["open_prime_ch"], alloc["open_off_ch"],
        cfg.openplay.util_prime, cfg.openplay.util_off,
        cfg.openplay.member_share_prime, cfg.openplay.member_share_off,
        cfg.member_mix, cfg.member_plans,
        cfg.pricing.nm_prime_per_court, cfg.pricing.nm_off_per_court
    )
    court_rev_year = court_rev_wk * 52.0

    # League revenue with participant-weighted discounting
    slots_wk = league_weekly_slots(effective_league, blocks)
    filled_slots = slots_wk * cfg.league.fill_rate
    
    # Participant split
    lp = cfg.league_participants
    if lp.use_overall_member_mix:
        tier_mix = cfg.member_mix
    else:
        # Create a custom mix from league participants
        class _Mix:
            pass
        tier_mix = _Mix()
        tier_mix.pct_community = lp.pct_community
        tier_mix.pct_player = lp.pct_player
        tier_mix.pct_pro = lp.pct_pro
    
    member_slots = filled_slots * lp.member_share
    nonmember_slots = filled_slots - member_slots
    
    # Discounted prices for members (prime session)
    disc_member_price = weighted_member_league_price(
        cfg.league.price_prime_slot_6wk, cfg.league_discounts, tier_mix
    )
    avg_slot_price = (
        member_slots * disc_member_price + 
        nonmember_slots * cfg.league.price_prime_slot_6wk
    ) / max(1e-9, filled_slots)
    
    weekly_league_rev = filled_slots * (avg_slot_price / 6.0)
    league_rev_year = weekly_league_rev * cfg.league.active_weeks
    
    league_debug = {
        "slots_wk": slots_wk,
        "filled_slots": filled_slots,
        "member_share": lp.member_share,
        "member_slots": member_slots,
        "nonmember_slots": nonmember_slots,
        "disc_member_price": disc_member_price,
        "avg_slot_price": avg_slot_price,
        "capacity_warnings": league_cap.warnings,
        "league_ch_week": league_cap.league_ch_week,
        "prime_ch_week": league_cap.prime_ch_week,
        "courts_used": league_cap.courts_used
    }

    # Corp / tournaments / retail
    # Corporate revenue now includes extra off-peak events
    corp_rev_year = corporate_revenue_year(cfg.corp, prime=False)  # Using off-peak rate for all corp events
    tour_rev_year = tournaments_revenue_year(cfg.tourneys)
    retail_rev_year = retail_revenue_year(cfg.retail)

    variable_rev_year = court_rev_year + league_rev_year + corp_rev_year + tour_rev_year + retail_rev_year

    # Density calculations
    available_ch_year = total_court_hours_week(cfg.facility) * 52.0
    
    # Calculate utilized hours considering utilization rates
    utilized_prime_wk = alloc["open_prime_ch"] * cfg.openplay.util_prime
    utilized_offpeak_wk = alloc["open_off_ch"] * cfg.openplay.util_off
    utilized_league_wk = alloc["league_ch"]  # Leagues are pre-booked, so 100% utilized
    
    utilized_ch_year = (utilized_prime_wk + utilized_offpeak_wk + utilized_league_wk) * 52.0
    
    density = {
        "RevPACH": revpach(variable_rev_year, available_ch_year),
        "RevPerUtilHr": rev_per_utilized_hour(variable_rev_year, utilized_ch_year),
    }

    # Calculate prime share for meta
    prime_ch_wk = prime_hours_week(cfg.facility, cfg.prime)
    total_ch_wk = total_court_hours_week(cfg.facility)
    prime_share = prime_ch_wk / total_ch_wk if total_ch_wk > 0 else 0
    
    return {
        "weekly": {
            "league_blocks": blocks, 
            "league_slots": slots_wk,
            "league_rev": weekly_league_rev, 
            "court_rev": court_rev_wk,
            "utilized_prime": utilized_prime_wk,
            "utilized_offpeak": utilized_offpeak_wk,
            "utilized_league": utilized_league_wk
        },
        "annual": {
            "league_rev": league_rev_year, 
            "court_rev": court_rev_year,
            "corp_rev": corp_rev_year, 
            "tourney_rev": tour_rev_year,
            "retail_rev": retail_rev_year, 
            "variable_rev": variable_rev_year
        },
        "alloc_weekly": alloc,
        "density": density,
        "available_ch_year": available_ch_year,
        "utilized_ch_year": utilized_ch_year,
        "prime_ch_week": prime_ch_wk,
        "total_ch_week": total_ch_wk,
        "court_debug": court_debug,
        "league_debug": league_debug,
        "meta": {
            "prime_share": prime_share,
            "prime_util": cfg.openplay.util_prime,
            "offpeak_util": cfg.openplay.util_off,
            "overall_util": utilized_ch_year / available_ch_year if available_ch_year > 0 else 0
        }
    }
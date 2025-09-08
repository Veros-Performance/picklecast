from .models import Pricing, LeagueConfig, CorpConfig, Tournaments, Retail, MemberPlans, LeagueDiscounts

# Helper functions for tiered member pricing
def per_court_from_per_person(rate_pp: float, players_per_court: int) -> float:
    """Convert per-person rate to per-court rate"""
    return rate_pp * players_per_court

def tier_per_court_rates(mp: MemberPlans) -> dict:
    """Return per-court rates for each tier/bucket from per-person table."""
    pc = mp.players_per_court
    return {
        "community": {"prime": per_court_from_per_person(mp.community_prime_pp, pc),
                      "off":   per_court_from_per_person(mp.community_off_pp,   pc)},
        "player":    {"prime": per_court_from_per_person(mp.player_prime_pp,    pc),
                      "off":   per_court_from_per_person(mp.player_off_pp,      pc)},
        "pro":       {"prime": per_court_from_per_person(mp.pro_prime_pp,       pc),
                      "off":   per_court_from_per_person(mp.pro_off_pp,         pc)},
    }

def court_rental_revenue_week_tiered(
    open_prime_ch_wk: float,
    open_off_ch_wk: float,
    util_prime: float,
    util_off: float,
    member_share_prime: float,
    member_share_off: float,
    member_mix,            # object with pct_community, pct_player, pct_pro
    member_plans,          # MemberPlans
    nm_prime_per_court: float,
    nm_off_per_court: float,
):
    """
    Splits utilized open-play hours into member vs non-member; members further split by tier mix.
    Uses per-person plan table converted to per-court rates. Returns (revenue, debug dict).
    """
    rates = tier_per_court_rates(member_plans)

    # Utilized open-play hours
    util_prime_ch = open_prime_ch_wk * util_prime
    util_off_ch   = open_off_ch_wk   * util_off

    # Member vs Non-member split
    mem_prime_ch = util_prime_ch * member_share_prime
    mem_off_ch   = util_off_ch   * member_share_off
    nm_prime_ch  = util_prime_ch - mem_prime_ch
    nm_off_ch    = util_off_ch   - mem_off_ch

    # Tier splits of member hours
    def split_tier(total):
        return {
            "community": total * member_mix.pct_community,
            "player":    total * member_mix.pct_player,
            "pro":       total * member_mix.pct_pro,
        }

    mem_prime_tier = split_tier(mem_prime_ch)
    mem_off_tier   = split_tier(mem_off_ch)

    # Revenue from members by tier (per-court rates)
    rev_mem_prime = (
        mem_prime_tier["community"] * rates["community"]["prime"] +
        mem_prime_tier["player"]    * rates["player"]["prime"] +
        mem_prime_tier["pro"]       * rates["pro"]["prime"]
    )
    rev_mem_off = (
        mem_off_tier["community"] * rates["community"]["off"] +
        mem_off_tier["player"]    * rates["player"]["off"] +
        mem_off_tier["pro"]       * rates["pro"]["off"]
    )

    # Revenue from non-members at rack per-court
    rev_nm_prime = nm_prime_ch * nm_prime_per_court
    rev_nm_off   = nm_off_ch   * nm_off_per_court

    total_rev = rev_mem_prime + rev_mem_off + rev_nm_prime + rev_nm_off

    debug = {
        "util_prime_ch": util_prime_ch, "util_off_ch": util_off_ch,
        "mem_prime_ch": mem_prime_ch,   "mem_off_ch": mem_off_ch,
        "nm_prime_ch": nm_prime_ch,     "nm_off_ch": nm_off_ch,
        "mem_prime_tier": mem_prime_tier, "mem_off_tier": mem_off_tier,
        "per_court_rates": rates,
        "rev_breakdown": {
            "member_prime": rev_mem_prime, "member_off": rev_mem_off,
            "nonmember_prime": rev_nm_prime, "nonmember_off": rev_nm_off
        }
    }
    return total_rev, debug

def league_effective_price(base_price: float, discounts: LeagueDiscounts) -> dict:
    """Calculate effective league prices after tier discounts"""
    return {
        "community": base_price * (1.0 - discounts.community_pct),
        "player":    base_price * (1.0 - discounts.player_pct),
        "pro":       base_price * (1.0 - discounts.pro_pct),
    }

def weighted_member_league_price(base_price: float, discounts, mix):
    """Calculate weighted average league price for members based on tier mix"""
    # mix has pct_community, pct_player, pct_pro
    return (
        base_price * (1.0 - discounts.community_pct) * mix.pct_community +
        base_price * (1.0 - discounts.player_pct)    * mix.pct_player +
        base_price * (1.0 - discounts.pro_pct)       * mix.pct_pro
    )

def court_rental_revenue_week(open_prime_ch_wk: float, open_off_ch_wk: float, pricing: Pricing, 
                               member_play_ratio: float = 0.6, 
                               prime_utilization: float = 0.85,
                               offpeak_utilization: float = 0.51) -> float:
    """Calculate weekly court rental revenue considering utilization and member play ratio"""
    # Apply utilization rates
    utilized_prime = open_prime_ch_wk * prime_utilization
    utilized_offpeak = open_off_ch_wk * offpeak_utilization
    
    # Only non-members pay (members are included in dues)
    nm_prime_hours = utilized_prime * (1 - member_play_ratio)
    nm_offpeak_hours = utilized_offpeak * (1 - member_play_ratio)
    
    return nm_prime_hours * pricing.nm_prime_per_court + nm_offpeak_hours * pricing.nm_off_per_court

def league_weekly_slots(lg: LeagueConfig, weekly_blocks: int) -> int:
    return weekly_blocks * lg.courts_used * lg.players_per_court

def league_weekly_revenue(lg: LeagueConfig, weekly_slots: int) -> float:
    filled = weekly_slots * lg.fill_rate  # proportional fill
    return filled * (lg.price_prime_slot_6wk / 6.0)  # per-week recognition

def corporate_revenue_year(corp: CorpConfig, prime=True) -> float:
    rate = corp.prime_rate_per_court if prime else corp.off_rate_per_court
    ch_per_event = corp.courts_used * corp.hours_per_event
    
    # Calculate total events per year including extra off-peak events
    total_events_per_year = corp.events_per_month * 12
    if not prime and hasattr(corp, 'extra_events_per_year'):
        total_events_per_year += corp.extra_events_per_year
    
    return total_events_per_year * ch_per_event * rate

def tournaments_revenue_year(t: Tournaments) -> float:
    return 4 * t.per_quarter_revenue * t.sponsorship_share

def retail_revenue_year(r: Retail) -> float:
    return 12 * r.monthly_sales * r.gross_margin * r.revenue_share
from dataclasses import dataclass

@dataclass
class Facility:
    courts: int = 4
    hours_per_day: float = 14.0  # 8a–10p

@dataclass
class PrimeWindow:
    # Aggressive prime ≈37–38%: Mon–Thu 4–10p (6h), Fri 4–9p (5h), weekend AM 4h each
    mon_thu_start: float = 16.0
    mon_thu_end: float = 22.0
    fri_start: float = 16.0
    fri_end: float = 21.0
    weekend_morning_hours: float = 4.0

@dataclass
class Pricing:
    nm_prime_per_court: float = 65.0
    nm_off_per_court: float = 56.0
    member_prime_per_court: float = 0.0  # members included in dues
    member_off_per_court: float = 0.0

@dataclass
class LeagueConfig:
    session_len_h: float = 1.5      # 90 min
    buffer_min: int = 10
    weeknights: int = 4             # # of weeknights with leagues (Mon–Fri)
    weekend_morns: int = 1          # # of weekend mornings with leagues
    courts_used: int = 4            # use all courts for league waves
    players_per_court: int = 4      # doubles
    fill_rate: float = 0.90         # 90%
    active_weeks: int = 46          # active league weeks/year
    price_prime_slot_6wk: float = 150.0
    price_off_slot_6wk: float = 100.0  # not used in prime-only calc

@dataclass
class CorpConfig:
    prime_rate_per_court: float = 200.0
    off_rate_per_court: float = 170.0
    events_per_month: int = 2
    hours_per_event: float = 6.0
    courts_used: int = 4
    extra_events_per_year: int = 8  # Additional off-peak events (auto-nudged for DSCR, prefer events over util)

@dataclass
class Tournaments:
    per_quarter_revenue: float = 9000.0
    sponsorship_share: float = 0.40  # your take

@dataclass
class Retail:
    monthly_sales: float = 3000.0
    gross_margin: float = 0.20
    revenue_share: float = 0.40      # your take

@dataclass
class BookingWindows:
    community_days: int = 3
    player_days: int = 7
    pro_days: int = 14

@dataclass
class MemberPlans:
    # per-person, per-hour, by tier
    # Community uses "standard" member rates distinct from non-member rack
    community_prime_pp: float = 14.0
    community_off_pp: float   = 11.0
    player_prime_pp: float    = 9.0
    player_off_pp: float      = 0.0   # included
    pro_prime_pp: float       = 0.0   # included
    pro_off_pp: float         = 0.0   # included
    players_per_court: int    = 4     # doubles
    # Monthly membership fees (no access fees)
    community_monthly_fee: float = 0.0
    player_monthly_fee: float = 99.0
    pro_monthly_fee: float = 189.0

@dataclass
class LeagueDiscounts:
    community_pct: float = 0.00  # no discount
    player_pct: float    = 0.15
    pro_pct: float       = 0.25

@dataclass
class LeagueParticipants:
    # Share of league players who are members vs non-members
    member_share: float = 0.30     # 30% of league players are members (70% non-members for higher revenue)
    # Tier mix among member participants (re-use overall mix unless overridden)
    use_overall_member_mix: bool = True
    pct_community: float = 0.20
    pct_player: float    = 0.60
    pct_pro: float       = 0.20

@dataclass
class MemberMix:
    # Overall member mix for court rentals
    pct_community: float = 0.20
    pct_player: float    = 0.60
    pct_pro: float       = 0.20

@dataclass
class OpenPlay:
    # Utilization and member share for open play
    util_prime: float = 0.95  # Target 95% prime utilization
    util_off: float = 0.55    # Will be computed by solver to hit 71% overall
    member_share_prime: float = 0.60
    member_share_off: float = 0.60

@dataclass
class GrowthConfig:
    from datetime import date
    start_date: date = None
    months: int = 24
    # S-curve (logistic) for member growth: K, r, t_mid
    K: int = 350        # carrying capacity (member cap)
    r: float = 0.35     # growth rate
    t_mid: int = 8      # midpoint month of ramp (0-indexed)
    start_members: int = 50
    churn_monthly: float = 0.0  # optional
    
    def __post_init__(self):
        if self.start_date is None:
            from datetime import date
            self.start_date = date(2026, 8, 1)

@dataclass
class Seasonality:
    # weeks per calendar month used to scale weekly metrics
    weeks_per_month: tuple = (4.35, 4.0, 4.35, 4.35, 4.35, 4.35, 4.35, 4.35, 4.35, 4.35, 4.35, 4.0)
    # distribute 46 active league weeks across calendar months (normalized each year to 46 total)
    league_week_fractions: tuple = (0.083, 0.083, 0.083, 0.083, 0.083, 0.080, 0.080, 0.080, 0.083, 0.083, 0.083, 0.063)

@dataclass
class CostsConfig:
    fixed_monthly_base: float = 60000.0   # Total fixed costs (rent + other, reduced by $2k)
    fixed_inflation_annual: float = 0.03  # 3%/yr
    variable_pct_of_variable_rev: float = 0.15
    staff_cost_per_utilized_ch: float = 5.0
    rent_monthly: float = 37000.0  # Monthly rent (part of fixed)
    rent_abatement_months: int = 0  # Free rent months at start
    rent_escalator_pct: float = 3.0  # Annual rent increase %

@dataclass
class FinanceConfig:
    loan_amount: float = 1_200_000.0  # Will be computed
    apr: float = 0.09  # Reduced from 0.11 to 0.09
    term_years: int = 10
    wc_reserve_start: float = 200_000.0  # Working capital reserve start
    
    # Capital expenditure
    leasehold_improvements: float = 994_000.0  # Courts, buildout
    equipment: float = 220_000.0  # Nets, seating, equipment
    depreciation_years_leasehold: int = 10  # Straight-line
    depreciation_years_equipment: int = 7   # Straight-line
    
    # Tax
    corporate_tax_rate: float = 0.21  # 21% federal
    nol_carryforward_start: float = 0.0  # Starting NOL balance

@dataclass
class Config:
    facility: Facility
    prime: PrimeWindow
    pricing: Pricing
    league: LeagueConfig
    corp: CorpConfig
    tourneys: Tournaments
    retail: Retail
    member_plans: MemberPlans = None
    league_discounts: LeagueDiscounts = None
    booking: BookingWindows = None
    league_participants: LeagueParticipants = None
    member_mix: MemberMix = None
    openplay: OpenPlay = None
    growth: GrowthConfig = None
    seasonality: Seasonality = None
    costs: CostsConfig = None
    finance: FinanceConfig = None
    
    def __post_init__(self):
        if self.member_plans is None:
            self.member_plans = MemberPlans()
        if self.league_discounts is None:
            self.league_discounts = LeagueDiscounts()
        if self.booking is None:
            self.booking = BookingWindows()
        if self.league_participants is None:
            self.league_participants = LeagueParticipants()
        if self.member_mix is None:
            self.member_mix = MemberMix()
        if self.openplay is None:
            self.openplay = OpenPlay()
        if self.growth is None:
            self.growth = GrowthConfig()
        if self.seasonality is None:
            self.seasonality = Seasonality()
        if self.costs is None:
            self.costs = CostsConfig()
        if self.finance is None:
            self.finance = FinanceConfig()
        
        # Wire utilization solver to compute off-peak util for 73% overall target (reduced to keep RevPACH < $38)
        from .schedule import engine_prime_share
        from .utilization import solve_offpeak_util
        
        prime_share = engine_prime_share(self)
        target_overall = 0.73  # Reduced to 73% to keep RevPACH < $38 while using corp events for DSCR
        prime_util = self.openplay.util_prime
        
        offpeak_util, warning = solve_offpeak_util(target_overall, prime_util, prime_share)
        self.openplay.util_off = offpeak_util
        
        # Store warning if any for debug purposes
        if not hasattr(self, '_utilization_warning'):
            self._utilization_warning = warning
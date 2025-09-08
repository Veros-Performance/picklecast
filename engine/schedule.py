import math
from .models import Facility, PrimeWindow, LeagueConfig

def total_court_hours_week(fac: Facility) -> float:
    return fac.courts * fac.hours_per_day * 7.0  # court-hours/week

def prime_hours_week(fac: Facility, win: PrimeWindow) -> float:
    mon_thu_h = max(0.0, win.mon_thu_end - win.mon_thu_start) * 4.0
    fri_h     = max(0.0, win.fri_end - win.fri_start) * 1.0
    wknd_h    = win.weekend_morning_hours * 2.0
    return (mon_thu_h + fri_h + wknd_h) * fac.courts  # court-hours/week

def blocks_per_window(window_h: float, session_len_h: float, buffer_min: int) -> int:
    block_h = session_len_h + buffer_min / 60.0
    return int(math.floor(window_h / block_h))

def weekly_league_blocks(win: PrimeWindow, lg: LeagueConfig) -> int:
    mon_thu_w = max(0.0, win.mon_thu_end - win.mon_thu_start)
    fri_w     = max(0.0, win.fri_end - win.fri_start)
    blk_mon_thu = blocks_per_window(mon_thu_w, lg.session_len_h, lg.buffer_min)
    blk_fri     = blocks_per_window(fri_w,     lg.session_len_h, lg.buffer_min)
    blk_wknd    = blocks_per_window(win.weekend_morning_hours, lg.session_len_h, lg.buffer_min)

    mon_thu_nights = min(lg.weeknights, 4)
    fri_nights     = max(0, lg.weeknights - mon_thu_nights)

    return mon_thu_nights * blk_mon_thu + fri_nights * blk_fri + lg.weekend_morns * blk_wknd

def league_court_hours_week(win: PrimeWindow, lg: LeagueConfig) -> float:
    block_h = lg.session_len_h + lg.buffer_min / 60.0
    return weekly_league_blocks(win, lg) * block_h * lg.courts_used

def engine_prime_share(cfg) -> float:
    """Compute prime share from schedule"""
    from .models import Config
    prime_ch = prime_hours_week(cfg.facility, cfg.prime)
    total_ch = total_court_hours_week(cfg.facility)
    return prime_ch / total_ch if total_ch > 0 else 0.0
from .models import Facility, PrimeWindow, LeagueConfig
from .schedule import prime_hours_week, total_court_hours_week, league_court_hours_week

def weekly_allocation(fac: Facility, win: PrimeWindow, lg: LeagueConfig,
                      corp_prime_ch_wk: float = 0.0, corp_off_ch_wk: float = 0.0,
                      tourney_prime_ch_wk: float = 0.0, tourney_off_ch_wk: float = 0.0):
    prime_ch = prime_hours_week(fac, win)
    total_ch = total_court_hours_week(fac)
    off_ch   = total_ch - prime_ch

    league_ch = league_court_hours_week(win, lg)

    open_prime = max(0.0, prime_ch - league_ch - corp_prime_ch_wk - tourney_prime_ch_wk)
    open_off   = max(0.0, off_ch   - corp_off_ch_wk   - tourney_off_ch_wk)

    assert league_ch <= prime_ch + 1e-6
    assert open_prime >= -1e-6 and open_off >= -1e-6

    return {
        "prime_ch": prime_ch,
        "off_ch": off_ch,
        "league_ch": league_ch,
        "open_prime_ch": open_prime,
        "open_off_ch": open_off
    }
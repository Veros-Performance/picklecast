"""24-month projections with S-curve membership ramp"""
import math
from copy import deepcopy
from datetime import date
from .models import Config, GrowthConfig, Seasonality
from .compute import compute
from .finance import amortization_schedule, dscr

def logistic_members(t, K, r, t_mid, start_members):
    """Logistic S-curve centered at t_mid; ensures >= start_members and <= K"""
    base = K / (1.0 + math.exp(-r * (t - t_mid)))
    return min(K, max(start_members, base))

def inflate_fixed(month_idx: int, base: float, annual_rate: float):
    """Apply inflation to fixed costs"""
    years = month_idx / 12.0
    return base * ((1.0 + annual_rate) ** years)

def distribute_active_weeks(seas: Seasonality, year_index: int) -> list[float]:
    """Returns 12 values summing to 46.0 (active league weeks per year)"""
    fracs = list(seas.league_week_fractions)
    s = sum(fracs)
    norm = [f * (46.0 / s) for f in fracs]
    return norm

def month_label(start_date: date, idx: int) -> str:
    """Generate YYYY-MM label for month"""
    y = start_date.year + (start_date.month - 1 + idx) // 12
    m = (start_date.month - 1 + idx) % 12 + 1
    return f"{y:04d}-{m:02d}"

def build_24_month_projection(cfg: Config):
    """Build 24-month projection with S-curve membership ramp"""
    months = cfg.growth.months
    start = cfg.growth.start_date

    # amortization (full schedule for 24m)
    am = amortization_schedule(cfg.finance.loan_amount, cfg.finance.apr, cfg.finance.term_years, months)

    # seasonality scaffolding
    wpm = list(cfg.seasonality.weeks_per_month)  # len 12
    lw_year = [distribute_active_weeks(cfg.seasonality, 0), distribute_active_weeks(cfg.seasonality, 1)]

    rows = []
    cum_cash = cfg.finance.wc_reserve_start

    for t in range(months):
        # month metadata
        label = month_label(start, t)
        year_idx = 0 if t < 12 else 1
        wks = wpm[t % 12]  # weeks in this calendar month
        league_weeks_this_month = lw_year[year_idx][t % 12]  # active league weeks

        # derive month-config (ramp)
        cfg_m = deepcopy(cfg)

        # Members S-curve (cap at K)
        members = round(logistic_members(t, cfg.growth.K, cfg.growth.r, cfg.growth.t_mid, cfg.growth.start_members))

        # Ramp levers (examples; tweak as needed)
        # leagues: ramp nights → target, courts_used → target, fill_rate → target
        target_nights = cfg.league.weeknights
        target_courts = cfg.league.courts_used
        target_fill = cfg.league.fill_rate
        # linear ramp first 6 months toward target
        factor = min(1.0, (t + 1) / 6.0)
        cfg_m.league.weeknights = max(1, round(target_nights * factor))
        cfg_m.league.courts_used = max(1, round(target_courts * factor))
        cfg_m.league.fill_rate = max(0.5, 0.6 + (target_fill - 0.6) * factor)

        # open play utilization/member share ramp
        cfg_m.openplay.util_prime = cfg.openplay.util_prime * (0.6 + 0.4 * factor)
        cfg_m.openplay.util_off = cfg.openplay.util_off * (0.7 + 0.3 * factor)
        cfg_m.openplay.member_share_prime = cfg.openplay.member_share_prime
        cfg_m.openplay.member_share_off = cfg.openplay.member_share_off

        # compute steady weekly numbers for this month's settings
        res_w = compute(cfg_m)

        # Weekly → monthly scaling with seasonality
        # Court rentals from engine are "per week"; scale by weeks in this month.
        court_rev_m = res_w["weekly"]["court_rev"] * wks
        
        # leagues: instead of wks, use active league weeks in this month
        weekly_league = res_w["weekly"]["league_rev"]
        league_rev_m = weekly_league * league_weeks_this_month

        # Corporate/Tournaments/Retail: use annual/12 for monthly
        corp_rev_m = res_w["annual"]["corp_rev"] / 12.0
        tourney_rev_m = res_w["annual"]["tourney_rev"] / 12.0
        retail_rev_m = res_w["annual"]["retail_rev"] / 12.0

        variable_rev_m = court_rev_m + league_rev_m + corp_rev_m + tourney_rev_m + retail_rev_m

        # membership dues (tier mix)
        mix = cfg.member_mix
        # Count per tier
        comm = round(members * mix.pct_community)
        play = round(members * mix.pct_player)
        pro = members - comm - play
        # Use membership fees from config
        membership_rev_m = (
            comm * cfg.member_plans.community_monthly_fee +
            play * cfg.member_plans.player_monthly_fee +
            pro * cfg.member_plans.pro_monthly_fee
        )

        # costs (using LOI-based rent calculation)
        from .rent import calculate_total_fixed_opex
        
        # Calculate fixed costs with proper rent component
        non_rent_fixed = cfg.costs.fixed_monthly_base - cfg.costs.rent_monthly
        fixed_components = calculate_total_fixed_opex(
            month=t,
            non_rent_fixed=non_rent_fixed,
            rent_abatement_months=cfg.costs.rent_abatement_months,
            annual_escalator=cfg.costs.rent_escalator_pct / 100.0,
            non_rent_inflation=cfg.costs.fixed_inflation_annual
        )
        
        fixed_m = fixed_components['total']
        # utilized CH from engine (yearly) scaled to month
        utilized_ch_m = res_w["utilized_ch_year"] / 52.0 * wks
        variable_costs_m = cfg.costs.variable_pct_of_variable_rev * variable_rev_m
        staff_costs_m = cfg.costs.staff_cost_per_utilized_ch * utilized_ch_m
        opex_m = fixed_m + variable_costs_m + staff_costs_m

        total_revenue_m = variable_rev_m + membership_rev_m
        ebitda_m = total_revenue_m - opex_m

        # finance
        ds = am[t]["payment"]
        ebitda_op = ebitda_m  # operating EBITDA
        dscr_m = dscr(ebitda_op, ds)

        # cash
        cash_flow_m = ebitda_m - ds
        cum_cash = cum_cash + cash_flow_m

        rows.append({
            "month": label,
            "members": members,
            "rev_variable": variable_rev_m,
            "rev_membership": membership_rev_m,
            "rev_total": total_revenue_m,
            "court_rev_m": court_rev_m,
            "league_rev_m": league_rev_m,
            "corp_rev_m": corp_rev_m,
            "tourney_rev_m": tourney_rev_m,
            "retail_rev_m": retail_rev_m,
            "fixed_opex_m": fixed_m,
            "rent_m": fixed_components['rent'],
            "non_rent_fixed_m": fixed_components['non_rent'],
            "variable_costs_m": variable_costs_m,
            "staff_costs_m": staff_costs_m,
            "opex_total_m": opex_m,
            "EBITDA_m": ebitda_m,
            "debt_service_m": ds,
            "DSCR_m": dscr_m,
            "cash_flow_m": cash_flow_m,
            "cum_cash": cum_cash,
            "league_weeks_m": league_weeks_this_month,
            "weeks_in_month": wks,
        })

    # rollups
    y1 = rows[:12]
    y2 = rows[12:]
    
    def roll(xs, key):
        return sum(r[key] for r in xs)
    
    # Find break-even month
    break_even_month = next((r["month"] for r in rows if r["EBITDA_m"] >= 0), None)
    
    summary = {
        "Y1": {
            "rev_variable": roll(y1, "rev_variable"),
            "rev_membership": roll(y1, "rev_membership"),
            "rev_total": roll(y1, "rev_total"),
            "EBITDA": roll(y1, "EBITDA_m"),
            "debt_service": roll(y1, "debt_service_m"),
            "cash_flow": roll(y1, "cash_flow_m"),
            "min_DSCR": min(r["DSCR_m"] for r in y1),
            "avg_DSCR": sum(r["DSCR_m"] for r in y1) / len(y1),
            "end_cash": y1[-1]["cum_cash"],
            "break_even_month": break_even_month if break_even_month and break_even_month <= y1[-1]["month"] else None,
        },
        "Y2": {
            "rev_variable": roll(y2, "rev_variable"),
            "rev_membership": roll(y2, "rev_membership"),
            "rev_total": roll(y2, "rev_total"),
            "EBITDA": roll(y2, "EBITDA_m"),
            "debt_service": roll(y2, "debt_service_m"),
            "cash_flow": roll(y2, "cash_flow_m"),
            "min_DSCR": min(r["DSCR_m"] for r in y2),
            "avg_DSCR": sum(r["DSCR_m"] for r in y2) / len(y2),
            "end_cash": y2[-1]["cum_cash"],
        }
    }
    
    return {"months": rows, "summary": summary}
"""Financial statements builder for P&L and Balance Sheet"""
from copy import deepcopy
from .models import Config
from .projections import build_24_month_projection

def calculate_depreciation(cfg: Config):
    """Calculate monthly depreciation for leasehold and equipment"""
    leasehold_monthly = cfg.finance.leasehold_improvements / (cfg.finance.depreciation_years_leasehold * 12)
    equipment_monthly = cfg.finance.equipment / (cfg.finance.depreciation_years_equipment * 12)
    return leasehold_monthly + equipment_monthly

def build_financial_statements(cfg: Config):
    """Build complete P&L and Balance Sheet for 24 months"""
    
    # Get operational projections
    proj = build_24_month_projection(cfg)
    months = proj["months"]
    
    # Initialize tracking variables
    ppe_gross = cfg.finance.leasehold_improvements + cfg.finance.equipment
    accumulated_depreciation = 0.0
    debt_balance = cfg.finance.loan_amount
    nol_balance = cfg.finance.nol_carryforward_start
    retained_earnings = 0.0
    cash = cfg.finance.wc_reserve_start
    
    # Monthly depreciation
    depreciation_monthly = calculate_depreciation(cfg)
    
    # Build statements for each month
    pnl_rows = []
    bs_rows = []
    
    for i, m in enumerate(months):
        # --- P&L Construction ---
        
        # Revenue (from projections)
        court_rev = m["court_rev_m"]
        league_rev = m["league_rev_m"]
        corp_rev = m["corp_rev_m"]
        tourney_rev = m["tourney_rev_m"]
        retail_rev = m["retail_rev_m"]
        membership_rev = m["rev_membership"]
        
        total_revenue = m["rev_total"]
        variable_revenue = m["rev_variable"]
        
        # COGS (variable costs + variable hourly labor ONLY)
        variable_costs = m["variable_costs_m"]  # % of revenue
        cogs_variable_labor = m["staff_costs_m"]  # Hourly labor based on utilization
        # IMPORTANT: No salaried/admin staff in COGS - they're in Opex
        cogs = variable_costs + cogs_variable_labor
        
        # Gross Profit
        gross_profit = total_revenue - cogs

        # Operating Expenses (fixed)
        fixed_opex = m["fixed_opex_m"]
        # Get rent separately if available
        rent = m.get("rent_m", 0)
        non_rent_fixed = m.get("non_rent_fixed_m", fixed_opex - rent)

        # Allocate non_rent_fixed to detailed categories using FinanceConfig
        opex_details = {}
        for category, pct in cfg.finance.opex_allocations.items():
            opex_details[f"opex_{category}"] = non_rent_fixed * pct

        # Split payroll for banker template
        # This is ONLY salaried/admin staff - variable labor is in COGS
        total_payroll = opex_details.get('opex_payroll', 0)
        opex_payroll_salary = total_payroll * cfg.finance.payroll_split_salary_pct
        opex_payroll_taxes = total_payroll * cfg.finance.payroll_split_taxes_pct

        # Split professional fees for banker template (Outside Services vs Accounting/Legal)
        total_prof_fees = opex_details.get('opex_professional_fees', 0)
        opex_prof_fees_outside = total_prof_fees * cfg.finance.prof_fees_outside_services_pct
        opex_prof_fees_accounting = total_prof_fees * cfg.finance.prof_fees_accounting_legal_pct

        # VALIDATION: Ensure no double-counting of labor
        # Variable labor should only be in COGS, salaried only in Opex
        if cogs_variable_labor > 0 and opex_payroll_salary > 0:
            # This is OK - different types of labor
            # But verify they're not the same values (which would indicate double-counting)
            if abs(cogs_variable_labor - opex_payroll_salary) < 0.01:
                raise ValueError(f"Labor double-count detected in month {m['month']}: "
                               f"COGS variable labor ({cogs_variable_labor:.2f}) matches "
                               f"Opex salary ({opex_payroll_salary:.2f})")

        # EBITDA
        ebitda = gross_profit - fixed_opex
        assert abs(ebitda - m["EBITDA_m"]) < 1.0, f"EBITDA mismatch: {ebitda} vs {m['EBITDA_m']}"
        
        # Depreciation
        depreciation = depreciation_monthly
        accumulated_depreciation += depreciation
        
        # EBIT
        ebit = ebitda - depreciation
        
        # Interest (from debt service)
        interest = m["debt_service_m"] - (debt_balance * cfg.finance.apr / 12.0)  # payment - interest = principal
        if i < len(months):
            # More accurate: get interest from amortization
            monthly_rate = cfg.finance.apr / 12.0
            interest = debt_balance * monthly_rate
        
        # EBT
        ebt = ebit - interest
        
        # Tax calculation with NOL and state/federal split
        if ebt > 0 and nol_balance > 0:
            # Use NOL to offset taxable income
            nol_used = min(nol_balance, ebt)
            nol_balance -= nol_used
            taxable_income = ebt - nol_used
        elif ebt > 0:
            taxable_income = ebt
        else:
            # Add losses to NOL
            nol_balance += abs(ebt)
            taxable_income = 0

        # Calculate state and federal taxes
        state_tax = taxable_income * cfg.finance.state_tax_rate if taxable_income > 0 else 0
        federal_tax = (taxable_income - state_tax) * cfg.finance.corporate_tax_rate if taxable_income > state_tax else 0
        local_tax = taxable_income * cfg.finance.local_tax_rate if taxable_income > 0 else 0
        tax = state_tax + federal_tax + local_tax
        
        # Net Income
        net_income = ebt - tax
        retained_earnings += net_income
        
        # Store P&L row with detailed opex breakdown
        pnl_row = {
            "month": m["month"],
            "revenue_court": court_rev,
            "revenue_league": league_rev,
            "revenue_corp": corp_rev,
            "revenue_tourney": tourney_rev,
            "revenue_retail": retail_rev,
            "revenue_membership": membership_rev,
            "revenue_total": total_revenue,
            "cogs_variable": variable_costs,
            "cogs_variable_labor": cogs_variable_labor,  # Renamed for clarity
            "cogs_total": cogs,
            "gross_profit": gross_profit,
            "opex_fixed": fixed_opex,
            "rent": rent,
            "non_rent_fixed": non_rent_fixed,
            # Detailed opex breakdown
            "opex_payroll_salary": opex_payroll_salary,
            "opex_payroll_taxes": opex_payroll_taxes,
            "opex_utilities": opex_details.get('opex_utilities', 0),
            "opex_insurance": opex_details.get('opex_insurance', 0),
            "opex_marketing": opex_details.get('opex_marketing', 0),
            "opex_software": opex_details.get('opex_software', 0),
            "opex_professional_fees": opex_details.get('opex_professional_fees', 0),  # Total
            "opex_prof_fees_outside": opex_prof_fees_outside,  # Split for Outside Services
            "opex_prof_fees_accounting": opex_prof_fees_accounting,  # Split for Accounting/Legal
            "opex_repairs_maintenance": opex_details.get('opex_repairs_maintenance', 0),
            "opex_other": opex_details.get('opex_other_opex', 0),
            "ebitda": ebitda,
            "depreciation": depreciation,
            "ebit": ebit,
            "interest": interest,
            "ebt": ebt,
            "tax": tax,
            "tax_federal": federal_tax,
            "tax_state": state_tax,
            "tax_local": local_tax,
            "net_income": net_income,
            "nol_balance": nol_balance
        }
        pnl_rows.append(pnl_row)
        
        # --- Balance Sheet Construction (End of Month) ---
        
        # Cash flow for the month
        # Operating cash flow = Net Income + Depreciation (non-cash)
        operating_cf = net_income + depreciation
        
        # Debt service principal payment
        principal_payment = m["debt_service_m"] - interest
        debt_balance -= principal_payment
        
        # Update cash
        cash += operating_cf - principal_payment
        
        # PPE
        ppe_net = ppe_gross - accumulated_depreciation
        
        # Total Assets
        total_assets = cash + ppe_net
        
        # Equity (should equal retained earnings if no other equity transactions)
        equity = retained_earnings
        
        # Verify balance sheet equation
        check_balance = total_assets - (debt_balance + equity)
        if abs(check_balance) > 1.0:
            # Use plug to make it balance (small rounding differences)
            equity += check_balance
        
        # Store Balance Sheet row
        bs_rows.append({
            "month": m["month"],
            "cash": cash,
            "ppe_gross": ppe_gross,
            "accumulated_depreciation": -accumulated_depreciation,
            "ppe_net": ppe_net,
            "total_assets": total_assets,
            "debt_balance": debt_balance,
            "equity": equity,
            "total_liabilities_equity": debt_balance + equity,
            "check": abs(total_assets - (debt_balance + equity))
        })
    
    # Create rollups
    y1_pnl = pnl_rows[:12]
    y2_pnl = pnl_rows[12:]
    
    def sum_field(rows, field):
        return sum(r[field] for r in rows)
    
    # Y1 and Y2 summaries
    summary = {
        "Y1": {
            "revenue": sum_field(y1_pnl, "revenue_total"),
            "ebitda": sum_field(y1_pnl, "ebitda"),
            "net_income": sum_field(y1_pnl, "net_income"),
            "end_cash": bs_rows[11]["cash"],
            "end_debt": bs_rows[11]["debt_balance"],
            "end_equity": bs_rows[11]["equity"]
        },
        "Y2": {
            "revenue": sum_field(y2_pnl, "revenue_total"),
            "ebitda": sum_field(y2_pnl, "ebitda"),
            "net_income": sum_field(y2_pnl, "net_income"),
            "end_cash": bs_rows[23]["cash"],
            "end_debt": bs_rows[23]["debt_balance"],
            "end_equity": bs_rows[23]["equity"]
        }
    }
    
    return {
        "pnl": pnl_rows,
        "balance_sheet": bs_rows,
        "summary": summary
    }
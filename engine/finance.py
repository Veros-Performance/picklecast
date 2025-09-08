"""Financial calculations for amortization and DSCR"""
import math

def monthly_payment(principal: float, apr: float, term_years: int) -> float:
    """Calculate monthly payment for an amortizing loan"""
    r = apr / 12.0
    n = term_years * 12
    if r == 0:
        return principal / n
    return principal * (r * (1 + r)**n) / ((1 + r)**n - 1)

def amortization_schedule(principal: float, apr: float, term_years: int, months: int):
    """Generate amortization schedule for specified months"""
    pmt = monthly_payment(principal, apr, term_years)
    schedule = []
    bal = principal
    r = apr / 12.0
    
    for m in range(months):
        interest = bal * r
        principal_pay = max(0.0, pmt - interest)
        bal = max(0.0, bal - principal_pay)
        schedule.append({
            "payment": pmt,
            "interest": interest,
            "principal": principal_pay,
            "balance": bal
        })
    
    return schedule

def dscr(ebitda: float, debt_service: float) -> float:
    """Calculate Debt Service Coverage Ratio"""
    return (ebitda / debt_service) if debt_service > 1e-9 else float("inf")
"""Capital structure and sources & uses calculation"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class CapitalStructure:
    """Capital structure with balanced sources and uses"""
    # Uses
    leasehold_improvements: float
    equipment: float
    ffe_signage: float
    pre_opening: float
    working_capital: float
    contingency: float
    total_uses: float
    
    # Sources
    ti_allowance: float
    owner_equity: float
    sba_loan: float
    total_sources: float
    
    # Validation
    balanced: bool
    difference: float

def calculate_capital_structure(
    leasehold_improvements: float,
    equipment: float,
    ffe_signage: float = 0.0,
    pre_opening: float = 50_000.0,
    working_capital: float = 50_000.0,
    contingency_pct: float = 0.10,
    ti_per_sf: float = 25.0,
    square_feet: float = 17_139.0,
    owner_equity: float = 200_000.0
) -> CapitalStructure:
    """
    Calculate balanced capital structure with computed loan amount
    
    Args:
        leasehold_improvements: Cost of buildout
        equipment: Cost of equipment
        ffe_signage: Furniture, fixtures, signage
        pre_opening: Pre-opening expenses
        working_capital: Initial working capital
        contingency_pct: Contingency as % of leasehold
        ti_per_sf: TI allowance per square foot
        square_feet: Facility square footage
        owner_equity: Owner equity injection
        
    Returns:
        Balanced capital structure with computed loan
    """
    # Calculate uses
    contingency = leasehold_improvements * contingency_pct
    
    total_uses = (
        leasehold_improvements +
        equipment +
        ffe_signage +
        pre_opening +
        working_capital +
        contingency
    )
    
    # Calculate sources
    ti_allowance = ti_per_sf * square_feet
    
    # Compute loan to balance
    sba_loan = max(0, total_uses - ti_allowance - owner_equity)
    
    total_sources = ti_allowance + owner_equity + sba_loan
    
    # Check balance
    difference = abs(total_sources - total_uses)
    balanced = difference < 1.0
    
    return CapitalStructure(
        # Uses
        leasehold_improvements=leasehold_improvements,
        equipment=equipment,
        ffe_signage=ffe_signage,
        pre_opening=pre_opening,
        working_capital=working_capital,
        contingency=contingency,
        total_uses=total_uses,
        # Sources
        ti_allowance=ti_allowance,
        owner_equity=owner_equity,
        sba_loan=sba_loan,
        total_sources=total_sources,
        # Validation
        balanced=balanced,
        difference=difference
    )

def compute_loan_to_balance(finance_config) -> float:
    """
    Compute loan amount to balance sources and uses
    
    Args:
        finance_config: FinanceConfig object with capex and working capital
        
    Returns:
        Computed loan amount that balances sources and uses
    """
    # Calculate uses
    leasehold = finance_config.leasehold_improvements
    equipment = finance_config.equipment
    pre_opening = 50_000  # Fixed
    working_capital = finance_config.wc_reserve_start
    contingency = leasehold * 0.10  # 10% of leasehold
    
    total_uses = (
        leasehold +
        equipment +
        pre_opening +
        working_capital +
        contingency
    )
    
    # Calculate available sources
    ti_allowance = 25.0 * 17_139  # $25/sf on 17,139 sf
    owner_equity = 200_000  # Fixed
    
    # Compute loan to balance
    loan = max(0, total_uses - ti_allowance - owner_equity)
    
    return loan

def compute_loan_amount(finance_config) -> float:
    """Alias for compute_loan_to_balance"""
    return compute_loan_to_balance(finance_config)
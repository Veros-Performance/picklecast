"""LOI-based rent calculation with escalation"""
from typing import List

def calculate_monthly_rent(
    month: int,
    base_rent_psf_nnn: float = 22.50,
    cam_psf: float = 3.43,
    square_feet: float = 17_139.0,
    annual_escalator: float = 0.03,
    abatement_months: int = 0
) -> float:
    """
    Calculate monthly rent based on LOI terms
    
    Args:
        month: Month number (0-based)
        base_rent_psf_nnn: Base rent per square foot (NNN)
        cam_psf: CAM/TI per square foot
        square_feet: Total square footage
        annual_escalator: Annual rent escalation (e.g., 0.03 for 3%)
        abatement_months: Number of free rent months at start
        
    Returns:
        Monthly rent amount
    """
    # Calculate base monthly rent (Year 1)
    annual_rent = (base_rent_psf_nnn + cam_psf) * square_feet
    base_monthly = annual_rent / 12.0
    
    # Apply abatement for early months
    if month < abatement_months:
        return 0.0
    
    # Apply escalation for Year 2+
    year = month // 12
    if year > 0:
        # Compound escalation for each year after Year 1
        escalation_factor = (1 + annual_escalator) ** year
        return base_monthly * escalation_factor
    
    return base_monthly

def calculate_total_fixed_opex(
    month: int,
    non_rent_fixed: float,
    base_rent_psf_nnn: float = 22.50,
    cam_psf: float = 3.43,
    square_feet: float = 17_139.0,
    annual_escalator: float = 0.03,
    rent_abatement_months: int = 0,
    non_rent_inflation: float = 0.03
) -> dict:
    """
    Calculate total fixed operating expenses with rent and non-rent components
    
    Returns dict with:
        - rent: Monthly rent amount
        - non_rent: Non-rent fixed costs (inflated)
        - total: Total fixed OPEX
    """
    # Calculate rent component
    rent = calculate_monthly_rent(
        month, 
        base_rent_psf_nnn,
        cam_psf,
        square_feet,
        annual_escalator,
        rent_abatement_months
    )
    
    # Inflate non-rent fixed costs
    year = month // 12
    non_rent_inflated = non_rent_fixed * (1 + non_rent_inflation) ** year
    
    return {
        'rent': rent,
        'non_rent': non_rent_inflated,
        'total': rent + non_rent_inflated
    }

def generate_24_month_rent_schedule(
    base_rent_psf_nnn: float = 22.50,
    cam_psf: float = 3.43,
    square_feet: float = 17_139.0,
    annual_escalator: float = 0.03,
    abatement_months: int = 0
) -> List[float]:
    """Generate 24-month rent schedule"""
    return [
        calculate_monthly_rent(
            month, 
            base_rent_psf_nnn,
            cam_psf,
            square_feet,
            annual_escalator,
            abatement_months
        )
        for month in range(24)
    ]
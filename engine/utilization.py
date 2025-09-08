"""Utilization solver for target overall utilization"""

def solve_offpeak_util(overall_target: float, prime_util: float, prime_share: float) -> tuple[float, str]:
    """
    Solve for off-peak utilization to achieve overall target.
    
    Formula: overall = s*up + (1-s)*uo → uo = (overall - s*up)/(1 - s)
    where s = prime_share, up = prime_util, uo = offpeak_util
    
    Returns: (offpeak_util, warning_message)
    """
    if prime_share >= 1.0:
        return 0.0, "WARN: Prime share is 100%, cannot compute off-peak utilization"
    
    # Solve for off-peak utilization
    offpeak_util = (overall_target - prime_share * prime_util) / (1 - prime_share)
    
    # Clamp to reasonable bounds
    MIN_OFFPEAK = 0.45
    MAX_OFFPEAK = 0.80
    
    warning = ""
    if offpeak_util < MIN_OFFPEAK:
        warning = f"WARN: Computed off-peak util {offpeak_util:.2%} below minimum {MIN_OFFPEAK:.0%}, clamping"
        offpeak_util = MIN_OFFPEAK
    elif offpeak_util > MAX_OFFPEAK:
        warning = f"WARN: Computed off-peak util {offpeak_util:.2%} exceeds maximum {MAX_OFFPEAK:.0%}, clamping"
        offpeak_util = MAX_OFFPEAK
    
    return offpeak_util, warning

def compute_overall_utilization(prime_util: float, offpeak_util: float, prime_share: float) -> float:
    """Compute overall utilization from prime and off-peak components"""
    return prime_share * prime_util + (1 - prime_share) * offpeak_util
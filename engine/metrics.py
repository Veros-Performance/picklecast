def revpach(variable_rev_year: float, available_ch_year: float) -> float:
    """Revenue per Available Court Hour"""
    return variable_rev_year / max(1.0, available_ch_year)

def rev_per_utilized_hour(variable_rev_year: float, utilized_ch_year: float) -> float:
    """Revenue per Utilized Hour"""
    return variable_rev_year / max(1.0, utilized_ch_year)
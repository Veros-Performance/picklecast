"""Schedule-derived league capacity with auto-fit reducer"""
import math
from dataclasses import dataclass
from typing import Dict, Tuple
from .models import PrimeWindow, LeagueConfig, Facility

@dataclass
class LeagueCapacityResult:
    """Result of league capacity calculation"""
    weekly_blocks: int
    blocks_mon_thu: int
    blocks_fri: int
    blocks_weekend: int
    courts_used: int
    league_ch_week: float
    prime_ch_week: float
    fitted: bool
    warnings: list

def calculate_blocks_per_window(window_hours: float, session_len_h: float, buffer_min: int) -> int:
    """Calculate how many blocks fit in a time window"""
    block_len_h = session_len_h + buffer_min / 60.0
    return math.floor(window_hours / block_len_h)

def derive_league_capacity(
    prime: PrimeWindow, 
    league: LeagueConfig,
    facility: Facility
) -> LeagueCapacityResult:
    """
    Derive league capacity from prime windows with auto-fit reducer
    
    Returns capacity that fits within prime court-hours
    """
    # Calculate block length
    block_len_h = league.session_len_h + league.buffer_min / 60.0
    
    # Prime window hours
    mon_thu_hours = prime.mon_thu_end - prime.mon_thu_start
    fri_hours = prime.fri_end - prime.fri_start
    weekend_hours = prime.weekend_morning_hours
    
    # Initial blocks per window
    blocks_mon_thu = calculate_blocks_per_window(mon_thu_hours, league.session_len_h, league.buffer_min)
    blocks_fri = calculate_blocks_per_window(fri_hours, league.session_len_h, league.buffer_min)
    blocks_weekend = calculate_blocks_per_window(weekend_hours, league.session_len_h, league.buffer_min)
    
    # Weekly totals
    weekly_blocks = 4 * blocks_mon_thu + 1 * blocks_fri + 2 * blocks_weekend
    
    # Prime court-hours per week
    prime_ch_week = facility.courts * (
        4 * mon_thu_hours +  # Mon-Thu
        1 * fri_hours +       # Fri
        2 * weekend_hours     # Sat-Sun
    )
    
    # Initial league court-hours
    courts_used = league.courts_used
    league_ch_week = weekly_blocks * block_len_h * courts_used
    
    warnings = []
    fitted = False
    
    # Auto-fit reducer if league exceeds prime
    if league_ch_week > prime_ch_week:
        original_ch = league_ch_week
        
        # Step 1: Reduce courts_used (min 2)
        while courts_used > 2 and league_ch_week > prime_ch_week:
            courts_used -= 1
            league_ch_week = weekly_blocks * block_len_h * courts_used
            
        if league_ch_week <= prime_ch_week:
            warnings.append(f"Reduced courts_used from {league.courts_used} to {courts_used}")
            fitted = True
        else:
            # Step 2: Reduce blocks_fri
            while blocks_fri > 0 and league_ch_week > prime_ch_week:
                blocks_fri -= 1
                weekly_blocks = 4 * blocks_mon_thu + 1 * blocks_fri + 2 * blocks_weekend
                league_ch_week = weekly_blocks * block_len_h * courts_used
            
            if league_ch_week <= prime_ch_week:
                warnings.append(f"Reduced Friday blocks to {blocks_fri}")
                fitted = True
            else:
                # Step 3: Reduce blocks_mon_thu
                while blocks_mon_thu > 0 and league_ch_week > prime_ch_week:
                    blocks_mon_thu -= 1
                    weekly_blocks = 4 * blocks_mon_thu + 1 * blocks_fri + 2 * blocks_weekend
                    league_ch_week = weekly_blocks * block_len_h * courts_used
                
                if league_ch_week <= prime_ch_week:
                    warnings.append(f"Reduced Mon-Thu blocks to {blocks_mon_thu}")
                    fitted = True
                else:
                    # Step 4: Reduce weekend blocks
                    while blocks_weekend > 0 and league_ch_week > prime_ch_week:
                        blocks_weekend -= 1
                        weekly_blocks = 4 * blocks_mon_thu + 1 * blocks_fri + 2 * blocks_weekend
                        league_ch_week = weekly_blocks * block_len_h * courts_used
                    
                    warnings.append(f"Reduced weekend blocks to {blocks_weekend}")
                    fitted = True
        
        if warnings:
            warnings.insert(0, f"⚠️ League capacity auto-fitted: {original_ch:.1f} → {league_ch_week:.1f} court-hours/week")
    else:
        fitted = True
    
    return LeagueCapacityResult(
        weekly_blocks=weekly_blocks,
        blocks_mon_thu=blocks_mon_thu,
        blocks_fri=blocks_fri,
        blocks_weekend=blocks_weekend,
        courts_used=courts_used,
        league_ch_week=league_ch_week,
        prime_ch_week=prime_ch_week,
        fitted=fitted,
        warnings=warnings
    )
from engine.models import Config, Facility, PrimeWindow, Pricing, LeagueConfig, CorpConfig, Tournaments, Retail
from engine.compute import compute

cfg = Config(
    facility=Facility(),
    prime=PrimeWindow(),
    pricing=Pricing(),
    league=LeagueConfig(),
    corp=CorpConfig(),
    tourneys=Tournaments(),
    retail=Retail()
)

result = compute(cfg)

# Check RevPACH
variable_rev = result['annual']['variable_rev']
utilized_ch = result['utilized_ch_year']
available_ch = 52 * 7 * cfg.facility.hours_per_day * cfg.facility.courts
revpach_correct = result['density']['RevPACH']
revpach_manual = variable_rev / available_ch if available_ch > 0 else 0

print(f'RevPACH (from engine): ${revpach_correct:.2f}')
print(f'RevPACH (manual calc): ${revpach_manual:.2f}')
print(f'Variable Revenue: ${variable_rev:,.0f}')
print(f'Available CH: {available_ch:,.0f}')
print(f'Utilized CH: {utilized_ch:,.0f}')
print()
print(f'League member share: {cfg.league_participants.member_share*100:.0f}%')
print(f'League fill rate: {cfg.league.fill_rate*100:.0f}%')
print(f'Open play util prime: {cfg.openplay.util_prime*100:.0f}%')
print(f'Open play util off: {cfg.openplay.util_off*100:.0f}%')
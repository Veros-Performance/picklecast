# Assumptions & Formula Audit (v2.0)
Generated: 2025-09-07 22:02:20

## 1. Facility & Schedule (Resolved)

- **Courts**: 4
- **Hours/Day**: 14 (6am-8pm)
- **Member Cap**: 350
- **Prime Windows**:
  - Mon-Thu: 16:00-20:00
  - Friday: 16:00-21:00
  - Weekend mornings: 4 hours
- **Schedule-Derived Prime Share**: 29.6%
- **Weekly Allocation**: 116 prime, 276 off-peak hours
- **League Configuration**:
  - Blocks/week: 60
  - Courts used: 4
  - Players/court: 4
  - Session: 1.5h + 10min buffer
  - Fill rate: 90%
- **Corporate**: 2 events/month, 6.0h × 4 courts
- **Tournaments**: $9,000/quarter, 40% share
- **Retail**: $3,000/month sales, 20% margin, 40% share

## 2. Pricing & Units Matrix (Authoritative)

| Category | Tier | Prime Rate | Off-Peak Rate | Unit | Conversion |
|----------|------|------------|---------------|------|------------|
| **Non-Member Court** | - | $65 | $56 | $/court/hr | Direct |
| **Member Court** | Community | $56.0 | $44.0 | $/court/hr | $14.0×4 |
| | Player | $36.0 | $0.0 | $/court/hr | $9.0×4 |
| | Pro | $0.0 | $0.0 | $/court/hr | $0.0×4 |
| **League** | Non-Member | $150.0 | $100.0 | $/player/6wk | Direct |
| | Community | $150.0 | $100.0 | $/player/6wk | 0% discount |
| | Player | $128 | $85 | $/player/6wk | 15% discount |
| | Pro | $112 | $75 | $/player/6wk | 25% discount |
| **Corporate** | - | $200.0 | $170.0 | $/court/hr | Direct |

**Players per Court**: 4 (used for all per-person → per-court conversions)

## 2.5. Utilization Configuration

- **Prime Share** (from schedule): 29.6%
- **Prime Utilization**: 95%
- **Off-Peak Utilization**: 64% (solved for 71% overall)
- **Overall Utilization**: 73%
- **Corporate Events**: 32/year (includes 8 extra off-peak)

## 2.6. Delta from Prior Run

| Metric | Prior | Current | Delta |
|--------|-------|---------|-------|
| Working Capital | $100,000 | $200,000 | +$100,000 |
| SBA Loan | $834,925 | $934,925 | +$100,000 |
| Annual Debt Service | $126,918 | $142,119 | +$15,201 |
| League Member Share | 35% | 65% | --30pp |
| League Non-members | 65% | 35% | +-30pp |
| Prime Utilization | 95% | 95% | - |

## 3. Revenue Formulas (Show Your Math)

### Court Revenue (Tiered)
```
Weekly = Σ[time_bucket] hours × utilization × (
    member_share × Σ[tier] (tier_mix × tier_rate) +
    (1 - member_share) × non_member_rate
)
```

**Example (Prime)**: 116h × 95% × (
    50% × (0.20×$56.0 + 0.50×$36.0 + 0.30×$0.0) +
    50% × $65
) = $7,909/week

### League Revenue
```
Weekly = blocks × players/block × fill_rate × (
    member_share × weighted_member_price +
    non_member_share × rack_rate
) ÷ 6 weeks
```
**League participant mix**: Members 65% • Non-members 35%
*Note: League mix set to 35% non-members by default (higher weighted slot price, consistent with strong demand)*
**Weighted member price**: Community 20%×$150.0 + 
Player 50%×$128 + 
Pro 30%×$112

### Monthly Scaling
- **Court**: Weekly × weeks/month = $7,909 × 4.35 = $34,402
- **League**: Weekly × league-weeks/month (must sum to 46/year)
- **Corporate**: 2 events × revenue/event
- **Tournaments**: $9,000/quarter × 40% × 4 ÷ 12 = $1,200/month
- **Retail**: $3,000 × 20% × 40% = $240/month

### Revenue Bridges
- **Weekly Court+League**: $12,782
- **Annual Variable**: $783,264
- **Annual Membership**: $446,040
- **Annual Total**: $1,229,304

## 4. Costs & Operating Model

- **Fixed OPEX Base**: $60,000/month
  - Rent: $37,000 (62%)
  - Other: $23,000 (38%)
- **Rent Abatement**: 0 months
- **Annual Escalators**: Rent 3.0%, Other 3.0%
- **Variable Cost**: 15.0% of variable revenue
- **Staff Cost**: $5.0/utilized court-hour
- **Utilized CH/month**: ~1254 (from engine)

## 5. Finance, Capex, Depreciation, Tax

### Sources & Uses
| Uses | Amount | Sources | Amount |
|------|--------|---------|--------|
| Leasehold Improvements | $994,000 | TI Allowance | $428,475 |
| Equipment/FF&E | $220,000 | Owner Equity | $200,000 |
| Pre-opening | $50,000 | SBA Loan (computed) | $934,925 |
| Working Capital | $200,000 | | |
| Contingency (10%) | $99,400 | | |
| **Total Uses** | **$1,563,400** | **Total Sources** | **$1,563,400** |

✓ Sources = Uses (balanced)

### Loan Terms
- **Amount (computed)**: $934,925
- **APR**: 9%
- **Term**: 10 years
- **Monthly Payment**: $11,843
- **Formula**: PMT = P × [r(1+r)^n] / [(1+r)^n - 1]

### Depreciation
- **Leasehold**: $994,000 / 10 years = $99,400/year
- **Equipment**: $220,000 / 7 years = $31,429/year
- **Total Annual**: $130,829
- **Tax Rate**: 21%
- **NOL Carryforward Start**: $0

### Opening Cash
- Working Capital: $200,000
- Flows into Balance Sheet as starting cash position

## 6. 24-Month Outputs (Key Lines)

| Metric | Year 1 | Year 2 |
|--------|--------|--------|
| Revenue | $888,377 | $1,198,701 |
| EBITDA | $-10,941 | $265,233 |
| Net Income | $-246,622 | $36,828 |
| End Cash | $6,646 | $89,466 |
| End Debt | $1,122,439 | $1,037,603 |

**Break-even Month**: Month 7 (EBITDA ≥ 0)
**Y1 Min DSCR**: -1.18
**Y2 Avg DSCR**: 1.45

✓ **DSCR Target Met**: Y2 DSCR (1.45) ≥ 1.25

## 7. Guardrails & Assertions (Pass/Fail)

- ✓ **Utilized ≤ Available Hours**: 15054 ≤ 20384
- ✓ **League Hours ≤ Prime Hours**: 100 ≤ 116
- ✓ **League Weeks/Year ≈ 46**: 46.0 ≈ 46
- ✓ **Membership ≤ Cap**: 348 ≤ 350
- ⚠️ WATCHLIST **RevPACH**: $38.43 (Watchlist: $28-35)
- ✓ **Balance Sheet Balances**: Assets = L + E for all months
- ✓ **Unit Audit**: Player off-peak = $0.00/court

## 8. LOI Reconciliation (Lease Offer)

| LOI Term | LOI Value | Model Value | Match |
|----------|-----------|-------------|-------|
| Base Rent | ~$37k/mo | $37,000/mo | ✓ |
| Annual Escalator | 3%/yr | 3.0%/yr | ✓ |
| TI Allowance | $428,475 | $428,475 | ✓ |
| Lease Term | 5 years | - | Info only |
| Free Rent | 0 months | 0 months | ✓ |


## 9. Top 10 Sensitivities (Biggest Impact on Y2 DSCR/Cash)

1. **Fixed OPEX base** (±$5k/mo → ±20% DSCR)
2. **League member share** (±10% → ±15% revenue)
3. **Corporate events/month** (±4 → ±$8k/mo)
4. **Courts used for leagues** (3 vs 4 → ±25% league rev)
5. **League fill rate** (80% vs 90% → ±11% league rev)
6. **Rent abatement months** (0 vs 6 → +$222k Y1 cash)
7. **Loan APR** (11% vs 9% → ±$15k/yr debt service)
8. **Working capital/equity** (±$50k → direct cash impact)
9. **Players per court** (4 vs 5 → ±25% on per-person rates)
10. **Member acquisition speed** (r=0.35 vs 0.5 → ±3mo to steady state)

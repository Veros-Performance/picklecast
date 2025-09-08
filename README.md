# Pickleball Facility Financial Model

Engine-based financial projections for indoor pickleball facilities with tiered member pricing.

## 🚀 Architecture Update (2025)

The application has been refactored to use a clean separation between business logic (engine) and UI:
- **`app.py`** (250 lines) - Minimal Streamlit UI that uses engine as single source of truth
- **`engine/`** - All business logic, pricing models, and calculations
- **`app_legacy.py`** (2,564 lines) - Preserved for reference only, DO NOT EDIT

## 📈 Current Features

- **Tiered Member Pricing**: Community ($14/$11), Player ($9/$0), Pro ($0/$0) per person/hour
- **League Discounts**: 0%/15%/25% based on member tier
- **Engine-based Calculations**: All metrics computed via `engine.compute()`
- **Export Guardrails**: RevPACH < $25, Rev/Util Hr < $60

## Overview

This Streamlit application provides a comprehensive financial model for indoor pickleball facilities. It includes:

- **Facility Model Validation Tab**: Validate projections against real market data from existing facilities
- **Veros Projections Tab**: Generate 24-month financial projections for a new facility

## Features

- Two-tier membership structure (members vs non-members/drop-ins)
- Time-based pricing with early bird, regular, and prime time rates
- Court utilization tracking
- Revenue breakdown by category (membership, court time, programming, ancillary)
- Facility economics modeling including lease, utilities, insurance, and staffing costs
- S-curve growth modeling for new facility ramp-up
- Break-even analysis

## Model Accuracy

The model achieves **84.8% accuracy** when validated against real facility revenue data.

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the new engine-based app:
```bash
streamlit run app.py
```

To view the legacy app (reference only):
```bash
streamlit run app_legacy.py
```

## Development

All new development should target:
- `engine/` for business logic changes
- `app.py` for UI changes

**DO NOT EDIT `app_legacy.py`** - it is preserved for reference only.

## Data Input

For validation, upload a CSV file with the following columns:
- `month`: Month name or number
- `total_revenue`: Total monthly revenue
- `membership_revenue`: Revenue from memberships
- `dropins`: Drop-in/court time revenue
- `programming`: Programming revenue (tournaments, leagues, etc.)
- `ancillary`: Ancillary revenue (pro shop, food, equipment)

## Default Parameters

The model is pre-configured with validated parameters:
- **Members**: 370
- **Non-members**: 150
- **Member rate**: $68/month + $6/hour
- **Non-member rate**: $10/hour
- **Programming revenue**: $38,000/month
- **Ancillary revenue**: $32,000/month

## Documentation

See the `/docs` folder for additional documentation:
- [TODO.md](docs/TODO.md) - Next steps and deployment tasks
- [PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) - Codebase organization
- [REFACTOR_SUGGESTIONS.md](docs/REFACTOR_SUGGESTIONS.md) - Architecture decisions
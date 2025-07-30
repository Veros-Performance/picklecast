# Pickleball Facility Financial Model

Validated financial projections for indoor pickleball facilities based on real market data.

## 📈 Current Status

This model represents a validated financial framework for Veros Pickleball operations, achieving 84.8% accuracy against real facility data. It serves as the foundation for investor presentations, business planning, and franchise scaling strategies.

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

Run the Streamlit app:
```bash
streamlit run app.py
```

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
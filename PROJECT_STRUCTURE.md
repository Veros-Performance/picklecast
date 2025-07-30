# Project Structure

## Overview
The Pickleball Financial Model has been refactored for better scalability and maintainability.

## Directory Structure

```
picklecast/
├── app.py                    # Main entry point - simplified to ~30 lines
├── config/
│   └── default_params.py     # All default parameters in one place
├── components/
│   ├── validation_tab.py     # Model validation tab logic
│   └── projections_tab.py    # Veros projections tab logic
├── utils/
│   ├── calculations.py       # Core calculation functions
│   └── visualizations.py     # Chart generation functions
├── data/
│   └── sample_data/          # CSV data files
└── models/                   # Ready for future model implementations
```

## Key Benefits

1. **Modular Design**: Each tab is now a separate component
2. **Centralized Config**: All parameters in `config/default_params.py`
3. **Reusable Utils**: Calculations and visualizations are shared
4. **Easy Extension**: Add new tabs by creating new components
5. **Clean Separation**: Business logic separated from UI

## Adding New Features

### To add a new business model tab:
1. Create a new file in `components/` (e.g., `franchise_tab.py`)
2. Add default parameters to `config/default_params.py`
3. Import and add the tab in `app.py`

### To add new calculations:
1. Add functions to `utils/calculations.py`
2. Import and use in any component

## No Functionality Changes
This refactoring maintains 100% of the original functionality while making the codebase more maintainable.
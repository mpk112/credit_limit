# Loan Limit Optimization System

## Project Overview

Kiro spec-driven data science project that determines optimal credit limit increase strategies for 30,000 consumer lending customers. Balances profitability maximization against default risk constraints using Linear Programming, Monte Carlo simulation, gradient boosting (XGBoost/LightGBM), and Markov chain modeling.

Spec files: `kiro/specs/loan-limit-optimization/` (requirements.md, design.md, tasks.md)

**Primary deliverable**: `loan_limit_optimization.ipynb` — single notebook that runs end-to-end with "Run All Cells"

> **Note**: The notebook (`loan_limit_optimization.ipynb`) was deleted from the working tree but exists in git history (`git show HEAD:loan_limit_optimization.ipynb`). Restore with `git restore loan_limit_optimization.ipynb` or rebuild. Several components also live in standalone `.py` files (untracked) that need to be integrated into the notebook.

## Tech Stack

- **Python 3.8+** — virtualenv at `.venv/`, activate with `source .venv/bin/activate`
- **Core**: pandas, numpy, scipy, scikit-learn
- **Optimization**: PuLP or CVXPY (CBC/GLPK solver backends)
- **ML**: XGBoost or LightGBM for default risk; logistic regression baseline exists
- **Macro data**: fredapi (FRED API), requests + requests-cache (World Bank)
- **Visualization**: matplotlib, seaborn (minimum 10 plots required)
- **Notebook**: Jupyter — `jupyter notebook loan_limit_optimization.ipynb`

## Environment Setup

```bash
source .venv/bin/activate
# .env file exists (gitignored) and contains FRED_API_KEY
# Cached macro data: cache/macro_data_2023.json (already fetched)
```

Key configurable parameters (all have defaults):

| Env Var | Default | Purpose |
|---|---|---|
| `FRED_API_KEY` | — | Required for macro data fetch; cached after first call |
| `NPV_DISCOUNT_RATE` | 0.19 | Annual NPV discount rate (per brief specification) |
| `SIMULATION_ITERATIONS` | 3500 | Monte Carlo iterations per customer |
| `MAX_PORTFOLIO_DEFAULT_RISK` | 0.05 | Portfolio risk cap |
| `MIN_PROFITABILITY_TARGET` | 1_000_000 | Minimum profit target |
| `MAX_TOTAL_EXPOSURE` | 500_000_000 | Maximum total credit exposure |
| `MAX_INDIVIDUAL_LIMIT` | 50_000 | Per-customer loan limit cap |
| `DEFAULT_RISK_THRESHOLD` | 0.15 | High-risk flag threshold |

## Architecture

Eight components in one Jupyter Notebook, executed sequentially:

```
loan_limit_increases.csv (30k records)
  → Data Loading & Preprocessing        load_and_preprocess_data()
  → Macro Data Enricher                 fetch_macro_data(), enrich_customer_data()
  → Risk Model                          classify_credit_states(), estimate_default_risk()
  → Markov Chain Analyzer               build_transition_matrix()
  → Demand Forecaster                   forecast_utilization()
  → Lifecycle Simulator                 simulate_loan_lifecycle()
  → Constraint Definition               create_constraint_set(), validate_constraints()
  → Optimization Engine                 optimize_limits_lp()  [MISSING]
  → Results & Visualization             generate_summary_report(), create_visualizations(), export_results()  [MISSING]
```

## Implementation Status

### In the Notebook (git HEAD) — Implemented
| Component | Functions | Status |
|---|---|---|
| Data Loading & Preprocessing | `load_and_preprocess_data()` | Complete |
| Macro Data Enricher | `fetch_macro_data()`, `fetch_macro_scenarios()`, `enrich_customer_data()` | Complete |
| Credit State Classification | `classify_credit_states()`, `calculate_composite_credit_score()`, `estimate_default_risk()` | Complete |
| Markov Chain Analyzer | imports from `transition_matrix_implementation.py`, runs integration test | Complete (via import) |
| Demand Forecaster | `forecast_utilization()` | Complete (inline + standalone) |
| Lifecycle Simulator | `simulate_loan_lifecycle()` | Complete (inline + standalone) |

### In Standalone `.py` Files — Not Yet in Notebook
| File | Functions | Notes |
|---|---|---|
| `constraint_validation_implementation.py` | `create_constraint_set()`, `validate_constraints()`, `identify_conflicts()`, `print_constraint_summary()` | Untracked; needs notebook integration |
| `validate_constraints_addition.py` | `validate_constraints()` | Alternative/supplemental version |
| `transition_matrix_implementation.py` | `build_transition_matrix()`, `TransitionMatrix`, `compute_steady_state()` | Imported by notebook already |
| `forecast_utilization_implementation.py` | `forecast_utilization()` + property tests P16–P18 | Standalone version |
| `lifecycle_simulation_implementation.py` | `simulate_loan_lifecycle()`, `simulate_cohort_lifecycle()` + helpers | Standalone version |
| `macro_enrichment_addition.py` | `fetch_macro_scenarios()`, `enrich_customer_data()` | Standalone version |

### Not Implemented Anywhere — Needs Building
| Component | Functions | Tasks |
|---|---|---|
| LP Optimization | `optimize_limits_lp()` | Task 11.1 |
| MDP Optimization | `optimize_limits_mdp()` | Task 12.1 (optional/advanced) |
| Solution Validation | `validate_solution()` | Task 14.1 |
| Sensitivity Analysis | `sensitivity_analysis()` | Task 14.2 |
| Results Reporting | `generate_summary_report()`, `create_visualizations()`, `export_results()` | Task 15.1–15.3 |
| Integration Pipeline | end-to-end wiring | Task 18.1 |
| Property Tests | P1–P3, P7–P9, P13–P18, P19–P27, P31–P44 | Multiple tasks |

## Key Data Structures

```python
# Input CSV columns (loan_limit_increases.csv)
['Customer ID', 'Initial Loan ($)', 'Days Since Last Loan',
 'On-time Payments (%)', 'No. of Increases in 2023', 'Total Profit Contribution ($)']

# Constraint_Set (dict)
{
    'max_portfolio_default_risk': 0.05,
    'min_profitability_target': 1_000_000,
    'max_total_exposure': 500_000_000,
    'max_individual_limit': 50_000,
    'max_debt_to_income_ratio': 0.43,
    'regulatory_capital_requirement': 0.08
}

# Optimization_Result (per customer output)
{
    'customer_id', 'current_limit', 'recommended_limit',
    'limit_increase', 'credit_state', 'default_risk',
    'profitability_score', 'expected_revenue', 'expected_loss'
}

# Macroeconomic scenarios
# Optimistic: GDP 3.5%, unemployment 3.5%, rate 4.0%, inflation 2.5%
# Baseline:   GDP 2.5%, unemployment 4.0%, rate 5.0%, inflation 3.5%
# Adverse:    GDP 0.5%, unemployment 5.5%, rate 6.0%, inflation 5.0%
```

## Key Correctness Properties (from design.md, P1–P44)

Critical properties to validate when implementing missing components:
- **P21**: ≥ 3,000 Monte Carlo iterations per customer
- **P25**: LP objective is maximum feasible value
- **P26**: All Constraint_Set constraints satisfied in solution
- **P27**: All limit increases ≥ 0
- **P29**: Portfolio default risk ≤ `max_portfolio_default_risk`
- **P30**: LP solver status is 'Optimal' or 'Feasible'
- **P36**: At least 10 visualizations created
- **P38**: End-to-end execution < 30 minutes (4-core/16GB laptop)
- **P39**: Peak memory ≤ 8GB

## Running the Notebook

```bash
source .venv/bin/activate
# Restore notebook if deleted:
git restore loan_limit_optimization.ipynb
jupyter notebook loan_limit_optimization.ipynb
# Then: Kernel → Restart & Run All
```

## Performance Notes

- Process customers in batches of 5,000 to stay under 8GB RAM
- Use `float32` where possible to halve memory vs `float64`
- Vectorize with numpy/pandas; avoid Python loops in Monte Carlo hot paths
- `joblib.Parallel` for parallelizing customer-level simulations
- LP solver timeout: 300 seconds (CBC backend preferred)
- Macro data is cached to `cache/macro_data_2023.json` — no repeated API calls needed

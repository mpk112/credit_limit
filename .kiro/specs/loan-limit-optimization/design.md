# Design Document

## System Architecture

The Loan Limit Optimization System is implemented as a single Jupyter Notebook containing six major functional components that work together to analyze customer data, model risk and behavior, and optimize loan limit decisions.

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Jupyter Notebook                             │
│                                                                   │
│  ┌──────────────────┐      ┌──────────────────┐                │
│  │ Data Loading &   │─────▶│ Macro Data       │                │
│  │ Preprocessing    │      │ Enricher         │                │
│  └──────────────────┘      └──────────────────┘                │
│           │                          │                           │
│           ▼                          ▼                           │
│  ┌─────────────────────────────────────────┐                   │
│  │         Risk Model                       │                   │
│  │  - Credit State Classification           │                   │
│  │  - Default Risk Estimation               │                   │
│  └─────────────────────────────────────────┘                   │
│           │                                                      │
│           ├──────────────┬──────────────┬──────────────┐       │
│           ▼              ▼              ▼              ▼       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐│
│  │ Markov Chain │ │   Demand     │ │  Lifecycle   │ │Optim.  ││
│  │  Analyzer    │ │  Forecaster  │ │  Simulator   │ │Engine  ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────┘│
│           │              │              │              │        │
│           └──────────────┴──────────────┴──────────────┘        │
│                          ▼                                       │
│           ┌──────────────────────────────┐                     │
│           │  Results & Visualization     │                     │
│           └──────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

1. **Data Loading & Preprocessing**: Loads 30,000 customer records from CSV, validates data quality, handles missing values, and normalizes features

2. **Macro Data Enricher**: Fetches macroeconomic indicators (GDP growth, unemployment rate, federal funds rate, CPI, inflation) from FRED and World Bank APIs with support for multiple scenarios (optimistic, baseline, adverse)

3. **Risk Model**: Classifies customers into credit states and estimates default probabilities using gradient boosting (XGBoost/LightGBM) with customer attributes and macroeconomic factors

4. **Markov Chain Analyzer**: Builds transition probability matrices to model how customers move between credit states over time (optional component for advanced use cases)

5. **Demand Forecaster**: Predicts loan utilization patterns using stochastic methods and Monte Carlo simulation with scenario support

6. **Lifecycle Simulator**: Simulates multi-period loan performance including utilization, payments, defaults, and state transitions using 3,000-4,000 iterations with cohort aggregation

7. **Optimization Engine**: Formulates and solves the loan limit problem using Linear Programming (LP) with scenario-based sensitivity analysis

8. **Results & Visualization**: Generates summary reports, customer-level recommendations, and visualizations for decision-making

## Data Models

### Customer_Record
```python
{
    'customer_id': str,
    'initial_loan': float,
    'days_since_last_loan': int,
    'on_time_payments_pct': float,
    'num_increases_2023': int,
    'total_profit_contribution': float,
    'credit_score': float,  # derived or provided
    'utilization_rate': float,  # derived
    'credit_state': str,  # assigned by Risk_Model
    'default_risk': float,  # calculated by Risk_Model
    'macro_gdp_growth': float,  # from Macro_Data_Enricher
    'macro_unemployment': float,
    'macro_fed_rate': float,
    'macro_cpi': float
}
```

### Credit_State
```python
{
    'state_name': str,  # e.g., 'Excellent', 'Good', 'Fair', 'Poor'
    'score_min': float,
    'score_max': float,
    'default_rate': float,
    'customer_count': int
}
```

### Transition_Matrix
```python
{
    'matrix': np.ndarray,  # shape (n_states, n_states)
    'state_labels': List[str],
    'steady_state': np.ndarray,  # shape (n_states,)
    'observation_period_days': int
}
```

### Constraint_Set
```python
{
    'max_portfolio_default_risk': float,  # e.g., 0.05
    'min_profitability_target': float,  # e.g., 1000000
    'max_total_exposure': float,  # e.g., 500000000
    'max_individual_limit': float,  # e.g., 50000
    'max_debt_to_income_ratio': float,  # e.g., 0.43
    'regulatory_capital_requirement': float  # e.g., 0.08
}
```

### Optimization_Result
```python
{
    'customer_id': str,
    'current_limit': float,
    'recommended_limit': float,
    'limit_increase': float,
    'credit_state': str,
    'default_risk': float,
    'profitability_score': float,
    'expected_revenue': float,
    'expected_loss': float
}
```

## Component Interfaces

### 1. Data Loading & Preprocessing

**Function**: `load_and_preprocess_data(file_path: str) -> pd.DataFrame`

**Inputs**:
- `file_path`: Path to loan_limit_increases.csv

**Outputs**:
- DataFrame with 30,000 validated and normalized customer records

**Processing Steps**:
1. Load CSV using pandas
2. Validate required columns exist
3. Handle missing values (median/mode imputation or exclusion)
4. Derive additional features (credit_score proxy, utilization_rate)
5. Normalize numerical features using StandardScaler
6. Log validation errors

**Error Handling**:
- Missing file → raise FileNotFoundError
- Invalid data format → log error, skip record
- Insufficient records → raise ValueError

---

### 2. Macro Data Enricher

**Function**: `fetch_macro_data(year: int = 2023) -> Dict[str, float]`

**Inputs**:
- `year`: Target year for macroeconomic data

**Outputs**:
- Dictionary with keys: 'gdp_growth', 'unemployment', 'fed_rate', 'cpi'

**Processing Steps**:
1. Initialize FRED API client (requires API key)
2. Fetch GDP growth rate (series: GDPC1)
3. Fetch unemployment rate (series: UNRATE)
4. Fetch federal funds rate (series: FEDFUNDS)
5. Fetch CPI (series: CPIAUCSL)
6. Cache results to local file
7. Retry failed requests up to 3 times with exponential backoff

**Function**: `enrich_customer_data(df: pd.DataFrame, macro_data: Dict) -> pd.DataFrame`

**Inputs**:
- `df`: Customer DataFrame
- `macro_data`: Macroeconomic indicators

**Outputs**:
- DataFrame with macro columns added

**Error Handling**:
- API failure after retries → use cached data or default values
- Missing API key → log warning, use default values

---

### 3. Risk Model

**Function**: `classify_credit_states(df: pd.DataFrame, n_states: int = 4) -> pd.DataFrame`

**Inputs**:
- `df`: Customer DataFrame
- `n_states`: Number of credit states (default 4)

**Outputs**:
- DataFrame with 'credit_state' column added

**Processing Steps**:
1. Calculate composite credit score from on_time_payments_pct and other factors
2. Define state boundaries using quantiles or domain-specific credit score ranges
3. Assign each customer to a credit state
4. Flag customers with insufficient data

**Function**: `estimate_default_risk(df: pd.DataFrame) -> pd.DataFrame`

**Inputs**:
- `df`: Customer DataFrame with credit_state

**Outputs**:
- DataFrame with 'default_risk' column added

**Processing Steps**:
1. Train gradient boosting model (XGBoost or LightGBM) using features: credit_score, utilization_rate, credit_state (encoded), macro indicators
2. Perform hyperparameter tuning using cross-validation
3. Predict default probability for each customer
4. Clip probabilities to [0.0, 1.0]
5. Calculate feature importance and SHAP values for interpretability
6. Flag high-risk customers (default_risk > configurable threshold)
7. Support model versioning and A/B testing

**Error Handling**:
- Insufficient data for classification → assign default state 'Unknown'
- Model convergence failure → use baseline default rates by state

---

### 4. Markov Chain Analyzer

**Function**: `build_transition_matrix(df: pd.DataFrame, observation_period: int = 90) -> Transition_Matrix`

**Inputs**:
- `df`: Customer DataFrame with historical credit_state data
- `observation_period`: Days for calculating transitions

**Outputs**:
- Transition_Matrix object

**Processing Steps**:
1. Extract state transition sequences from historical data
2. Count transitions between each pair of states
3. Normalize rows to create stochastic matrix
4. Validate matrix properties (row sums = 1.0, stochastic, irreducible)
5. Compute steady-state distribution using eigenvalue decomposition

**Error Handling**:
- Insufficient historical data → use uniform transition probabilities
- Non-irreducible matrix → add small epsilon to zero entries

---

### 5. Demand Forecaster

**Function**: `forecast_utilization(df: pd.DataFrame, horizon_days: int = 365, n_scenarios: int = 3000) -> pd.DataFrame`

**Inputs**:
- `df`: Customer DataFrame
- `horizon_days`: Forecast horizon
- `n_scenarios`: Number of Monte Carlo scenarios (default 3000, configurable)

**Outputs**:
- DataFrame with 'forecasted_utilization' and 'utilization_std' columns

**Processing Steps**:
1. Fit time series model (ARIMA or exponential smoothing) to historical utilization
2. Incorporate seasonality and trend components
3. Generate Monte Carlo scenarios for demand uncertainty
4. Calculate mean and standard deviation across scenarios
5. Use cohort averages for customers with insufficient history
6. Support scenario-based forecasting (optimistic, baseline, adverse)

**Error Handling**:
- Insufficient historical data → use cohort-based averages
- Model fitting failure → use simple moving average

---

### 6. Lifecycle Simulator

**Function**: `simulate_loan_lifecycle(df: pd.DataFrame, n_iterations: int = 3500, horizon_days: int = 365, discount_rate: float = 0.12) -> pd.DataFrame`

**Inputs**:
- `df`: Customer DataFrame
- `n_iterations`: Monte Carlo iterations per customer (default 3500, configurable)
- `horizon_days`: Simulation horizon
- `discount_rate`: NPV discount rate (default 12%, configurable)

**Outputs**:
- DataFrame with 'expected_revenue', 'expected_loss', 'profitability_score' columns

**Processing Steps**:
1. For each customer, run n_iterations Monte Carlo simulations:
   - Simulate credit state transitions
   - Simulate utilization changes using forecasted distributions
   - Simulate payment behavior (early, on-time, late, default)
   - Calculate revenue (interest + fees) and losses (defaults)
2. Aggregate results: mean, median, percentiles
3. Calculate net profitability_score = expected_revenue - expected_loss
4. Apply NPV discounting at configurable rate
5. Support cohort-based aggregation for performance optimization

**Error Handling**:
- Simulation divergence → cap extreme values
- Memory constraints → automatically switch to cohort-based aggregation

---

### 8. Solution Validation

**Function**: `validate_solution(results: List[Optimization_Result], constraints: Constraint_Set) -> Dict`

**Inputs**:
- `results`: Optimization results
- `constraints`: Constraint set

**Outputs**:
- Dictionary with validation status, constraint satisfaction details, and any violations

**Processing Steps**:
1. Calculate total portfolio default risk
2. Calculate total profitability
3. Calculate total exposure
4. Verify all individual limits within bounds
5. Check all constraints satisfied with configurable tolerances
6. Report detailed validation results including any violations

**Function**: `sensitivity_analysis(df: pd.DataFrame, constraints: Constraint_Set, scenarios: List[str] = ['optimistic', 'baseline', 'adverse']) -> pd.DataFrame`

**Inputs**:
- `df`: Customer DataFrame
- `constraints`: Base constraint set
- `scenarios`: List of macroeconomic scenarios to evaluate

**Outputs**:
- DataFrame with scenario results including objective values and portfolio metrics

**Processing Steps**:
1. Define scenario parameters (GDP growth, unemployment, interest rates, inflation)
2. For each scenario:
   - Enrich customer data with scenario-specific macro indicators
   - Re-estimate default risk using scenario-adjusted model
   - Re-run lifecycle simulation with scenario parameters
   - Re-optimize LP with scenario-specific inputs
3. Compare objective values and recommended limits across scenarios
4. Calculate scenario-weighted portfolio outcomes
5. Report range of outcomes and robustness metrics

**Error Handling**:
- Scenario parameter validation → report invalid parameters
- Optimization failure for scenario → log warning, continue with other scenarios

---

### 9. Results Reporting and Visualization

**Function**: `generate_summary_report(results: List[Optimization_Result]) -> Dict`

**Outputs**:
```python
{
    'total_customers': int,
    'customers_with_increases': int,
    'total_incremental_exposure': float,
    'expected_incremental_profit': float,
    'portfolio_default_risk': float,
    'avg_increase_amount': float
}
```

**Function**: `create_visualizations(df: pd.DataFrame, results: List[Optimization_Result]) -> None`

**Visualizations**:
1. Credit state distribution (bar chart)
2. Transition probability heatmap
3. Default risk distribution (histogram)
4. Current vs recommended limits by credit state (grouped bar chart)
5. Risk-return scatter plot (default_risk vs profitability_score)
6. Optimization objective convergence (line chart)
7. Limit increase distribution (histogram)
8. Sensitivity analysis results (box plot)
9. Macroeconomic indicators time series
10. Portfolio exposure before/after (stacked bar chart)

**Function**: `export_results(results: List[Optimization_Result], output_path: str) -> None`

**Outputs**:
- CSV file with customer-level recommendations

## Implementation Technology Stack

### Core Libraries
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations and array operations
- **scipy**: Statistical functions and optimization
- **scikit-learn**: Machine learning models (logistic regression, preprocessing)

### Optimization Libraries
- **PuLP** or **CVXPY**: Linear programming formulation and solving
- **CBC** or **GLPK**: LP solver backends

### API Integration
- **fredapi**: FRED API client for macroeconomic data
- **requests**: HTTP requests for World Bank API
- **requests-cache**: API response caching

### Visualization
- **matplotlib**: Core plotting library
- **seaborn**: Statistical visualizations
- **plotly** (optional): Interactive visualizations

### Jupyter Environment
- **jupyter**: Notebook environment
- **IPython**: Enhanced interactive Python shell

## Error Handling Strategy

### Data Quality Issues
- **Missing values**: Impute using median (numerical) or mode (categorical), or exclude record if >30% missing
- **Invalid values**: Log warning, replace with NaN, handle in imputation
- **Duplicate records**: Keep first occurrence, log warning

### API Failures
- **Network errors**: Retry up to 3 times with exponential backoff (1s, 2s, 4s)
- **Rate limiting**: Implement request throttling, use cached data
- **Missing API keys**: Log warning, use default/cached values

### Model Failures
- **Convergence issues**: Increase max iterations, adjust tolerance, use fallback method
- **Numerical instability**: Add regularization, scale features, clip extreme values
- **Insufficient data**: Use cohort averages, baseline rates, or exclude customer

### Optimization Failures
- **Infeasible constraints**: Report conflicting constraints, suggest relaxation
- **Solver timeout**: Return best solution found, log status
- **Unbounded problem**: Add missing constraints, validate formulation

### Performance Issues
- **Memory constraints**: Process data in batches, use chunking
- **Computation time**: Parallelize Monte Carlo simulations, reduce iterations
- **Large datasets**: Use vectorized operations, avoid loops

## Performance Optimization

### Vectorization
- Use numpy/pandas vectorized operations instead of Python loops
- Leverage broadcasting for element-wise operations
- Use pandas groupby for aggregations

### Parallelization
- Use multiprocessing for Monte Carlo simulations
- Parallelize customer-level computations
- Use joblib for parallel function execution

### Memory Management
- Process customers in batches of 5,000
- Delete intermediate DataFrames after use
- Use appropriate data types (float32 vs float64)

### Caching
- Cache API responses to disk
- Cache intermediate computation results
- Use memoization for repeated calculations

## Correctness Properties

### Data Integrity Properties
1. **P1_LoadExactCount**: After loading, customer count equals 30,000
2. **P2_NoMissingRequired**: All required fields present after preprocessing
3. **P3_NormalizedRange**: Normalized features in range [-3, 3] (3 std devs)

### Macroeconomic Data Properties
4. **P4_MacroIndicatorsPresent**: All 4+ macro indicators fetched successfully
5. **P5_MacroDataCached**: Cached data file created after first fetch
6. **P6_MacroMergeComplete**: All customers have macro data after merge
7. **P7_ScenarioParametersDefined**: Scenario parameters defined for optimistic, baseline, adverse

### Credit State Properties
8. **P8_StateCountValid**: Number of credit states equals configured n_states
9. **P9_AllCustomersClassified**: Every customer assigned exactly one credit state
10. **P10_StateDistributionNonEmpty**: Each credit state has at least one customer

### Markov Chain Properties
11. **P11_TransitionMatrixStochastic**: Each row sums to 1.0 ± 0.001
12. **P12_TransitionMatrixSquare**: Matrix dimensions are (n_states, n_states)
13. **P13_SteadyStateValid**: Steady state probabilities sum to 1.0 ± 0.001

### Risk Model Properties
14. **P14_DefaultRiskRange**: All default_risk values in [0.0, 1.0]
15. **P15_HighRiskFlagged**: Customers with default_risk > threshold are flagged
16. **P16_RiskIncorporatesMacro**: Default risk calculation uses macro indicators
17. **P17_FeatureImportance**: Gradient boosting provides feature importance scores

### Demand Forecasting Properties
18. **P18_UtilizationRange**: Forecasted utilization in [0.0, 1.0]
19. **P19_MinScenarios**: At least 3,000 Monte Carlo scenarios generated
20. **P20_ForecastHorizonValid**: Forecast horizon matches configured days

### Lifecycle Simulation Properties
21. **P21_MinIterations**: At least 3,000 Monte Carlo iterations per customer
22. **P22_ProfitabilityCalculated**: All customers have profitability_score
23. **P23_NPVDiscounted**: Profitability scores discounted at configurable rate
24. **P24_CohortAggregation**: Automatic fallback to cohort-based aggregation when memory exceeds limits

### Optimization Properties
25. **P25_ObjectiveMaximized**: LP objective value is maximum feasible value
26. **P26_ConstraintsSatisfied**: All constraints in Constraint_Set satisfied
27. **P27_NonNegativeIncreases**: All limit increases ≥ 0
28. **P28_IndividualLimitRespected**: No customer exceeds max_individual_limit
29. **P29_PortfolioRiskRespected**: Portfolio default risk ≤ max_portfolio_default_risk
30. **P30_SolverConverged**: LP solver status is 'Optimal' or 'Feasible'

### Validation Properties
31. **P31_SolutionValid**: validate_solution returns True for optimal solution
32. **P32_SensitivityScenariosComplete**: All scenarios executed successfully
33. **P33_ObjectiveRangeReported**: Sensitivity analysis reports min/max objectives

### Reporting Properties
34. **P34_SummaryReportComplete**: Summary report contains all required fields
35. **P35_CustomerTableComplete**: Customer table has all required columns
36. **P36_MinVisualizationsGenerated**: At least 10 visualizations created
37. **P37_ResultsExported**: CSV file created with optimization results

### Performance Properties
38. **P38_ExecutionTime**: End-to-end execution completes within 30 minutes
39. **P39_MemoryLimit**: Peak memory usage ≤ 8GB
40. **P40_ProgressIndicators**: Progress messages displayed during long operations

### Code Quality Properties
41. **P41_FunctionsDocumented**: All functions have docstrings
42. **P42_VariableNamesDescriptive**: Variables follow Python naming conventions
43. **P43_RequirementsListed**: Notebook includes requirements cell with versions
44. **P44_NotebookExecutable**: Notebook runs without errors using "Run All Cells"

## Testing Strategy

### Unit Tests
- Test each component function independently
- Use synthetic data with known properties
- Verify correctness properties hold

### Integration Tests
- Test component interactions
- Verify data flows correctly between components
- Check end-to-end pipeline execution

### Property-Based Tests
- Use Hypothesis library to generate test cases
- Verify correctness properties hold for random inputs
- Test edge cases and boundary conditions

### Performance Tests
- Measure execution time for 30,000 customers
- Monitor memory usage during execution
- Verify performance properties satisfied

### Validation Tests
- Compare optimization results against baseline
- Verify constraint satisfaction
- Check sensitivity analysis results are reasonable

## Deployment Considerations

### Environment Setup
1. Install Python 3.8+
2. Install required packages: `pip install -r requirements.txt`
3. Obtain FRED API key (free registration)
4. Set environment variable: `export FRED_API_KEY=your_key`

### Data Requirements
- Input file: `loan_limit_increases.csv` with 30,000 records
- Columns: Customer ID, Initial Loan ($), Days Since Last Loan, On-time Payments (%), No. of Increases in 2023, Total Profit Contribution ($)

### Configuration Parameters

All key parameters are configurable via environment variables for flexibility:

| Parameter | Default | Environment Variable | Description |
|-----------|---------|---------------------|-------------|
| `NPV_DISCOUNT_RATE` | 0.12 | `NPV_DISCOUNT_RATE` | Annual discount rate for NPV calculations |
| `SIMULATION_ITERATIONS` | 3500 | `SIMULATION_ITERATIONS` | Monte Carlo iterations per customer |
| `MAX_PORTFOLIO_DEFAULT_RISK` | 0.05 | `MAX_PORTFOLIO_DEFAULT_RISK` | Maximum portfolio default risk threshold |
| `MIN_PROFITABILITY_TARGET` | 1000000 | `MIN_PROFITABILITY_TARGET` | Minimum profitability target |
| `MAX_TOTAL_EXPOSURE` | 500000000 | `MAX_TOTAL_EXPOSURE` | Maximum total credit exposure |
| `MAX_INDIVIDUAL_LIMIT` | 50000 | `MAX_INDIVIDUAL_LIMIT` | Maximum individual loan limit |
| `DEFAULT_RISK_THRESHOLD` | 0.15 | `DEFAULT_RISK_THRESHOLD` | High-risk customer threshold |
| `SCENARIO_WEIGHTS` | {"optimistic": 0.3, "baseline": 0.4, "adverse": 0.3} | `SCENARIO_WEIGHTS` | Scenario weights for portfolio outcomes |

### Scenario Parameters

Scenario parameters are defined in the macro data enricher:

| Scenario | GDP Growth | Unemployment | Interest Rates | Inflation |
|----------|------------|--------------|----------------|-----------|
| Optimistic | 3.5% | 3.5% | 4.0% | 2.5% |
| Baseline | 2.5% | 4.0% | 5.0% | 3.5% |
| Adverse | 0.5% | 5.5% | 6.0% | 5.0% |

### Execution
1. Open Jupyter Notebook: `jupyter notebook loan_limit_optimization.ipynb`
2. Run all cells sequentially
3. Review visualizations and summary report
4. Export results to CSV for downstream use

### Monitoring
- Check execution logs for warnings/errors
- Verify all correctness properties satisfied
- Review sensitivity analysis for robustness
- Validate results against business expectations

## Future Enhancements

### Model Improvements
- Incorporate additional customer features (income, employment, credit history)
- Use advanced ML models (gradient boosting, neural networks) for default prediction
- Implement reinforcement learning for dynamic limit adjustment policies

### Optimization Enhancements
- Multi-objective optimization (profitability, risk, customer satisfaction)
- Robust optimization under uncertainty
- Real-time optimization with streaming data

### Operational Features
- Automated model retraining pipeline
- A/B testing framework for limit strategies
- Real-time monitoring dashboard
- Integration with loan origination system

### Scalability
- Distributed computing for larger datasets (Spark, Dask)
- Cloud deployment (AWS, Azure, GCP)
- API service for real-time limit recommendations

# Implementation Plan: Loan Limit Optimization System

## Overview

This implementation plan breaks down the Loan Limit Optimization System into discrete coding tasks. The system is implemented as a single Jupyter Notebook that processes 30,000 customer records, enriches them with macroeconomic data, models credit risk using gradient boosting, forecasts demand, simulates loan lifecycles with 3,000-4,000 iterations, and optimizes loan limits using Linear Programming with scenario-based sensitivity analysis.

## Key Methodology Updates (Industry Alignment)

This implementation follows industry best practices for credit limit optimization:

- **Primary Optimization**: Linear Programming (LP) for efficient, globally optimal solutions at scale
- **Default Risk Modeling**: Gradient Boosting (XGBoost/LightGBM) for superior predictive accuracy
- **Lifecycle Simulation**: 3,000-4,000 Monte Carlo iterations with cohort aggregation for performance
- **Scenario Analysis**: Multiple macroeconomic scenarios (optimistic, baseline, adverse) for robustness
- **Flexible Configuration**: All key parameters (discount rate, inflation, iterations) are configurable

## Tasks

- [x] 1. Set up Jupyter Notebook structure and dependencies
  - Create `loan_limit_optimization.ipynb` notebook file
  - Add markdown introduction cell explaining the system purpose and methodology
  - Create requirements cell listing all Python packages with versions: pandas, numpy, scipy, scikit-learn, xgboost (or lightgbm), PuLP (or CVXPY), fredapi, requests, requests-cache, matplotlib, seaborn, jupyter, shap
  - Add import statements for all required libraries
  - Configure matplotlib/seaborn visualization settings
  - Set random seeds for reproducibility
  - _Requirements: 13.1, 13.2, 13.3, 16.5_

- [x] 2. Implement data loading and preprocessing component
  - [x] 2.1 Create `load_and_preprocess_data()` function
    - Implement CSV loading using pandas with error handling for missing files
    - Validate required columns exist: customer_id, initial_loan, days_since_last_loan, on_time_payments_pct, num_increases_2023, total_profit_contribution
    - Implement missing value detection and logging
    - Implement median/mode imputation for missing values
    - Derive credit_score proxy and utilization_rate features
    - Apply StandardScaler normalization to numerical features
    - Return validated DataFrame with exactly 30,000 records
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_
  
  - [x] 2.2 Write property test for data loading
    - **Property P1_LoadExactCount: After loading, customer count equals 30,000**
    - **Validates: Requirements 13.1**
  
  - [ ]* 2.3 Write property test for data preprocessing
    - **Property P2_NoMissingRequired: All required fields present after preprocessing**
    - **Property P3_NormalizedRange: Normalized features in range [-3, 3]**
    - **Validates: Requirements 13.3, 13.5**

- [x] 3. Implement macroeconomic data enrichment component
  - [x] 3.1 Create `fetch_macro_data()` function
    - Initialize FRED API client with API key from environment variable
    - Fetch GDP growth rate (series: GDPC1) for target year
    - Fetch unemployment rate (series: UNRATE) for target year
    - Fetch federal funds rate (series: FEDFUNDS) for target year
    - Fetch CPI (series: CPIAUCSL) for target year
    - Fetch inflation rate (series: CPIAUCSL) for target year
    - Implement retry logic with exponential backoff (3 attempts: 1s, 2s, 4s)
    - Cache results to local JSON file
    - Return dictionary with keys: gdp_growth, unemployment, fed_rate, cpi, inflation
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  
  - [x] 3.2 Create `fetch_macro_scenarios()` function
    - Define scenario parameters for optimistic, baseline, and adverse conditions
    - Optimistic: Low unemployment, moderate GDP growth, stable rates
    - Baseline: Historical averages
    - Adverse: High unemployment, low/negative GDP growth, elevated rates
    - Return dictionary of scenario parameters
    - _Requirements: 13.5, 13.6_
  
  - [x] 3.3 Create `enrich_customer_data()` function
    - Accept customer DataFrame and macro_data dictionary
    - Add macro indicator columns to each customer record
    - Validate all customers have macro data after merge
    - _Requirements: 13.5_
  
  - [ ]* 3.4 Write property tests for macro data enrichment
    - **Property P4_MacroIndicatorsPresent: All 4+ macro indicators fetched successfully**
    - **Property P5_MacroDataCached: Cached data file created after first fetch**
    - **Property P6_MacroMergeComplete: All customers have macro data after merge**
    - **Validates: Requirements 13.2, 13.4, 13.5**

- [x] 4. Checkpoint - Ensure data loading and enrichment work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement credit state classification and risk model
  - [x] 5.1 Create `classify_credit_states()` function
    - Calculate composite credit score from on_time_payments_pct and other factors
    - Define 4 credit state boundaries using quantile-based thresholds
    - Assign each customer to exactly one credit state (Excellent, Good, Fair, Poor)
    - Flag customers with insufficient data and assign default state
    - Add credit_state column to DataFrame
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  
  - [x] 5.2 Create `estimate_default_risk()` function
    - Train gradient boosting model (XGBoost or LightGBM) using features: credit_score, utilization_rate, credit_state (encoded), macro indicators
    - Perform hyperparameter tuning using cross-validation
    - Predict default probability for each customer
    - Clip probabilities to [0.0, 1.0]
    - Calculate feature importance and SHAP values for interpretability
    - Flag high-risk customers (default_risk > configurable threshold)
    - Add default_risk column to DataFrame
    - Support model versioning and A/B testing
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_
  
  - [x]* 5.3 Write property tests for credit state classification
    - **Property P7_StateCountValid: Number of credit states equals configured n_states**
    - **Property P8_AllCustomersClassified: Every customer assigned exactly one credit state**
    - **Property P9_StateDistributionNonEmpty: Each credit state has at least one customer**
    - **Validates: Requirements 13.1, 13.3**
  
  - [x]* 5.4 Write property tests for default risk estimation
    - **Property P13_DefaultRiskRange: All default_risk values in [0.0, 1.0]**
    - **Property P14_HighRiskFlagged: Customers with default_risk > threshold are flagged**
    - **Property P15_RiskIncorporatesMacro: Default risk calculation uses macro indicators**
    - **Validates: Requirements 13.2, 13.3, 13.4**

- [ ] 6. Implement Markov chain transition modeling
  - [x] 6.1 Create `build_transition_matrix()` function
    - Extract state transition sequences from historical credit_state data
    - Count transitions between each pair of credit states
    - Normalize rows to create stochastic matrix (each row sums to 1.0)
    - Validate matrix is square with dimensions (n_states, n_states)
    - Compute steady-state distribution using eigenvalue decomposition
    - Return Transition_Matrix object with matrix, state_labels, steady_state, observation_period_days
    - Handle insufficient historical data by using uniform transition probabilities
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_
    - _Implementation: `transition_matrix_implementation.py`_
  
  - [ ]* 6.2 Write property tests for Markov chain
    - **Property P10_TransitionMatrixStochastic: Each row sums to 1.0 ± 0.001**
    - **Property P11_TransitionMatrixSquare: Matrix dimensions are (n_states, n_states)**
    - **Property P12_SteadyStateValid: Steady state probabilities sum to 1.0 ± 0.001**
    - **Validates: Requirements 13.3, 13.1, 13.4**

- [x] 7. Implement demand forecasting component
  - [x] 7.1 Create `forecast_utilization()` function
    - Fit time series model (ARIMA or exponential smoothing) to historical utilization data
    - Incorporate seasonality and trend components
    - Generate 3,000-4,000 Monte Carlo scenarios for demand uncertainty (configurable)
    - Calculate mean and standard deviation of forecasted utilization across scenarios
    - Use cohort-based averages for customers with insufficient history
    - Ensure forecasted utilization values are in range [0.0, 1.0]
    - Support scenario-based forecasting (optimistic, baseline, adverse)
    - Add forecasted_utilization and utilization_std columns to DataFrame
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_
    - _Implementation: Added to `loan_limit_optimization.ipynb` at cell index 21_
  
  - [ ]* 7.2 Write property tests for demand forecasting
    - **Property P16_UtilizationRange: Forecasted utilization in [0.0, 1.0]**
    - **Property P17_MinScenarios: At least 3,000 Monte Carlo scenarios generated**
    - **Property P18_ForecastHorizonValid: Forecast horizon matches configured days**
    - **Validates: Requirements 13.1, 13.4, 13.1**

- [x] 8. Checkpoint - Ensure modeling components work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement loan lifecycle simulation
  - [x] 9.1 Create `simulate_loan_lifecycle()` function
    - Accept customer DataFrame, n_iterations (3,000-4,000, configurable), horizon_days (365), discount_rate (default 12%, configurable)
    - For each customer, run Monte Carlo simulations:
      - Simulate credit state transitions
      - Simulate utilization changes using forecasted distributions
      - Simulate payment behavior (early, on-time, late, default)
      - Calculate revenue (interest + fees) and losses (defaults)
    - Aggregate results: calculate mean, median, and percentiles
    - Calculate net profitability_score = expected_revenue - expected_loss
    - Apply NPV discounting at configurable rate
    - Support cohort-based aggregation for performance optimization
    - Add expected_revenue, expected_loss, profitability_score columns to DataFrame
    - Process customers in batches of 5,000 to manage memory
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7_
    - _Implementation: Added to `loan_limit_optimization.ipynb`_
  
  - [ ]* 9.2 Write property tests for lifecycle simulation
    - **Property P19_MinIterations: At least 3,000 Monte Carlo iterations per customer**
    - **Property P20_ProfitabilityCalculated: All customers have profitability_score**
    - **Property P21_NPVDiscounted: Profitability scores discounted at configurable rate**
    - **Validates: Requirements 13.2, 13.4, 13.4**

- [ ] 10. Implement constraint definition and validation
  - [ ] 10.1 Create Constraint_Set data structure
    - Define dictionary or dataclass with fields: max_portfolio_default_risk, min_profitability_target, max_total_exposure, max_individual_limit, max_debt_to_income_ratio, regulatory_capital_requirement
    - Set default values based on business requirements (e.g., max_portfolio_default_risk=0.05, max_individual_limit=50000)
    - _Requirements: 13.1, 13.2, 13.3_
  
  - [ ] 10.2 Create `validate_constraints()` function
    - Check mathematical feasibility of constraint set
    - Identify conflicting constraints if infeasible
    - Return validation result with error messages
    - _Requirements: 13.4, 13.5_

- [ ] 11. Implement Linear Programming optimization
  - [ ] 11.1 Create `optimize_limits_lp()` function
    - Accept customer DataFrame, Constraint_Set, and optional scenario parameter
    - Formulate LP using PuLP or CVXPY library
    - Define decision variables: increase_i for each customer i
    - Set objective function: Maximize Σ (profitability_score_i * increase_i)
    - Add constraint: Portfolio default risk ≤ max_portfolio_default_risk
    - Add constraint: Total profitability ≥ min_profitability_target
    - Add constraint: Total exposure ≤ max_total_exposure
    - Add constraint: Individual limits ≤ max_individual_limit
    - Add constraint: All increases ≥ 0
    - Solve using CBC or GLPK solver with 300-second timeout
    - Extract optimal increase values and calculate recommended limits
    - Return list of Optimization_Result objects
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_
  
  - [ ]* 11.2 Write property tests for LP optimization
    - **Property P22_ObjectiveMaximized: LP objective value is maximum feasible value**
    - **Property P23_ConstraintsSatisfied: All constraints in Constraint_Set satisfied**
    - **Property P24_NonNegativeIncreases: All limit increases ≥ 0**
    - **Property P25_IndividualLimitRespected: No customer exceeds max_individual_limit**
    - **Property P26_PortfolioRiskRespected: Portfolio default risk ≤ max_portfolio_default_risk**
    - **Property P27_SolverConverged: LP solver status is 'Optimal' or 'Feasible'**
    - **Validates: Requirements 13.1, 13.3, 13.2, 13.2, 13.1, 13.6**

- [ ] 12. Implement scenario-based sensitivity analysis
  - [ ] 12.1 Create `sensitivity_analysis()` function
    - Accept customer DataFrame, Constraint_Set, and list of scenarios
    - Define scenario parameters (GDP growth, unemployment, interest rates, inflation)
    - For each scenario (optimistic, baseline, adverse):
      - Enrich customer data with scenario-specific macro indicators
      - Re-estimate default risk using scenario-adjusted model
      - Re-run lifecycle simulation with scenario parameters
      - Re-optimize LP with scenario-specific inputs
    - Compare objective values and recommended limits across scenarios
    - Calculate scenario-weighted portfolio outcomes
    - Return DataFrame with scenario results
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_
  
  - [ ]* 12.2 Write property tests for sensitivity analysis
    - **Property P32_SensitivityScenariosComplete: All scenarios executed successfully**
    - **Property P33_ObjectiveRangeReported: Sensitivity analysis reports min/max objectives**
    - **Validates: Requirements 13.4, 13.5, 13.6**

- [ ] 13. Checkpoint - Ensure optimization engines work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Implement solution validation
  - [ ] 14.1 Create `validate_solution()` function
    - Accept optimization results and Constraint_Set
    - Calculate total portfolio default risk from results
    - Calculate total profitability from results
    - Calculate total exposure from results
    - Verify all individual limits within bounds
    - Check all constraints satisfied with configurable tolerances
    - Return detailed validation results including any violations
    - _Requirements: 13.1, 13.2_

- [ ] 15. Implement results reporting and visualization
  - [ ] 15.1 Create `generate_summary_report()` function
    - Accept optimization results list
    - Calculate total_customers, customers_with_increases, total_incremental_exposure
    - Calculate expected_incremental_profit, portfolio_default_risk, avg_increase_amount
    - Return dictionary with all summary metrics
    - _Requirements: 13.1_
  
  - [ ] 15.2 Create `create_visualizations()` function
    - Generate credit state distribution bar chart
    - Generate default risk distribution histogram
    - Generate current vs recommended limits grouped bar chart by credit state
    - Generate risk-return scatter plot (default_risk vs profitability_score)
    - Generate optimization objective convergence line chart
    - Generate limit increase distribution histogram
    - Generate sensitivity analysis results box plot
    - Generate macroeconomic indicators time series
    - Generate portfolio exposure before/after stacked bar chart
    - Use matplotlib and seaborn for all visualizations
    - _Requirements: 13.4, 13.5, 13.3, 13.4_
  
  - [ ] 15.3 Create `export_results()` function
    - Accept optimization results and output file path
    - Create DataFrame with columns: customer_id, current_limit, recommended_limit, limit_increase, credit_state, default_risk, profitability_score
    - Export to CSV format
    - _Requirements: 13.2, 13.5_
  
  - [ ]* 15.4 Write property tests for reporting
    - **Property P34_SummaryReportComplete: Summary report contains all required fields**
    - **Property P35_CustomerTableComplete: Customer table has all required columns**
    - **Property P36_MinVisualizationsGenerated: At least 10 visualizations created**
    - **Property P37_ResultsExported: CSV file created with optimization results**
    - **Validates: Requirements 13.1, 13.2, 13.5, 13.5**

- [ ] 16. Implement performance monitoring and optimization
  - [ ] 16.1 Add performance tracking
    - Add timing decorators or context managers to measure execution time of major functions
    - Add memory profiling to track peak memory usage
    - Add progress indicators for long-running operations (data loading, simulation, optimization)
    - Log performance metrics to identify bottlenecks
    - _Requirements: 13.1, 13.3, 13.4, 13.5_
  
  - [ ] 16.2 Optimize computational performance
    - Ensure vectorized operations used for numerical computations (numpy/pandas)
    - Implement batch processing for customers (batches of 5,000)
    - Use appropriate data types (float32 vs float64) to reduce memory
    - Delete intermediate DataFrames after use
    - _Requirements: 13.2_
  
  - [ ]* 16.3 Write property tests for performance
    - **Property P38_ExecutionTime: End-to-end execution completes within 30 minutes**
    - **Property P39_MemoryLimit: Peak memory usage ≤ 8GB**
    - **Property P40_ProgressIndicators: Progress messages displayed during long operations**
    - **Validates: Requirements 13.1, 13.4, 13.5**

- [ ] 17. Add documentation and code quality improvements
  - [ ] 17.1 Add comprehensive documentation
    - Add docstrings to all functions with parameters, return values, and purpose
    - Add markdown cells documenting each major section: introduction, methodology, data loading, modeling, optimization, results
    - Add inline comments explaining complex algorithmic logic
    - Ensure variable names follow Python naming conventions (snake_case)
    - _Requirements: 13.2, 13.1, 13.2, 13.3, 13.4_
  
  - [ ]* 17.2 Write property tests for code quality
    - **Property P41_FunctionsDocumented: All functions have docstrings**
    - **Property P42_VariableNamesDescriptive: Variables follow Python naming conventions**
    - **Property P43_RequirementsListed: Notebook includes requirements cell with versions**
    - **Property P44_NotebookExecutable: Notebook runs without errors using "Run All Cells"**
    - **Validates: Requirements 13.1, 13.2, 13.5, 13.6**

- [ ] 18. Integration and end-to-end testing
  - [ ] 18.1 Create main execution pipeline
    - Wire all components together in logical execution order
    - Load and preprocess data
    - Fetch and enrich with macro data (including scenarios)
    - Classify credit states and estimate default risk (gradient boosting)
    - Build transition matrix (optional)
    - Forecast utilization
    - Simulate loan lifecycle (3,000-4,000 iterations)
    - Define constraints
    - Run LP optimization
    - Run scenario-based sensitivity analysis
    - Validate solution
    - Generate summary report
    - Create visualizations
    - Export results to CSV
    - _Requirements: 13.3, 13.6_
  
  - [ ]* 18.2 Write integration tests
    - Test end-to-end pipeline execution with sample data
    - Verify all components integrate correctly
    - Verify data flows correctly between components
    - Test error handling and edge cases
    - _Requirements: 13.6_

- [ ] 19. Final checkpoint - Ensure complete system works end-to-end
  - Run "Run All Cells" in Jupyter Notebook
  - Verify all visualizations generated
  - Verify summary report produced
  - Verify CSV export created
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties from the design document
- Unit tests and integration tests validate specific examples and edge cases
- The system is implemented as a single Jupyter Notebook for ease of presentation and modification
- All optimization and simulation components use configurable parameters for flexibility
- Performance optimization focuses on vectorization and batch processing for 30,000 customers
- The implementation uses standard Python data science libraries (pandas, numpy, scipy, scikit-learn)
- Gradient boosting uses XGBoost or LightGBM for superior predictive accuracy
- LP optimization uses PuLP or CVXPY for formulation
- Macroeconomic data requires FRED API key (free registration at https://fred.stlouisfed.org/docs/api/api_key.html)

## Configuration Parameters

All key parameters are configurable via environment variables or function parameters for flexibility:

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

### Performance Targets

- **Execution Time**: End-to-end processing of 30,000 customers within 30 minutes
- **Memory Usage**: Peak memory usage below 8GB
- **Simulation Iterations**: 3,000-4,000 per customer (configurable)
- **Cohort Aggregation**: Automatic fallback when memory exceeds limits

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1"]
    },
    {
      "id": 1,
      "tasks": ["2.1", "3.1"]
    },
    {
      "id": 2,
      "tasks": ["2.2", "2.3", "3.2"]
    },
    {
      "id": 3,
      "tasks": ["3.3", "5.1"]
    },
    {
      "id": 4,
      "tasks": ["5.2", "6.1"]
    },
    {
      "id": 5,
      "tasks": ["5.3", "5.4", "6.2", "7.1"]
    },
    {
      "id": 6,
      "tasks": ["7.2", "9.1"]
    },
    {
      "id": 7,
      "tasks": ["9.2", "10.1"]
    },
    {
      "id": 8,
      "tasks": ["10.2", "11.1"]
    },
    {
      "id": 9,
      "tasks": ["11.2", "12.1"]
    },
    {
      "id": 10,
      "tasks": ["12.2", "14.1"]
    },
    {
      "id": 11,
      "tasks": ["14.2", "15.1"]
    },
    {
      "id": 12,
      "tasks": ["14.3", "15.2", "15.3"]
    },
    {
      "id": 13,
      "tasks": ["15.4", "16.1"]
    },
    {
      "id": 14,
      "tasks": ["16.2", "17.1"]
    },
    {
      "id": 15,
      "tasks": ["16.3", "17.2", "18.1"]
    },
    {
      "id": 16,
      "tasks": ["18.2"]
    }
  ]
}
```

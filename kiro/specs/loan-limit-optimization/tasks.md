# Implementation Plan: Loan Limit Optimization System

## Overview

This implementation plan breaks down the Loan Limit Optimization System into discrete coding tasks. The system is implemented as a single Jupyter Notebook that processes 30,000 customer records, enriches them with macroeconomic data, models credit risk and state transitions, forecasts demand, simulates loan lifecycles, and optimizes loan limits using Linear Programming and Markov Decision Process techniques.

## Tasks

- [ ] 1. Set up Jupyter Notebook structure and dependencies
  - Create `loan_limit_optimization.ipynb` notebook file
  - Add markdown introduction cell explaining the system purpose and methodology
  - Create requirements cell listing all Python packages with versions: pandas, numpy, scipy, scikit-learn, PuLP (or CVXPY), fredapi, requests, requests-cache, matplotlib, seaborn, jupyter
  - Add import statements for all required libraries
  - Configure matplotlib/seaborn visualization settings
  - Set random seeds for reproducibility
  - _Requirements: 12.1, 12.2, 12.3, 15.5_

- [ ] 2. Implement data loading and preprocessing component
  - [x] 2.1 Create `load_and_preprocess_data()` function
    - Implement CSV loading using pandas with error handling for missing files
    - Validate required columns exist: customer_id, initial_loan, days_since_last_loan, on_time_payments_pct, num_increases_2023, total_profit_contribution
    - Implement missing value detection and logging
    - Implement median/mode imputation for missing values
    - Derive credit_score proxy and utilization_rate features
    - Apply StandardScaler normalization to numerical features
    - Return validated DataFrame with exactly 30,000 records
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ] 2.2 Write property test for data loading
    - **Property P1_LoadExactCount: After loading, customer count equals 30,000**
    - **Validates: Requirements 1.1**
  
  - [ ] 2.3 Write property test for data preprocessing
    - **Property P2_NoMissingRequired: All required fields present after preprocessing**
    - **Property P3_NormalizedRange: Normalized features in range [-3, 3]**
    - **Validates: Requirements 1.3, 1.5**

- [ ] 3. Implement macroeconomic data enrichment component
  - [x] 3.1 Create `fetch_macro_data()` function
    - Initialize FRED API client with API key from environment variable
    - Fetch GDP growth rate (series: GDPC1) for 2023
    - Fetch unemployment rate (series: UNRATE) for 2023
    - Fetch federal funds rate (series: FEDFUNDS) for 2023
    - Fetch CPI (series: CPIAUCSL) for 2023
    - Implement retry logic with exponential backoff (3 attempts: 1s, 2s, 4s)
    - Cache results to local JSON file
    - Return dictionary with keys: gdp_growth, unemployment, fed_rate, cpi
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [x] 3.2 Create `enrich_customer_data()` function
    - Accept customer DataFrame and macro_data dictionary
    - Add macro indicator columns to each customer record
    - Validate all customers have macro data after merge
    - _Requirements: 2.5_
  
  - [ ] 3.3 Write property tests for macro data enrichment
    - **Property P4_MacroIndicatorsPresent: All 4 macro indicators fetched successfully**
    - **Property P5_MacroDataCached: Cached data file created after first fetch**
    - **Property P6_MacroMergeComplete: All customers have macro data after merge**
    - **Validates: Requirements 2.2, 2.4, 2.5**

- [ ] 4. Checkpoint - Ensure data loading and enrichment work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement credit state classification and risk model
  - [x] 5.1 Create `classify_credit_states()` function
    - Calculate composite credit score from on_time_payments_pct and other factors
    - Define 4 credit state boundaries using quantile-based thresholds
    - Assign each customer to exactly one credit state (Excellent, Good, Fair, Poor)
    - Flag customers with insufficient data and assign default state
    - Add credit_state column to DataFrame
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [x] 5.2 Create `estimate_default_risk()` function
    - Build logistic regression model using scikit-learn
    - Use features: credit_score, utilization_rate, credit_state (encoded), macro indicators
    - Train model on historical data or use domain-based risk rates
    - Predict default probability for each customer
    - Clip probabilities to [0.0, 1.0]
    - Flag high-risk customers (default_risk > configurable threshold)
    - Add default_risk column to DataFrame
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [ ] 5.3 Write property tests for credit state classification
    - **Property P7_StateCountValid: Number of credit states equals configured n_states**
    - **Property P8_AllCustomersClassified: Every customer assigned exactly one credit state**
    - **Property P9_StateDistributionNonEmpty: Each credit state has at least one customer**
    - **Validates: Requirements 3.1, 3.3**
  
  - [ ] 5.4 Write property tests for default risk estimation
    - **Property P13_DefaultRiskRange: All default_risk values in [0.0, 1.0]**
    - **Property P14_HighRiskFlagged: Customers with default_risk > threshold are flagged**
    - **Property P15_RiskIncorporatesMacro: Default risk calculation uses macro indicators**
    - **Validates: Requirements 5.2, 5.3, 5.4**

- [ ] 6. Implement Markov chain transition modeling
  - [x] 6.1 Create `build_transition_matrix()` function
    - Extract state transition sequences from historical credit_state data
    - Count transitions between each pair of credit states
    - Normalize rows to create stochastic matrix (each row sums to 1.0)
    - Validate matrix is square with dimensions (n_states, n_states)
    - Compute steady-state distribution using eigenvalue decomposition
    - Return Transition_Matrix object with matrix, state_labels, steady_state, observation_period_days
    - Handle insufficient historical data by using uniform transition probabilities
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [ ] 6.2 Write property tests for Markov chain
    - **Property P10_TransitionMatrixStochastic: Each row sums to 1.0 ± 0.001**
    - **Property P11_TransitionMatrixSquare: Matrix dimensions are (n_states, n_states)**
    - **Property P12_SteadyStateValid: Steady state probabilities sum to 1.0 ± 0.001**
    - **Validates: Requirements 4.3, 4.1, 4.4**

- [ ] 7. Implement demand forecasting component
  - [x] 7.1 Create `forecast_utilization()` function
    - Fit time series model (ARIMA or exponential smoothing) to historical utilization data
    - Incorporate seasonality and trend components
    - Generate at least 1,000 Monte Carlo scenarios for demand uncertainty
    - Calculate mean and standard deviation of forecasted utilization across scenarios
    - Use cohort-based averages for customers with insufficient history
    - Ensure forecasted utilization values are in range [0.0, 1.0]
    - Add forecasted_utilization and utilization_std columns to DataFrame
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [ ] 7.2 Write property tests for demand forecasting
    - **Property P16_UtilizationRange: Forecasted utilization in [0.0, 1.0]**
    - **Property P17_MinScenarios: At least 1,000 Monte Carlo scenarios generated**
    - **Property P18_ForecastHorizonValid: Forecast horizon matches configured days**
    - **Validates: Requirements 6.1, 6.4, 6.1**

- [ ] 8. Checkpoint - Ensure modeling components work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement loan lifecycle simulation
  - [x] 9.1 Create `simulate_loan_lifecycle()` function
    - Accept customer DataFrame, transition_matrix, n_iterations (minimum 10,000), horizon_days (365)
    - For each customer, run Monte Carlo simulations:
      - Simulate credit state transitions using transition_matrix
      - Simulate utilization changes using forecasted distributions
      - Simulate payment behavior (early, on-time, late, default)
      - Calculate revenue (interest at 19% + fees) and losses (defaults)
    - Aggregate results: calculate mean, median, and percentiles
    - Calculate net profitability_score = expected_revenue - expected_loss
    - Apply NPV discounting at 19% annual rate
    - Add expected_revenue, expected_loss, profitability_score columns to DataFrame
    - Process customers in batches of 5,000 to manage memory
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ] 9.2 Write property tests for lifecycle simulation
    - **Property P19_MinIterations: At least 10,000 Monte Carlo iterations per customer**
    - **Property P20_ProfitabilityCalculated: All customers have profitability_score**
    - **Property P21_NPVDiscounted: Profitability scores discounted at 19% annual rate**
    - **Validates: Requirements 7.2, 7.4, 7.4**

- [ ] 10. Implement constraint definition and validation
  - [x] 10.1 Create Constraint_Set data structure
    - Define dictionary or dataclass with fields: max_portfolio_default_risk, min_profitability_target, max_total_exposure, max_individual_limit, max_debt_to_income_ratio, regulatory_capital_requirement
    - Set default values based on business requirements (e.g., max_portfolio_default_risk=0.05, max_individual_limit=50000)
    - _Requirements: 8.1, 8.2, 8.3_
    - _Status: Completed - defined in notebook as dictionary with default values_
  
  - [x] 10.2 Create `validate_constraints()` function
    - Check mathematical feasibility of constraint set
    - Identify conflicting constraints if infeasible
    - Return validation result with error messages
    - _Requirements: 8.4, 8.5_
    - _Status: Completed - implemented in notebook_

- [ ] 11. Implement Linear Programming optimization
  - [ ] 11.1 Create `optimize_limits_lp()` function
    - Accept customer DataFrame and Constraint_Set
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
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_
    - _Status: Missing - needs implementation_
  
  - [ ] 11.2 Write property tests for LP optimization
    - **Property P22_ObjectiveMaximized: LP objective value is maximum feasible value**
    - **Property P23_ConstraintsSatisfied: All constraints in Constraint_Set satisfied**
    - **Property P24_NonNegativeIncreases: All limit increases ≥ 0**
    - **Property P25_IndividualLimitRespected: No customer exceeds max_individual_limit**
    - **Property P26_PortfolioRiskRespected: Portfolio default risk ≤ max_portfolio_default_risk**
    - **Property P27_SolverConverged: LP solver status is 'Optimal' or 'Feasible'**
    - **Validates: Requirements 9.1, 9.3, 9.2, 8.2, 8.1, 9.6**

- [ ] 12. Implement Markov Decision Process optimization
  - [ ] 12.1 Create `optimize_limits_mdp()` function
    - Accept customer DataFrame, transition_matrix, Constraint_Set, max_iterations (1000)
    - Define state space: credit states from transition_matrix
    - Define action space: discretized loan limit adjustment amounts
    - Define reward function: R(s, a) = profitability_score(s, a) - penalty * default_risk(s, a)
    - Initialize value function V(s) = 0 for all states
    - Implement value iteration algorithm:
      - For each state s and action a: Calculate Q(s, a) = R(s, a) + γ * Σ P(s'|s, a) * V(s')
      - Update V(s) = max_a Q(s, a)
      - Update policy π(s) = argmax_a Q(s, a)
    - Iterate until convergence or max_iterations reached
    - Return optimal policy mapping states to actions
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_
    - _Status: Missing - needs implementation_
  
  - [ ] 12.2 Write property tests for MDP optimization
    - **Property P28_PolicyConverged: MDP policy converges within max_iterations**
    - **Property P29_PolicyComplete: Policy defined for all credit states**
    - **Property P30_RewardFunctionValid: Reward function incorporates profitability and risk**
    - **Validates: Requirements 10.6, 10.5, 10.2**

- [ ] 13. Checkpoint - Ensure optimization engines work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Implement solution validation and sensitivity analysis
  - [ ] 14.1 Create `validate_solution()` function
    - Accept optimization results and Constraint_Set
    - Calculate total portfolio default risk from results
    - Calculate total profitability from results
    - Calculate total exposure from results
    - Verify all individual limits within bounds
    - Check all constraints satisfied
    - Return boolean indicating constraint satisfaction
    - _Requirements: 11.1, 11.2_
    - _Status: Missing - needs implementation_
  
  - [ ] 14.2 Create `sensitivity_analysis()` function
    - Accept customer DataFrame, base Constraint_Set, n_scenarios (minimum 5)
    - Define sensitivity scenarios:
      - Scenario 1: Increase risk tolerance by 20%
      - Scenario 2: Decrease risk tolerance by 20%
      - Scenario 3: Optimistic macro conditions (low unemployment)
      - Scenario 4: Pessimistic macro conditions (high unemployment)
      - Scenario 5: Baseline
    - Re-optimize for each scenario using optimize_limits_lp()
    - Compare objective values and recommended limits across scenarios
    - Return DataFrame with scenario results
    - _Requirements: 11.3, 11.4, 11.5_
    - _Status: Missing - needs implementation_
  
  - [ ] 14.3 Write property tests for validation and sensitivity
    - **Property P31_SolutionValid: validate_solution returns True for optimal solution**
    - **Property P32_SensitivityScenariosComplete: All n_scenarios executed successfully**
    - **Property P33_ObjectiveRangeReported: Sensitivity analysis reports min/max objectives**
    - **Validates: Requirements 11.1, 11.4, 11.5**

- [ ] 15. Implement results reporting and visualization
  - [x] 15.1 Create `generate_summary_report()` function
    - Accept optimization results list
    - Calculate total_customers, customers_with_increases, total_incremental_exposure
    - Calculate expected_incremental_profit, portfolio_default_risk, avg_increase_amount
    - Return dictionary with all summary metrics
    - _Requirements: 13.1_
    - _Status: Completed - implemented in notebook_
  
  - [x] 15.2 Create `create_visualizations()` function
    - Generate credit state distribution bar chart
    - Generate transition probability heatmap
    - Generate default risk distribution histogram
    - Generate current vs recommended limits grouped bar chart by credit state
    - Generate risk-return scatter plot (default_risk vs profitability_score)
    - Generate optimization objective convergence line chart
    - Generate limit increase distribution histogram
    - Generate sensitivity analysis results box plot
    - Generate macroeconomic indicators time series
    - Generate portfolio exposure before/after stacked bar chart
    - Use matplotlib and seaborn for all visualizations
    - _Requirements: 12.4, 12.5, 13.3, 13.4_
    - _Status: Completed - implemented in notebook_
  
  - [x] 15.3 Create `export_results()` function
    - Accept optimization results and output file path
    - Create DataFrame with columns: customer_id, current_limit, recommended_limit, limit_increase, credit_state, default_risk, profitability_score
    - Export to CSV format
    - _Requirements: 13.2, 13.5_
    - _Status: Completed - implemented in notebook_
  
  - [ ] 15.4 Write property tests for reporting
    - **Property P34_SummaryReportComplete: Summary report contains all required fields**
    - **Property P35_CustomerTableComplete: Customer table has all required columns**
    - **Property P36_MinVisualizationsGenerated: At least 10 visualizations created**
    - **Property P37_ResultsExported: CSV file created with optimization results**
    - **Validates: Requirements 13.1, 13.2, 12.5, 13.5**

- [ ] 16. Implement performance monitoring and optimization
  - [x] 16.1 Add performance tracking
    - Add timing decorators or context managers to measure execution time of major functions
    - Add memory profiling to track peak memory usage
    - Add progress indicators for long-running operations (data loading, simulation, optimization)
    - Log performance metrics to identify bottlenecks
    - _Requirements: 14.1, 14.3, 14.4, 14.5_
    - _Status: Completed - implemented in notebook_
  
  - [x] 16.2 Optimize computational performance
    - Ensure vectorized operations used for numerical computations (numpy/pandas)
    - Implement batch processing for customers (batches of 5,000)
    - Use appropriate data types (float32 vs float64) to reduce memory
    - Delete intermediate DataFrames after use
    - _Requirements: 14.2_
    - _Status: Completed - implemented in notebook_
  
  - [ ] 16.3 Write property tests for performance
    - **Property P38_ExecutionTime: End-to-end execution completes within 30 minutes**
    - **Property P39_MemoryLimit: Peak memory usage ≤ 8GB**
    - **Property P40_ProgressIndicators: Progress messages displayed during long operations**
    - **Validates: Requirements 14.1, 14.4, 14.5**

- [ ] 17. Add documentation and code quality improvements
  - [x] 17.1 Add comprehensive documentation
    - Add docstrings to all functions with parameters, return values, and purpose
    - Add markdown cells documenting each major section: introduction, methodology, data loading, modeling, optimization, results
    - Add inline comments explaining complex algorithmic logic
    - Ensure variable names follow Python naming conventions (snake_case)
    - _Requirements: 12.2, 15.1, 15.2, 15.3, 15.4_
    - _Status: Completed - implemented in notebook_
  
  - [ ] 17.2 Write property tests for code quality
    - **Property P41_FunctionsDocumented: All functions have docstrings**
    - **Property P42_VariableNamesDescriptive: Variables follow Python naming conventions**
    - **Property P43_RequirementsListed: Notebook includes requirements cell with versions**
    - **Property P44_NotebookExecutable: Notebook runs without errors using "Run All Cells"**
    - **Validates: Requirements 15.1, 15.2, 15.5, 12.6**

- [ ] 18. Integration and end-to-end testing
  - [ ] 18.1 Create main execution pipeline
    - Wire all components together in logical execution order
    - Load and preprocess data
    - Fetch and enrich with macro data
    - Classify credit states and estimate default risk
    - Build transition matrix
    - Forecast utilization
    - Simulate loan lifecycle
    - Define constraints
    - Run LP optimization
    - Run MDP optimization (optional)
    - Validate solution
    - Perform sensitivity analysis
    - Generate summary report
    - Create visualizations
    - Export results to CSV
    - _Requirements: 12.3, 12.6_
    - _Status: Missing - needs implementation_
  
  - [ ] 18.2 Write integration tests
    - Test end-to-end pipeline execution with sample data
    - Verify all components integrate correctly
    - Verify data flows correctly between components
    - Test error handling and edge cases
    - _Requirements: 12.6_

- [ ] 19. Final checkpoint - Ensure complete system works end-to-end
  - Run "Run All Cells" in Jupyter Notebook
  - Verify all visualizations generated
  - Verify summary report produced
  - Verify CSV export created
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties from the design document
- Unit tests and integration tests validate specific examples and edge cases
- The system is implemented as a single Jupyter Notebook for ease of presentation and modification
- All optimization and simulation components use configurable parameters for flexibility
- Performance optimization focuses on vectorization and batch processing for 30,000 customers
- The implementation uses standard Python data science libraries (pandas, numpy, scipy, scikit-learn)
- Optimization uses either PuLP or CVXPY for linear programming formulation
- Macroeconomic data requires FRED API key (free registration at https://fred.stlouisfed.org/docs/api/api_key.html)

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

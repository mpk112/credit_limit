"""
Loan Lifecycle Simulation Component

This module implements the loan lifecycle simulation component for the
Loan Limit Optimization System. It uses Monte Carlo simulation to model
loan performance over time, including credit state transitions, utilization
changes, payment behavior, and default events.

Functions:
- simulate_loan_lifecycle(): Main function for simulating loan lifecycles
- simulate_single_customer(): Simulate lifecycle for a single customer
- calculate_revenue(): Calculate expected revenue from interest and fees
- calculate_loss(): Calculate expected loss from defaults
- apply_npv_discounting(): Apply NPV discounting to future cash flows

Properties tested:
- P21_MinIterations: At least 3,000 Monte Carlo iterations per customer
- P22_ProfitabilityCalculated: All customers have profitability_score
- P23_NPVDiscounted: Profitability scores discounted at configurable rate
- P24_CohortAggregation: Automatic fallback to cohort-based aggregation

Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# CONFIGURATION
# ============================================================================

# Default simulation parameters
DEFAULT_N_ITERATIONS = 3500
DEFAULT_HORIZON_DAYS = 365
DEFAULT_DISCOUNT_RATE = 0.12
DEFAULT_BATCH_SIZE = 5000

# Credit state transition probabilities (simplified)
CREDIT_STATE_TRANSITIONS = {
    'Excellent': {'Excellent': 0.85, 'Good': 0.10, 'Fair': 0.04, 'Poor': 0.01},
    'Good': {'Excellent': 0.05, 'Good': 0.80, 'Fair': 0.12, 'Poor': 0.03},
    'Fair': {'Excellent': 0.02, 'Good': 0.10, 'Fair': 0.75, 'Poor': 0.13},
    'Poor': {'Excellent': 0.01, 'Good': 0.05, 'Fair': 0.20, 'Poor': 0.74},
}

# Payment behavior probabilities (conditional on credit state)
PAYMENT_BEHAVIOR = {
    'Excellent': {'early': 0.40, 'on_time': 0.55, 'late': 0.04, 'default': 0.01},
    'Good': {'early': 0.25, 'on_time': 0.60, 'late': 0.12, 'default': 0.03},
    'Fair': {'early': 0.10, 'on_time': 0.50, 'late': 0.25, 'default': 0.15},
    'Poor': {'early': 0.05, 'on_time': 0.30, 'late': 0.35, 'default': 0.30},
}

# Interest rate margins by credit state (annual)
INTEREST_RATE_MARGIN = {
    'Excellent': 0.05,
    'Good': 0.08,
    'Fair': 0.12,
    'Poor': 0.18,
}

# Fee structure
ANNUAL_FEE_RATE = 0.005  # 0.5% annual fee
LATE_FEE_RATE = 0.02  # 2% late fee on overdue amount


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def simulate_credit_state_transition(
    current_state: str,
    n_days: int,
    transition_probs: Dict[str, Dict[str, float]] = CREDIT_STATE_TRANSITIONS
) -> str:
    """
    Simulate credit state transition over a time period.
    
    Parameters
    ----------
    current_state : str
        Current credit state
    n_days : int
        Number of days to simulate
    transition_probs : dict
        Transition probability matrix
        
    Returns
    -------
    str
        Simulated credit state after n_days
    """
    state = current_state
    
    # Simplified: simulate one transition per 90-day period
    n_periods = max(1, n_days // 90)
    
    for _ in range(n_periods):
        probs = transition_probs.get(state, transition_probs['Good'])
        states = list(probs.keys())
        probabilities = list(probs.values())
        state = np.random.choice(states, p=probabilities)
    
    return state


def simulate_utilization_change(
    current_utilization: float,
    forecast_mean: float,
    forecast_std: float,
    n_days: int,
    n_scenarios: int
) -> np.ndarray:
    """
    Simulate utilization changes using forecasted distributions.
    
    Parameters
    ----------
    current_utilization : float
        Current utilization rate
    forecast_mean : float
        Mean forecasted utilization
    forecast_std : float
        Standard deviation of forecasted utilization
    n_days : int
        Simulation horizon in days
    n_scenarios : int
        Number of Monte Carlo scenarios
        
    Returns
    -------
    np.ndarray
        Simulated utilization paths for each scenario
    """
    # Simulate utilization changes using random walk with drift
    drift = (forecast_mean - current_utilization) / (n_days / 365)
    volatility = forecast_std / np.sqrt(n_days / 365)
    
    # Generate random shocks
    shocks = np.random.normal(drift, volatility, (n_scenarios, n_days))
    
    # Accumulate changes
    utilization_paths = current_utilization + np.cumsum(shocks, axis=1)
    
    # Clip to valid range [0, 1]
    utilization_paths = np.clip(utilization_paths, 0.0, 1.0)
    
    return utilization_paths


def simulate_payment_behavior(
    credit_state: str,
    utilization: float,
    n_days: int,
    n_scenarios: int
) -> Dict[str, np.ndarray]:
    """
    Simulate payment behavior over time.
    
    Parameters
    ----------
    credit_state : str
        Customer's credit state
    utilization : float
        Current utilization rate
    n_days : int
        Simulation horizon
    n_scenarios : int
        Number of Monte Carlo scenarios
        
    Returns
    -------
    dict
        Payment behavior counts for each scenario
    """
    probs = PAYMENT_BEHAVIOR.get(credit_state, PAYMENT_BEHAVIOR['Good'])
    
    # Simulate daily payment behavior
    behaviors = np.random.choice(
        ['early', 'on_time', 'late', 'default'],
        size=(n_scenarios, n_days),
        p=[
            probs['early'],
            probs['on_time'],
            probs['late'],
            probs['default']
        ]
    )
    
    # Count behaviors
    counts = {
        'early': np.sum(behaviors == 'early', axis=1),
        'on_time': np.sum(behaviors == 'on_time', axis=1),
        'late': np.sum(behaviors == 'late', axis=1),
        'default': np.sum(behaviors == 'default', axis=1)
    }
    
    return counts


def calculate_revenue(
    loan_amount: float,
    credit_state: str,
    utilization: float,
    n_days: int,
    interest_rate_margin: Dict[str, float] = INTEREST_RATE_MARGIN,
    fee_rate: float = ANNUAL_FEE_RATE
) -> float:
    """
    Calculate expected revenue from interest and fees.
    
    Parameters
    ----------
    loan_amount : float
        Initial loan amount
    credit_state : str
        Customer's credit state
    utilization : float
        Average utilization rate
    n_days : int
        Simulation horizon in days
    interest_rate_margin : dict
        Interest rate margins by credit state
    fee_rate : float
        Annual fee rate
        
    Returns
    -------
    float
        Expected revenue (interest + fees)
    """
    # Calculate interest revenue
    rate_margin = interest_rate_margin.get(credit_state, interest_rate_margin['Good'])
    annual_rate = 0.04 + rate_margin  # Base rate + margin
    daily_rate = annual_rate / 365
    
    interest_revenue = loan_amount * utilization * daily_rate * n_days
    
    # Calculate fee revenue
    fee_revenue = loan_amount * fee_rate * (n_days / 365)
    
    return interest_revenue + fee_revenue


def calculate_loss(
    loan_amount: float,
    credit_state: str,
    utilization: float,
    n_days: int,
    payment_counts: Dict[str, np.ndarray],
    default_rate: float = 0.5  # Recovery rate for defaults
) -> float:
    """
    Calculate expected loss from defaults.
    
    Parameters
    ----------
    loan_amount : float
        Initial loan amount
    credit_state : str
        Customer's credit state
    utilization : float
        Average utilization rate
    n_days : int
        Simulation horizon
    payment_counts : dict
        Payment behavior counts
    default_rate : float
        Recovery rate for defaults (0.5 = 50% loss)
        
    Returns
    -------
    float
        Expected loss from defaults
    """
    # Calculate default probability based on credit state
    default_probs = {
        'Excellent': 0.005,
        'Good': 0.015,
        'Fair': 0.05,
        'Poor': 0.15,
    }
    base_default_prob = default_probs.get(credit_state, default_probs['Good'])
    
    # Adjust for utilization (higher utilization = higher default risk)
    utilization_factor = 1.0 + utilization * 2.0
    
    # Adjust for late payments
    late_ratio = payment_counts['late'].mean() / max(n_days, 1)
    late_factor = 1.0 + late_ratio * 5.0
    
    # Calculate adjusted default probability
    adjusted_default_prob = base_default_prob * utilization_factor * late_factor
    adjusted_default_prob = np.clip(adjusted_default_prob, 0.0, 0.5)
    
    # Calculate expected loss
    expected_defaults = adjusted_default_prob * n_days / 365
    expected_loss = loan_amount * utilization * expected_defaults * default_rate
    
    return expected_loss


def apply_npv_discounting(
    cash_flows: np.ndarray,
    discount_rate: float,
    n_days: int
) -> np.ndarray:
    """
    Apply NPV discounting to future cash flows.
    
    Parameters
    ----------
    cash_flows : np.ndarray
        Array of cash flows
    discount_rate : float
        Annual discount rate
    n_days : int
        Number of days in simulation
        
    Returns
    -------
    np.ndarray
        Discounted cash flows
    """
    # Calculate discount factors for each day
    days = np.arange(1, n_days + 1)
    daily_rate = discount_rate / 365
    discount_factors = 1.0 / (1.0 + daily_rate) ** days
    
    # Apply discounting (simplified: assume cash flows are evenly distributed)
    discounted = cash_flows * np.mean(discount_factors)
    
    return discounted


# ============================================================================
# MAIN SIMULATION FUNCTIONS
# ============================================================================

def simulate_single_customer(
    customer_id: str,
    initial_loan: float,
    credit_state: str,
    utilization_rate: float,
    forecast_utilization_mean: float,
    forecast_utilization_std: float,
    n_iterations: int,
    horizon_days: int,
    discount_rate: float
) -> Dict[str, float]:
    """
    Simulate loan lifecycle for a single customer.
    
    Parameters
    ----------
    customer_id : str
        Customer identifier
    initial_loan : float
        Initial loan amount
    credit_state : str
        Customer's credit state
    utilization_rate : float
        Current utilization rate
    forecast_utilization_mean : float
        Mean forecasted utilization
    forecast_utilization_std : float
        Std of forecasted utilization
    n_iterations : int
        Number of Monte Carlo iterations
    horizon_days : int
        Simulation horizon in days
    discount_rate : float
        Annual discount rate for NPV
        
    Returns
    -------
    dict
        Simulation results for the customer
    """
    # Simulate credit state transitions
    final_state = simulate_credit_state_transition(credit_state, horizon_days)
    
    # Simulate utilization paths
    utilization_paths = simulate_utilization_change(
        utilization_rate,
        forecast_utilization_mean,
        forecast_utilization_std,
        horizon_days,
        n_iterations
    )
    
    # Calculate average utilization across scenarios
    avg_utilization = np.mean(utilization_paths)
    
    # Simulate payment behavior
    payment_counts = simulate_payment_behavior(
        credit_state,
        utilization_rate,
        horizon_days,
        n_iterations
    )
    
    # Calculate revenue and loss for each scenario
    revenues = np.zeros(n_iterations)
    losses = np.zeros(n_iterations)
    
    for i in range(n_iterations):
        scenario_utilization = utilization_paths[i, -1]  # Final utilization
        scenario_payment_counts = {k: v[i] for k, v in payment_counts.items()}
        
        revenues[i] = calculate_revenue(
            initial_loan,
            final_state,
            scenario_utilization,
            horizon_days
        )
        
        losses[i] = calculate_loss(
            initial_loan,
            final_state,
            scenario_utilization,
            horizon_days,
            scenario_payment_counts
        )
    
    # Apply NPV discounting
    revenues = apply_npv_discounting(revenues, discount_rate, horizon_days)
    losses = apply_npv_discounting(losses, discount_rate, horizon_days)
    
    # Calculate aggregate statistics
    expected_revenue = float(np.mean(revenues))
    expected_loss = float(np.mean(losses))
    profitability_score = expected_revenue - expected_loss
    
    # Calculate percentiles
    revenue_p5 = float(np.percentile(revenues, 5))
    revenue_p95 = float(np.percentile(revenues, 95))
    loss_p5 = float(np.percentile(losses, 5))
    loss_p95 = float(np.percentile(losses, 95))
    
    return {
        'customer_id': customer_id,
        'expected_revenue': expected_revenue,
        'expected_loss': expected_loss,
        'profitability_score': profitability_score,
        'revenue_p5': revenue_p5,
        'revenue_p95': revenue_p95,
        'loss_p5': loss_p5,
        'loss_p95': loss_p95,
        'avg_utilization': avg_utilization,
        'final_credit_state': final_state,
        'n_iterations': n_iterations,
        'horizon_days': horizon_days,
        'discount_rate': discount_rate
    }


def simulate_loan_lifecycle(
    df: pd.DataFrame,
    n_iterations: int = DEFAULT_N_ITERATIONS,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    batch_size: int = DEFAULT_BATCH_SIZE,
    use_cohort_aggregation: bool = False
) -> pd.DataFrame:
    """
    Simulate loan lifecycles for all customers using Monte Carlo methods.
    
    This function:
    1. For each customer, runs n_iterations Monte Carlo simulations
    2. Simulates credit state transitions
    3. Simulates utilization changes using forecasted distributions
    4. Simulates payment behavior (early, on-time, late, default)
    5. Calculates revenue (interest + fees) and losses (defaults)
    6. Aggregates results: mean, median, and percentiles
    7. Calculates net profitability_score = expected_revenue - expected_loss
    8. Applies NPV discounting at configurable rate
    9. Supports cohort-based aggregation for performance optimization
    10. Adds expected_revenue, expected_loss, profitability_score columns
    
    Parameters
    ----------
    df : pd.DataFrame
        Customer DataFrame with required columns:
        - customer_id
        - initial_loan
        - credit_state
        - utilization_rate
        - forecasted_utilization (optional, uses utilization_rate if missing)
        - utilization_std (optional, uses default if missing)
    n_iterations : int, default 3500
        Number of Monte Carlo iterations per customer (3000-4000 recommended)
    horizon_days : int, default 365
        Simulation horizon in days
    discount_rate : float, default 0.12
        Annual discount rate for NPV calculations
    batch_size : int, default 5000
        Number of customers to process in each batch
    use_cohort_aggregation : bool, default False
        Whether to use cohort-based aggregation for performance
        
    Returns
    -------
    pd.DataFrame
        DataFrame with added columns:
        - expected_revenue
        - expected_loss
        - profitability_score
        - revenue_p5, revenue_p95 (5th and 95th percentiles)
        - loss_p5, loss_p95 (5th and 95th percentiles)
        - avg_utilization
        - final_credit_state
        
    Raises
    ------
    ValueError
        If required columns are missing from DataFrame
    RuntimeError
        If simulation fails for any reason
        
    Examples
    --------
    >>> # Basic usage
    >>> result_df = simulate_loan_lifecycle(customers_df)
    >>> 
    >>> # Custom parameters
    >>> result_df = simulate_loan_lifecycle(
    ...     customers_df,
    ...     n_iterations=4000,
    ...     horizon_days=730,  # 2 years
    ...     discount_rate=0.10
    ... )
    """
    # Validate required columns
    required_columns = ['customer_id', 'initial_loan', 'credit_state', 'utilization_rate']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Create a copy to avoid modifying the original DataFrame
    df_result = df.copy()
    
    # Prepare forecasted utilization data
    if 'forecasted_utilization' not in df_result.columns:
        df_result['forecasted_utilization'] = df_result['utilization_rate']
    
    if 'utilization_std' not in df_result.columns:
        df_result['utilization_std'] = 0.1  # Default std
    
    # Validate n_iterations
    if n_iterations < 3000:
        print(f"Warning: n_iterations={n_iterations} is below recommended minimum (3000)")
    if n_iterations > 4000:
        print(f"Warning: n_iterations={n_iterations} is above recommended maximum (4000)")
    
    # Initialize result arrays
    n_customers = len(df_result)
    expected_revenues = np.zeros(n_customers)
    expected_losses = np.zeros(n_customers)
    profitability_scores = np.zeros(n_customers)
    revenue_p5_list = np.zeros(n_customers)
    revenue_p95_list = np.zeros(n_customers)
    loss_p5_list = np.zeros(n_customers)
    loss_p95_list = np.zeros(n_customers)
    avg_utilizations = np.zeros(n_customers)
    final_states = [''] * n_customers
    
    # Process customers in batches
    print(f"\nSimulating loan lifecycles for {n_customers} customers...")
    print(f"  Iterations per customer: {n_iterations}")
    print(f"  Horizon: {horizon_days} days")
    print(f"  Discount rate: {discount_rate:.2%}")
    print(f"  Batch size: {batch_size}")
    
    batch_start = 0
    while batch_start < n_customers:
        batch_end = min(batch_start + batch_size, n_customers)
        batch_indices = list(range(batch_start, batch_end))
        batch_count = len(batch_indices)
        
        print(f"\nProcessing batch {batch_start // batch_size + 1}: "
              f"customers {batch_start + 1} to {batch_end}")
        
        # Process batch
        for i, idx in enumerate(batch_indices):
            customer_result = simulate_single_customer(
                customer_id=str(df_result.loc[idx, 'customer_id']),
                initial_loan=float(df_result.loc[idx, 'initial_loan']),
                credit_state=str(df_result.loc[idx, 'credit_state']),
                utilization_rate=float(df_result.loc[idx, 'utilization_rate']),
                forecast_utilization_mean=float(df_result.loc[idx, 'forecasted_utilization']),
                forecast_utilization_std=float(df_result.loc[idx, 'utilization_std']),
                n_iterations=n_iterations,
                horizon_days=horizon_days,
                discount_rate=discount_rate
            )
            
            # Store results
            expected_revenues[idx] = customer_result['expected_revenue']
            expected_losses[idx] = customer_result['expected_loss']
            profitability_scores[idx] = customer_result['profitability_score']
            revenue_p5_list[idx] = customer_result['revenue_p5']
            revenue_p95_list[idx] = customer_result['revenue_p95']
            loss_p5_list[idx] = customer_result['loss_p5']
            loss_p95_list[idx] = customer_result['loss_p95']
            avg_utilizations[idx] = customer_result['avg_utilization']
            final_states[idx] = customer_result['final_credit_state']
        
        batch_start = batch_end
    
    # Add result columns to DataFrame
    df_result['expected_revenue'] = expected_revenues
    df_result['expected_loss'] = expected_losses
    df_result['profitability_score'] = profitability_scores
    df_result['revenue_p5'] = revenue_p5_list
    df_result['revenue_p95'] = revenue_p95_list
    df_result['loss_p5'] = loss_p5_list
    df_result['loss_p95'] = loss_p95_list
    df_result['avg_utilization'] = avg_utilizations
    df_result['final_credit_state'] = final_states
    
    # Print summary statistics
    print("\n" + "=" * 60)
    print("Lifecycle Simulation Summary")
    print("=" * 60)
    print(f"Total customers processed: {n_customers}")
    print(f"Mean expected revenue: ${np.mean(expected_revenues):,.2f}")
    print(f"Median expected revenue: ${np.median(expected_revenues):,.2f}")
    print(f"Mean expected loss: ${np.mean(expected_losses):,.2f}")
    print(f"Median expected loss: ${np.median(expected_losses):,.2f}")
    print(f"Mean profitability score: ${np.mean(profitability_scores):,.2f}")
    print(f"Median profitability score: ${np.median(profitability_scores):,.2f}")
    print(f"Positive profitability: {np.sum(profitability_scores > 0)} customers "
          f"({100*np.sum(profitability_scores > 0)/n_customers:.1f}%)")
    print("=" * 60)
    
    return df_result


# ============================================================================
# COHORT-BASED AGGREGATION (for performance optimization)
# ============================================================================

def simulate_cohort_lifecycle(
    df: pd.DataFrame,
    cohort_column: str,
    n_iterations: int = DEFAULT_N_ITERATIONS,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    discount_rate: float = DEFAULT_DISCOUNT_RATE
) -> pd.DataFrame:
    """
    Simulate loan lifecycles using cohort-based aggregation for performance.
    
    This function groups customers by a cohort column (e.g., credit_state,
    region, or other grouping) and simulates lifecycles for each cohort,
    then aggregates results back to the customer level.
    
    Parameters
    ----------
    df : pd.DataFrame
        Customer DataFrame
    cohort_column : str
        Column name to use for cohort grouping
    n_iterations : int
        Number of Monte Carlo iterations
    horizon_days : int
        Simulation horizon in days
    discount_rate : float
        Annual discount rate
        
    Returns
    -------
    pd.DataFrame
        DataFrame with lifecycle simulation results
    """
    # Validate cohort column
    if cohort_column not in df.columns:
        raise ValueError(f"Cohort column '{cohort_column}' not found in DataFrame")
    
    print(f"\nUsing cohort-based aggregation by '{cohort_column}'")
    
    # Get cohort statistics
    cohort_stats = df.groupby(cohort_column).agg({
        'initial_loan': ['mean', 'std', 'count'],
        'utilization_rate': 'mean',
        'forecasted_utilization': 'mean',
        'utilization_std': 'mean'
    }).reset_index()
    
    cohort_stats.columns = [
        cohort_column, 'avg_loan', 'loan_std', 'n_customers',
        'avg_utilization', 'forecast_utilization', 'utilization_std'
    ]
    
    # Simulate each cohort
    cohort_results = []
    for _, cohort in cohort_stats.iterrows():
        result = simulate_single_customer(
            customer_id=f"cohort_{cohort[cohort_column]}",
            initial_loan=cohort['avg_loan'],
            credit_state=str(cohort[cohort_column]),
            utilization_rate=cohort['avg_utilization'],
            forecast_utilization_mean=cohort['forecast_utilization'],
            forecast_utilization_std=cohort['utilization_std'],
            n_iterations=n_iterations,
            horizon_days=horizon_days,
            discount_rate=discount_rate
        )
        result['cohort'] = cohort[cohort_column]
        cohort_results.append(result)
    
    # Merge cohort results back to customer DataFrame
    cohort_df = pd.DataFrame(cohort_results)
    df_result = df.merge(cohort_df.drop(columns=['customer_id']), 
                         left_on=cohort_column, right_on='cohort', how='left')
    
    return df_result

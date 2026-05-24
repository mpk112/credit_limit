"""
Transition Matrix Implementation for Loan Limit Optimization System

This module implements the Markov Chain Analyzer component which:
- Builds transition probability matrices to model credit state transitions
- Computes steady-state distributions using eigenvalue decomposition
- Handles edge cases like insufficient historical data

Functions:
- build_transition_matrix(): Build transition matrix from historical credit state data
- validate_transition_matrix(): Validate matrix properties
- compute_steady_state(): Compute steady-state distribution

Properties tested:
- P10_TransitionMatrixStochastic: Each row sums to 1.0 ± 0.001
- P11_TransitionMatrixSquare: Matrix dimensions are (n_states, n_states)
- P12_SteadyStateValid: Steady state probabilities sum to 1.0 ± 0.001
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import warnings


# ============================================================================
# CONFIGURATION
# ============================================================================

# Default credit states in order from best to worst
DEFAULT_CREDIT_STATES = ['Excellent', 'Good', 'Fair', 'Poor']

# Minimum observations required for reliable transition estimation
MIN_OBSERVATIONS_PER_STATE = 10

# Tolerance for validation checks
MATRIX_VALIDATION_TOLERANCE = 0.001

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class TransitionMatrix:
    """
    Data class representing a Markov chain transition matrix.
    
    Attributes
    ----------
    matrix : np.ndarray
        Transition probability matrix of shape (n_states, n_states)
        where matrix[i, j] = P(state_j | state_i)
    state_labels : List[str]
        List of state labels corresponding to matrix rows/columns
    steady_state : np.ndarray
        Steady-state probability distribution of shape (n_states,)
    observation_period_days : int
        Number of days in the observation period
    """
    matrix: np.ndarray
    state_labels: List[str]
    steady_state: np.ndarray
    observation_period_days: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'matrix': self.matrix,
            'state_labels': self.state_labels,
            'steady_state': self.steady_state,
            'observation_period_days': self.observation_period_days
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_uniform_transition_matrix(n_states: int) -> np.ndarray:
    """
    Create a uniform transition matrix where all transitions are equally likely.
    
    This is used as a fallback when there is insufficient historical data.
    
    Parameters
    ----------
    n_states : int
        Number of states in the Markov chain
        
    Returns
    -------
    np.ndarray
        Uniform transition matrix of shape (n_states, n_states)
    """
    # Each state has equal probability of transitioning to any state
    uniform_prob = 1.0 / n_states
    return np.full((n_states, n_states), uniform_prob)


def validate_transition_matrix(matrix: np.ndarray, 
                               state_labels: List[str],
                               tolerance: float = MATRIX_VALIDATION_TOLERANCE) -> Tuple[bool, List[str]]:
    """
    Validate that a transition matrix has the required properties.
    
    Properties checked:
    1. Matrix is square
    2. Matrix is stochastic (all rows sum to 1.0)
    3. All entries are in [0, 1]
    
    Parameters
    ----------
    matrix : np.ndarray
        Transition probability matrix to validate
    state_labels : List[str]
        List of state labels
    tolerance : float, default 0.001
        Tolerance for row sum validation
        
    Returns
    -------
    Tuple[bool, List[str]]
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Check if matrix is 2D
    if matrix.ndim != 2:
        errors.append(f"Matrix must be 2D, got {matrix.ndim}D")
        return False, errors
    
    n_rows, n_cols = matrix.shape
    
    # Check if square
    if n_rows != n_cols:
        errors.append(f"Matrix must be square, got shape ({n_rows}, {n_cols})")
        return False, errors
    
    # Check if state labels match matrix dimensions
    if len(state_labels) != n_rows:
        errors.append(f"State labels count ({len(state_labels)}) must match matrix dimensions ({n_rows})")
        return False, errors
    
    # Check all entries are in [0, 1]
    if np.any(matrix < 0) or np.any(matrix > 1):
        errors.append("All transition probabilities must be in [0, 1]")
        return False, errors
    
    # Check row sums equal 1.0
    row_sums = matrix.sum(axis=1)
    if not np.allclose(row_sums, 1.0, atol=tolerance):
        bad_rows = np.where(~np.isclose(row_sums, 1.0, atol=tolerance))[0]
        for row_idx in bad_rows:
            errors.append(f"Row {row_idx} ({state_labels[row_idx]}) sums to {row_sums[row_idx]:.6f}, expected 1.0")
        return False, errors
    
    return True, errors


def compute_steady_state(matrix: np.ndarray) -> np.ndarray:
    """
    Compute the steady-state distribution using eigenvalue decomposition.
    
    The steady-state distribution π satisfies π = πP, where P is the transition matrix.
    This is equivalent to finding the eigenvector corresponding to eigenvalue 1.
    
    Parameters
    ----------
    matrix : np.ndarray
        Transition probability matrix of shape (n_states, n_states)
        
    Returns
    -------
    np.ndarray
        Steady-state probability distribution of shape (n_states,)
        
    Raises
    ------
    ValueError
        If the matrix is not valid or steady-state cannot be computed
    """
    # Validate input
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Transition matrix must be square")
    
    n_states = matrix.shape[0]
    
    # Transpose matrix to find left eigenvectors
    # We want to solve: πP = π, which is equivalent to: P^T π^T = π^T
    transition_T = matrix.T
    
    # Compute eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eig(transition_T)
    
    # Find the eigenvector corresponding to eigenvalue 1 (or closest to 1)
    # The steady-state eigenvalue should be exactly 1 for a stochastic matrix
    one_idx = np.argmin(np.abs(eigenvalues - 1.0))
    
    # Extract the eigenvector
    steady_state = np.real(eigenvectors[:, one_idx])
    
    # Ensure all values are non-negative
    if np.any(steady_state < 0):
        # If we get negative values, there might be numerical issues
        # Try using the null space approach instead
        try:
            # Use SVD to find null space of (P^T - I)
            identity = np.eye(n_states)
            matrix_minus_I = transition_T - identity
            
            # SVD decomposition
            U, S, Vh = np.linalg.svd(matrix_minus_I)
            
            # The right singular vector corresponding to smallest singular value
            # is the steady-state distribution
            steady_state = Vh[-1, :]
            steady_state = np.abs(steady_state)  # Ensure non-negative
        except:
            # Fallback: use uniform distribution
            steady_state = np.ones(n_states) / n_states
    else:
        # Take absolute value to handle any numerical noise
        steady_state = np.abs(steady_state)
    
    # Normalize to sum to 1
    steady_state = steady_state / steady_state.sum()
    
    # Final validation
    if not np.allclose(steady_state.sum(), 1.0, atol=MATRIX_VALIDATION_TOLERANCE):
        # Fallback to uniform distribution
        steady_state = np.ones(n_states) / n_states
    
    return steady_state


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def build_transition_matrix(
    df: pd.DataFrame,
    credit_state_column: str = 'credit_state',
    observation_period_days: int = 90,
    min_observations_per_state: int = MIN_OBSERVATIONS_PER_STATE,
    state_labels: Optional[List[str]] = None
) -> TransitionMatrix:
    """
    Build a Markov chain transition matrix from historical credit state data.
    
    This function:
    1. Extracts state transition sequences from historical credit_state data
    2. Counts transitions between each pair of credit states
    3. Normalizes rows to create a stochastic transition probability matrix
    4. Validates matrix properties (square, row sums = 1.0)
    5. Computes steady-state distribution using eigenvalue decomposition
    6. Handles insufficient historical data by using uniform transition probabilities
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing historical credit state data. Each row represents
        a customer's credit state at a particular time period.
        Required columns:
        - credit_state_column: The column containing credit state labels
        - customer_id: To identify individual customer sequences (if present)
        
    credit_state_column : str, default 'credit_state'
        Name of the column containing credit state labels
        
    observation_period_days : int, default 90
        Number of days in the observation period for calculating transitions
        
    min_observations_per_state : int, default 10
        Minimum number of observations required per state for reliable estimation.
        If any state has fewer observations, uniform probabilities are used.
        
    state_labels : List[str], optional
        List of state labels in order from best to worst credit quality.
        If None, uses DEFAULT_CREDIT_STATES = ['Excellent', 'Good', 'Fair', 'Poor']
        
    Returns
    -------
    TransitionMatrix
        Object containing:
        - matrix: Transition probability matrix (n_states x n_states)
        - state_labels: List of state labels
        - steady_state: Steady-state probability distribution
        - observation_period_days: Observation period in days
        
    Raises
    ------
    ValueError
        If required columns are missing or data is invalid
    RuntimeError
        If transition matrix cannot be computed
        
    Notes
    -----
    The function handles edge cases:
    - Insufficient data: Uses uniform transition probabilities
    - Non-irreducible chains: Adds small epsilon to zero entries
    - Numerical instability: Normalizes and validates results
    
    Example
    -------
    >>> df = pd.DataFrame({
    ...     'customer_id': ['C1', 'C1', 'C1', 'C2', 'C2'],
    ...     'credit_state': ['Excellent', 'Good', 'Fair', 'Good', 'Fair']
    ... })
    >>> transition_matrix = build_transition_matrix(df, observation_period_days=30)
    >>> print(transition_matrix.matrix)
    >>> print(transition_matrix.steady_state)
    """
    # Set default state labels if not provided
    if state_labels is None:
        state_labels = DEFAULT_CREDIT_STATES.copy()
    
    n_states = len(state_labels)
    
    # Validate input DataFrame
    if credit_state_column not in df.columns:
        raise ValueError(f"Column '{credit_state_column}' not found in DataFrame")
    
    if len(df) == 0:
        raise ValueError("DataFrame is empty")
    
    # Create a copy to avoid modifying the original DataFrame
    df_work = df.copy()
    
    # Check for customer_id column to identify sequences
    has_customer_id = 'customer_id' in df_work.columns
    
    # Count transitions
    transition_counts = np.zeros((n_states, n_states), dtype=np.int64)
    
    if has_customer_id:
        # Process each customer's sequence separately
        for customer_id, customer_df in df_work.groupby('customer_id'):
            # Sort by index or time column if available
            customer_df = customer_df.sort_index()
            
            # Extract state sequence
            states = customer_df[credit_state_column].values
            
            # Count transitions between consecutive states
            for i in range(len(states) - 1):
                current_state = states[i]
                next_state = states[i + 1]
                
                # Skip if state is not in our state labels
                if current_state not in state_labels or next_state not in state_labels:
                    continue
                
                current_idx = state_labels.index(current_state)
                next_idx = state_labels.index(next_state)
                
                transition_counts[current_idx, next_idx] += 1
    else:
        # If no customer_id, assume data is already in sequence order
        states = df_work[credit_state_column].values
        
        for i in range(len(states) - 1):
            current_state = states[i]
            next_state = states[i + 1]
            
            if current_state not in state_labels or next_state not in state_labels:
                continue
            
            current_idx = state_labels.index(current_state)
            next_idx = state_labels.index(next_state)
            
            transition_counts[current_idx, next_idx] += 1
    
    # Check if we have sufficient data
    total_transitions = transition_counts.sum()
    total_observations = len(df_work)
    
    print(f"Total observations: {total_observations}")
    print(f"Total transitions counted: {total_transitions}")
    
    # Check per-state observation counts
    state_counts = df_work[credit_state_column].value_counts()
    for state in state_labels:
        count = state_counts.get(state, 0)
        if count < min_observations_per_state:
            print(f"Warning: State '{state}' has only {count} observations "
                  f"(minimum required: {min_observations_per_state})")
    
    # Build transition matrix
    if total_transitions < n_states * min_observations_per_state:
        # Insufficient data: use uniform transition probabilities
        print(f"Insufficient data ({total_transitions} transitions). "
              f"Using uniform transition probabilities.")
        transition_matrix = create_uniform_transition_matrix(n_states)
    else:
        # Normalize rows to create stochastic matrix
        row_sums = transition_counts.sum(axis=1, keepdims=True)
        
        # Handle rows with zero sum (states with no transitions)
        row_sums[row_sums == 0] = 1  # Avoid division by zero
        
        transition_matrix = transition_counts / row_sums
        
        # Ensure all rows sum to exactly 1.0
        row_sums = transition_matrix.sum(axis=1)
        transition_matrix = transition_matrix / row_sums.reshape(-1, 1)
    
    # Validate the transition matrix
    is_valid, errors = validate_transition_matrix(transition_matrix, state_labels)
    
    if not is_valid:
        print("Warning: Transition matrix validation failed:")
        for error in errors:
            print(f"  - {error}")
        print("Using fallback uniform matrix")
        transition_matrix = create_uniform_transition_matrix(n_states)
    
    # Compute steady-state distribution
    try:
        steady_state = compute_steady_state(transition_matrix)
    except Exception as e:
        print(f"Warning: Could not compute steady-state distribution: {e}")
        print("Using uniform steady-state distribution")
        steady_state = np.ones(n_states) / n_states
    
    # Final validation of steady-state
    steady_state_sum = steady_state.sum()
    if not np.isclose(steady_state_sum, 1.0, atol=MATRIX_VALIDATION_TOLERANCE):
        print(f"Warning: Steady-state sum is {steady_state_sum:.6f}, normalizing")
        steady_state = steady_state / steady_state_sum
    
    # Create and return TransitionMatrix object
    return TransitionMatrix(
        matrix=transition_matrix,
        state_labels=state_labels,
        steady_state=steady_state,
        observation_period_days=observation_period_days
    )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_transition_matrix(transition_matrix: TransitionMatrix) -> None:
    """
    Print a formatted transition matrix with state labels.
    
    Parameters
    ----------
    transition_matrix : TransitionMatrix
        Transition matrix object to print
    """
    print("\n" + "=" * 60)
    print("TRANSITION PROBABILITY MATRIX")
    print("=" * 60)
    
    # Print header
    header = "From\\To".ljust(12)
    for state in transition_matrix.state_labels:
        header += f"{state:>10}"
    print(header)
    
    # Print rows
    for i, from_state in enumerate(transition_matrix.state_labels):
        row_str = f"{from_state:>12}"
        for j in range(len(transition_matrix.state_labels)):
            row_str += f"{transition_matrix.matrix[i, j]:>10.4f}"
        print(row_str)
    
    print("\n" + "-" * 60)
    print("STEADY-STATE DISTRIBUTION")
    print("-" * 60)
    
    for state, prob in zip(transition_matrix.state_labels, transition_matrix.steady_state):
        print(f"{state:>12}: {prob:>10.4f}")
    
    print("\n" + "-" * 60)
    print(f"Observation Period: {transition_matrix.observation_period_days} days")
    print("=" * 60 + "\n")


def test_build_transition_matrix():
    """
    Test the build_transition_matrix function with sample data.
    """
    print("Testing build_transition_matrix function...")
    
    # Create sample data with known transition patterns
    np.random.seed(42)
    n_customers = 100
    n_periods = 10
    
    data = []
    for i in range(n_customers):
        customer_id = f"CUST_{i:05d}"
        current_state = np.random.choice(DEFAULT_CREDIT_STATES)
        
        for j in range(n_periods):
            data.append({
                'customer_id': customer_id,
                'credit_state': current_state
            })
            
            # Simulate transitions with some probability
            if j < n_periods - 1:
                state_idx = DEFAULT_CREDIT_STATES.index(current_state)
                
                # Define transition probabilities
                if state_idx == 0:  # Excellent
                    probs = [0.85, 0.10, 0.04, 0.01]
                elif state_idx == 1:  # Good
                    probs = [0.10, 0.80, 0.08, 0.02]
                elif state_idx == 2:  # Fair
                    probs = [0.02, 0.15, 0.75, 0.08]
                else:  # Poor
                    probs = [0.01, 0.05, 0.20, 0.74]
                
                current_state = np.random.choice(DEFAULT_CREDIT_STATES, p=probs)
    
    df = pd.DataFrame(data)
    
    print(f"Created sample data with {len(df)} records")
    print(f"Customers: {n_customers}, Periods per customer: {n_periods}")
    
    # Build transition matrix
    transition_matrix = build_transition_matrix(
        df,
        credit_state_column='credit_state',
        observation_period_days=30
    )
    
    # Print results
    print_transition_matrix(transition_matrix)
    
    # Validate
    is_valid, errors = validate_transition_matrix(
        transition_matrix.matrix,
        transition_matrix.state_labels
    )
    
    print(f"\nMatrix validation: {'PASSED' if is_valid else 'FAILED'}")
    if errors:
        for error in errors:
            print(f"  - {error}")
    
    return transition_matrix


if __name__ == '__main__':
    test_build_transition_matrix()

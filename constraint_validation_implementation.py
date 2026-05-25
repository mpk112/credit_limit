"""
Constraint Definition and Validation Module
============================================

This module implements constraint definition and validation for the Loan Limit
Optimization System. It provides:

- Constraint_Set data structure with default business values
- validate_constraints() function to check mathematical feasibility
- Conflict detection for infeasible constraint sets

Functions:
- create_constraint_set(): Create a Constraint_Set with default or custom values
- validate_constraints(): Validate constraint set for mathematical feasibility
- identify_conflicts(): Identify conflicting constraints if infeasible

Properties tested:
- P13.1: Constraint_Set has all required fields with valid default values
- P13.2: Constraint_Set supports custom values
- P13.3: validate_constraints() checks mathematical feasibility
- P13.4: validate_constraints() identifies conflicting constraints
- P13.5: validate_constraints() returns detailed error messages

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ConstraintStatus(Enum):
    """Status of constraint validation."""
    VALID = "valid"
    INVALID = "invalid"
    INFEASIBLE = "infeasible"


@dataclass
class ConstraintValidationResult:
    """Result of constraint validation."""
    status: ConstraintStatus
    is_valid: bool
    is_feasible: bool
    error_messages: List[str]
    conflicting_constraints: List[Tuple[str, str]]
    
    def __post_init__(self):
        if self.status == ConstraintStatus.VALID:
            self.is_valid = True
            self.is_feasible = True
        elif self.status == ConstraintStatus.INVALID:
            self.is_valid = False
            self.is_feasible = True
        elif self.status == ConstraintStatus.INFEASIBLE:
            self.is_valid = True
            self.is_feasible = False


# Default constraint values based on business requirements
DEFAULT_CONSTRAINTS = {
    'max_portfolio_default_risk': 0.05,           # 5% maximum portfolio default risk
    'min_profitability_target': 1000000,          # $1,000,000 minimum profitability
    'max_total_exposure': 500000000,              # $500M maximum total exposure
    'max_individual_limit': 50000,                # $50K maximum individual loan limit
    'max_debt_to_income_ratio': 0.43,             # 43% maximum debt-to-income ratio
    'regulatory_capital_requirement': 0.08        # 8% regulatory capital requirement
}


def create_constraint_set(
    max_portfolio_default_risk: float = DEFAULT_CONSTRAINTS['max_portfolio_default_risk'],
    min_profitability_target: float = DEFAULT_CONSTRAINTS['min_profitability_target'],
    max_total_exposure: float = DEFAULT_CONSTRAINTS['max_total_exposure'],
    max_individual_limit: float = DEFAULT_CONSTRAINTS['max_individual_limit'],
    max_debt_to_income_ratio: float = DEFAULT_CONSTRAINTS['max_debt_to_income_ratio'],
    regulatory_capital_requirement: float = DEFAULT_CONSTRAINTS['regulatory_capital_requirement']
) -> Dict[str, float]:
    """
    Create a Constraint_Set with default or custom values.
    
    This function creates a dictionary containing all business and regulatory
    constraints for the loan limit optimization system. Default values are based
    on industry standards and regulatory requirements.
    
    Parameters
    ----------
    max_portfolio_default_risk : float, default 0.05
        Maximum allowed portfolio default risk (as decimal, e.g., 0.05 = 5%)
    min_profitability_target : float, default 1000000
        Minimum required profitability target in dollars
    max_total_exposure : float, default 500000000
        Maximum total credit exposure in dollars
    max_individual_limit : float, default 50000
        Maximum individual loan limit in dollars
    max_debt_to_income_ratio : float, default 0.43
        Maximum debt-to-income ratio (as decimal)
    regulatory_capital_requirement : float, default 0.08
        Regulatory capital requirement (as decimal)
    
    Returns
    -------
    Dict[str, float]
        Dictionary containing all constraint values
    
    Raises
    ------
    ValueError
        If any constraint value is negative or invalid
    
    Examples
    --------
    >>> # Create with default values
    >>> constraints = create_constraint_set()
    >>> print(f"Max portfolio default risk: {constraints['max_portfolio_default_risk']}")
    >>> 
    >>> # Create with custom values
    >>> constraints = create_constraint_set(
    ...     max_portfolio_default_risk=0.03,
    ...     min_profitability_target=1500000
    ... )
    """
    # Validate input values
    constraints = {
        'max_portfolio_default_risk': max_portfolio_default_risk,
        'min_profitability_target': min_profitability_target,
        'max_total_exposure': max_total_exposure,
        'max_individual_limit': max_individual_limit,
        'max_debt_to_income_ratio': max_debt_to_income_ratio,
        'regulatory_capital_requirement': regulatory_capital_requirement
    }
    
    # Validate each constraint
    for key, value in constraints.items():
        if value < 0:
            raise ValueError(f"Constraint '{key}' cannot be negative: {value}")
    
    # Validate ratio constraints are in [0, 1] range
    ratio_constraints = ['max_portfolio_default_risk', 'max_debt_to_income_ratio', 
                         'regulatory_capital_requirement']
    for key in ratio_constraints:
        if constraints[key] > 1:
            raise ValueError(f"Ratio constraint '{key}' must be <= 1: {constraints[key]}")
    
    # Validate that max_individual_limit doesn't exceed max_total_exposure
    if max_individual_limit > max_total_exposure:
        raise ValueError(
            f"max_individual_limit ({max_individual_limit}) cannot exceed "
            f"max_total_exposure ({max_total_exposure})"
        )
    
    return constraints


def validate_constraints(
    constraints: Dict[str, float],
    customer_df: Optional[pd.DataFrame] = None
) -> ConstraintValidationResult:
    """
    Validate constraint set for mathematical feasibility.
    
    This function checks whether the provided constraint set is mathematically
    feasible and identifies any conflicting constraints. It performs both
    individual constraint validation and cross-constraint feasibility checks.
    
    Parameters
    ----------
    constraints : Dict[str, float]
        Dictionary containing constraint values
    customer_df : pd.DataFrame, optional
        Customer DataFrame for feasibility checks (optional)
    
    Returns
    -------
    ConstraintValidationResult
        Object containing validation status, error messages, and conflicting constraints
    
    Notes
    -----
    The function checks:
    1. Individual constraint validity (non-negative, proper ranges)
    2. Cross-constraint feasibility (e.g., profitability vs. exposure limits)
    3. Business logic consistency (e.g., individual vs. portfolio limits)
    
    Examples
    --------
    >>> constraints = create_constraint_set()
    >>> result = validate_constraints(constraints)
    >>> if result.is_valid:
    ...     print("All constraints are valid!")
    >>> else:
    ...     for error in result.error_messages:
    ...         print(f"Error: {error}")
    """
    error_messages = []
    conflicting_constraints = []
    
    # Extract constraint values
    max_default_risk = constraints.get('max_portfolio_default_risk', 0.05)
    min_profitability = constraints.get('min_profitability_target', 1000000)
    max_exposure = constraints.get('max_total_exposure', 500000000)
    max_individual = constraints.get('max_individual_limit', 50000)
    max_dti = constraints.get('max_debt_to_income_ratio', 0.43)
    capital_requirement = constraints.get('regulatory_capital_requirement', 0.08)
    
    # Check 1: Validate individual constraint values
    if max_default_risk < 0 or max_default_risk > 1:
        error_messages.append(
            f"max_portfolio_default_risk must be in [0, 1], got {max_default_risk}"
        )
    
    if min_profitability < 0:
        error_messages.append(
            f"min_profitability_target cannot be negative: {min_profitability}"
        )
    
    if max_exposure < 0:
        error_messages.append(
            f"max_total_exposure cannot be negative: {max_exposure}"
        )
    
    if max_individual < 0:
        error_messages.append(
            f"max_individual_limit cannot be negative: {max_individual}"
        )
    
    if max_dti < 0 or max_dti > 1:
        error_messages.append(
            f"max_debt_to_income_ratio must be in [0, 1], got {max_dti}"
        )
    
    if capital_requirement < 0 or capital_requirement > 1:
        error_messages.append(
            f"regulatory_capital_requirement must be in [0, 1], got {capital_requirement}"
        )
    
    # Check 2: Cross-constraint feasibility
    # Check if max_individual_limit is reasonable relative to max_total_exposure
    if max_individual > max_exposure:
        error_messages.append(
            f"max_individual_limit ({max_individual}) exceeds max_total_exposure ({max_exposure}). "
            f"Either increase max_total_exposure or decrease max_individual_limit."
        )
        conflicting_constraints.append(('max_individual_limit', 'max_total_exposure'))
    
    # Check 3: Business logic consistency (if customer data provided)
    if customer_df is not None:
        # Check if minimum profitability is achievable given exposure limits
        if len(customer_df) > 0:
            avg_profitability = customer_df.get('profitability_score', pd.Series([0])).mean()
            max_customers_with_profit = int(max_exposure / max_individual) if max_individual > 0 else 0
            
            # Rough estimate: can we achieve profitability target?
            if max_customers_with_profit > 0 and avg_profitability > 0:
                max_possible_profit = max_customers_with_profit * avg_profitability
                if max_possible_profit < min_profitability:
                    error_messages.append(
                        f"Profitability target (${min_profitability:,.0f}) may be unachievable. "
                        f"Estimated max profit with current constraints: ${max_possible_profit:,.0f}. "
                        f"Consider increasing max_total_exposure or relaxing profitability target."
                    )
                    conflicting_constraints.append(('min_profitability_target', 'max_total_exposure'))
    
    # Determine overall status
    if error_messages:
        if conflicting_constraints:
            status = ConstraintStatus.INFEASIBLE
        else:
            status = ConstraintStatus.INVALID
    else:
        status = ConstraintStatus.VALID
    
    return ConstraintValidationResult(
        status=status,
        is_valid=not bool(error_messages),
        is_feasible=status != ConstraintStatus.INFEASIBLE,
        error_messages=error_messages,
        conflicting_constraints=conflicting_constraints
    )


def identify_conflicts(constraints: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Identify specific conflicting constraints and suggest resolutions.
    
    This function analyzes the constraint set to identify specific conflicts
    and provides actionable suggestions for resolution.
    
    Parameters
    ----------
    constraints : Dict[str, float]
        Dictionary containing constraint values
    
    Returns
    -------
    List[Dict[str, Any]]
        List of conflict descriptions with suggested resolutions
    
    Examples
    --------
    >>> constraints = create_constraint_set()
    >>> conflicts = identify_conflicts(constraints)
    >>> for conflict in conflicts:
    ...     print(f"Issue: {conflict['issue']}")
    ...     print(f"Suggestion: {conflict['suggestion']}")
    """
    conflicts = []
    
    max_default_risk = constraints.get('max_portfolio_default_risk', 0.05)
    min_profitability = constraints.get('min_profitability_target', 1000000)
    max_exposure = constraints.get('max_total_exposure', 500000000)
    max_individual = constraints.get('max_individual_limit', 50000)
    max_dti = constraints.get('max_debt_to_income_ratio', 0.43)
    capital_requirement = constraints.get('regulatory_capital_requirement', 0.08)
    
    # Conflict 1: Individual vs. Portfolio limits
    if max_individual > max_exposure:
        conflicts.append({
            'type': 'limit_conflict',
            'issue': 'Individual limit exceeds total exposure',
            'constraints': ['max_individual_limit', 'max_total_exposure'],
            'suggestion': (
                f"Increase max_total_exposure to at least {max_individual:,.0f} "
                f"or decrease max_individual_limit to {max_exposure:,.0f}"
            )
        })
    
    # Conflict 2: Profitability vs. Exposure
    if min_profitability > 0 and max_exposure > 0:
        # Rough heuristic: profitability per dollar of exposure
        # Assume ~10% return on exposure for profitability
        implied_profitability_ratio = min_profitability / max_exposure
        if implied_profitability_ratio > 0.15:  # More than 15% return needed
            conflicts.append({
                'type': 'profitability_constraint',
                'issue': 'High profitability target relative to exposure',
                'constraints': ['min_profitability_target', 'max_total_exposure'],
                'suggestion': (
                    f"Consider increasing max_total_exposure or reducing "
                    f"min_profitability_target. Current ratio: {implied_profitability_ratio:.2%}"
                )
            })
    
    # Conflict 3: Capital requirement vs. Risk tolerance
    if capital_requirement > max_default_risk:
        conflicts.append({
            'type': 'capital_risk_conflict',
            'issue': 'Capital requirement exceeds default risk tolerance',
            'constraints': ['regulatory_capital_requirement', 'max_portfolio_default_risk'],
            'suggestion': (
                f"Increase max_portfolio_default_risk to at least {capital_requirement:.2%} "
                f"or reduce regulatory_capital_requirement to {max_default_risk:.2%}"
            )
        })
    
    return conflicts


def print_constraint_summary(constraints: Dict[str, float]) -> None:
    """
    Print a formatted summary of constraint values.
    
    Parameters
    ----------
    constraints : Dict[str, float]
        Dictionary containing constraint values
    """
    print("=" * 70)
    print("CONSTRAINT SET SUMMARY")
    print("=" * 70)
    
    print(f"{'Constraint':<40} {'Value':>25}")
    print("-" * 70)
    
    print(f"{'Max Portfolio Default Risk':<40} {constraints['max_portfolio_default_risk']:>25.2%}")
    print(f"{'Min Profitability Target':<40} ${constraints['min_profitability_target']:>23,.0f}")
    print(f"{'Max Total Exposure':<40} ${constraints['max_total_exposure']:>23,.0f}")
    print(f"{'Max Individual Limit':<40} ${constraints['max_individual_limit']:>23,.0f}")
    print(f"{'Max Debt-to-Income Ratio':<40} {constraints['max_debt_to_income_ratio']:>25.2%}")
    print(f"{'Regulatory Capital Requirement':<40} {constraints['regulatory_capital_requirement']:>25.2%}")
    
    print("=" * 70)


# Test the implementation
if __name__ == '__main__':
    print("=" * 70)
    print("Constraint Definition and Validation - Test Suite")
    print("=" * 70)
    
    # Test 1: Create constraint set with defaults
    print("\n--- Test 1: Default Constraint Set ---")
    constraints = create_constraint_set()
    print_constraint_summary(constraints)
    
    # Test 2: Validate constraints
    print("\n--- Test 2: Validate Constraints ---")
    result = validate_constraints(constraints)
    print(f"Validation Status: {'PASSED' if result.is_valid else 'FAILED'}")
    print(f"Feasibility: {'FEASIBLE' if result.is_feasible else 'INFEASIBLE'}")
    if result.error_messages:
        print("Error Messages:")
        for msg in result.error_messages:
            print(f"  - {msg}")
    
    # Test 3: Create invalid constraint set
    print("\n--- Test 3: Invalid Constraint Set ---")
    invalid_constraints = None
    try:
        invalid_constraints = create_constraint_set(
            max_individual_limit=1000000,  # Exceeds default max_total_exposure
            max_portfolio_default_risk=-0.01  # Invalid negative value
        )
        invalid_result = validate_constraints(invalid_constraints)
        print(f"Validation Status: {'PASSED' if invalid_result.is_valid else 'FAILED'}")
        print(f"Feasibility: {'FEASIBLE' if invalid_result.is_feasible else 'INFEASIBLE'}")
        if invalid_result.error_messages:
            print("Error Messages:")
            for msg in invalid_result.error_messages:
                print(f"  - {msg}")
    except ValueError as e:
        print(f"Constraint creation failed (expected): {e}")
        print("This demonstrates that create_constraint_set() properly validates inputs")
    
    # Test 4: Identify conflicts (using a constraint set that has conflicts)
    print("\n--- Test 4: Identify Conflicts ---")
    # Create a constraint set with a conflict (max_individual > max_total_exposure)
    # We'll bypass the validation in create_constraint_set for this test
    conflict_constraints = {
        'max_portfolio_default_risk': 0.05,
        'min_profitability_target': 1000000,
        'max_total_exposure': 500000000,
        'max_individual_limit': 600000000,  # Exceeds max_total_exposure
        'max_debt_to_income_ratio': 0.43,
        'regulatory_capital_requirement': 0.08
    }
    conflicts = identify_conflicts(conflict_constraints)
    if conflicts:
        print("Identified Conflicts:")
        for i, conflict in enumerate(conflicts, 1):
            print(f"\n  Conflict {i}: {conflict['issue']}")
            print(f"    Type: {conflict['type']}")
            print(f"    Constraints: {', '.join(conflict['constraints'])}")
            print(f"    Suggestion: {conflict['suggestion']}")
    else:
        print("No conflicts identified.")
    
    # Test 5: Create feasible custom constraint set
    print("\n--- Test 5: Custom Feasible Constraint Set ---")
    custom_constraints = create_constraint_set(
        max_portfolio_default_risk=0.03,
        min_profitability_target=1500000,
        max_total_exposure=600000000,
        max_individual_limit=40000,
        max_debt_to_income_ratio=0.40,
        regulatory_capital_requirement=0.07
    )
    print_constraint_summary(custom_constraints)
    custom_result = validate_constraints(custom_constraints)
    print(f"Validation Status: {'PASSED' if custom_result.is_valid else 'FAILED'}")
    
    print("\n" + "=" * 70)
    print("Constraint Validation Tests Complete!")
    print("=" * 70)

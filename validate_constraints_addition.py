# ============================================================================
# CONSTRAINT VALIDATION
# ============================================================================

def validate_constraints(constraint_set: dict) -> dict:
    """
    Validate mathematical feasibility of a constraint set for loan limit optimization.
    
    This function checks if the provided constraints are mathematically feasible and
    identifies any conflicting constraints that would make optimization impossible.
    
    Parameters
    ----------
    constraint_set : dict
        Dictionary containing constraint parameters with keys:
        - 'max_portfolio_default_risk': Maximum portfolio-wide default risk (0-1)
        - 'min_profitability_target': Minimum total profitability target (positive)
        - 'max_total_exposure': Maximum total credit exposure (positive)
        - 'max_individual_limit': Maximum individual loan limit (positive)
        - 'max_debt_to_income_ratio': Maximum debt-to-income ratio (0-1)
        - 'regulatory_capital_requirement': Regulatory capital requirement (0-1)
        
    Returns
    -------
    dict
        Validation result with keys:
        - 'is_valid': bool indicating if constraints are feasible
        - 'errors': list of error messages for constraint violations
        - 'warnings': list of warning messages for potential issues
        
    Examples
    --------
    >>> constraints = get_constraint_set()
    >>> result = validate_constraints(constraints)
    >>> if result['is_valid']:
    ...     print("Constraints are feasible")
    >>> else:
    ...     print("Constraints have errors:", result['errors'])
    
    >>> # Test with infeasible constraints
    >>> infeasible = get_constraint_set(
    ...     max_individual_limit=100000,
    ...     max_total_exposure=50000
    ... )
    >>> result = validate_constraints(infeasible)
    >>> print(f"Valid: {result['is_valid']}, Errors: {len(result['errors'])}")
    """
    errors = []
    warnings = []
    
    # Extract constraint values with defaults for missing keys
    max_portfolio_default_risk = constraint_set.get('max_portfolio_default_risk', 0.05)
    min_profitability_target = constraint_set.get('min_profitability_target', 1000000.0)
    max_total_exposure = constraint_set.get('max_total_exposure', 500000000.0)
    max_individual_limit = constraint_set.get('max_individual_limit', 50000.0)
    max_debt_to_income_ratio = constraint_set.get('max_debt_to_income_ratio', 0.43)
    regulatory_capital_requirement = constraint_set.get('regulatory_capital_requirement', 0.08)
    
    # ============================================================================
    # CHECK 1: Mathematical feasibility of individual constraints
    # ============================================================================
    
    # Check max_portfolio_default_risk (should be between 0 and 1)
    if not isinstance(max_portfolio_default_risk, (int, float)):
        errors.append("max_portfolio_default_risk must be a numeric value")
    elif max_portfolio_default_risk < 0 or max_portfolio_default_risk > 1:
        errors.append(
            f"max_portfolio_default_risk must be between 0 and 1, got {max_portfolio_default_risk}"
        )
    
    # Check min_profitability_target (should be positive)
    if not isinstance(min_profitability_target, (int, float)):
        errors.append("min_profitability_target must be a numeric value")
    elif min_profitability_target <= 0:
        errors.append(
            f"min_profitability_target must be positive, got {min_profitability_target}"
        )
    
    # Check max_total_exposure (should be positive)
    if not isinstance(max_total_exposure, (int, float)):
        errors.append("max_total_exposure must be a numeric value")
    elif max_total_exposure <= 0:
        errors.append(
            f"max_total_exposure must be positive, got {max_total_exposure}"
        )
    
    # Check max_individual_limit (should be positive)
    if not isinstance(max_individual_limit, (int, float)):
        errors.append("max_individual_limit must be a numeric value")
    elif max_individual_limit <= 0:
        errors.append(
            f"max_individual_limit must be positive, got {max_individual_limit}"
        )
    
    # Check max_debt_to_income_ratio (should be between 0 and 1)
    if not isinstance(max_debt_to_income_ratio, (int, float)):
        errors.append("max_debt_to_income_ratio must be a numeric value")
    elif max_debt_to_income_ratio < 0 or max_debt_to_income_ratio > 1:
        errors.append(
            f"max_debt_to_income_ratio must be between 0 and 1, got {max_debt_to_income_ratio}"
        )
    
    # Check regulatory_capital_requirement (should be between 0 and 1)
    if not isinstance(regulatory_capital_requirement, (int, float)):
        errors.append("regulatory_capital_requirement must be a numeric value")
    elif regulatory_capital_requirement < 0 or regulatory_capital_requirement > 1:
        errors.append(
            f"regulatory_capital_requirement must be between 0 and 1, got {regulatory_capital_requirement}"
        )
    
    # ============================================================================
    # CHECK 2: Constraint conflicts
    # ============================================================================
    
    # Check 2.1: max_individual_limit should not exceed max_total_exposure
    if max_individual_limit > max_total_exposure:
        errors.append(
            f"max_individual_limit (${max_individual_limit:,.0f}) exceeds max_total_exposure "
            f"(${max_total_exposure:,.0f}). Individual limits cannot exceed total exposure."
        )
    
    # Check 2.2: min_profitability_target should be achievable given max_total_exposure
    # This is a heuristic check - we assume a minimum profitability per dollar of exposure
    # A reasonable minimum is 0.05 (5% return on exposure)
    minimum_profitability_per_dollar = 0.05
    max_achievable_profitability = max_total_exposure * minimum_profitability_per_dollar
    
    if min_profitability_target > max_achievable_profitability:
        warnings.append(
            f"min_profitability_target (${min_profitability_target:,.0f}) may be difficult to achieve "
            f"given max_total_exposure (${max_total_exposure:,.0f}). "
            f"Estimated maximum achievable profitability: ${max_achievable_profitability:,.0f}. "
            f"Consider increasing exposure or reducing target."
        )
    
    # Check 2.3: max_portfolio_default_risk should allow for some profitable customers
    # If default risk is too high (close to 1), it may be impossible to have profitable customers
    # We assume a minimum acceptable default risk of 0.01 (1%) for a viable portfolio
    if max_portfolio_default_risk > 0.95:
        warnings.append(
            f"max_portfolio_default_risk ({max_portfolio_default_risk:.2%}) is very high. "
            f"This may make it difficult to identify profitable customers. "
            f"Consider a more conservative default risk threshold."
        )
    
    # Check 2.4: max_portfolio_default_risk should be achievable given regulatory requirements
    # If regulatory capital requirement is very high, it may limit the feasible default risk
    if regulatory_capital_requirement > 0.15:
        warnings.append(
            f"regulatory_capital_requirement ({regulatory_capital_requirement:.2%}) is high. "
            f"This may limit the feasible portfolio size and default risk tolerance."
        )
    
    # ============================================================================
    # CHECK 3: Ratio consistency checks
    # ============================================================================
    
    # Check that max_debt_to_income_ratio is reasonable
    if max_debt_to_income_ratio < 0.1:
        warnings.append(
            f"max_debt_to_income_ratio ({max_debt_to_income_ratio:.2f}) is very low. "
            f"This may significantly limit loan sizes for customers."
        )
    
    # ============================================================================
    # FINAL VALIDATION RESULT
    # ============================================================================
    
    is_valid = len(errors) == 0
    
    result = {
        'is_valid': is_valid,
        'errors': errors,
        'warnings': warnings
    }
    
    return result


# ============================================================================
# TEST THE FUNCTION
# ============================================================================

print("\n" + "=" * 70)
print("Testing validate_constraints() Function")
print("=" * 70)

# Test 1: Valid constraint set
print("\n--- Test 1: Valid constraint set ---")
valid_constraints = get_constraint_set()
result = validate_constraints(valid_constraints)
print(f"Is valid: {result['is_valid']}")
print(f"Errors: {len(result['errors'])}")
print(f"Warnings: {len(result['warnings'])}")
if result['errors']:
    for error in result['errors']:
        print(f"  - {error}")
if result['warnings']:
    for warning in result['warnings']:
        print(f"  - {warning}")

# Test 2: Invalid constraint set (max_individual_limit > max_total_exposure)
print("\n--- Test 2: Invalid constraint set (conflicting limits) ---")
invalid_constraints = get_constraint_set(
    max_individual_limit=100000,
    max_total_exposure=50000
)
result = validate_constraints(invalid_constraints)
print(f"Is valid: {result['is_valid']}")
print(f"Errors: {len(result['errors'])}")
if result['errors']:
    for error in result['errors']:
        print(f"  - {error}")

# Test 3: Invalid constraint set (out of range values)
print("\n--- Test 3: Invalid constraint set (out of range values) ---")
invalid_constraints = get_constraint_set(
    max_portfolio_default_risk=1.5,
    min_profitability_target=-100000,
    max_debt_to_income_ratio=1.2
)
result = validate_constraints(invalid_constraints)
print(f"Is valid: {result['is_valid']}")
print(f"Errors: {len(result['errors'])}")
if result['errors']:
    for error in result['errors']:
        print(f"  - {error}")

# Test 4: Edge case - very high default risk
print("\n--- Test 4: Edge case (high default risk warning) ---")
edge_constraints = get_constraint_set(
    max_portfolio_default_risk=0.98
)
result = validate_constraints(edge_constraints)
print(f"Is valid: {result['is_valid']}")
print(f"Warnings: {len(result['warnings'])}")
if result['warnings']:
    for warning in result['warnings']:
        print(f"  - {warning}")

# Test 5: Edge case - very low debt-to-income ratio
print("\n--- Test 5: Edge case (low debt-to-income warning) ---")
edge_constraints = get_constraint_set(
    max_debt_to_income_ratio=0.05
)
result = validate_constraints(edge_constraints)
print(f"Is valid: {result['is_valid']}")
print(f"Warnings: {len(result['warnings'])}")
if result['warnings']:
    for warning in result['warnings']:
        print(f"  - {warning}")

print("\n" + "=" * 70)
print("validate_constraints() Function Tests Complete")
print("=" * 70)

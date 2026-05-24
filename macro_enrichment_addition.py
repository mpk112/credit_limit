# Macro Enrichment Component Additions
# ======================================

def fetch_macro_scenarios() -> Dict[str, Dict[str, float]]:
    """
    Define scenario parameters for macroeconomic conditions.
    
    This function defines scenario parameters for optimistic, baseline, and 
    adverse economic conditions that can be used for sensitivity analysis.
    
    Scenario Parameters
    -------------------
    Optimistic: Low unemployment, moderate GDP growth, stable rates
    Baseline: Historical averages (based on 2023 data)
    Adverse: High unemployment, low/negative GDP growth, elevated rates
    
    Returns
    -------
    dict
        Dictionary of scenario parameters with keys:
        - 'optimistic': Low unemployment, moderate GDP growth, stable rates
        - 'baseline': Historical averages
        - 'adverse': High unemployment, low/negative GDP growth, elevated rates
        
    Example
    -------
    >>> scenarios = fetch_macro_scenarios()
    >>> print(f"Optimistic GDP growth: {scenarios['optimistic']['gdp_growth']:.2f}%")
    >>> print(f"Adverse unemployment: {scenarios['adverse']['unemployment']:.1f}%")
    """
    scenarios = {
        'optimistic': {
            'gdp_growth': 3.5,      # Moderate GDP growth
            'unemployment': 3.5,    # Low unemployment
            'fed_rate': 4.0,        # Stable, moderate rates
            'cpi': 218.0,           # Stable CPI
            'inflation': 2.5        # Low inflation
        },
        'baseline': {
            'gdp_growth': 2.1,      # Historical average (2023 actual: ~2.1%)
            'unemployment': 3.8,    # Historical average (2023 actual: ~3.7%)
            'fed_rate': 5.3,        # Historical average (2023 average)
            'cpi': 294.0,           # Historical average (2023 actual: ~294)
            'inflation': 3.5        # Historical average (2023 actual: ~3.4%)
        },
        'adverse': {
            'gdp_growth': 0.5,      # Low or negative GDP growth
            'unemployment': 5.5,    # High unemployment
            'fed_rate': 6.0,        # Elevated interest rates
            'cpi': 305.0,           # Higher CPI
            'inflation': 5.0        # Higher inflation
        }
    }
    
    print("Scenario parameters defined:")
    for scenario_name, params in scenarios.items():
        print(f"  {scenario_name}:")
        print(f"    GDP Growth: {params['gdp_growth']:.1f}%")
        print(f"    Unemployment: {params['unemployment']:.1f}%")
        print(f"    Fed Rate: {params['fed_rate']:.1f}%")
        print(f"    CPI: {params['cpi']:.1f}")
        print(f"    Inflation: {params['inflation']:.1f}%")
    
    return scenarios


def enrich_customer_data(
    df: pd.DataFrame,
    macro_data: Dict[str, float]
) -> pd.DataFrame:
    """
    Enrich customer DataFrame with macroeconomic indicators.
    
    This function adds macroeconomic indicator columns to each customer record,
    allowing the model to account for economic conditions when making loan
    limit recommendations.
    
    Parameters
    ----------
    df : pd.DataFrame
        Customer DataFrame with customer records
    macro_data : dict
        Dictionary containing macroeconomic indicators with keys:
        'gdp_growth', 'unemployment', 'fed_rate', 'cpi', 'inflation'
        
    Returns
    -------
    pd.DataFrame
        Customer DataFrame with added macro indicator columns:
        - macro_gdp_growth
        - macro_unemployment
        - macro_fed_rate
        - macro_cpi
        - macro_inflation
        
    Raises
    ------
    ValueError
        If required macro indicators are missing from macro_data
    RuntimeError
        If not all customers have macro data after merge
        
    Examples
    --------
    >>> macro_data = fetch_macro_data(2023)
    >>> enriched_df = enrich_customer_data(customers_df, macro_data)
    >>> print(enriched_df[['macro_gdp_growth', 'macro_unemployment']].head())
    """
    # Step 1: Validate macro_data contains all required indicators
    required_indicators = ['gdp_growth', 'unemployment', 'fed_rate', 'cpi', 'inflation']
    missing_indicators = [ind for ind in required_indicators if ind not in macro_data]
    
    if missing_indicators:
        raise ValueError(
            f"macro_data is missing required indicators: {missing_indicators}. "
            f"Expected keys: {required_indicators}"
        )
    
    # Step 2: Add macro indicator columns to each customer record
    # Since macro data is constant across all customers, we broadcast the values
    df_enriched = df.copy()
    
    df_enriched['macro_gdp_growth'] = macro_data['gdp_growth']
    df_enriched['macro_unemployment'] = macro_data['unemployment']
    df_enriched['macro_fed_rate'] = macro_data['fed_rate']
    df_enriched['macro_cpi'] = macro_data['cpi']
    df_enriched['macro_inflation'] = macro_data['inflation']
    
    print(f"Added macroeconomic indicators to {len(df_enriched)} customer records")
    
    # Step 3: Validate all customers have macro data after merge
    missing_macro = df_enriched[['macro_gdp_growth', 'macro_unemployment', 
                                  'macro_fed_rate', 'macro_cpi', 'macro_inflation']].isnull().sum()
    
    if missing_macro.any():
        raise RuntimeError(
            f"Not all customers have macro data after merge. "
            f"Missing values: {missing_macro[missing_macro > 0].to_dict()}"
        )
    
    print("All customers have macro data after merge")
    
    return df_enriched

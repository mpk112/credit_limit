# Architecture — Loan Limit Term Extension Optimisation System

**Notebook:** `loan_limit_term_extension.ipynb`  
**Branch:** `term_extension`  
**Cells:** 35 | **Runtime:** < 30 seconds | **Accounts:** 30,000

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INPUT LAYER                                           │
│                                                                          │
│   loan_limit_increases.csv          FRED API / cache/macro_2023.json    │
│   (30,000 accounts × 6 features)    (GDP, Unemployment, Fed Rate, CPI)  │
└────────────────────┬────────────────────────────┬────────────────────────┘
                     │                            │
                     ▼                            ▼
┌────────────────────────────────┐   ┌────────────────────────────────────┐
│  STAGE 1 · Data Preprocessing  │   │  STAGE 3 · Macro Enrichment        │
│  Cell 5                        │   │  Cell 9                            │
│                                │   │                                    │
│  • Load & validate 30,000 rows │   │  • fetch_macro_data()              │
│  • Rename columns              │   │    → FRED API (GDPC1, UNRATE,      │
│  • Eligibility gate:           │   │      FEDFUNDS, CPIAUCSL)           │
│    days_since_last_loan ≥ 60   │   │    → disk cache fallback           │
│    → 25,068 eligible           │   │    → baseline defaults fallback    │
│  • StandardScaler normalise    │   │  • fetch_macro_scenarios()         │
│  • Borda-count credit score:   │   │    → optimistic / baseline / adv.  │
│    0.35·payment + 0.30·disc +  │   │  • enrich_with_macro()             │
│    0.20·recency + 0.15·value   │   │    → unemp adj → +λ hazard         │
└────────────────────┬───────────┘   │    → GDP adj  → +term days         │
                     │               │    → macro cols on every customer   │
                     ▼               └──────────────┬─────────────────────┘
┌────────────────────────────────┐                  │
│  STAGE 2 · Credit Scoring      │◄─────────────────┘
│  Cell 7                        │
│                                │
│  • risk_rank = 1 − credit_score│
│  • KMeans(k=4) on risk_rank    │
│  • Centroid ordering:          │
│    lowest risk → Excellent     │
│    highest risk → Poor         │
│  • Output: credit_state column │
│                                │
│  States:  Excellent / Good /   │
│           Fair / Poor          │
└────────────────────┬───────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
┌─────────────────────┐  ┌─────────────────────────────────────────────────┐
│  STAGE 4 · Markov   │  │  STAGE 5 · Monte Carlo Simulation               │
│  Cell 11            │  │  Cell 15                                         │
│                     │  │                                                  │
│  build_transition_  │  │  simulate_term_extensions()                      │
│  matrix()           │  │  Vectorised — no Python loops                    │
│                     │  │                                                  │
│  4×4 matrix:        │  │  Per customer (all 30k as matrix ops):           │
│  Exc→{E,G,F,P}      │  │  • T ~ lognorm(_ln_params(mean,std))            │
│  Goo→{E,G,F,P}      │  │    clipped [30, 180] days                       │
│  Fai→{E,G,F,P}      │  │  • p_def_T = 1−exp(−λ·T/365)                   │
│  Poo→{E,G,F,P}      │  │  • is_early ~ Bernoulli(p_early_s)              │
│                     │  │  • is_default ~ Bernoulli(p_def_T) if ¬early    │
│  Eigenvalue         │  │                                                  │
│  decomposition →    │  │  NPV:                                            │
│  steady-state probs │  │  • revenue = $40 × annuity_factor(T, r=19%)     │
│                     │  │  • loss = L×LGD×1(default)×exp(−r·T/730)       │
│  Base steady-state: │  │                                                  │
│  Exc 19% Goo 34%    │  │  3,500 iterations per customer                  │
│  Fai 26% Poo 21%    │  │  Runtime: 4.9 seconds                           │
└─────────┬───────────┘  │                                                  │
          │              │  Outputs per customer:                           │
          │              │  • expected_revenue, expected_loss               │
          │              │  • profitability_score                           │
          │              │  • p_default_sim, p_early_sim                   │
          │              │  • expected_term_days                            │
          └──────────────┴────────────────────┬────────────────────────────┘
                                              │
                                              ▼
                              ┌───────────────────────────────┐
                              │  STAGE 6 · GBM Uptake Forecast│
                              │  Cell 13                       │
                              │                                │
                              │  forecast_uptake()             │
                              │                                │
                              │  U_T = μ_i · exp(             │
                              │    −½σ²·dt + σ·dW)            │
                              │  dW ~ N(0, √dt)               │
                              │                                │
                              │  Per-state params:             │
                              │  Exc: μ=0.80, σ=0.10          │
                              │  Goo: μ=0.70, σ=0.12          │
                              │  Fai: μ=0.55, σ=0.16          │
                              │  Poo: μ=0.35, σ=0.20          │
                              │                                │
                              │  Macro drift adj:              │
                              │  optimistic: +0.02             │
                              │  adverse:    −0.03             │
                              │                                │
                              │  Output: uptake_probability    │
                              └───────────────┬────────────────┘
                                              │
                                              ▼
                              ┌───────────────────────────────┐
                              │  STAGE 7 · LP Optimisation    │
                              │  Cell 19                       │
                              │                                │
                              │  optimize_extensions_lp()      │
                              │                                │
                              │  Decision: x_i ∈ {0,1}        │
                              │                                │
                              │  Objective:                    │
                              │  max Σ profitability_i         │
                              │      × uptake_i × x_i         │
                              │                                │
                              │  Constraints:                  │
                              │  (1) Σ(p_def_i−0.05)·L_i·x_i  │
                              │      ≤ 0  (5% risk cap)        │
                              │  (2) Σ L_i·x_i ≤ $500M        │
                              │  (3) x_i=0 if ineligible       │
                              │                                │
                              │  Solver: SciPy HiGHS (LP       │
                              │  relaxation + rounding)        │
                              └───────────────┬────────────────┘
                                              │
                          ┌───────────────────┴──────────────────┐
                          │          LP–MARKOV FEEDBACK           │
                          │          Cell 21  (5 iterations)      │
                          │                                        │
                          │  lp_markov_feedback()                  │
                          │                                        │
                          │  Each iteration:                       │
                          │  1. Run LP → get granted[]             │
                          │  2. apply_policy_to_transitions()      │
                          │     shift = 0.12 × frac_granted        │
                          │     Poor→Good prob increases           │
                          │  3. Recompute steady-state             │
                          │  4. Rescale default_risk               │
                          │  5. Re-run LP with updated risks       │
                          │                                        │
                          │  Converges when Δgranted < 0.5        │
                          │                                        │
                          │  Poor steady-state: 21% → 16.7%       │
                          └───────────────────┬──────────────────┘
                                              │
                     ┌────────────────────────┴──────────────────────┐
                     │                                                │
                     ▼                                                ▼
        ┌────────────────────────┐              ┌──────────────────────────────┐
        │  STAGE 8 · Validation  │              │  STAGE 9 · Sensitivity       │
        │  Cell 23               │              │  Cell 25                     │
        │                        │              │                              │
        │  validate_solution()   │              │  sensitivity_analysis()      │
        │                        │              │                              │
        │  45 property checks:   │              │  3 scenarios:                │
        │  P1  30,000 customers  │              │  Optimistic: risk×0.80       │
        │  P2  eligibility       │              │              loss×0.85       │
        │  P3  finite scores     │              │              cap×1.10        │
        │  P4  non-neg revenue   │              │  Baseline:   ×1.00           │
        │  P5  non-neg loss      │              │  Adverse:    risk×1.35       │
        │  P6  binary grants     │              │              loss×1.25       │
        │  ...                   │              │              cap×0.90        │
        │  P45 CSV export        │              │                              │
        │                        │              │  Re-runs full LP per scenario│
        └────────────────────────┘              └──────────────────────────────┘
                     │                                                │
                     └────────────────────────┬──────────────────────┘
                                              │
                     ┌────────────────────────┴──────────────────────┐
                     │                                                │
                     ▼                                                ▼
        ┌────────────────────────┐              ┌──────────────────────────────┐
        │  STAGE 10 · Charts     │              │  STAGE 11 · Export           │
        │  Cell 29               │              │  Cell 31                     │
        │                        │              │                              │
        │  12 visualisations:    │              │  term_extension_results.csv  │
        │  01 states_risk        │              │  (30,000 rows × 13 cols)     │
        │  02 term_outcomes      │              │                              │
        │  03 profitability      │              │  Columns:                    │
        │  04 lp_results         │              │  customer_id                 │
        │  05 markov             │              │  credit_state                │
        │  06 sensitivity        │              │  eligible                    │
        │  07 uptake             │              │  extension_granted           │
        │  08 decision_boundary  │              │  p_default_sim               │
        │  09 pareto_curve       │              │  p_early_sim                 │
        │  10 term_uptake        │              │  expected_term_days          │
        │  11 sensitivity_detail │              │  uptake_probability          │
        │  12 risk_cap_slack     │              │  profitability_score         │
        │                        │              │  expected_revenue            │
        └────────────────────────┘              │  expected_loss               │
                                                └──────────────────────────────┘
```

---

## Stage Summary Table

| Stage | Cells | Component | Method | Key Output |
|-------|-------|-----------|--------|------------|
| 1 | 5 | Data Preprocessing | pandas, StandardScaler, Borda-count | `credit_score`, `eligible` |
| 2 | 7 | Credit Scoring | K-Means on `risk_rank` (k=4) | `credit_state` ∈ {Excellent, Good, Fair, Poor} |
| 3 | 9 | Macro Enrichment | FRED API → cache → baseline fallback | `macro_*` cols, adjusted `default_risk` |
| 4 | 11 | Markov Chain | 4×4 transition matrix, eigenvalue steady-state | `TransitionMatrix`, steady-state probs |
| 5 | 15 | Monte Carlo | Vectorised (n_customers × 3,500) NumPy ops | `profitability_score`, `p_default_sim` |
| 6 | 13 | GBM Uptake | Geometric Brownian Motion per state | `uptake_probability` |
| 7 | 19 | LP Optimisation | Binary ILP, SciPy HiGHS solver | `extension_granted` ∈ {0, 1} |
| 8 | 21 | LP–Markov Feedback | 5-iteration policy feedback loop | Adjusted transition matrix, converged grants |
| 9 | 23 | Validation | 45 property tests | Pass/fail report |
| 10 | 25 | Sensitivity | 3 macro scenarios × full LP re-run | Scenario comparison table |
| 11 | 29 | Visualisations | matplotlib / seaborn | 12 PNG charts |
| 12 | 31 | Export | CSV | `term_extension_results.csv` |

---

## Data Flow

```
loan_limit_increases.csv
        │
        ▼
  df_raw (30,000 × 6)
        │
        ├── eligible flag (25,068 pass)
        │
        ▼
  df + credit_state
        │
        ├── macro_* columns (FRED / cache)
        │
        ▼
  df + default_risk adjusted
        │
        ├── TransitionMatrix (4×4)
        │
        ▼
  df + profitability_score, p_default_sim, expected_term_days
        │
        ├── uptake_probability (GBM)
        │
        ▼
  LP input: profit_scores = profitability × uptake
        │
        ├── 5× LP–Markov feedback loop
        │
        ▼
  results_df: extension_granted ∈ {0,1} for all 30,000
        │
        ├── validation (45 checks)
        ├── sensitivity (3 scenarios)
        ├── 12 charts
        └── term_extension_results.csv
```

---

## Key Parameters

| Parameter | Value | Configurable via env var |
|-----------|-------|--------------------------|
| Accounts | 30,000 | — |
| Eligible accounts | 25,068 | `MIN_DAYS_SINCE_LOAN=60` |
| Monte Carlo iterations | 3,500 | `SIMULATION_ITERATIONS` |
| NPV discount rate | 19% | `NPV_DISCOUNT_RATE` |
| LGD | 60% | `LGD` |
| Profit per extension | $40 | `PROFIT_PER_EXTENSION` |
| Max portfolio default risk | 5% | `MAX_PORTFOLIO_DEFAULT_RISK` |
| Max total exposure | $500M | `MAX_TOTAL_EXPOSURE` |
| Batch size (MC) | 5,000 | `BATCH_SIZE` |
| LP–Markov iterations | 5 | hardcoded |
| Property tests | 45 / 45 passing | — |

---

## Results (Baseline Scenario)

| Metric | Value |
|--------|-------|
| Extensions granted | 22,887 (76.3% overall · 91.3% of eligible) |
| Total extended exposure | $59,980,315 |
| Projected revenue | $899,373 |
| Projected expected losses | $298,485 |
| Net projected profit | $600,888 |
| Return on exposure | 1.04% |
| Portfolio default risk | 0.84% (cap: 5.0% — slack by 4.2 pp) |
| Average extension term | 68.5 days |
| Poor steady-state (post-feedback) | 16.7% (down from 21.0%) |

# Architecture — Multi-Period Lifecycle Simulation

**Notebook:** `loan_limit_lifecycle.ipynb`  
**Branch:** `term_ext_lifecycle`  
**Cells:** 24 | **Accounts:** 30,000 | **Default window:** 1 year / 12 monthly campaigns

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                                      │
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
│  • Rename columns              │   │    → FRED API / cache / defaults   │
│  • Eligibility gate:           │   │  • enrich_with_macro()             │
│    days_since_last_loan ≥ 60   │   │    → unemp adj → +λ hazard         │
│  • Borda-count credit score:   │   │    → GDP adj  → +term days         │
│    0.35·payment + 0.30·disc +  │   │  • create_constraints()            │
│    0.20·recency + 0.15·value   │   │    → risk cap 5%, exposure $500M   │
└────────────────────┬───────────┘   └──────────────┬─────────────────────┘
                     │                              │
                     ▼                              │
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
└────────────────────┬───────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│  STAGE 4 · Helper Function Definitions  (Cell 12, 14, 16, 17)          │
│                                                                         │
│  forecast_uptake()          simulate_term_extensions()                  │
│  GBM per-state params:      Vectorised Monte Carlo:                     │
│  Exc: μ=0.80, σ=0.10        T ~ lognorm clipped [30,180]d              │
│  Goo: μ=0.70, σ=0.12        p_def_T = 1−exp(−λ·T/365)                 │
│  Fai: μ=0.55, σ=0.16        revenue = $40 × annuity_factor(T, r=19%)  │
│  Poo: μ=0.35, σ=0.20        loss = L×LGD×p_def×exp(−r·T/730)         │
│                                                                         │
│  optimize_extensions_lp()                                               │
│  max Σ profitability_i × uptake_i × x_i                                │
│  s.t. Σ(p_def_i−0.05)·L_i·x_i ≤ 0  (5% risk cap)                     │
│       Σ L_i·x_i ≤ $500M             (exposure cap)                     │
│                                                                         │
│  NOTE: These functions are NOT called here. They are called             │
│        inside simulate_lifecycle() on each campaign's eligible pool.   │
└────────────────────┬───────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│  STAGE 5 · Lifecycle Configuration & Re-scoring Helper  (Cell 19)      │
│                                                                         │
│  Config:                         Frozen reference distributions (t=0): │
│  SIMULATION_YEARS        = 1     _lc_ref['ontime']  = sorted 30K vals  │
│  CAMPAIGN_INTERVAL_DAYS  = 30    _lc_ref['numinc']  = sorted 30K vals  │
│  LIFECYCLE_MC_ITER       = 200   _lc_ref['days']    = sorted 30K vals  │
│  ONTIME_PAYMENT_BOOST    = +2pp  _lc_ref['profit']  = sorted 30K vals  │
│  EARLY_PAYMENT_BOOST     = +1pp                                         │
│  DEFAULT_PAYMENT_PENALTY = −10pp K-Means centroids re-fit on df_raw   │
│                                  (same k=4, seed=42 as Stage 2)        │
│                                                                         │
│  _lc_rescore(idx):                                                      │
│  1. searchsorted → percentile rank against frozen t=0 arrays           │
│  2. Borda-count → risk_rank                                             │
│  3. argmin(|risk_rank − centroids|) → new credit_state                 │
│  4. default_risk = base[state] × (0.5 + within-state percentile)       │
└────────────────────┬───────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│  STAGE 6 · simulate_lifecycle()  (Cell 20)                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Campaign Loop  (×N_CAMPAIGNS, every CAMPAIGN_INTERVAL_DAYS)    │   │
│  │                                                                   │   │
│  │  Step 1a — Advance time                                          │   │
│  │    feat_days[idle]   += interval                                  │   │
│  │    ext_rem[active]   -= interval                                  │   │
│  │                                                                   │   │
│  │  Step 1b — Complete extensions (ext_rem ≤ 0)                    │   │
│  │    u1 < p_early  → early repayment  (+1pp on_time_pct)          │   │
│  │    u2 < p_def_T  → default          (−10pp on_time_pct)         │   │
│  │    else          → on-time          (+2pp on_time_pct)           │   │
│  │    Revenue earned regardless; loss only on default               │   │
│  │    → _lc_rescore() on completing customers                       │   │
│  │                                                                   │   │
│  │  Step 2 — Eligibility check                                      │   │
│  │    elig = ~active & feat_days ≥ MIN_DAYS_SINCE_LOAN              │   │
│  │                                                                   │   │
│  │  Step 3 — Monte Carlo + GBM + LP on eligible subset             │   │
│  │    simulate_term_extensions(cdf, n_iter=LIFECYCLE_MC_ITER)       │   │
│  │    forecast_uptake(cdf, macro)                                    │   │
│  │    optimize_extensions_lp(cdf, constraints)                      │   │
│  │    (all stdout suppressed via redirect_stdout)                   │   │
│  │                                                                   │   │
│  │  Step 4 — Bernoulli acceptance draw                              │   │
│  │    accept = rng.random() < uptake_probability                    │   │
│  │    (LP grants offer; this decides who takes it)                  │   │
│  │                                                                   │   │
│  │  Step 5 — Draw actual term T for acceptors                       │   │
│  │    T = clip(exp(μ_ln + σ_ln × N(0,1)), 30, 180)                 │   │
│  │    ext_active, ext_rem, ext_lam, ext_p_early, ext_blc set        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Outputs:                                                               │
│  lc_customers  — per-customer lifetime summary (30,000 rows)           │
│  lc_campaigns  — per-campaign log (N_CAMPAIGNS rows)                   │
└────────────────────┬───────────────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌──────────────────────┐  ┌──────────────────────────────────────────────┐
│  STAGE 7 · Results   │  │  STAGE 8 · Sensitivity Analysis              │
│  Cell 21             │  │  Cell 23                                     │
│                      │  │                                              │
│  Per-state summary:  │  │  Grid: 3 × 3 = 9 combinations               │
│  avg extensions,     │  │  ONTIME_BOOST ∈ [0.5, 2.0, 5.0] pp         │
│  avg profit,         │  │  DEFAULT_PENALTY ∈ [5, 10, 20] pp           │
│  default rate,       │  │                                              │
│  final state dist.   │  │  Per run: 180d / 7d interval / 500 MC iter  │
│                      │  │                                              │
│  Credit migration    │  │  Outputs:                                    │
│  4×4 crosstab        │  │  • Net profit pivot table                   │
│  initial → final     │  │  • Default rate pivot table                 │
│                      │  │  • % Excellent / Poor pivot tables          │
│  4 charts:           │  │  • 2 sensitivity charts                     │
│  cumulative profit   │  │  • lifecycle_sensitivity.csv                │
│  extensions hist     │  │                                              │
│  state drift bars    │  └──────────────────────────────────────────────┘
│  portfolio risk      │
│                      │
│  lifecycle_results   │
│  .csv (30,000 rows)  │
└──────────────────────┘
```

---

## Stage Summary Table

| Stage | Cell | Component | Method | Key Output |
|-------|------|-----------|--------|------------|
| 1 | 5 | Data Preprocessing | pandas, Borda-count, StandardScaler | `credit_score`, `eligible` |
| 2 | 7 | Credit Scoring | K-Means (k=4, seed=42) on `risk_rank` | `credit_state` ∈ {Excellent, Good, Fair, Poor} |
| 3 | 9 | Macro Enrichment | FRED API → cache → baseline fallback | `macro_data`, adjusted `default_risk`, `constraints` |
| 4 | 12,14,16,17 | Helper Definitions | GBM, vectorised Monte Carlo, LP (HiGHS) | Function objects only — not executed here |
| 5 | 19 | Lifecycle Config | Frozen t=0 refs, K-Means re-fit, `_lc_rescore()` | `_lc_ref`, `_lc_cents`, `_lc_ref_rr` |
| 6 | 20 | Lifecycle Simulation | Campaign loop — MC → GBM → LP → Bernoulli → outcome | `lc_customers`, `lc_campaigns` |
| 7 | 21 | Results & Charts | pandas crosstab, matplotlib | 4 charts, `lifecycle_results.csv` |
| 8 | 23 | Sensitivity Analysis | 9-combo parameter grid, 180d sub-simulation | 4 pivot tables, 2 charts, `lifecycle_sensitivity.csv` |

---

## Key Differences vs One-Shot Model

| Aspect | One-Shot | Lifecycle |
|--------|----------|-----------|
| LP runs | 1 (all 30K) | 1 per campaign (eligible subset) |
| Acceptance | Implicit — uptake weights LP objective | Explicit Bernoulli draw on `uptake_probability` |
| Extension term | Monte Carlo mean (`expected_term_days`) | Actual lognormal draw per extension |
| Outcome | Expected loss/revenue | Realised draw (early / on-time / default) |
| Credit state | Fixed at t=0 | Re-scored after every extension outcome |
| Feature update | None | `on_time_pct` ± pp based on outcome |
| Markov chain | LP–Markov 5-iteration feedback | Removed — feature update replaces it |

---

## Data Flow

```
loan_limit_increases.csv
        │
        ▼
  df_raw (30,000 × 6)  ──────────────────────────────────────────────────────┐
        │                                                               frozen │
        ▼                                                          reference  │
  df + credit_state + default_risk                               distributions│
        │                                                           (_lc_ref) │
        ├── macro_data + constraints                                           │
        │                                                                      │
        ▼                                                                      │
  Helper functions defined                                                     │
  (forecast_uptake, simulate_term_extensions, optimize_extensions_lp)         │
        │                                                                      │
        ▼                                                                      │
  Lifecycle config + _lc_rescore() ◄────────────────────────────────────────┘
        │
        ▼
  Campaign loop (×N_CAMPAIGNS):
    eligible customers → MC → GBM → LP → accept? → draw T → track extension
    completing extensions → draw outcome → update features → _lc_rescore()
        │
        ▼
  lc_customers (per-customer lifetime) + lc_campaigns (per-campaign log)
        │
        ├── 4 result charts + lifecycle_results.csv
        └── 9-combo sensitivity grid + 2 sensitivity charts + lifecycle_sensitivity.csv
```

---

## Key Parameters

| Parameter | Default | Env var override |
|-----------|---------|-----------------|
| `SIMULATION_YEARS` | 1 | `SIMULATION_YEARS` |
| `CAMPAIGN_INTERVAL_DAYS` | 30 | `CAMPAIGN_INTERVAL_DAYS` |
| `LIFECYCLE_MC_ITER` | 200 | `LIFECYCLE_MC_ITER` |
| `ONTIME_PAYMENT_BOOST` | 2.0 pp | `ONTIME_PAYMENT_BOOST` |
| `EARLY_PAYMENT_BOOST` | 1.0 pp | `EARLY_PAYMENT_BOOST` |
| `DEFAULT_PAYMENT_PENALTY` | 10.0 pp | `DEFAULT_PAYMENT_PENALTY` |
| `NPV_DISCOUNT_RATE` | 19% | `NPV_DISCOUNT_RATE` |
| `LGD` | 60% | `LGD` |
| `PROFIT_PER_EXTENSION` | $40 | `PROFIT_PER_EXTENSION` |
| `MIN_DAYS_SINCE_LOAN` | 60 days | `MIN_DAYS_SINCE_LOAN` |
| `MAX_PORTFOLIO_DEFAULT_RISK` | 5% | `MAX_PORTFOLIO_DEFAULT_RISK` |
| `MAX_TOTAL_EXPOSURE` | $500M | `MAX_TOTAL_EXPOSURE` |

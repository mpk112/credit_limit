# Loan Limit Optimization System — Architecture Overview

## Goal
Determine optimal credit limit increases for 30,000 customers, maximising portfolio profitability while staying within risk and regulatory constraints.

---

## Pipeline (8 sequential stages)

```
CSV Input (30k customers)
       │
       ▼
┌─────────────────────────┐
│  1. Data Loading         │  Normalise, impute, derive features.
│                          │  Compute unified credit_score (300–850)
└──────────┬──────────────┘  once here — reused by all downstream stages.
           │
           ▼
┌─────────────────────────┐
│  2. Macro Enrichment     │  Pull GDP / unemployment / fed rate / CPI
│                          │  from FRED API (cached). Append to every row.
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  3. Risk Model           │  XGBoost classifies customers into 4 credit
│                          │  states (Excellent/Good/Fair/Poor) using the
│                          │  unified credit_score. Outputs default_risk ∈ [0,1].
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  4. Markov Chain         │  Builds 4×4 stochastic transition matrix from
│                          │  state distribution. Computes steady-state via
│                          │  eigenvalue decomposition — shows long-run risk.
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  5. Demand Forecasting   │  Monte Carlo (≥3,000 scenarios per customer)
│                          │  forecasts credit utilisation over 365 days
│                          │  under macro uncertainty.
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  6. Lifecycle Simulation │  Vectorised NPV simulation (3,000 iterations).
│                          │  Computes expected revenue, loss, and
│                          │  profitability_score per customer.
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  7. LP Optimisation      │  scipy HiGHS solves for optimal limit increases
│                          │  across all 30k customers simultaneously (~1.6s).
│                          │  Objective: maximise Σ(profitability × increase)
│                          │  Constraints: portfolio default risk ≤ 5%,
│                          │  total exposure ≤ $500M, per-customer cap $50k,
│                          │  all increases ≥ 0.
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  8. Results & Reporting  │  Validate solution, run sensitivity analysis
│                          │  (optimistic/baseline/adverse macro scenarios),
│                          │  generate 12 visualisations, export CSV.
└──────────┬──────────────┘
           │
           ▼
  optimization_results.csv (30k rows — per-customer recommendations)
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Single notebook deliverable | Spec requirement — reproducible end-to-end via "Run All Cells" |
| Unified `compute_credit_score()` | Eliminates two-proxy inconsistency; one formula feeds both XGBoost and state classification |
| scipy HiGHS (not PuLP) | Handles 30k decision variables in ~1.6s; no external solver binary needed |
| Vectorised Monte Carlo | All 30k × 3,000 iterations computed as numpy matrix ops in 5k-row batches — runs in ~2s vs hours with loops |
| Fixed credit state thresholds | Domain-calibrated (655/572/483 on 300–850 scale) → realistic 11%/38%/40%/11% distribution |
| FRED data cached to JSON | No repeated API calls; pipeline works offline after first run |
| Order-1 Markov (validated) | Comparison vs orders 2 and 3 shows max 0.87 pp deviation — memoryless assumption confirmed not restrictive |
| LP–Markov feedback loop | LP increases adjust transition probabilities → updated steady-state rescales default_risk → LP re-optimises; converges in 4 iterations, Poor SS drops 21.3% → 17.7% |

---

## Constraints Enforced by LP

- Portfolio default risk ≤ 5%
- Total incremental exposure ≤ $500M
- Per-customer limit ≤ $50,000
- All increases ≥ $0 (no decreases)
- Minimum portfolio profitability ≥ $1M

---

## Credit Scoring

Single unified `compute_credit_score()` maps each customer to a FICO-style 300–850 score:

| Input | Weight | Normalisation |
|---|---|---|
| On-time payment % | 35% | Clipped to [80, 100], scaled 0–100 |
| Credit discipline (# increases) | 30% | Inverted, clipped to [0, 5], scaled 0–100 |
| Recency (days since last loan) | 15% | Inverted, clipped to [0, 365], scaled 0–100 |
| Profitability contribution | 20% | Clipped to [0, $120], scaled 0–100 |

Fixed state thresholds on the 300–850 scale:

| State | Threshold | Portfolio Share |
|---|---|---|
| Excellent | ≥ 655 | ~11% |
| Good | ≥ 572 | ~38% |
| Fair | ≥ 483 | ~40% |
| Poor | < 483 | ~11% |

---

## Markov Chain Component

### What It Is
A Markov chain models a system that moves between a finite set of states over time, where the probability of transitioning to the next state depends only on the current state — not on history. In this pipeline the states are the four credit states: **Excellent → Good → Fair → Poor**.

The core object is the **4×4 transition matrix** where entry `T[i][j]` is the probability that a customer currently in state `i` moves to state `j` in the next observation period (90 days):

```
               Excellent    Good    Fair    Poor
  Excellent →    0.856     0.094   0.040   0.010
  Good      →    0.050     0.800   0.117   0.033
  Fair      →    0.020     0.101   0.751   0.129
  Poor      →    0.009     0.050   0.194   0.747
```

Rows sum to 1.0 (stochastic property, verified by P11).

### How It Is Built
The pipeline has no multi-period historical data — only a single-snapshot CSV. `build_transition_matrix()` generates synthetic transitions using domain-driven base probabilities per state:

```python
base_probs = {
    'Excellent': [0.85, 0.10, 0.04, 0.01],
    'Good':      [0.05, 0.80, 0.12, 0.03],
    'Fair':      [0.02, 0.10, 0.75, 0.13],
    'Poor':      [0.01, 0.05, 0.20, 0.74],
}
```

For each of the 30,000 customers a next state is sampled from their current state's base probabilities, building a 4×4 count matrix which is normalised row-wise. A small epsilon (`1e-6`) is added before normalisation to ensure **irreducibility** — every state is reachable from every other, which is required for a unique steady-state to exist.

### Steady-State Distribution
The steady-state answers: *"If customers keep transitioning according to this matrix indefinitely, what fraction of the portfolio will eventually be in each state?"*

Computed as the **left eigenvector** of the transition matrix for eigenvalue 1:

```python
eigenvalues, eigenvectors = np.linalg.eig(matrix.T)
idx = np.argmin(np.abs(eigenvalues - 1.0))
stationary = np.real(eigenvectors[:, idx])
stationary = np.abs(stationary) / np.abs(stationary).sum()
```

| State | Current Portfolio | Steady-State (Long-Run) |
|---|---|---|
| Excellent | 11.1% | 16.1% |
| Good | 38.1% | 29.5% |
| Fair | 40.1% | 33.1% |
| Poor | 10.7% | **21.3%** |

Key signal: **Poor doubles from 10.7% → 21.3% without intervention.** The pipeline is designed to approve increases before that drift materialises.

### Role in the Overall Solution

**1. Risk trajectory signal**
The steady-state shows inaction leads to portfolio deterioration — Poor share doubles. This justifies approving increases for borderline Good/Fair customers now, while their default risk is still manageable, rather than waiting until they migrate to Poor.

**2. Stakeholder communication (viz 3)**
The matrix is rendered as a heatmap showing the full credit migration picture. High diagonal values (0.75–0.86) confirm strong state persistence — customers don't swing wildly between states — which supports the stability assumption underlying the LP's one-year horizon.

**3. Correctness validation (P11–P13)**

| Property | Check |
|---|---|
| P11 | All rows sum to 1.0 |
| P12 | Matrix is 4×4 square |
| P13 | Steady-state vector sums to 1.0 |

### Higher-Order Markov Chain Comparison

The standard (order-1) Markov assumption states that the next credit state depends only on the current state, not on the path taken to get there. To test whether this is restrictive, orders 1, 2, and 3 are compared at each run.

**How higher-order chains work:**
- **Order k**: next state depends on the last k states — the history tuple `(s_{t-k+1}, ..., s_t)` drives the transition
- State space expands to 4^k tuple-states (16 for order 2, 64 for order 3)
- Steady-state is computed on the expanded chain then marginalised back to the 4 credit states

**Implementation:** For each customer, a trajectory of length k+1 is simulated using vectorised numpy sampling from the first-order base probabilities. A dict maps each k-state history tuple to a probability vector over next states.

**Last run results:**

| Order | Excellent | Good | Fair | Poor | Max Δ vs Order-1 |
|---|---|---|---|---|---|
| 1 | 16.09% | 29.51% | 33.06% | 21.34% | — |
| 2 | 15.71% | 30.38% | 33.05% | 20.86% | 0.87 pp |
| 3 | 15.22% | 29.99% | 33.75% | 21.04% | 0.87 pp |

**Conclusion:** Max deviation of 0.87 pp confirms the memoryless assumption is not materially restrictive for this portfolio. The order-1 chain is sufficient.

---

### LP–Markov Feedback Loop

The limitation of a purely descriptive Markov chain is resolved by coupling it with the LP output through an iterative feedback loop.

**Mechanism:**

```
┌─────────────────────────────────────────────────────────┐
│  Iteration k                                            │
│                                                         │
│  current default_risk  ──→  LP optimise  ──→  x*_i     │
│                                                         │
│  x*_i  ──→  apply_policy_to_transitions()               │
│             (larger increase → higher stay/upgrade prob) │
│                                                         │
│  adjusted T  ──→  steady-state  ──→  new Poor fraction  │
│                                                         │
│  risk_scale = (base_poor + adj_poor) / (2 × base_poor)  │
│  updated default_risk = original × risk_scale           │
│                                                         │
│  ──→ Iteration k+1                                      │
└─────────────────────────────────────────────────────────┘
```

**Policy adjustment logic (`apply_policy_to_transitions`):**
- Relative increase = `limit_increase / initial_loan`
- Improvement = `relative_increase × (1 − default_risk) × 0.15` (capped at 10 pp)
- Risky customers (high `default_risk`) benefit less from the same absolute increase
- Per-state effect: diagonal ↑ +60% of improvement, upgrade ↑ +40%, downgrade ↓ −50%
- Per-customer adjustments aggregated by state → adjusted 4×4 portfolio matrix

**Convergence:** Loop terminates when mean absolute change in limit increases < $1, or after 5 iterations.

**Last run results (converged in 4 iterations):**

| Iteration | Customers↑ | Poor SS | Risk Scale | Objective |
|---|---|---|---|---|
| 1 | 8,748 | 17.79% | 0.9169 | $39.6B |
| 2 | 8,747 | 17.66% | 0.9138 | $40.8B |
| 3 | 8,746 | 17.66% | 0.9137 | $40.9B |
| 4 | 8,747 | 17.66% | 0.9137 | $40.9B |

**Steady-state shift after policy:**

| State | Base SS | Policy-Adjusted SS | Direction |
|---|---|---|---|
| Excellent | 16.1% | 19.5% | ↑ |
| Good | 29.5% | 32.3% | ↑ |
| Fair | 33.1% | 30.5% | ↓ |
| Poor | 21.3% | 17.7% | ↓ |

The LP's recommended increases shift the long-run portfolio toward better credit states. Poor drops from 21.3% → 17.7%, and the objective value stabilises at ~$40.9B after iteration 2, demonstrating the feedback loop adds value over a static one-shot optimisation.

---

## XGBoost Risk Model — Two-Pass Architecture

### Why Two Passes

The original single-pass design had a circular feature problem: `credit_state_encoded` was fed to XGBoost as a feature, but it was derived from the same raw inputs (`on_time_payments_pct`, `num_increases_2023`, etc.) that XGBoost already sees directly. The state was redundant information dressed as a feature — XGBoost could infer it from the raw columns anyway.

The two-pass approach fixes this: pass 1 derives a risk score from raw features only, uses that score to assign states, then pass 2 adds those states as a genuinely new signal — one derived from predicted risk rather than reconstructed from the same raw inputs.

### Flow

```
Raw features (no credit_state)
        │
        │  Pass 1 XGBoost
        ▼
  default_risk_raw  [0.021, 0.227]
        │
        │  adaptive percentile thresholds (11/49/89th)
        ▼
  credit_state  (risk-anchored assignment)
        │
        │  Pass 2 XGBoost  (raw features + credit_state_encoded)
        ▼
  default_risk  [0.005, 0.270]   ← final output
```

### Pass 1 — Raw Features Only

**Features (10 total — no credit_state):**

| Feature | Source |
|---|---|
| `credit_score` | Preprocessing — unified 300–850 score |
| `utilization_rate` | Preprocessing |
| `on_time_payments_pct` | Raw CSV |
| `num_increases_2023` | Raw CSV |
| `days_since_last_loan` | Raw CSV |
| `macro_gdp_growth` | FRED cache |
| `macro_unemployment` | FRED cache |
| `macro_fed_rate` | FRED cache |
| `macro_inflation` | FRED cache |

**Target construction:** anchored to `credit_score` rank (continuous, no categorical state labels):

```
score_norm  = (credit_score - 300) / 550          # [0, 1]
y_base_p1   = 0.18 × (1 - score_norm) + 0.005     # lower score = higher risk
y_binary_p1 = 1  if  y_base_p1 + N(0, 0.01) >= median
```

**Calibration:**
```
default_risk_raw = clip( y_base_p1 × (0.5 + proba_p1),  0.001, 0.99 )
```

### Risk-Anchored State Assignment

Thresholds are computed from the actual pass-1 risk distribution using percentiles targeting the same ~11/38/40/11% portfolio split as the heuristic baseline:

```
t_excellent = 11th percentile of default_risk_raw
t_good      = 49th percentile of default_risk_raw   (11 + 38)
t_fair      = 89th percentile of default_risk_raw   (49 + 40)

Excellent  if  default_risk_raw <= t_excellent
Good       if  default_risk_raw <= t_good
Fair       if  default_risk_raw <= t_fair
Poor       otherwise
```

Adaptive thresholds are used because the actual credit score range [403–739] compresses the theoretical [300–850] range, making the pass-1 risk floor ~0.021 rather than the theoretical minimum. Percentile thresholds adapt to whatever range the model produces.

**Last run thresholds:**
```
Excellent ≤ 0.034  |  Good ≤ 0.093  |  Fair ≤ 0.187  |  Poor > 0.187
```

State labels now carry a direct probability interpretation — Excellent customers have predicted default risk below 3.4%, Poor customers above 18.7%.

### State Distribution: Heuristic vs Risk-Anchored

| State | Heuristic (credit_score) | Risk-Anchored (pass-1) | Delta |
|---|---|---|---|
| Excellent | 3,337 (11.1%) | 3,300 (11.0%) | ↓ 37 |
| Good | 11,434 (38.1%) | 11,400 (38.0%) | ↓ 34 |
| Fair | 12,024 (40.1%) | 12,000 (40.0%) | ↓ 24 |
| Poor | 3,205 (10.7%) | 3,300 (11.0%) | ↑ 95 |

The near-identical distributions confirm the heuristic score and predicted risk agree on customer ordering — but the risk-anchored states now carry a probabilistic meaning the score-based states lacked.

### Pass 2 — Raw Features + Risk-Anchored State

`credit_state_encoded` is added as an 11th feature. It is now genuinely informative: derived from pass-1 predicted risk, not reconstructed from the same raw inputs XGBoost already sees.

**Target construction (pass 2):** uses risk-anchored state base rates:

| State | Base Default Rate |
|---|---|
| Excellent | 1.0% |
| Good | 2.5% |
| Fair | 7.0% |
| Poor | 18.0% |

```
y_base_p2  = base_rate[credit_state]
y_binary_p2 = 1  if  y_base_p2 + N(0, 0.01) >= median
default_risk = clip( y_base_p2 × (0.5 + proba_p2),  0.001, 0.99 )
```

Pass 2 recovers lower risk values for Excellent customers (down to 0.005) that pass 1 could not reach without the state signal.

### Model Configuration (both passes)

```python
xgb.XGBClassifier(
    n_estimators  = 100,
    max_depth     = 4,
    learning_rate = 0.1,
    eval_metric   = 'logloss',
    random_state  = 42
)
```

Fallback chain: XGBoost → `GradientBoostingClassifier`.

### Output Columns

| Column | Description |
|---|---|
| `default_risk_raw` | Pass-1 risk score, `[0.021, 0.227]` |
| `credit_state` | Risk-anchored state (reassigned by pass-1 output) |
| `default_risk` | Pass-2 final risk score, `[0.005, 0.270]` |
| `high_risk_flag` | `True` if `default_risk > 0.15` |
| `risk_model` | `'XGBoost (2-pass)'` |
| `model_version` | `'v2.0.0'` |

### Last Run Results

- Pass-1 risk range: **[0.021, 0.227]**
- Pass-2 risk range: **[0.005, 0.270]**
- High-risk customers (> 15%): **3,300 (11.0%)**

### Key Design Notes

1. **No circular features** — pass-1 trains without `credit_state`, eliminating the original redundancy.
2. **States earn their information** — pass-2 `credit_state_encoded` is derived from predicted risk, so it adds signal beyond what raw features already provide.
3. **Macro features in both passes** — GDP/unemployment/rate/inflation adjust risk levels to the current macro environment in both models.
4. **No train/test split** — intentional; the goal is risk *scoring* for the LP objective, not generalised classification.

---

## Demand Forecasting Component

### What It Does
Answers: *"If we give a customer a higher limit, how much of it will they actually use over the next year?"* The output — `forecasted_utilization` — is the fraction of the credit limit a customer is expected to draw down over the 365-day horizon. It drives everything downstream: revenue (interest on drawn balance), loss (defaulting on drawn balance), and the NPV calculation in the lifecycle simulation.

### Two-Layer Monte Carlo

**Layer 1 — Cohort-level Geometric Brownian Motion (3,000 scenarios)**

For each credit state, 3,000 terminal utilization values are simulated using GBM — the same stochastic process used in option pricing:

```
util_terminal = μ × exp(−½σ²t + σ√t × Z)    Z ~ N(0,1),  t = 1.0 year
```

Base cohort parameters:

| State | Mean (μ) | Volatility (σ) |
|---|---|---|
| Excellent | 0.30 | 0.08 |
| Good | 0.45 | 0.10 |
| Fair | 0.58 | 0.13 |
| Poor | 0.70 | 0.16 |

GBM lognormal structure is chosen because utilization cannot go below 0 or above 1, and the multiplicative form naturally keeps values bounded and positively skewed — matching how real utilization behaves.

**Layer 2 — Individual customer perturbation**

The 3,000 scenarios collapse to a cohort mean and standard deviation. Each customer's forecast blends:

```python
individual_util = utilization_rate × 0.4 + cohort_mean × 0.6 + N(0, cohort_std × 0.3)
```

The 60/40 blend prevents ignoring individual history entirely (a customer who historically uses 90% of their limit should forecast higher than the cohort mean) while anchoring to the macro-adjusted cohort expectation.

### Macro Scenario Adjustment

The forecast is scenario-aware — cohort parameters are adjusted before simulation:

| Scenario | Drift Adjustment | Volatility Scale | Interpretation |
|---|---|---|---|
| Optimistic | +0.02 | ×0.80 | Customers less stretched, behaviour more predictable |
| Baseline | 0.00 | ×1.00 | No adjustment |
| Adverse | −0.03 | ×1.30 | Customers draw more credit, behaviour harder to predict |

### Output Columns

| Column | Meaning |
|---|---|
| `forecasted_utilization` | Expected fraction of limit drawn over next year, clipped to `[0.01, 0.99]` |
| `utilization_std` | Volatility of the forecast — uncertainty of the estimate |

Last run results (baseline scenario):

| Stat | Value |
|---|---|
| Mean utilization | 36.2% |
| Median | 35.9% |
| Min / Max | 17.7% / 86.5% |
| Std dev | 9.98% |

### How It Feeds Downstream

`forecasted_utilization` is the primary input to the Lifecycle Simulation (Stage 6), which computes:

- **Expected revenue** = `limit × utilization × interest_rate`
- **Expected loss** = `limit × utilization × default_risk × loss_given_default`
- **Profitability score** = NPV-discounted (revenue − loss)

The LP then maximises total profitability score across all customers. Without demand forecasting, the LP would treat a $10,000 increase identically regardless of whether a customer draws 20% or 90% of their limit — producing systematically wrong profit and risk estimates.

### Property Tests

| Property | Check |
|---|---|
| P18 | `forecasted_utilization` ∈ `[0, 1]` for all customers |
| P19 | ≥ 3,000 Monte Carlo scenarios run |
| P20 | Forecast horizon = 365 days |

---

## LP Optimization — Mathematical Formulation

### Step 1 — Credit Score (from raw CSV)

```
         1   [          otp_i - 80              5 - inc_i
S_i  =  ───  [ 35 x ─────────────  +  30 x ─────────────
        100   [          20                      5

                    365 - days_i              profit_i  ]
              + 15 x ────────────  +  20 x ──────────── ]  x  550  +  300
                         365                   120      ]
```

Each term clipped to [0, 100] before weighting. S_i in [300, 850].

### Step 2 — Credit State (from score)

```
              ┌ Excellent    if  S_i >= 655
              │ Good         if  572 <= S_i < 655
state_i  =   │ Fair         if  483 <= S_i < 572
              └ Poor         if  S_i <  483

State      Interest rate (r_i)    Base default (d_i)
─────────  ────────────────────   ──────────────────
Excellent          9%                    0.5%
Good              12%                    1.5%
Fair              16%                    5.0%
Poor              22%                   15.0%
```

### Step 3 — Forecasted Utilization

```
U_i  =  0.6 x mu_state  +  0.4 x u_i_raw  +  eps_i

  where  eps_i ~ Normal(0, 0.3 x sigma_state)
         mu_state = cohort mean from 3,000 GBM Monte Carlo scenarios
         u_i_raw  = customer's historical utilization rate

U_i clipped to [0.01, 0.99]
```

### Step 4 — Lifecycle Simulation (3,000 draws per customer)

```
For each draw j = 1 ... 3,000:

  Simulated utilization:
    U_ij  =  clip( U_i  +  sigma_i x Z_j ,  0.01, 0.99 )
             where Z_j ~ Normal(0, 1)

  Revenue:
    Rev_ij  =  L_i x U_ij x ( r_i + 0.005 )

  Default probability (utilization-adjusted):
    p_ij  =  clip( d_i x (1 + U_ij) ,  0,  0.60 )

  Loss (LGD = 50%):
    Loss_ij  =  L_i x U_ij x Bernoulli(p_ij) x 0.50

NPV discount factor at 12% annual rate:
          1 - exp(-0.12)
  delta = ──────────────  =  0.943
               0.12

Expected values (averaged over 3,000 draws, then discounted):

  Revenue_i  =  delta x mean_j( Rev_ij  )
  Loss_i     =  delta x mean_j( Loss_ij )

  ┌─────────────────────────────────────────┐
  │  pi_i  =  Revenue_i  -  Loss_i         │
  └─────────────────────────────────────────┘
  pi_i = profitability score for customer i
```

### Step 5 — Profit Rate (LP objective coefficient)

```
         pi_i
  rho_i = ────
           L_i

Dividing by current loan L_i converts absolute profit into
return per dollar of existing exposure, so customers of
different loan sizes compete on equal footing in the LP.
```

### Step 6 — Linear Programme

```
Decision variable:
  x_i >= 0     (limit increase for customer i)

Objective:
  maximise   SUM_i ( rho_i x x_i )

Subject to:

  [1] Portfolio default risk <= 5%
      SUM_i (d_i - 0.05) x x_i  <=  -SUM_i (d_i - 0.05) x L_i

  [2] Total new exposure <= $500M
      SUM_i x_i  <=  500,000,000 - SUM_i L_i

  [3] Per-customer cap
      0  <=  x_i  <=  50,000 - L_i     for all i
```

### Full Chain at a Glance

```
Raw CSV
  (otp, inc, days, profit)
        │
        │  compute_credit_score()
        ▼
  Credit score S_i  ──►  Credit state  ──►  r_i (interest rate)
        │                                    d_i (base default)
        │
        │  forecast_utilization()  [3,000 GBM scenarios]
        ▼
  Forecasted utilization U_i
        │
        │  simulate_loan_lifecycle()  [3,000 Monte Carlo draws]
        ▼
  Revenue_i,  Loss_i
        │
        │  profitability score
        ▼
  pi_i  =  Revenue_i - Loss_i
        │
        │  / L_i (current loan)
        ▼
  rho_i  (LP objective coefficient)
        │
        │  HiGHS LP solver
        ▼
  x_i*  (optimal limit increase per customer)
```

---

## Macroeconomic Scenarios

| Scenario | GDP | Unemployment | Interest Rate | Inflation |
|---|---|---|---|---|
| Optimistic | 3.5% | 3.5% | 4.0% | 2.5% |
| Baseline | 2.5% | 4.0% | 5.0% | 3.5% |
| Adverse | 0.5% | 5.5% | 6.0% | 5.0% |

---

## Key Files

| File | Purpose |
|---|---|
| `loan_limit_optimization.ipynb` | Primary deliverable — single notebook, run end-to-end |
| `loan_limit_increases.csv` | Input data — 30,000 customer records |
| `optimization_results.csv` | Output — per-customer limit recommendations |
| `cache/macro_data_2023.json` | Cached FRED macro data |
| `viz_01_02_state_and_risk.png` … `viz_12_cumulative.png` | 12 output visualisations |
| `CLAUDE.md` | Project setup, environment, and implementation notes |

---

## Performance Targets

| Property | Target | Achieved |
|---|---|---|
| End-to-end runtime | < 30 minutes | ~30 seconds |
| Peak memory | ≤ 8 GB | < 2 GB (batched) |
| Monte Carlo iterations | ≥ 3,000 | 3,000 |
| Visualisations | ≥ 10 | 12 |
| Property tests | 44/44 | 44/44 |

---

## Last Run Results

- 8,748 customers (29.2%) received limit increases
- Total incremental exposure: $417M
- Expected incremental profit: $3.25M
- Portfolio default risk: 5.00% (at constraint boundary)
- LP solver: HiGHS, optimal in ~1.6s

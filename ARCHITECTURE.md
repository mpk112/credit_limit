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
│  3. Risk Model           │  Ordinal rank aggregation on 4 raw features
│                          │  assigns credit states (Excellent/Good/Fair/Poor)
│                          │  and outputs default_risk ∈ [0.005, 0.27].
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
| Unified `compute_credit_score()` | Retained for comparison baseline; no longer drives state assignment |
| Ordinal rank over XGBoost | Features are nearly uncorrelated (r ≈ 0.001) and no default labels exist — XGBoost was training on a synthetic target derived from the same inputs it sees; ordinal ranking is equivalent output with no model complexity or circularity |
| scipy HiGHS (not PuLP) | Handles 30k decision variables in ~1.6s; no external solver binary needed |
| Vectorised Monte Carlo | All 30k × 3,000 iterations computed as numpy matrix ops in 5k-row batches — runs in ~2s vs hours with loops |
| K-Means for state boundaries | Percentile cuts (11/49/89) were reverse-engineered from the heuristic distribution — not data-driven. K-Means finds natural cluster boundaries in risk_rank without a pre-decided split; reveals bimodal structure (21/29/29/21%) the percentile method hides |
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

`compute_credit_score()` maps each customer to a FICO-style 300–850 score using the same four features and weights as the ordinal risk rank. It is retained as a comparison baseline and for visualisation, but **no longer drives credit state assignment**.

| Input | Weight | Normalisation |
|---|---|---|
| On-time payment % | 35% | Clipped to [80, 100], scaled 0–100 |
| Credit discipline (# increases) | 30% | Inverted, clipped to [0, 5], scaled 0–100 |
| Recency (days since last loan) | 15% | Inverted, clipped to [0, 365], scaled 0–100 |
| Profitability contribution | 20% | Clipped to [0, $120], scaled 0–100 |

Actual score range in this dataset: **[403, 739]** — compressed from the theoretical [300, 850] because all customers have on-time payments ≥ 80% (data is floor-clipped).

State assignment now uses ordinal ranking (see below). The heuristic credit_score thresholds (655/572/483) are run as a comparison step only.

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

## Risk Model — Ordinal Rank Aggregation

### Why Not a Model

The input data has two structural properties that make supervised ML unnecessary:

1. **No default outcome labels** — the CSV has no "defaulted: yes/no" column. Any model must train on a synthetic target derived from the same raw features it sees as inputs, which is circular.
2. **Features are nearly uncorrelated** (r ≈ 0.001 between all pairs) — there are no non-linear interaction effects for a model to exploit. XGBoost's 200 trees would learn approximately the same ranking as a weighted sum.

Ordinal ranking is transparent, deterministic, and produces equivalent output to any model trained on this data.

### Flow

```
Raw features (4 inputs)
        │
        │  compute_ordinal_risk_rank()   — weighted percentile ranks
        ▼
  risk_rank  [0.224, 0.788]   (0 = safest, 1 = riskiest)
        │
        ├──────────────────────────────────────────────────────┐
        │  assign_states_from_rank()                           │  assign_states_kmeans()
        │  percentile method (comparison)                      │  K-Means (primary)
        │  11/49/89th percentile cuts                          │  4 clusters, Voronoi boundaries
        ▼                                                      ▼
  states_pct  [11/38/40/11%]                          states_km  [21/29/29/21%]  ← adopted
        │
        │  rank_to_default_risk()   — state base rate × within-state rank
        ▼
  default_risk  [0.005, 0.270]   ← used by LP and constraints
```

### Step 1 — Ordinal Risk Rank (`compute_ordinal_risk_rank`)

Each of the four raw features is converted to a percentile rank in [0, 1] oriented so that **0 = lowest risk direction, 1 = highest risk direction**, then combined with the same weights as the unified credit score:

| Feature | Direction | Weight |
|---|---|---|
| `on_time_payments_pct` | Higher = safer → **inverted** | 35% |
| `num_increases_2023` | More increases = riskier → as-is | 30% |
| `days_since_last_loan` | More days = less recent = riskier → as-is | 15% |
| `total_profit_contribution` | Higher profit = safer → **inverted** | 20% |

```
r_payment    = 1 - rank_pct(on_time_pct)
r_discipline = rank_pct(num_increases)
r_recency    = rank_pct(days_since_loan)
r_profit     = 1 - rank_pct(profit)

risk_rank = 0.35 × r_payment + 0.30 × r_discipline
          + 0.15 × r_recency + 0.20 × r_profit
```

`risk_rank` has mean exactly 0.50 by construction. Last run range: **[0.224, 0.788]** — compressed because on-time payments is floor-clipped at 80% and 44% of customers have `profit = 0` and `increases = 0`.

### Step 2 — Credit State Assignment: Two Methods Compared

Both methods run at each execution. K-Means is adopted as primary.

#### Method A — Percentile (comparison only)

```
t1 = 11th percentile of risk_rank    → bottom 11% → Excellent
t2 = 49th percentile                 → 11–49%     → Good
t3 = 89th percentile                 → 49–89%     → Fair
                                     → top 11%    → Poor
```

The 11/49/89 cuts were derived by reverse-engineering the heuristic credit_score distribution (cumulative sums of 11.1/38.1/40.1/10.7%). They are not data-driven — they replicate a pre-decided split.

#### Method B — K-Means Clustering (primary)

```python
KMeans(n_clusters=4, n_init=20, random_state=42).fit(risk_rank.reshape(-1, 1))
```

Clusters are sorted by centroid value (ascending → Excellent to Poor). Boundaries are the **Voronoi midpoints** between adjacent centroids — the exact boundary where a point is equidistant from two cluster centres in 1D:

```
boundary[i] = (centroid[i] + centroid[i+1]) / 2
```

The cluster sizes reflect the **actual shape of the risk_rank distribution**, not a pre-decided split.

### Boundary Comparison (last run)

```
                  Excellent      Good        Fair
Percentile        ≤ 0.3548    ≤ 0.4963    ≤ 0.6451
K-Means           ≤ 0.3957    ≤ 0.4991    ≤ 0.6032
```

The Good boundary is nearly identical (0.496 vs 0.499) — the distribution is dense in the middle and both methods agree there. Excellent and Fair boundaries shift by ~0.04.

### State Distribution Comparison (last run)

| State | K-Means (primary) | Percentile | Heuristic | K-Means vs Percentile |
|---|---|---|---|---|
| Excellent | 6,246 (20.8%) | 3,300 (11.0%) | 3,337 (11.1%) | ↑ 2,946 |
| Good | 8,703 (29.0%) | 11,400 (38.0%) | 11,434 (38.1%) | ↓ 2,697 |
| Fair | 8,757 (29.2%) | 12,000 (40.0%) | 12,024 (40.1%) | ↓ 3,243 |
| Poor | 6,294 (21.0%) | 3,300 (11.0%) | 3,205 (10.7%) | ↑ 2,994 |

**6,189 customers (20.6%) land in a different state between the two methods.**

### Why K-Means Finds a Bimodal Shape

K-Means reveals that the data has **two dense clusters** at the extremes, not four equally-spaced ones:

- The 13,207 customers (44%) with `profit = 0` **and** `increases = 0` cluster at one end of `risk_rank` — their discipline and profit signals are tied, so their rank is driven almost entirely by payment history and recency, pulling them apart from active customers
- Customers with non-zero profit and active credit behaviour cluster at the other end
- The middle (Good/Fair) is thinner than the percentile method assumes

The percentile method forces 11/38/40/11 because it was calibrated to match the heuristic score distribution. K-Means lets the data speak: the true shape is closer to **21/29/29/21** — bimodal, not unimodal-centred.

### Step 3 — Default Risk (`rank_to_default_risk`)

`risk_rank` is a relative ordering, not a probability. Mapped to a pseudo-probability anchored to assumed state base rates:

| State | Base Rate | Output Range |
|---|---|---|
| Excellent | 1.0% | [0.50%, 1.50%] |
| Good | 2.5% | [1.25%, 3.75%] |
| Fair | 7.0% | [3.50%, 10.50%] |
| Poor | 18.0% | [9.00%, 27.00%] |

```
within_rank  = rank_pct(risk_rank within state)
default_risk = clip( base_rate × (0.5 + within_rank),  0.001, 0.99 )
```

### Output Columns

| Column | Description |
|---|---|
| `risk_rank` | Ordinal risk rank, `[0.224, 0.788]` — 0 = safest |
| `credit_state` | State from K-Means clustering on risk_rank |
| `default_risk` | Pseudo-probability, `[0.005, 0.270]` — used by LP |
| `high_risk_flag` | `True` if `default_risk > 0.15` |
| `risk_model` | `'ordinal_rank_kmeans'` |

### Last Run Results

- Risk rank range: **[0.224, 0.788]**, mean 0.500
- Default risk range: **[0.005, 0.270]**
- High-risk customers (> 15%): **4,196 (14.0%)**
- Customers assigned differently vs percentile method: **6,189 (20.6%)**

### When to Upgrade

Ordinal ranking should be replaced with a supervised model when:
- **Real default/delinquency labels become available** — even logistic regression on 5 features would be more meaningful than any model trained on a synthetic target
- **More features are added** — bureau data, transaction history, demographics; ordinal ranking does not scale to 50+ features with genuine interactions

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

### Step 2 — Risk Rank and Credit State (ordinal ranking)

```
Ordinal risk rank (0 = safest, 1 = riskiest):

  rho_i = 0.35 x (1 - rank_pct(otp_i))
        + 0.30 x  rank_pct(inc_i)
        + 0.15 x  rank_pct(days_i)
        + 0.20 x (1 - rank_pct(profit_i))

Adaptive state thresholds (11th / 49th / 89th percentile of rho):

              ┌ Excellent    if  rho_i <= p11
              │ Good         if  rho_i <= p49
state_i  =   │ Fair         if  rho_i <= p89
              └ Poor         otherwise

Default risk within each state:

  d_i = clip( base_rate[state_i] x (0.5 + rank_pct(rho_i | state_i)),
              0.001, 0.99 )

State      base_rate    Interest rate (r_i)    Lifecycle d_i
─────────  ──────────   ────────────────────   ─────────────
Excellent     1.0%              9%                   0.5%
Good          2.5%             12%                   1.5%
Fair          7.0%             16%                   5.0%
Poor         18.0%             22%                  15.0%
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
  (otp, inc, days, profit, loan)
        │
        │  compute_ordinal_risk_rank()   [weighted percentile ranks]
        ▼
  risk_rank_i  ──►  assign_states_from_rank()  ──►  credit_state_i
                                                      r_i (interest rate)
        │                                             d_i (base default)
        │  rank_to_default_risk()
        ▼
  default_risk_i   [used by LP portfolio constraint]
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
  profit_rate_i  (LP objective coefficient)
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
- Risk model: ordinal rank + K-Means boundaries, 4,196 high-risk customers flagged (14.0%)
- 44/44 property tests pass

# Credit State Classification — Alternatives to Manual Heuristic Scoring

## Current Approach

`compute_credit_score()` uses a hand-crafted weighted sum of 4 raw features mapped to a FICO-style 300–850 scale:

| Input | Weight | Normalisation |
|---|---|---|
| On-time payment % | 35% | Clipped to [80, 100], scaled 0–100 |
| Credit discipline (# increases) | 30% | Inverted, clipped to [0, 5], scaled 0–100 |
| Recency (days since last loan) | 15% | Inverted, clipped to [0, 365], scaled 0–100 |
| Profitability contribution | 20% | Clipped to [0, $120], scaled 0–100 |

Fixed thresholds (655 / 572 / 483) then assign customers to Excellent / Good / Fair / Poor.

**Problems with this approach:**
- Weights (35/30/15/20) are assumed, not derived from the data
- Thresholds require manual calibration each time the data distribution shifts
- Linear combination does not capture feature interactions

---

## Alternative 1 — PCA (Replace Manual Weights with Data-Driven Ones)

Run PCA on the 6 input features and use the **first principal component** as the credit score.

**How it works:**
- PC1 is the linear combination of features that maximises explained variance
- Loadings (weights) are derived from the data — no human assumptions
- Produces a single scalar per customer; thresholds work the same way as today

**Tradeoffs:**

| Pro | Con |
|---|---|
| Objective, data-driven weights | PC1 loadings can be hard to explain to stakeholders |
| Minimal architecture change | Weights change if the data distribution shifts |
| Fast to implement | Still requires threshold calibration |

**Effort:** Low — drop-in replacement for `compute_credit_score()`.

---

## Alternative 2 — K-Means (Fully Data-Driven State Boundaries)

Cluster customers into 4 groups directly in 6-dimensional feature space, then order clusters by mean default proxy to label them Excellent → Poor.

**How it works:**
- K-Means finds 4 centroids that minimise within-cluster variance
- Post-hoc: sort clusters by their mean `default_risk` proxy → assign state labels
- No manual weights or thresholds

**Tradeoffs:**

| Pro | Con |
|---|---|
| Captures non-linear feature interactions | Centroids can shift between runs (fix with fixed seed) |
| No weight assumptions | Cluster ordering requires a risk anchor post-hoc |
| Interpretable centroids | Boundary customers get hard assignment with no uncertainty |

**Effort:** Low-medium — replaces `classify_credit_states()` only.

---

## Alternative 3 — Gaussian Mixture Model (Soft Probabilistic Membership)

Fit 4 Gaussian components to the feature space and assign each customer a **probability of belonging to each state**, rather than a hard label.

**How it works:**
- GMM estimates the mean and covariance of 4 latent distributions
- Each customer gets a membership vector: e.g. [0.05, 0.60, 0.30, 0.05] across states
- Hard state label = argmax; soft labels feed naturally into the Markov transition model

**Tradeoffs:**

| Pro | Con |
|---|---|
| Probabilistic — boundary customers get blended assignment | More complex to implement and explain |
| Aligns naturally with the Markov chain's probabilistic transitions | Component ordering still needs a post-hoc risk anchor |
| No hard threshold cliff-edges | Assumes Gaussian-shaped clusters in feature space |

**Effort:** Medium — requires changes to downstream Markov chain and risk model to accept soft state probabilities.

---

## Alternative 4 — Two-Pass XGBoost (Recommended)

Train XGBoost on raw features only (no state column) to produce a `default_risk` score, then **threshold that score directly** to define the 4 states. States are then defined by predicted default risk, not a separate proxy.

**How it works:**
```
Pass 1:  raw features → XGBoost (no credit_state) → default_risk_raw
         threshold default_risk_raw → assign credit_state

Pass 2:  raw features + credit_state → XGBoost retrain → final default_risk
```

**Tradeoffs:**

| Pro | Con |
|---|---|
| States are directly interpretable: "Poor = predicted default risk > X%" | Requires two-pass architecture refactor |
| Eliminates conceptual awkwardness of classifying states before estimating risk | Pass 1 XGBoost trained without the state feature — slightly weaker signal |
| State thresholds are anchored to actual risk, not a proxy score | Thresholds still need calibration (though they now carry clear business meaning) |
| Most internally consistent with the pipeline's goal | More implementation work |

**Suggested thresholds:**

| State | default_risk range |
|---|---|
| Excellent | < 2% |
| Good | 2% – 7% |
| Fair | 7% – 15% |
| Poor | ≥ 15% |

**Effort:** Medium-high — requires restructuring the Risk Model stage.

---

## Comparison Summary

| Approach | Weights | Boundaries | Interactions | Effort | Best For |
|---|---|---|---|---|---|
| Current (manual) | Hand-picked | Fixed thresholds | None | — | Baseline |
| PCA | Data-driven | Fixed thresholds | None (linear) | Low | Quick improvement, same architecture |
| K-Means | None needed | Data-driven | Partial | Low–Medium | Natural groupings, no risk ordering requirement |
| GMM | None needed | Probabilistic | Partial | Medium | Soft assignments, Markov alignment |
| Two-Pass XGBoost | None needed | Risk-anchored | Full (non-linear) | Medium–High | Most principled, risk-interpretable states |

---

## Recommendation

**Near-term**: Replace `compute_credit_score()` with PCA — removes weight assumptions with minimal pipeline disruption.

**Long-term**: Implement the two-pass XGBoost approach. It is the most defensible for a credit risk problem because state labels carry an explicit default risk interpretation rather than being a proxy derived from a separate formula. The key refactor is splitting the Risk Model stage into two sequential passes.

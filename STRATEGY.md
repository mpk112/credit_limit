# Term Extension Optimisation — Strategy Reference

A consolidated strategy guide covering fee calibration, assumption levers, and
recalibration recommendations derived from the term extension model analysis.

---

## 1. Fee Sensitivity Strategy

### Core Question: At what fee does the approval rate start falling?

The breakeven condition per customer:

```
fee × annuity_factor(T, r=19%)  >  balance × LGD × p_default × exp(−r×T/730)

Breakeven fee per customer  =  (balance × LGD × p_default × loss_discount) / annuity_factor
```

### Per-State Breakeven Fee Distribution

| State | Min | Median | 95th pct | Max (first denial threshold) |
|-------|-----|--------|----------|------------------------------|
| Excellent | $0.32 | $3.29 | $7.51 | **$13.68** |
| Good | $0.90 | $8.22 | $16.36 | **$25.50** |
| Fair | $2.29 | $18.63 | $34.51 | **$52.00** |
| Poor | $5.00 | $34.36 | $61.33 | **$80.44** |

The **max breakeven fee** is the tipping point — drop the offered fee below this and
the first customer in that state gets denied:

- Below **$52** → first Fair customer denied
- Below **$25.50** → first Good customer denied
- Below **$13.68** → first Excellent customer denied

### Fee Sweep — Approval Rate by Credit State

| Fee | Excellent | Good | Fair | Poor |
|-----|-----------|------|------|------|
| $40 (current) | 100.0% | 100.0% | 99.2% | 60.2% |
| $35 | 100.0% | 100.0% | 95.7% | 51.4% |
| $30 | 100.0% | 100.0% | 86.3% | 42.1% |
| $25 | 100.0% | 99.97% | 71.3% | 33.5% |
| $20 | 100.0% | 99.4% | 54.4% | 24.6% |
| $15 | 100.0% | 91.0% | 37.9% | 15.0% |
| $10 | 99.5% | 62.5% | 22.2% | 6.5% |
| $5 | 74.9% | 26.2% | 5.3% | 0% |

### Strategic Insight

The $40 fee is generous relative to credit risk — especially for Excellent and Good
customers whose median breakeven fee is $3.29 and $8.22 respectively. This creates
a large profit buffer but also means approval rates are insensitive to most risk
parameter changes. Reducing the fee is the single most direct lever for controlling
approval volume.

**Fee strategy options:**

| Goal | Recommended fee | Effect |
|------|----------------|--------|
| Maximise profit volume | $40 (current) | 100% Excellent/Good, 99% Fair |
| Stress-test resilience | $30 | Fair drops to 86%, stress-tests model |
| Risk-based tiering | Variable: $35 Excellent, $30 Good, $25 Fair, $20 Poor | Differentiates by risk |
| Regulatory conservatism | $25 | Good stays ~100%, Fair at 71% |

---

## 2. Assumption Levers Strategy

### Breakeven Threshold

```
p_def × balance  <  80.0   →  profitable  (grant extension)
p_def × balance  ≥  80.0   →  unprofitable (deny)

where 80.0 = $39.38 / (LGD × 0.82 discount factor)
```

Max `p_def × balance` by state at baseline:

| State | Max p_def × balance | vs Breakeven of 80 |
|-------|--------------------|--------------------|
| Excellent | 22.8 | 3.5× below — immune to calibration |
| Good | 42.5 | 1.9× below — immune to most changes |
| Fair | 86.7 | 3 customers breach — 99.96% approval |
| Poor | 134.1 | Many breach → 60.2% approval |

### Lever 1 — LGD (Loss Given Default)

Baseline: **60%**. Industry range for unsecured consumer: 55–80%.

| LGD | Excellent | Good | Fair | Poor |
|-----|-----------|------|------|------|
| 60% (base) | 100.0% | 100.0% | 99.2% | 60.2% |
| 65% | 100.0% | 100.0% | 97.5% | 54.9% |
| 70% | 100.0% | 100.0% | 94.6% | 49.8% |
| 75% | 100.0% | 100.0% | 90.9% | 46.1% |
| 80% | 100.0% | 100.0% | 86.3% | 42.1% |
| 85% | 100.0% | 100.0% | 81.3% | 38.6% |

**Strategy:** LGD=70% is the industry midpoint for unsecured consumer credit and a
defensible conservative assumption. Applying it brings Fair approval to ~95% and
Poor to ~50% without changing the product structure.

### Lever 2 — Hazard Rate λ (Annual Default Probability)

Baseline: 1.5% / 4% / 10% / 22% (Excellent / Good / Fair / Poor).

| λ multiplier | Fair λ | Excellent | Good | Fair | Poor |
|---|---|---|---|---|---|
| ×1.0 (base) | 10% | 100.0% | 100.0% | 99.2% | 60.2% |
| ×1.2 | 12% | 100.0% | 100.0% | 93.1% | 34.5% |
| ×1.5 | 15% | 100.0% | 100.0% | 76.6% | 25.8% |
| ×2.0 | 20% | 100.0% | 99.97% | 54.4% | 15.7% |
| ×2.5 | 25% | 100.0% | 99.4% | 41.3% | 10.5% |
| ×3.0 | 30% | 100.0% | 95.6% | 32.8% | 7.0% |

**Strategy:** λ×1.2 (Fair → 12%) is within a normal recession calibration range and
is justifiable as a model conservatism buffer. Good doesn't crack below 100% until
λ×2.5. Excellent is immune throughout — even at λ×3.0, their low balances keep
`p_def × balance` below 80.

### Lever 3 — Balance Exposure Multiplier

Baseline: 100% of outstanding balance. Increasing this simulates including accrued
interest, collection fees, or legal costs in the loss estimate.

| Balance mult | Excellent | Good | Fair | Poor |
|---|---|---|---|---|
| ×1.0 (base) | 100.0% | 100.0% | 99.2% | 44.1% |
| ×1.1 | 100.0% | 100.0% | 97.1% | 38.4% |
| ×1.2 | 100.0% | 100.0% | 93.1% | 34.5% |
| ×1.5 | 100.0% | 100.0% | 76.6% | 25.8% |
| ×2.0 | 100.0% | 99.97% | 54.4% | 15.7% |

**Strategy:** A ×1.2 multiplier (add 20% for collection costs) is conservative but
defensible. Mathematically equivalent to raising LGD from 60% to 72%.

### Lever 4 — Minimum Uptake Threshold (Policy Gate)

A policy override that rejects low-intent customers regardless of profitability.

| Min uptake | Excellent | Good | Fair | Poor |
|---|---|---|---|---|
| None (base) | 100.0% | 100.0% | 99.2% | 44.1% |
| 30% | 100.0% | 100.0% | 99.2% | 44.1% |
| 40% | 100.0% | 100.0% | 99.2% | 0% |
| 55% | 100.0% | 100.0% | 49.5% | 0% |
| 60% | 100.0% | 100.0% | 0% | 0% |

**Strategy:** Useful as a capacity management gate (limit offers to high-intent
customers only) rather than a risk control. Poor customers have GBM base rate μ=0.35,
so a 40% threshold cuts them entirely. Use in combination with a tiered rollout.

### Levers That Do NOT Work

| Lever | Effect | Why |
|-------|--------|-----|
| Discount rate (19% → 36%) | Zero | Revenue and loss discounting cancel out |
| Per-customer p_default cap | Zero | Fair p_def already < 3% at typical terms |
| Excellent denial via calibration | Impossible | Requires LGD > 214% |

---

## 3. Recommended Recalibration Strategy

Combining two conservative but defensible assumption changes produces realistic
sub-100% approval rates without changing the product structure:

```
LGD:  60% → 70%    (industry midpoint for unsecured consumer credit)
λ:    ×1.2          (20% uplift for economic stress / model conservatism)
```

**Outcome:**

| State | Baseline | Recalibrated |
|-------|----------|--------------|
| Excellent | 100.0% | 100.0% |
| Good | 100.0% | 100.0% |
| Fair | 99.2% | ~88% |
| Poor | 60.2% | ~35% |

Excellent and Good remain fully approved — their risk is genuinely low and the model
is correct to approve them. Fair and Poor reach more defensible approval rates that
reflect real-world heterogeneity within those tiers.

---

## 4. Risk-Based Dynamic Pricing Strategy

Rather than a flat $40 fee, set the fee as a function of customer risk:

```
fee_i  =  fee_floor  +  (fee_ceiling − fee_floor) × (1 − p_default_i / p_default_max)
```

Example calibration:

| State | p_default range | Dynamic fee range | vs flat $40 |
|-------|----------------|-------------------|-------------|
| Excellent | 0.3–0.8% | $36–$40 | Slight discount — attracts uptake |
| Good | 0.8–2.5% | $32–$38 | Moderate discount |
| Fair | 2.5–5.0% | $25–$33 | Larger discount — compensates risk |
| Poor | 5.0–8.0% | $18–$26 | Deep discount — borderline customers |

**Effect:** Increases uptake for risky customers (lower fee → higher acceptance rate)
while reducing revenue per extension for those customers. Net impact depends on
uptake elasticity — estimated +$42K–$85K revenue uplift based on a 10 pp uptake lift
for Poor/Fair segments.

---

## 5. Tiered Rollout Strategy

Deploy in phases to manage operational risk and validate model assumptions:

| Phase | Segment | Accounts | Expected profit | Risk |
|-------|---------|----------|----------------|------|
| 1 | Top-quartile by profitability_score | ~6,000 | ~$260K | Low |
| 2 | All eligible Excellent + Good + Fair | ~19,714 | ~$578K | Moderate |
| 3 | LP-approved Poor (post Phase 2 validation) | ~3,210 | ~$53K | Higher |

**Gate between each phase:** Compare 30-day rolling actual default rate vs simulated
`p_default_sim`. Proceed only if actual ≤ 1.5× simulated.

---

## 6. Scenario Strategy Summary

| Scenario | Fee | LGD | λ mult | Approval (Fair) | Net Profit |
|----------|-----|-----|--------|-----------------|------------|
| Aggressive | $40 | 60% | ×1.0 | 99.2% | $601K |
| Conservative | $40 | 70% | ×1.2 | ~88% | ~$580K |
| Stress test | $30 | 70% | ×1.2 | ~60% | ~$390K |
| Risk-based pricing | Variable | 65% | ×1.1 | ~93% | ~$640K |
| Regulatory floor | $25 | 75% | ×1.5 | ~55% | ~$310K |

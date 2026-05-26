# Assumption Sensitivity — Approval Rate Analysis

> **Question:** Which model assumptions (other than the $40 fee and max term) bring the
> approval rate below 100% for Excellent, Good, and Fair credit states?

The baseline model approves 100% of eligible Excellent and Good customers, ~99.2% of Fair,
and 60.2% of Poor. The analysis below stress-tests every calibration assumption to identify
which levers actually matter.

---

## Breakeven Condition

The LP grants an extension when:

```
profitability_score = expected_revenue − expected_loss > 0

where:
  expected_revenue = $40 × annuity_factor(T, r=19%)
  expected_loss    = balance × LGD × p_default × exp(−r × T/730)

Simplified breakeven:  p_def × balance  <  80.0
  (= $39.38 / (LGD × 0.82 discount_factor))
```

| State | Max `p_def × balance` | vs Breakeven of 80 |
|-------|----------------------|---------------------|
| Excellent | 22.8 | **3.5× below** — safe margin |
| Good | 42.5 | **1.9× below** — comfortable |
| Fair | 86.7 | **3 customers breach** → 99.96% approval |
| Poor | 134.1 | Many breach → 60.2% approval |

---

## 1. LGD — Loss Given Default (baseline: 60%)

Only affects Fair and Poor. **Excellent and Good are immune** — even at LGD=100% their
max `p_def × balance` (22.8 and 42.5) never reaches any plausible breakeven.

| LGD | Excellent | Good | Fair | Poor |
|-----|-----------|------|------|------|
| 60% (base) | 100.0% | 100.0% | 99.2% | 60.2% |
| 65% | 100.0% | 100.0% | 97.5% | 54.9% |
| 70% | 100.0% | 100.0% | **94.6%** | 49.8% |
| 75% | 100.0% | 100.0% | **90.9%** | 46.1% |
| 80% | 100.0% | 100.0% | **86.3%** | 42.1% |
| 85% | 100.0% | 100.0% | **81.3%** | 38.6% |

**Realistic calibration range:** 65–75% (industry standard for unsecured consumer credit).
LGD=70% brings Fair approval to ~95% and Poor to ~50% — a more defensible assumption.

---

## 2. Hazard Rate λ — Annual Default Probability Multiplier (baseline: 1.5% / 4% / 10% / 22%)

The most powerful lever. Scaling all λ values proportionally:

| λ multiplier | Fair λ | Excellent | Good | Fair | Poor |
|---|---|---|---|---|---|
| ×1.0 (base) | 10% | 100.0% | 100.0% | 99.2% | 44.1% |
| ×1.2 | 12% | 100.0% | 100.0% | **93.1%** | 34.5% |
| ×1.5 | 15% | 100.0% | 100.0% | **76.6%** | 25.8% |
| ×2.0 | 20% | 100.0% | **99.97%** | **54.4%** | 15.7% |
| ×2.5 | 25% | 100.0% | **99.4%** | **41.3%** | 10.5% |
| ×3.0 | 30% | 100.0% | **95.6%** | **32.8%** | 7.0% |

- **Fair** starts declining at λ×1.2 — a 20% hazard rate increase is within a normal
  recession calibration range.
- **Good** first dips below 100% at λ×2.5 (Good λ → 10%, matching current Fair baseline).
- **Excellent** never falls below 100% at any tested multiplier — their low balances mean
  even λ=4.5% produces `p_def × balance` well below the breakeven.

---

## 3. Balance Exposure Multiplier (baseline: 100% of outstanding balance)

Equivalent to assuming a larger fraction of the balance is at risk (e.g. including
accrued interest or fees on default). Mathematically identical in effect to scaling LGD.

| Balance mult | Excellent | Good | Fair | Poor |
|---|---|---|---|---|
| ×1.0 (base) | 100.0% | 100.0% | 99.2% | 44.1% |
| ×1.1 | 100.0% | 100.0% | **97.1%** | 38.4% |
| ×1.2 | 100.0% | 100.0% | **93.1%** | 34.5% |
| ×1.3 | 100.0% | 100.0% | **88.1%** | 31.6% |
| ×1.5 | 100.0% | 100.0% | **76.6%** | 25.8% |
| ×2.0 | 100.0% | **99.97%** | **54.4%** | 15.7% |

A ×1.5 balance multiplier is equivalent in effect to LGD 60% → 90%. Justified if
collection costs, legal fees, and accrued interest are included in the loss estimate.

---

## 4. Minimum Uptake Threshold (policy gate, not profit gate)

Requires a minimum GBM uptake probability before offering — rejects low-intent customers
regardless of profitability.

| Min uptake | Excellent | Good | Fair | Poor |
|---|---|---|---|---|
| None (base) | 100.0% | 100.0% | 99.2% | 44.1% |
| 30% | 100.0% | 100.0% | 99.2% | 44.1% |
| 40% | 100.0% | 100.0% | 99.2% | **0%** |
| 55% | 100.0% | 100.0% | **49.5%** | **0%** |
| 60% | 100.0% | 100.0% | **0%** | **0%** |

**Note:** This is a policy override, not a profitability change. Poor customers have a
GBM base acceptance rate of μ=0.35, so almost none clear a 40% threshold. The cliff
behaviour (100% → 0%) is a consequence of the GBM σ being relatively tight per state.

---

## 5. Discount Rate / Cost of Capital (baseline: 19%)

| Discount rate | Excellent | Good | Fair | Poor |
|---|---|---|---|---|
| 19% (base) | 100.0% | 100.0% | 99.2% | 44.1% |
| 22% | 100.0% | 100.0% | 99.2% | 44.1% |
| 25% | 100.0% | 100.0% | 99.2% | 44.1% |
| 32% | 100.0% | 100.0% | 99.2% | 44.1% |
| 36% | 100.0% | 100.0% | 99.2% | 44.1% |

**Zero effect across the entire range.** The discount rate reduces the annuity revenue
and the present value of losses in near-equal proportion — the two effects cancel.
Changing the discount rate alone is not a useful lever for controlling approval rates.

---

## 6. Per-Customer p_default Hard Cap

A regulatory-style individual cap: deny any customer whose simulated p_default exceeds
the cap regardless of profitability.

| Cap | Excellent | Good | Fair | Poor |
|---|---|---|---|---|
| 8% | 100.0% | 100.0% | 99.2% | 44.1% |
| 5% | 100.0% | 100.0% | 99.2% | 44.1% |
| 3% | 100.0% | 100.0% | 99.2% | 44.1% |

**No effect** because Fair customers' simulated `p_default_sim` is already below 3% at
their typical 60–75 day terms (Fair λ=10% → p_def ≈ 1.6% at 60 days). The cap would
only bite at levels below ~1.5%, which would also eliminate most Good customers.

---

## Why Excellent Cannot Be Denied by Any Calibration Change Alone

The hardest constraint in the model:

```
To deny any Excellent customer:
  p_def × balance × LGD × discount_factor  >  $40 (fee)
  22.8 × LGD × 0.82  >  40
  LGD  >  2.14  (214% — physically impossible)
```

Excellent customers would require a **structural model change** to see any denials:
- Add an origination / servicing cost per extension (e.g. $15 fixed cost → fee net = $25)
- Reduce the periodic payment from $40 to < $11.20
- Cap the annuity at a much shorter term
- Use a fundamentally different revenue model

Under any pure calibration change (LGD, λ, discount rate, balance exposure), Excellent
customers remain fully approved.

---

## Summary — Lever Ranking

| Lever | First state denied | Minimum change | Effective? |
|---|---|---|---|
| **Hazard rate λ** | Fair at λ×1.2 | Fair: 10% → 12% | ✅ Yes — recalibration |
| **LGD** | Fair at 70% | 60% → 70% | ✅ Yes — stress standard |
| **Balance exposure mult** | Fair at ×1.1 | +10% stress buffer | ✅ Moderate |
| **Uptake threshold** | Poor at 40% | Policy gate | ⚠️ Policy, not model |
| **Discount rate** | None | N/A | ❌ No effect |
| **Per-customer p_def cap** | None below 1.5% | N/A | ❌ No effect |
| **Excellent approval** | Never | Requires fee < $11.20 | ❌ Impossible via calibration |

### Recommended recalibration for more realistic approval rates

Combining two changes keeps the model within defensible assumptions while producing
sub-100% approval across Fair and some Good:

```
LGD: 60% → 70%    (industry midpoint for unsecured consumer)
λ:   ×1.2          (20% uplift for economic stress / model conservatism)

Result:
  Excellent: 100%   (unchanged — genuinely low risk)
  Good:      100%   (unchanged)
  Fair:       ~88%  (more realistic for a heterogeneous tier)
  Poor:       ~30%  (tighter, reflecting real charge-off experience)
```

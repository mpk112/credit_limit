# Strategy 2 — Profit & Risk Optimisation Workings

All numbers are derived from `term_extension_results.csv` (LGD = 60%, r = 19%).

---

## Baseline (Current State)

| Metric | Value |
|---|---|
| Total customers | 30,000 |
| Eligible customers | 25,068 |
| Extensions granted | 22,887 |
| Total revenue | $899,373 |
| Total expected losses | $298,485 |
| **Net profit** | **$600,888** |
| Portfolio default risk | 0.84% |
| Portfolio risk cap | 5.0% (slack: 4.16 pp) |
| Fee charged | $40 flat |

### Breakdown by credit state (granted customers)

| State | Granted | Avg term | Avg revenue | Avg loss | Avg profit | Avg p_default |
|---|---|---|---|---|---|---|
| Excellent | 4,093 | 90.0 days | $39.08 | $3.54 | $35.54 | 0.22% |
| Good | 7,643 | 75.0 days | $39.23 | $8.41 | $30.82 | 0.52% |
| Fair | 7,941 | 60.0 days | $39.38 | $18.41 | $20.97 | 1.14% |
| Poor | 3,210 | 46.4 days | $39.52 | $22.91 | $16.61 | 2.07% |

**Key observation:** Poor customers already get the shortest average terms (46.4 days) — the lognormal term distribution is already self-correcting for risk. Their losses ($22.91) are below revenue ($39.52), so every approved Poor customer still contributes positive profit.

---

## The Core Profit Formula

For each customer, the model calculates:

```
Profit per customer = Revenue − Loss

Revenue = fee × exp(−r × T / 365)
Loss    = balance × LGD × p_default × exp(−r × T / 730)

Where:
  fee     = $40 (current)
  r       = 19% annual discount rate
  T       = extension term in days
  LGD     = 60% (loss given default)
  balance = outstanding loan amount
```

The LP grants an extension when `Profit > 0`, i.e., when `Revenue > Loss`.

Breakeven: `balance × 0.60 × p_default × discount < $39.38`

---

## Strategy 1 — Raise the Flat Fee

**Concept:** Revenue scales directly with the fee. The same 22,887 customers are approved at any fee below $52 (the first denial threshold for Fair customers). Losses are unchanged.

**Formula:**
```
New revenue = $899,373 × (new_fee / $40)
New profit  = New revenue − $298,485 (losses unchanged)
```

**Working:**

| Fee | Revenue | Losses | Profit | vs Baseline |
|---|---|---|---|---|
| $40 (current) | $899,373 | $298,485 | $600,888 | — |
| $42 | $944,342 | $298,485 | $645,857 | **+$44,969** |
| $44 | $989,310 | $298,485 | $690,825 | **+$89,937** |
| $46 | $1,034,279 | $298,485 | $735,794 | **+$134,906** |
| $48 | $1,079,248 | $298,485 | $780,763 | **+$179,875** |
| $50 | $1,124,216 | $298,485 | $825,731 | **+$224,843** |
| $52 | $1,169,185 | $298,485 | $870,700 | **+$269,812** |

**Why doesn't a higher fee deny more customers?**
The breakeven fee per state shows how much room exists before denials start:

| State | Median breakeven fee | Max breakeven fee (first denial) |
|---|---|---|
| Excellent | $3.29 | $13.68 |
| Good | $8.22 | $25.50 |
| Fair | $18.63 | $52.00 |
| Poor | $34.36 | $80.44 |

At $48, every Excellent and Good customer clears the threshold with room to spare. Fair customers start being denied only above $52.

**Impact at $48:**

| Metric | Before | After |
|---|---|---|
| Profit | $600,888 | $780,763 |
| Change | — | **+$179,875 (+29.9%)** |
| Approvals | 22,887 | 22,887 (unchanged) |
| Portfolio risk | 0.84% | **0.84% (unchanged)** |

**Risk impact:** None. The same customers are approved — same default probabilities, same balances.

---

## Strategy 2 — Tiered Pricing by Credit State

**Concept:** Instead of a single price for everyone, charge more to low-risk customers (who will pay without hesitation) and keep the price unchanged for higher-risk customers (who are borderline).

**Proposed tiers:**

| State | Current fee | Proposed fee | Rationale |
|---|---|---|---|
| Excellent | $40 | $50 | Median breakeven only $3.29 — massive margin, zero denial risk |
| Good | $40 | $46 | Median breakeven $8.22 — still far from any threshold |
| Fair | $40 | $45 | Stays below the $52 first-denial threshold |
| Poor | $40 | $40 | Keep unchanged — they are already borderline |

**Working:**

Revenue increment per state:

```
Excellent: 4,093 customers × $39.08 avg × (50−40)/40 = +$39,989
Good:      7,643 customers × $39.23 avg × (46−40)/40 = +$44,977
Fair:      7,941 customers × $39.38 avg × (45−40)/40 = +$39,087
Poor:      no change                                  = +$0
─────────────────────────────────────────────────────────────────
Total revenue increase:                               +$124,053
```

**Impact (E$50 / G$46 / F$45 / P$40):**

| Metric | Before | After |
|---|---|---|
| Revenue | $899,373 | $1,023,426 |
| Losses | $298,485 | $298,485 |
| Profit | $600,888 | $724,941 |
| Change | — | **+$124,053 (+20.6%)** |
| Portfolio risk | 0.84% | **0.84% (unchanged)** |

**Aggressive tier (E$52 / G$48 / F$46 / P$40):**

| Metric | Before | After |
|---|---|---|
| Profit | $600,888 | $755,748 |
| Change | — | **+$154,860 (+25.8%)** |
| Portfolio risk | 0.84% | **0.84% (unchanged)** |

**Risk impact:** None. Tiered pricing changes revenue only — approval decisions and default probabilities are unchanged.

---

## Strategy 3 — 30-Day Micro-Extensions for Currently-Denied Customers

**Concept:** There are 2,181 eligible customers currently denied because they are unprofitable at their assigned term (typically 60–90 days). A shorter 30-day extension dramatically reduces the default probability, flipping many from unprofitable to profitable.

**Why 30-day terms help:**

Default probability shrinks with shorter term:
```
p_default(T) = 1 − exp(−λ × T / 365)

For Poor (λ = 22%):
  T = 90 days → p_def = 5.28%
  T = 60 days → p_def = 3.55%
  T = 30 days → p_def = 1.79%
```

Loss at T = 30 days:
```
loss = balance × 0.60 × 0.0179 × exp(−0.19 × 30/730)
     = balance × 0.01066

Breakeven balance = $39.38 / 0.01066 = $3,694

vs T = 90 days breakeven balance = $1,233
```

So at 30 days, customers with balances up to $3,694 become profitable — vs only $1,233 at 90 days.

**Actual result from data:**
Of 2,181 denied eligible customers, **1,676 would be profitable at 30 days**.

```
Revenue from 1,676 new approvals = $66,001
Loss from 1,676 new approvals    = $45,129
─────────────────────────────────────────
Net profit                       = $20,872
```

**Impact:**

| Metric | Before | After |
|---|---|---|
| Approvals | 22,887 | 24,563 |
| Profit | $600,888 | $621,760 |
| Change | — | **+$20,872 (+3.5%)** |
| Portfolio risk | 0.84% | **0.87% (+0.03 pp)** |

**Risk impact:** Small. The 1,676 new customers have avg p_default = 1.16% and avg balance $3,976 — higher-than-average risk, but only moves the portfolio from 0.84% → 0.87%, well within the 5% cap.

---

## Strategy 4 — Reduce Eligibility Gate (60 → 45 Days)

**Concept:** Currently 4,932 customers are ineligible because their last loan was less than 60 days ago. Reducing the gate to 45 days for Excellent and Good customers only unlocks a safe, profitable subset.

**Why Excellent/Good only?**
Their low default risk means they will almost certainly be approved once eligible. Letting in Poor/Fair customers at 45 days adds more complexity with less certain payoff.

**Estimation working:**
```
Ineligible Excellent: 2,113 customers
Ineligible Good:      1,624 customers

Assuming days_since_last_loan is uniformly distributed [0, 59]:
Customers in the 45–59 day window = 15/60 = 25% of ineligible

New Excellent eligible: 2,113 × 0.25 = 528
New Good eligible:      1,624 × 0.25 = 406
Total new eligible:     934 customers → all approved (100% approval rate)
```

**Revenue and loss for new approvals:**
```
Excellent: 528 × $39.08 avg revenue = $20,634
Good:      406 × $39.23 avg revenue = $15,927
Total new revenue:                    $36,561

Excellent: 528 × $3.54 avg loss  = $1,869
Good:      406 × $8.41 avg loss  = $3,414
Total new loss:                    $5,283

Net profit from new approvals:     $31,278
```

**Impact:**

| Metric | Before | After |
|---|---|---|
| Eligible customers | 25,068 | ~26,002 |
| Approvals | 22,887 | ~23,821 |
| Profit | $600,888 | $632,165 |
| Change | — | **+$31,277 (+5.2%)** |
| Portfolio risk | 0.84% | **0.83% (−0.01 pp)** |

**Risk impact:** Slightly decreases. Adding Excellent/Good customers (p_default 0.22%–0.52%) to a portfolio averaging 0.84% pulls the weighted average down.

---

## Strategy 5 — Concentration Limit on Poor Customers (Risk Reduction Tool)

**Concept:** This strategy does not increase profit — it trades some profit for a lower, more defensible portfolio risk. Useful if the model needs to demonstrate conservatism (regulatory review, board presentation).

**Working:**

Each approved Poor customer contributes:
```
Avg revenue: $39.52
Avg loss:    $22.91
Avg profit:  $16.61 per customer
```

Removing Poor customers reduces both revenue and loss, with a net profit cost:
```
Cost of removing one Poor customer: $16.61 profit foregone
Benefit: portfolio risk decreases
```

**Impact at various concentration caps:**

| Poor cap | Poor removed | Revenue lost | Loss saved | Profit change | Portfolio risk |
|---|---|---|---|---|---|
| 14% (current) | 0 | $0 | $0 | $0 | 0.84% |
| 12% | 456 | −$18,022 | −$10,447 | **−$7,575** | ~0.78% |
| 10% | 921 | −$36,398 | −$21,100 | **−$15,298** | ~0.70% |
| 5% | 2,099 | −$82,952 | −$48,067 | **−$34,885** | ~0.55% |
| 0% (no Poor) | 3,210 | −$126,859 | −$73,544 | **−$53,315** | ~0.42% |

**Risk impact:** Significant reduction. Use this if the target is to demonstrate sub-0.7% portfolio risk, e.g. for a regulatory submission. Cost is modest — removing all Poor reduces profit by only $53K (8.9%).

---

## Strategy 6 — Phased Rollout (Risk Containment, Not Profit Change)

**Concept:** Same total profit as the full model, but released in phases. If the model is wrong (e.g., actual defaults exceed simulated), losses are contained to the phase already deployed.

**Phase structure:**

| Phase | Customers | Selection criterion | Expected profit | Portfolio risk |
|---|---|---|---|---|
| 1 | ~6,000 | Top quartile by profitability_score | ~$212K | ~0.30% |
| 2 | ~16,600 | All eligible Excellent + Good + remaining Fair | ~$565K | ~0.60% |
| 3 | ~3,210 | LP-approved Poor | ~$53K | 0.84% |

**Gate between phases:**
After each phase, compare actual 30-day default rate to model's `p_default_sim`. Proceed only if:
```
actual_default_rate  ≤  1.5 × simulated p_default_sim
```

If the gate fails, stop and recalibrate before Phase 3.

**Risk impact:** Does not change total expected profit ($600,888) but limits downside exposure if the Monte Carlo simulation has underestimated defaults.

---

## Combined Scenario

All profit-generating strategies are additive (they address different customers/mechanics):

```
Baseline profit:                $600,888

+ Strategy 1 (fee $40 → $48):  +$179,875
+ Strategy 3 (30-day denied):  +$ 20,872
+ Strategy 4 (gate 60 → 45d):  +$ 31,277
─────────────────────────────────────────
Combined profit:                $832,912
Total uplift:                   +$232,024  (+38.6%)
```

**Combined risk:** 0.87% (still 4.13 pp below the 5% cap).

Note: Combining Strategy 1 (fee raise) with Strategy 2 (tiered pricing) is mutually exclusive — choose one or the other. Tiered pricing gives lower absolute profit ($724,941) than a flat $48 raise ($780,763) because it keeps Poor at $40. The flat raise is simpler; tiered pricing is more defensible from a risk-based pricing standpoint.

---

## Summary — All Strategies Ranked

| Strategy | Profit gain | New profit | Risk | Implementation |
|---|---|---|---|---|
| 1a. Raise fee to $48 (flat) | **+$179,875** | $780,763 | 0.84% (unchanged) | Config change |
| 1b. Raise fee to $50 (flat) | **+$224,843** | $825,731 | 0.84% (unchanged) | Config change |
| 2a. Tiered E$50/G$46/F$45/P$40 | **+$124,053** | $724,941 | 0.84% (unchanged) | Config change |
| 2b. Tiered E$52/G$48/F$46/P$40 | **+$154,860** | $755,748 | 0.84% (unchanged) | Config change |
| 3. 30-day micro-extensions | **+$20,872** | $621,760 | 0.87% (+0.03 pp) | Model change (offer T=30 to denied) |
| 4. Reduce eligibility gate to 45d | **+$31,277** | $632,165 | 0.83% (−0.01 pp) | Config change |
| 5. Concentration limit 10% Poor | **−$15,298** | $585,590 | 0.70% (−0.14 pp) | LP constraint change |
| 6. Phased rollout | **$0** | $600,888 | Contained per phase | Process change |

**Best combined (fee + micro + gate):**

| Metric | Value |
|---|---|
| Profit | $832,912 |
| Uplift vs baseline | +$232,024 (+38.6%) |
| Portfolio risk | 0.87% |
| Risk cap headroom | 4.13 pp |

---

## What Each Strategy Actually Changes

| Strategy | What changes | What stays the same |
|---|---|---|
| Fee raise | Revenue per customer | Approvals, losses, risk |
| Tiered pricing | Revenue per customer by state | Approvals, losses, risk |
| 30-day micro | Which denied customers get approved | Existing approvals, existing losses |
| Gate reduction | Who is eligible | Approval logic, fees, losses per customer |
| Concentration limit | Max Poor approvals | Fee, approval logic for other states |
| Phased rollout | When customers are offered | Total approvals, total profit |

# Credit Limit Extension — Portfolio Strategy

**Audience:** Risk Officers, Credit Committee, Portfolio Management  
**Simulation:** 30,000 accounts · 12 monthly campaigns · 1-year horizon  
**Model:** Multi-period lifecycle with Monte Carlo, GBM uptake forecasting, and LP optimisation

---

## Executive Position

The simulation demonstrates that a well-constrained extension programme is a high-conviction opportunity. Over a 12-month horizon, the optimised policy generates **$1.41M net profit on $2.12M revenue** — a **66.6% margin** — while keeping portfolio default rates at **0.66%**, more than seven times below the 5% risk constraint. The programme reaches **96.1% of the customer base** with at least one approved offer, confirming broad eligibility without sacrificing credit discipline.

The core strategic insight is that the model's LP optimiser is consistently conservative: it approves only customers where the expected default contribution stays below the portfolio risk cap, and the realised outcomes bear this out. The risk budget is not being consumed — it is being actively preserved as a buffer.

---

## Tier Strategy

The portfolio is segmented into four credit tiers — Excellent, Good, Fair, and Poor — defined by a composite score weighting on-time payment history (35%), credit utilisation (30%), recency (20%), and profitability contribution (15%).

### Excellent — Accelerate

| Metric | Value |
|--------|-------|
| Customers | 6,206 (20.7% of portfolio) |
| Accept rate | 79.5% |
| Avg lifetime profit | $68.70 per customer |
| Default rate | 0.17% |
| Profit margin | 90.8% |

**Strategy:** Offer extensions in every campaign without restriction. Excellent-tier customers generate the highest per-customer return at the lowest risk. The 90.8% profit margin reflects minimal loss provisions; the 0.17% default rate is consistent with near-zero credit risk. Limit increases of 20–25% are appropriate given the balance sheet strength of this segment. No additional approval gates are required — the LP constraint provides sufficient guardrail.

**Growth lever:** 99.5% of Excellent customers remain Excellent at year-end. The strategy priority here is retention and volume — ensuring every eligible customer receives a timely offer.

---

### Good — Standard Approval

| Metric | Value |
|--------|-------|
| Customers | 9,267 (30.9% of portfolio) |
| Accept rate | 74.3% |
| Avg lifetime profit | $58.25 per customer |
| Default rate | 0.43% |
| Profit margin | 76.5% |

**Strategy:** Approve all LP-selected offers on the standard monthly cadence. Good-tier customers are the portfolio's volume engine — largest segment with strong margins and a proven 74.3% take-up. The 0.43% default rate is well within tolerance.

The standout finding for this segment is **credit upside**: 81.8% of Good customers migrate to Excellent by year-end, driven by consistent on-time payment behaviour rewarded by the re-scoring mechanism. This makes Good the highest-value tier for portfolio quality improvement, not just current-period profit. Limit increases of 15–20% are recommended.

---

### Fair — Selective Approval

| Metric | Value |
|--------|-------|
| Customers | 9,089 (30.3% of portfolio) |
| Accept rate | 61.8% |
| Avg lifetime profit | $40.23 per customer |
| Default rate | 0.88% |
| Profit margin | 55.4% |

**Strategy:** Maintain eligibility but apply additional campaign-interval spacing — offering every second campaign rather than every month. The 55.4% margin is profitable but thinner, and the 0.88% default rate represents meaningful loss exposure at scale. The LP optimiser already filters the riskiest Fair accounts; the additional spacing provides a behavioural test: customers who remain eligible after 60 days are demonstrating sustained repayment discipline.

The migration data is positive: **83.8% of Fair customers improve to Good or Excellent by year-end**. The programme is not a one-time transaction for this segment — it is a credit rehabilitation pathway. Approve selectively and track migration velocity as the primary KPI, not short-term profit.

Limit increases of 10–15% are recommended, sized to be meaningful enough to incentivise uptake without overextending exposure.

---

### Poor — Restricted Access

| Metric | Value |
|--------|-------|
| Customers | 5,438 (18.1% of portfolio) |
| Accept rate | 44.3% |
| Avg lifetime profit | $14.62 per customer |
| Default rate | 1.54% |
| Profit margin | 28.0% |

**Strategy:** Limit offers to every third campaign and impose an enhanced pre-approval review. The 1.54% default rate is more than nine times higher than the Excellent tier; the 28% margin leaves limited room for loss absorption at scale. The LP correctly limits exposure here — Poor customers receive the fewest offers and smallest limits.

Critically, 28.3% of Poor customers remain in Poor at year-end, and 40.2% migrate only to Fair — a slow recovery trajectory. Offering too aggressively to this segment accelerates losses without meaningful credit improvement. The correct posture is controlled access: small limit increases (5–10%), longer re-eligibility windows, and a requirement for at least two consecutive on-time payments before the next offer.

Poor-tier accounts should not be excluded entirely. The 0.9% who migrate to Excellent and the 30.6% who reach Good demonstrate that even this segment responds to the right incentive structure. The programme's cost is low; the rehabilitation upside, though slow, is real.

---

## Risk Budget Utilisation

The 5% portfolio default risk cap set in the LP constraint was never breached across any of the 12 simulation campaigns. Peak campaign-level default risk reached **0.99%** — less than one-fifth of the permitted ceiling.

This has two strategic implications:

1. **The policy is conservative.** There is headroom to modestly increase offer volumes to Fair and Poor segments without violating the risk constraint — provided the LP is re-run on each expanded eligible pool.

2. **The cap itself should be re-calibrated annually.** A 5% cap designed for a static one-shot model is structurally over-conservative when applied to a lifecycle model with monthly re-scoring. The dynamic re-scoring mechanism removes the riskiest customers from eligibility before they can contribute to portfolio default. Risk officers should consider moving to a 2–3% operational cap with a 5% hard ceiling, giving the LP more freedom to approve borderline Good and Fair customers.

---

## Sensitivity Analysis — Parameter Levers

The 9-scenario sensitivity grid varied the on-time payment boost (0.5pp / 2.0pp / 5.0pp) and the default penalty (5pp / 10pp / 20pp) across 180-day sub-simulations.

### On-Time Payment Boost — The Most Powerful Lever

| Boost | % Excellent at End | Profit |
|-------|--------------------|--------|
| 0.5 pp | 42.7% | $673,501 |
| 2.0 pp | 49.2% | $692,743 |
| 5.0 pp | 61.9% | $664,309 |

Increasing the on-time boost from 0.5pp to 5.0pp moves **19.2 percentage points** more customers into the Excellent tier — the single most effective lever for long-term portfolio quality. Profit peaks at 2.0pp ($692K) rather than 5.0pp ($664K), suggesting that very aggressive rewards accelerate re-scoring to the point where customers quickly become ineligible for further extensions (reducing offer volume and total revenue).

**Recommendation:** Set the on-time payment boost at **2.0pp** as the baseline. This balances credit improvement velocity against offer volume — the portfolio earns more and upgrades faster without exhausting the eligible pool.

### Default Penalty — A Second-Order Effect

| Penalty | % Poor at End | Default Rate |
|---------|--------------|--------------|
| 5 pp | 5.38% | 0.64% |
| 10 pp | 5.67% | 0.62% |
| 20 pp | 5.72% | 0.61% |

The default penalty has a marginal effect on aggregate profit (< 1% variance across all scenarios) but meaningfully reduces the share of customers remaining in Poor. Higher penalties create stronger downward pressure on borderline accounts, accelerating exit from Poor — whether to Fair or out of the eligible pool entirely. The default rate is slightly lower at higher penalties because higher-risk accounts drop out of eligibility faster.

**Recommendation:** Set the default penalty at **10pp** — sufficient to move Poor accounts quickly without creating cliff-edge dynamics where any default immediately renders an account permanently ineligible.

---

## Operational Recommendations

**1. Move to a 30-day campaign cadence as the standard.** The simulation uses monthly campaigns and produces strong results. Daily campaigns (used in stress-testing) add computational overhead without proportional profit improvement; the Bernoulli acceptance mechanism means customers who miss one campaign remain eligible the next.

**2. Re-score after every extension outcome, not on a fixed schedule.** The feature update mechanism — adjusting `on_time_pct` by ±pp and re-running Borda-count scoring — is what drives the 81.8% Good → Excellent migration rate. This should be operationalised as a real-time event trigger, not a batch process.

**3. Monitor three KPIs per campaign:** net profit, default rate, and % Excellent. The sensitivity analysis confirms these three move in opposite directions under parameter changes — no single KPI tells the full story.

**4. Expand the exposure cap from $500M to $650M.** The current cap was never approached in simulation; the peak utilisation rate was well below 10%. The constraint is not binding and limits potential volume for Good and Excellent accounts.

**5. Automate LP re-optimisation.** The LP runs in under 1 second per campaign on the full 30,000-account pool. There is no operational justification for manual override of LP decisions — exceptions should require documented risk officer approval with rationale logged.

---

## Summary Position

| Tier | Offer Cadence | Limit Increase | Priority |
|------|--------------|----------------|----------|
| Excellent | Every campaign | +20–25% | Maximum volume |
| Good | Every campaign | +15–20% | Standard approval |
| Fair | Every 2nd campaign | +10–15% | Selective; track migration |
| Poor | Every 3rd campaign | +5–10% | Enhanced review required |

The programme is profitable, risk-constrained, and structurally self-improving: customers who repay on time migrate to higher tiers, increasing future profit and reducing future loss provisions. The risk budget is effectively a ratchet — discipline today funds volume tomorrow.

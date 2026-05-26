# Customer Behaviour Insights — Credit Limit Extension Lifecycle

**Audience:** Risk Officers, Credit Committee, Portfolio Management  
**Simulation:** 30,000 accounts · 12 monthly campaigns · 1-year horizon  
**Model:** Multi-period lifecycle — each customer is re-scored after every extension outcome

---

## Overview

This document describes how customers behave over a 12-month credit limit extension programme. Because the simulation tracks each customer's actions and outcomes month by month — rather than assuming a single static profile — it reveals patterns that a one-shot model cannot. Customers move between credit tiers, repay at different rates, and respond to offers differently depending on their segment and history.

The central finding is that **behaviour is more dynamic than credit scoring typically assumes.** The majority of Fair-tier customers improve significantly within a year. Good-tier customers overwhelmingly converge to Excellent. Even within the Poor tier, a substantial minority demonstrates enough repayment discipline to recover. The extension programme is not just a revenue tool — it is a structured behavioural incentive.

---

## Offer and Acceptance Behaviour

Of 107,931 total offers made across 12 campaigns, **70,317 were accepted** — a portfolio-wide acceptance rate of **65.1%**. The remaining 34.8% declined for reasons captured in the GBM uptake model: unfavourable macroeconomic conditions, recent credit events, or low perceived need for the limit increase.

Acceptance rates differ sharply by tier:

| Tier | Total Offered | Total Accepted | Acceptance Rate |
|------|--------------|----------------|-----------------|
| Excellent | 18,788 | 14,932 | **79.5%** |
| Good | 31,905 | 23,711 | **74.3%** |
| Fair | 36,036 | 22,273 | **61.8%** |
| Poor | 21,202 | 9,401 | **44.3%** |

Three patterns stand out:

**High acceptance is a signal of creditworthiness, not just demand.** Excellent and Good customers accept more readily because they have a track record of successfully completing extensions. They have demonstrated to themselves — not just to the lender — that the product works for them. Poor-tier customers are more hesitant, partly because they have had adverse outcomes in the past.

**Fair tier receives the most offers in absolute terms** (36,036), reflecting its size (9,089 customers) and monthly campaign eligibility. Despite the lower per-customer profit, Fair customers represent the largest aggregate revenue pool precisely because of volume.

**Poor-tier hesitancy is economically rational.** The 44.3% acceptance rate among Poor customers partially reflects self-selection: customers who know they are financially stretched are less likely to take on additional credit. This natural demand suppression is a real-world risk mitigant that the LP alone cannot produce.

---

## Repayment Behaviour

Of 70,317 completed or in-progress extensions, outcomes broke down as follows:

| Outcome | Count | Share of Extensions |
|---------|-------|---------------------|
| On-time completion | 43,366 | 61.7% |
| Early repayment | 10,172 | 14.5% |
| Default | 466 | 0.66% |
| Active (in-progress at year-end) | ~16,313 | 23.2% |

**Early repayment is the underappreciated behaviour.** 14.5% of all extensions are repaid ahead of schedule, with a concentration in the Excellent tier (2,959 of 14,932 extensions, or 19.8%). Early repayers are the portfolio's best customers: they exhibit low credit risk, high liquidity, and consistent discipline. The simulation rewards them with a +1pp on-time payment boost — smaller than the on-time completion boost (+2pp) — because their credit score is already strong and additional scoring uplift has diminishing marginal value.

**Default is rare and concentrated.** The 466 defaults across 70,317 extensions translate to a **0.66% default rate**, against a 5% LP risk cap. Defaults are disproportionately concentrated in Poor (1.54%) and Fair (0.88%), consistent with the underlying risk ranking. Excellent-tier defaults (0.17%) are largely noise — 25 events out of 14,932 extensions — and do not represent a systemic pattern.

The default rate by tier reveals a clean risk gradient:

| Tier | Default Rate | Default Count |
|------|-------------|---------------|
| Excellent | 0.17% | 25 |
| Good | 0.43% | 101 |
| Fair | 0.88% | 195 |
| Poor | 1.54% | 145 |

The 9× difference between Excellent and Poor validates the four-tier segmentation. These are genuinely different populations with meaningfully different risk profiles, not just arbitrary labels.

---

## Credit Migration — The Long-Term Behavioural Story

The most important insight from the lifecycle model is how dramatically customers move between tiers over 12 months. The migration matrix below shows the probability of ending in each tier, conditional on starting state:

| Starting Tier | → Excellent | → Good | → Fair | → Poor |
|--------------|-------------|--------|--------|--------|
| **Excellent** | **99.5%** | 0.2% | 0.2% | 0.1% |
| **Good** | **81.8%** | 17.1% | 0.4% | 0.7% |
| **Fair** | **31.8%** | 52.0% | 14.1% | 2.0% |
| **Poor** | 0.9% | 30.6% | 40.2% | **28.3%** |

### What the Migration Matrix Reveals

**Good → Excellent is the dominant pathway.** 81.8% of customers who start in Good reach Excellent by year-end. This is not a gradual drift — it is a structural outcome of the re-scoring mechanism. Customers who accept extensions and repay on time earn a +2pp boost to their on-time payment percentile rank every cycle. With a monthly cadence and a strong starting position, this compounding effect moves most Good customers across the Excellent threshold within 4–6 campaigns.

**Fair is a transition state, not a steady state.** 83.8% of Fair customers improve (31.8% → Excellent, 52.0% → Good). Only 14.1% remain Fair and 2.0% deteriorate to Poor. This challenges the common assumption that Fair customers represent stable medium-risk accounts. Given the right incentive — a timely extension offer with a meaningful limit increase — most Fair customers actively rehabilitate their credit profile within a year.

**Poor splits into three behavioural groups.** The Poor tier does not exhibit uniform stagnation:
- **30.6% recover to Good** — these are customers who had adverse events but retained underlying financial discipline
- **40.2% reach Fair** — slow improvers who are making progress but remain elevated-risk
- **28.3% remain Poor** — the genuinely distressed segment where offer activity has limited positive effect

Risk officers should not treat Poor as a monolithic segment. The 30.6% who recover to Good are worth identifying and targeting with modest but regular offers. Behavioural signals — specifically whether a Poor customer completed their last extension on time or early — are more predictive of future trajectory than the tier label alone.

**Excellent is an absorbing state in practice.** The 99.5% self-retention rate means that once a customer reaches Excellent, the programme shifts from credit improvement to relationship maintenance. These customers need competitive offers and fast eligibility cycles, not additional risk screening.

---

## How Behaviour Evolves Over Time

The simulation tracks `on_time_pct` — the running share of a customer's credit history involving on-time payments — as the primary dynamic feature. This metric is updated after every extension outcome:

- **On-time completion:** +2.0 percentage points
- **Early repayment:** +1.0 percentage point
- **Default:** −10.0 percentage points

The asymmetry is intentional and reflects empirical loss dynamics: a single default carries roughly 5× the behavioural signal of a successful completion. This is consistent with the credit scoring literature and reflects the practical reality that defaults damage repayment capacity and customer trust simultaneously.

**Positive feedback loop in upper tiers.** For Excellent and Good customers, each completed extension improves their on-time percentage, which improves their Borda-count score, which maintains or improves their tier. This creates a virtuous cycle: better scores → more offers → more completions → better scores. The 81.8% Good → Excellent migration rate is a product of this compounding.

**Negative shock absorption in lower tiers.** For Fair and Poor customers, a single default imposes a −10pp penalty, which can be enough to re-classify them downward. However, the simulation shows that most Fair and Poor customers avoid default entirely — the 0.88% and 1.54% rates leave 99.1% and 98.5% of completed extensions default-free, respectively. The LP constraint plays a key role here: by withholding offers from the highest-risk Fair and Poor accounts each campaign, it prevents the defaults that would otherwise entrench customers in poor tiers.

---

## Macroeconomic Sensitivity

The simulation incorporates macroeconomic enrichment via Federal Reserve economic data: GDP growth, unemployment rate, Federal Funds rate, and CPI. These factors adjust the base default hazard rate (λ) and uptake probability through the GBM model.

Under baseline 2023 macro conditions (GDP +2.5%, unemployment 3.5%, Fed rate 5.25%), the programme performs at the results described above. Behavioural sensitivity to macro conditions concentrates in two areas:

- **Uptake rates are macro-sensitive.** Rising unemployment suppresses demand for credit limit extensions, particularly in Fair and Poor tiers where customers are already margin-constrained. A 1pp increase in unemployment is estimated to reduce Fair and Poor acceptance rates by approximately 4–6 percentage points.

- **Default rates are partially macro-correlated.** The λ-adjustment in the Monte Carlo accounts for elevated unemployment raising default hazard. Under a recession scenario (unemployment +3pp, GDP −1%), the Poor-tier default rate is estimated to rise to approximately 2.8–3.2% — still within the LP cap but meaningfully above the baseline 1.54%.

Risk officers should treat the macro adjustment as a forward-looking stress scenario tool, not just a historical calibration. The LP constraint's 5% hard cap provides insulation across a wide range of macro conditions; the operational 0.66% realised default rate represents the favourable-conditions baseline, not the floor.

---

## Behavioural Archetypes

Based on the migration matrix and repayment outcomes, four customer archetypes emerge that cut across the formal tier structure:

**The Reliable Repayer (Excellent and upper-Good):** Accepts most offers, repays on time, rarely defaults. Constitutes the majority of profitable volume. Behaviour is stable and predictable. Key retention risk: competitor offers with higher limits. Strategy: prioritise every-campaign eligibility and competitive limit sizing.

**The Upward Mover (lower-Good and upper-Fair):** Starts at moderate credit quality but demonstrates consistent improvement over the programme year. Likely completing extensions on time, accumulating on-time payment boosts, and re-scoring upward. This archetype represents the programme's highest credit-improvement ROI. Strategy: regular offers, meaningful limit increases, and track migration velocity monthly.

**The Slow Recoverer (lower-Fair and upper-Poor):** Makes progress but at a slower rate. May have had one adverse event (a late payment, a temporary income disruption) that created the Fair/Poor classification. Responds to offers but with longer decision times and lower acceptance rates. Strategy: every-other-campaign cadence with slightly smaller limit increases; monitor whether completion rates are improving.

**The Persistent Risk (lower-Poor):** Remains in Poor at year-end despite eligibility and offers. Completion rates are low, acceptance rates are low, and any defaults pull credit scores further down. This archetype is not well served by the standard extension programme. Strategy: freeze extension offers and redirect to a structured repayment assistance or credit counselling pathway.

---

## Key Behavioural Takeaways for Risk Officers

1. **The majority of customers improve.** Across the full portfolio, only 28.3% of Poor customers (5% of all 30,000) remain in Poor at year-end. Every other starting-tier has strong upward migration. The programme is net positive for portfolio credit quality.

2. **On-time completion is the dominant outcome by volume** (61.7%), not default (0.66%). Risk discussions that anchor on default scenarios significantly overstate the expected loss picture.

3. **Early repayment is a leading indicator of Excellent-tier behaviour.** Customers with two or more early repayments in the observation window should be pre-classified as Excellent regardless of their current tier label and offered accordingly.

4. **The Fair tier requires active management, not passive monitoring.** 83.8% improvement is high, but the 2.0% who deteriorate to Poor represent a preventable tail risk. Identifying which Fair customers are likely to deteriorate — using completion pattern data rather than just the tier label — should be a standing risk function task.

5. **Credit migration is faster than annual cycle reviews assume.** Under monthly re-scoring, meaningful tier movement happens within 3–4 months of programme entry. Annual credit reviews systematically lag behind the customer's actual current risk profile. Moving to quarterly re-scoring as a minimum is advisable even without the full lifecycle simulation infrastructure.

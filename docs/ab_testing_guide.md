# A/B Testing Guide — Analytics Team

## Principles

1. **One change per test.** Never run multi-variable tests unless it is a full factorial design with sufficient power.
2. **Pre-register your hypothesis.** Write the expected direction and magnitude of change before launching.
3. **Never stop early.** Peeking at results and stopping when p < 0.05 inflates false-positive rate to over 30%.
4. **Randomise at the right unit.** User-level randomisation prevents contamination. Page-level randomisation is only acceptable for purely cosmetic changes.

---

## Choosing the Right Statistical Test

### Conversion Rate Metrics (binary outcomes)

Use a **two-proportion z-test** or **chi-square test**.

Assumptions: samples are independent, each observation is binary (converted / not converted), expected count in each cell ≥ 5.

### Continuous Metrics (revenue, session duration, LTV)

Use a **two-sample t-test** for normally distributed data. For skewed distributions (common with revenue), use the **Mann-Whitney U test** (non-parametric).

Apply the **delta method** when the metric is a ratio (e.g., revenue per session).

### Count Metrics (pageviews, events per session)

Use a **Poisson regression** or bootstrap confidence intervals.

---

## Minimum Detectable Effect (MDE)

The MDE is the smallest relative change in a metric that an experiment is powered to detect.

**Standard settings:**
- Statistical power: 80% (β = 0.20)
- Significance level: 5% (α = 0.05), two-tailed
- Typical MDE for conversion metrics: 5–10% relative lift

**MDE formula (conversion):**

```
MDE = z_α/2 + z_β / sqrt(n × p × (1 - p)) × sqrt(2)
```

Where p is the baseline conversion rate and n is the per-variant sample size.

Use a sample size calculator before launching. Never launch a test without confirming you have enough traffic to reach the MDE.

---

## Minimum Sample Size

Calculate required sample size per variant before launch. Common mistake: running a test until "it looks significant" rather than until the pre-calculated sample size is reached.

**Rule:** Run for a minimum of **two full business cycles** (typically 14 days) AND until the minimum sample size is reached, whichever is longer.

Rationale: Two weeks captures weekday/weekend variation. Stopping at 3 days may catch a Monday spike that doesn't represent steady-state behaviour.

---

## Uplift Measurement

Report uplift as **relative change**, not absolute change.

**Relative uplift:** `(Treatment - Control) / Control × 100`

Always report:
- Point estimate (observed uplift)
- 95% confidence interval
- p-value
- Sample sizes for both variants
- Statistical power achieved

Do not report p-value alone. A p-value of 0.04 with a confidence interval of [-1%, +15%] is not actionable.

---

## Novelty Effect

New features often show inflated early engagement that decays. For features with high novelty risk, run the test for 4 weeks minimum and examine the treatment effect in week 3–4 in isolation.

---

## CUPED (Controlled-experiment Using Pre-Experiment Data)

CUPED reduces variance by adjusting for pre-experiment user behaviour, increasing statistical power without increasing sample size by up to 40%.

Use CUPED when:
- Pre-experiment data is available (at least 14 days)
- The metric is correlated with pre-experiment behaviour (typical for engagement metrics)

**Formula:** `Y_adjusted = Y - θ × (X - E[X])`

Where X is a pre-experiment covariate, θ = Cov(Y, X) / Var(X).

---

## Guardrail Metrics

Every experiment must define at least one guardrail metric — a metric that must not degrade. If a guardrail metric shows statistically significant degradation, ship nothing regardless of primary metric results.

Common guardrail metrics: page load time, error rate, refund rate.

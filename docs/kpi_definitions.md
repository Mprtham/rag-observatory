# KPI Definitions — Analytics Team

## Overview

This document defines the canonical KPIs tracked by the analytics team. Every metric listed here has a single agreed definition, an owner, and a refresh cadence. Discrepancies between this document and any dashboard or report should be raised as a data quality issue.

A **metric** is any quantitative measure. A **KPI** (Key Performance Indicator) is a metric directly tied to a strategic business objective with a defined target and owner. Not every metric is a KPI.

---

## Acquisition Metrics

### Customer Acquisition Cost (CAC)

**Definition:** Total sales and marketing spend divided by the number of new customers acquired in the same period.

**Formula:** `CAC = Total S&M Spend / New Customers Acquired`

**Period:** Monthly, rolling 90-day.

**Owner:** Growth team.

**Notes:** Include fully-loaded costs (headcount, tools, ad spend). Do not blend organic and paid CAC — report separately.

### Organic Acquisition Rate

**Definition:** Percentage of new users who arrive via organic channels (SEO, direct, referral) rather than paid media.

**Formula:** `Organic Rate = Organic New Users / Total New Users × 100`

**Target:** > 40% organic mix.

---

## Engagement Metrics

### Monthly Active Users (MAU)

**Definition:** Count of distinct users who perform at least one meaningful action (not just a session open) within a rolling 30-day window.

**Meaningful actions include:** completing a form, viewing a product page for > 10 seconds, clicking a CTA, making a purchase.

**Meaningful actions exclude:** bot traffic, internal staff, test accounts.

**Owner:** Product analytics.

**Refresh:** Daily.

### Daily Active Users (DAU)

**Definition:** Distinct users performing a meaningful action in a given calendar day.

**DAU/MAU ratio:** Target > 0.20. Below 0.10 signals low habit formation.

### Session Duration

**Definition:** Time from first event to last event in a session. Sessions with no second event are counted as 0 seconds (bounce).

---

## Retention Metrics

### Day-N Retention

**Definition:** Percentage of users from a cohort who return on day N after signup.

**Formula:** `Day-N Retention = (Cohort users active on day N) / (Cohort size) × 100`

**Standard cohort windows:** Day 1, Day 7, Day 14, Day 30.

**Benchmarks (SaaS):** Day-7 > 25%, Day-30 > 15% is considered healthy.

### Churn Rate

**Definition:** Percentage of active users at the start of a period who are no longer active at the end.

**Formula:** `Churn = Users Lost / Users at Start of Period × 100`

**Note:** Do not confuse with revenue churn. User churn and revenue churn are tracked separately.

---

## Revenue Metrics

### Lifetime Value (LTV)

**Definition:** Predicted net revenue from a customer over the full duration of their relationship.

**Simple formula:** `LTV = ARPU × Average Customer Lifetime`

**Segmentation:** LTV must be computed by acquisition cohort and channel. Blended LTV hides segment variation.

### LTV:CAC Ratio

**Definition:** Ratio of LTV to CAC. A ratio above 3:1 indicates a healthy business model.

**Target:** LTV:CAC ≥ 3.

---

## Data Freshness SLA

| Metric | Refresh Cadence | Max Staleness |
|--------|-----------------|---------------|
| MAU    | Daily           | 26 hours      |
| DAU    | Daily           | 4 hours       |
| CAC    | Monthly         | 3 days        |
| LTV    | Monthly         | 3 days        |
| Retention curves | Weekly | 7 days   |

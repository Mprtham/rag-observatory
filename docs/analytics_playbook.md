# Analytics Team Playbook

## Mission

Turn user behaviour into commercial decisions. Every analysis should end with a recommendation, not just a finding.

---

## How We Work

### Weekly Cadence

- **Monday:** Experiment readout — running tests reviewed, decisions made
- **Wednesday:** Ad-hoc requests triaged and prioritised
- **Friday:** KPI dashboard review with product and growth leads

### Monthly Cadence

- Full KPI review with senior leadership
- Retention cohort update
- Data quality scorecard circulated to all stakeholders

---

## Request Triage Framework

All analytics requests are triaged using four criteria:

1. **Decision impact:** Will this change a product or commercial decision this quarter?
2. **Urgency:** Is there a hard deadline (launch, board meeting, investor update)?
3. **Effort:** Estimated hours to deliver a reliable answer.
4. **Reversibility:** If we get this wrong, what is the cost?

Requests that score high on decision impact and reversibility get prioritised. Pure curiosity requests are deferred to exploration sprints.

---

## Analysis Standards

### Every Analysis Must Include

1. **Question framing** — What decision will this analysis inform?
2. **Data sources** — Which tables, date ranges, and filters were applied?
3. **Methodology** — What statistical approach was used and why?
4. **Caveats** — What are the limitations? What could make this wrong?
5. **Recommendation** — A clear, actionable recommendation, not just findings.

### Reproducibility

All analyses must be reproducible. SQL queries and Python notebooks must be version-controlled in GitHub. Raw data must not be modified — always work from a snapshot or staging table.

---

## SQL Style Guide (BigQuery)

### Naming Conventions

- Tables and columns: `snake_case`
- CTEs: descriptive names, `snake_case`, no abbreviations
- Aggregates in SELECT: always alias, e.g., `COUNT(*) AS total_sessions`

### CTE Structure

Each CTE on its own named block with a blank line between blocks. Avoid nesting CTEs deeper than 3 levels.

```sql
WITH
active_users AS (
    SELECT user_id, MAX(event_date) AS last_active
    FROM events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY user_id
),

cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_size
    FROM users
    GROUP BY cohort_month
)

SELECT ...
FROM active_users
LEFT JOIN cohort_sizes USING (cohort_month)
```

### Formatting Rules

- Keywords uppercase: `SELECT`, `FROM`, `WHERE`, `GROUP BY`, `ORDER BY`
- Indentation: 4 spaces, no tabs
- Commas: leading (before the column name), not trailing
- Window functions: write `PARTITION BY` and `ORDER BY` on separate lines

---

## Dashboard Design Principles

1. **Lead with the metric, not the chart.** Show the KPI number first, chart second.
2. **One page = one question.** Each dashboard tab should answer exactly one business question.
3. **Show context.** Every metric needs a comparison — vs prior period, vs target, vs benchmark.
4. **Avoid dual-axis charts.** They confuse most audiences. Use separate panels instead.
5. **Write the insight, not just the title.** Chart titles should say what the data shows, not what the data is. "Retention dropped 8% in March after pricing change" not "Retention Rate."

---

## Escalation Policy

If an analysis reveals a finding that could materially affect revenue, user trust, or regulatory compliance, escalate to the Head of Analytics immediately, regardless of the ticket priority. Do not wait for the weekly review.

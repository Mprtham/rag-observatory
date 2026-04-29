# Data Quality Standards — Analytics Team

## Five Core Dimensions

We track five data quality dimensions across all production datasets.

### 1. Completeness
Percentage of non-null values in required fields. Target: > 99% for primary keys and critical dimensions, > 95% for optional fields.

### 2. Accuracy
Values conform to business rules and domain constraints. Examples: dates cannot be in the future for historical tables, revenue cannot be negative, user IDs must match the users table.

### 3. Consistency
The same fact is represented identically across systems. Example: a user who signed up on 2024-01-15 in the CRM must show signup_date = '2024-01-15' in the warehouse — not 2024-01-14 due to timezone mismatch.

### 4. Timeliness
Data is available within the agreed SLA after the source event occurs. Freshness SLAs are defined per dataset in the Data Catalog.

### 5. Uniqueness
No duplicate records on primary key columns. Duplicates in dimension tables cause fan-out in joins and inflate all downstream metrics.

---

## Automated Data Quality Tests

All production dbt models must include dbt tests covering:

- `not_null` on all primary keys and required foreign keys
- `unique` on all primary keys
- `accepted_values` on all status and type enum columns
- `relationships` for all foreign key joins
- Custom row-count delta test: alert if row count drops > 20% vs 7-day average

Failing dbt tests block the model from materialising. Tests run on every pipeline execution.

---

## Alert Thresholds

Data quality alerts trigger when any of the following conditions are met:

- **Null rate breach:** null rate in a required column exceeds defined threshold (default 1%)
- **Row count anomaly:** row count drops more than 20% vs the 7-day rolling average, or is 0
- **Duplicate primary keys detected:** any duplicate in a unique-constrained column
- **Freshness SLA breached:** table not updated within SLA window (per Data Catalog)
- **Schema change detected:** new column added, column dropped, or data type changed without prior notice

---

## Incident Response

### Severity Levels

| Severity | Criteria | Response Time |
|----------|----------|---------------|
| P1 | Core revenue/KPI metric broken | 1 hour |
| P2 | Secondary metric broken, workaround exists | 4 hours |
| P3 | Non-critical dataset, no business impact | Next sprint |

### Process

1. Alert fires in Slack (#data-alerts channel).
2. On-call data engineer acknowledges within SLA.
3. Impact assessment: which downstream tables, dashboards, and reports are affected?
4. Hotfix or rollback applied.
5. Post-mortem written within 48 hours for P1 and P2 incidents.

---

## Data Governance Principles

- All datasets must have a documented owner (team + individual) in the Data Catalog.
- Schema changes require a PR with a migration plan reviewed by the data engineering lead.
- PII fields must be tagged in dbt metadata. Masked views are required for analyst access to PII.
- Raw source data is never modified. Transformations happen in staging and marts layers only.
- Deprecated datasets are soft-deleted (flagged, not dropped) for 90 days before permanent removal.

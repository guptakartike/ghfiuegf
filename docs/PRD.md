# Product Requirements Document (PRD)

## UK Wind Generation Forecast Analytics

**Status:** Initial product specification\
**Data scope:** January 2026\
**Primary users:** Electricity purchasing / trading operations teams

## 1. Product Overview

Build a web application that helps an electricity purchasing team
understand UK wind generation forecasts available at a defined day-ahead
decision cutoff and evaluate those forecasts against subsequently
observed actual generation.

Data sources: - **WINDFOR:** Wind generation forecasts, including
publication time and delivery time. - **FUELHH:** Actual half-hourly
generation, filtered to `fuelType == WIND`.

The application must distinguish information available at decision time
from information published later. It must not use later forecast
versions when evaluating a historical purchasing decision.

## 2. Problem Statement

Wind forecasts are revised over time. Users need to understand: 1. What
forecast was available at the decision cutoff? 2. How did it compare
with actual generation? 3. When and by how much did forecasts
overestimate or underestimate generation? 4. How did forecast accuracy
vary across delivery periods?

Comparing actuals against the latest forecast would introduce look-ahead
bias. Forecast versions must be preserved.

## 3. Goals

-   Present forecast and actual wind generation clearly.
-   Allow inspection of forecast versions by publication and delivery
    time.
-   Quantify forecast error using consistent definitions.
-   Make historical evaluation reproducible and auditable.
-   Provide a dependable data pipeline and API.

## 4. Non-Goals

-   Automated electricity trading or bidding.
-   Price forecasting or price optimisation.
-   Building new wind forecast models.
-   Other generation fuel types.
-   Real-time dispatch.
-   Microservices architecture.

## 5. Data Requirements

### 5.1 WINDFOR forecasts

Required fields: - `publishTime`: forecast publication timestamp. -
`startTime`: delivery timestamp. - `generation`: forecast wind
generation.

Preserve multiple versions for the same delivery time.

### 5.2 FUELHH actuals

Filter to `fuelType == WIND`.

Required fields: - `startTime`: half-hourly delivery timestamp. -
`generation`: actual wind generation. - `publishTime`: source
publication timestamp, where supplied.

Forecasts are hourly; actuals are half-hourly. For hourly comparison,
aggregate the two corresponding half-hourly actual MW observations using
their arithmetic mean. Do not sum MW values.

### 5.3 Time and data handling

-   Store timezone-aware timestamps in UTC.
-   Use `Europe/London` for UK market time, display, and decision rules.
-   Keep publication and delivery timestamps distinct.
-   Do not replace missing values with zero.
-   Exclude incomplete pairs from accuracy calculations and report
    sample counts.

### 5.4 Dataset period

The analysis scope is January 2026. The implementation must explicitly
document whether the period is defined by delivery date or decision date
and handle boundary observations consistently.

## 6. Decision Cutoff and Look-Ahead Control

A provisional operational cutoff of **15:00 UK time on D-1** has been
discussed, but it must not be represented as a verified market
gate-closure rule without supporting evidence and client confirmation.

The system must: - Record the cutoff rule and timezone. - Select only
forecast versions published no later than the applicable cutoff. -
Define treatment of forecasts published exactly at the cutoff. - Make
the selected publication timestamp inspectable.

The final cutoff is a product/data decision that must be confirmed
before interpreting results as decision-time performance.

## 7. Core User Workflows

### Overview

See data coverage and high-level forecast/actual and accuracy summaries.

### Forecast Explorer

Select a delivery period and inspect forecast generation, publication
timestamp, available versions, and the version selected for the decision
cutoff.

### Forecast Accuracy

Review error over time, error distribution, largest
overestimates/underestimates, sample counts, and data coverage.

## 8. Functional Requirements

-   **FR-1 Data status:** expose data coverage and ingestion status.
-   **FR-2 Version preservation:** retain distinct forecast versions and
    publication timestamps.
-   **FR-3 Decision-time selection:** select eligible versions using the
    documented cutoff.
-   **FR-4 Alignment:** align hourly forecasts with hourly actuals
    derived from half-hourly observations.
-   **FR-5 Metrics:** calculate Error, MAE, RMSE, and Bias/MBE.
-   **FR-6 Transparency:** show valid matched sample counts and
    missing-data exclusions.
-   **FR-7 Health:** expose `GET /api/v1/health`.

Metric definitions: - Error = `Forecast - Actual` (MW). - MAE = mean
absolute error (MW). - RMSE = root mean squared error (MW). - Bias / MBE
= mean error (MW). - Positive error means overforecasting; negative
error means underforecasting.

## 9. Proposed API Surface

These are planned endpoints, not a claim that they are already
implemented.

  -------------------------------------------------------------------------------
  Method                  Endpoint                        Purpose
  ----------------------- ------------------------------- -----------------------
  GET                     `/api/v1/health`                Backend health

  GET                     `/api/v1/data/status`           Data coverage and
                                                          ingestion status

  GET                     `/api/v1/overview`              Summary metrics

  GET                     `/api/v1/forecasts`             Forecast observations

  GET                     `/api/v1/forecasts/history`     Forecast history by
                                                          delivery time

  GET                     `/api/v1/forecasts/versions`    Available forecast
                                                          versions

  GET                     `/api/v1/accuracy`              Aggregate accuracy
                                                          metrics

  GET                     `/api/v1/accuracy/timeseries`   Accuracy over time

  GET                     `/api/v1/accuracy/errors`       Error observations

  GET                     `/api/v1/accuracy/top-errors`   Largest forecast errors
  -------------------------------------------------------------------------------

## 10. Non-Functional Requirements

-   Correctness: no look-ahead bias.
-   Traceability: retain publication and delivery timestamps.
-   Reliability: idempotent ingestion and validation before insertion.
-   Maintainability: modular monolith with separated API, data access,
    and domain logic.
-   Security: secrets stay out of source control.
-   Reproducibility: document period, cutoff, aggregation, and metrics.
-   Performance: support interactive exploration of January 2026 data.
-   Testing: cover cutoff selection, aggregation, missing data, and
    metrics.

## 11. Current Implementation Baseline

Infrastructure already established: - React + TypeScript + Vite frontend
scaffold. - FastAPI backend scaffold and health endpoint. - PostgreSQL
database. - SQLAlchemy models for `wind_forecasts` and
`actual_generation`. - Alembic migrations. - Docker Compose local
environment. - GitHub Actions checks for backend tests, frontend build,
and Docker image builds. - Vercel frontend and Render backend
deployments configured.

Forecast ingestion, analytics endpoints, metric calculations, and full
dashboard workflows remain application-development work.

## 12. Acceptance Criteria

1.  January 2026 source data is ingested and validated.
2.  Forecast versions are preserved.
3.  Half-hourly actuals are correctly aggregated to hourly values.
4.  The documented cutoff is applied without look-ahead.
5.  Error, MAE, RMSE, and bias are tested and reproducible.
6.  Missing data is not silently converted to zero.
7.  Users can inspect selected publication times and matched sample
    counts.
8.  Overview, Forecast Explorer, and Forecast Accuracy workflows are
    usable.
9.  Documentation describes setup, assumptions, and deployment.

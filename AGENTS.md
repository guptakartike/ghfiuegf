Wind Analytics — Agent Instructions

1. Project Overview

Wind Analytics is a UK electricity market analytics platform focused on national wind generation forecasting.

The application helps energy procurement teams:

* Understand available wind generation forecasts.
* Compare forecasts against actual generation.
* Quantify forecast errors.
* Make better day-ahead electricity purchasing decisions.

The project scope is restricted to national-level wind generation data from Elexon.

Data Sources

* WINDFOR: Wind generation forecasts.
* FUELHH: Actual generation, filtered to fuelType=WIND.

Analysis Period

* Decision dates: January 1–31, 2026.
* Delivery dates: January 2–February 1, 2026.

⸻

2. Technology Stack

Frontend

* React
* TypeScript
* Vite
* Tailwind CSS
* Recharts
* Lucide React

Backend

* Python
* FastAPI
* SQLAlchemy
* Pydantic
* Pandas
* NumPy
* HTTPX

Database

* PostgreSQL
* Alembic migrations

Infrastructure

* Docker
* Docker Compose
* GitHub Actions
* Vercel
* Render
* Neon PostgreSQL

Use the existing stack. Do not introduce additional technologies without a clear technical reason.

⸻

3. Architecture Principles

1. Use a modular monolith architecture.
2. Do not introduce microservices.
3. Maintain clear separation of concerns.
4. Keep business logic separate from API routes.
5. Keep database operations separate from business logic.
6. Use dependency injection where appropriate.
7. Avoid global mutable state.
8. Prefer simple, maintainable implementations over unnecessary abstractions.
9. Preserve existing infrastructure and project conventions.
10. Avoid premature optimization.

⸻

4. Repository Rules

Before modifying code:

1. Inspect the relevant files.
2. Understand existing implementations.
3. Check related models, schemas, services and tests.
4. Identify dependencies and potential side effects.

While modifying code:

* Make minimal, focused changes.
* Do not rewrite working modules unnecessarily.
* Do not duplicate existing functionality.
* Do not modify unrelated files.
* Do not introduce unnecessary dependencies.
* Maintain consistent naming conventions.
* Follow existing directory structure.

Never delete existing functionality without explicit justification.

⸻

5. Data Engineering Rules

These rules are critical.

Elexon Data

* Use only national-level Elexon data.
* Forecast source: WINDFOR.
* Actual source: FUELHH.
* Filter actual generation strictly to WIND.
* Preserve all forecast publication versions.
* Never overwrite historical forecast versions.

Date Handling

* Decision dates: January 1–31, 2026.
* Delivery dates: January 2–February 1, 2026.
* Do not confuse publication dates, decision dates and delivery dates.
* Respect documented Elexon API query limitations.
* Split large date ranges into valid API requests.

Timestamp Handling

* Store timestamps in timezone-aware UTC.
* Use Europe/London for UK market date/time interpretation.
* Never assume UTC and UK local time are always interchangeable.
* Handle daylight saving time correctly.

Data Quality

* Never silently replace missing values with zero.
* Never silently discard invalid records.
* Report rejected records and reasons.
* Detect missing settlement intervals.
* Validate duplicate records.
* Validate generation values and timestamp consistency.

Forecast Accuracy

* Error definition: Forecast - Actual.
* Positive error means overforecasting.
* Negative error means underforecasting.
* Aggregate two half-hourly actual observations into hourly average MW when comparing against hourly forecasts.
* Never sum MW observations when calculating hourly average generation.
* Prevent look-ahead bias.
* Only use forecast versions available before the documented decision cutoff.

⸻

6. Backend Development Rules

* Use FastAPI conventions.
* Use Pydantic for request and response validation.
* Use SQLAlchemy for database operations.
* Use Alembic for schema migrations.
* Use HTTPX for external API requests.
* Use bounded retries for transient failures.
* Do not retry permanent client errors.
* Implement database operations efficiently.
* Use PostgreSQL-native conflict handling for idempotent ingestion.
* Avoid opening a separate database session for every individual record.
* Handle exceptions explicitly.
* Never expose secrets or database credentials in logs.

⸻

7. Frontend Development Rules

* Use functional React components.
* Use TypeScript strictly.
* Avoid unnecessary any types.
* Keep components small and reusable.
* Separate API communication from UI components.
* Use consistent loading, error and empty states.
* Use responsive layouts.
* Keep visualizations understandable and accurate.
* Do not fabricate analytics or display placeholder metrics as real results.
* Ensure displayed values come from actual backend responses.

⸻

8. Testing Requirements

Every meaningful feature must have appropriate tests.

Backend

* Unit tests for business logic.
* API integration tests.
* Database persistence tests.
* Data validation tests.
* Error-handling tests.
* Boundary-condition tests.

Frontend

* Component tests where appropriate.
* API integration validation.
* Production build verification.

General

* Never claim tests passed without executing them.
* Do not weaken or delete tests to achieve a passing result.
* Do not rely exclusively on mocked tests for critical data pipelines.
* Test duplicate ingestion and repeated execution.
* Test invalid and missing data.
* Run targeted tests during development.
* Run the complete test suite before completing a phase.

⸻

9. Git Workflow

* Work on feature-specific branches.
* Never commit directly to main.
* Never merge branches automatically.
* Do not commit without explicit permission.
* Keep commits focused and descriptive.
* Do not include secrets, .env files, virtual environments or build artifacts.
* Preserve existing Git history.

Current feature branch for Phase 1:

feature/elexon-data-ingestion

⸻

10. Development Workflow

For every task:

1. Understand the requested task.
2. Inspect only relevant files.
3. Identify the implementation approach.
4. Implement the requested changes.
5. Run relevant tests.
6. Review the final diff.
7. Report results.

Do not move to another phase without explicit instruction.

Completion Report

After every task, provide:

* Summary of changes.
* Files created.
* Files modified.
* Tests executed.
* Actual test results.
* Known limitations.
* Recommended next step.

Clearly distinguish completed work from pending work.

⸻

11. Token Efficiency

Minimize unnecessary context consumption.

* Do not repeatedly read the entire repository.
* Do not reread unchanged files.
* Do not print entire files unless necessary.
* Prefer targeted file searches.
* Use concise terminal output.
* Avoid unnecessary explanations.
* Avoid unrelated research.
* Do not repeat completed audits.
* Reuse existing implementation decisions.
* Inspect only relevant dependencies.
* Do not run the full test suite after every minor edit.
* Run targeted tests first and the full suite at phase completion.

Do not sacrifice correctness or testing to save tokens.

⸻

12. Critical Restrictions

NEVER:

1. Invent data or analytics results.
2. Fabricate API responses.
3. Ignore API limitations.
4. Silently discard invalid records.
5. Introduce look-ahead bias.
6. Overwrite historical forecasts.
7. Modify production data during testing.
8. Rewrite working infrastructure unnecessarily.
9. Claim unexecuted tests passed.
10. Commit or merge without permission.
11. Start a future phase without approval.

When requirements are ambiguous, inspect project documentation and existing decisions before making assumptions.

⸻

13. Current Project Status

Foundation infrastructure is complete.

Phase 1: Elexon Data Ingestion & Validation.

Current focus:

* Correct async ingestion execution.
* Correct Elexon response parsing.
* Implement API date-range chunking.
* Fix retry behavior.
* Implement efficient idempotent persistence.
* Normalize timestamps.
* Improve ingestion reporting.
* Add genuine end-to-end ingestion tests.

Do not start forecast selection, actual aggregation, accuracy analytics or dashboard implementation until Phase 1 is verified and approved.
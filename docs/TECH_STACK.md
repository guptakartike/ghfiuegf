# Technology Stack

## UK Wind Generation Forecast Analytics

## 1. Stack Summary

  -----------------------------------------------------------------------
  Layer                   Technology              Responsibility
  ----------------------- ----------------------- -----------------------
  Frontend                React                   User interface

  Language                TypeScript              Typed frontend
                                                  development

  Build tool              Vite                    Development and
                                                  production builds

  Styling                 Tailwind CSS            UI styling

  Charts                  Recharts                Analytical
                                                  visualisations

  Icons                   Lucide React            Interface icons

  Backend                 FastAPI                 REST API

  Backend language        Python 3.12             API and data-processing
                                                  logic

  Validation/config       Pydantic,               Validation and
                          pydantic-settings       environment
                                                  configuration

  Database                PostgreSQL              Persistent storage

  ORM                     SQLAlchemy              Database access and
                                                  models

  Migrations              Alembic                 Version-controlled
                                                  schema changes

  Data processing         Pandas, NumPy           Alignment and metric
                                                  calculations

  Testing                 Pytest, HTTPX           Automated tests and API
                                                  tests

  Package manager         pnpm                    Frontend dependencies

  Containers              Docker                  Reproducible images

  Orchestration           Docker Compose          Local multi-container
                                                  environment

  CI                      GitHub Actions          Backend, frontend, and
                                                  Docker validation

  Frontend hosting        Vercel                  Frontend deployment

  Backend hosting         Render                  API deployment

  Database hosting        Neon PostgreSQL         Hosted PostgreSQL
  -----------------------------------------------------------------------

## 2. Architecture

Use a **modular monolith**. The React frontend communicates with a
single FastAPI backend over HTTP/REST. The backend separates API,
configuration, database, model, and domain/service responsibilities.
PostgreSQL is the persistent data store.

Microservices are not required for this project; a modular monolith
reduces operational complexity.

## 3. Frontend

-   **React + TypeScript + Vite:** component-based UI, static typing,
    fast development, and production builds.
-   **Tailwind CSS:** utility-first styling and responsive layouts.
-   **Recharts:** forecast/actual time series and forecast-error charts.
-   **Lucide React:** consistent interface icons.

## 4. Backend

-   **FastAPI:** REST endpoints, request handling, dependency injection,
    and OpenAPI documentation.
-   **Python 3.12:** CI and container runtime for consistent
    environments.
-   **Pydantic / pydantic-settings:** schema validation and environment
    configuration.
-   **Pandas / NumPy:** timestamp alignment, aggregation, missing-data
    handling, and metric calculations.

## 5. Database

-   **PostgreSQL:** stores forecast versions and actual generation.
-   **SQLAlchemy:** ORM and database sessions.
-   **Alembic:** version-controlled schema migrations.

Current tables: - `wind_forecasts` - `actual_generation`

Constraints: - Unique `(publish_time, start_time)` for forecast
versions. - Unique `start_time` for actual generation. - Index on
forecast `start_time`.

## 6. Data and Time Conventions

-   Sources: Elexon WINDFOR and FUELHH.
-   Actuals: filter `fuelType == WIND`.
-   Forecasts: hourly; actuals: half-hourly.
-   Hourly actual comparison value: arithmetic mean of the two
    half-hourly MW observations.
-   Error convention: `Forecast - Actual`.
-   Store timestamps in UTC using timezone-aware columns.
-   Use `Europe/London` for UK market decision rules and display.
-   Preserve forecast versions; do not overwrite with the latest
    version.
-   Do not fill missing generation values with zero.

## 7. Infrastructure and Deployment

-   **Docker:** separate frontend and backend images; PostgreSQL uses
    the official image.
-   **Docker Compose:** local frontend `localhost:3000`, backend
    `localhost:8000`, PostgreSQL `localhost:5432`.
-   **GitHub Actions:** backend tests, frontend build, and Docker
    Compose image build.
-   **Hosting:** Vercel frontend, Render backend, Neon PostgreSQL.

## 8. Environment Configuration

Backend:

``` env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
```

Frontend:

``` env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Production values are configured in hosting platforms. Never commit
`.env` files, credentials, or tokens. In Docker Compose, the backend
connects to the database using service hostname `db`, not `localhost`.

## 9. Engineering Conventions

-   Keep API routes thin; place domain logic in service modules.
-   Keep database access behind SQLAlchemy models and session
    dependencies.
-   Use Alembic for schema changes.
-   Use typed request and response schemas.
-   Validate external data before persistence.
-   Make ingestion idempotent.
-   Make units and timezone semantics explicit.
-   Test decision-time selection and metric calculations independently.
-   Keep secrets out of Git and Docker build contexts.

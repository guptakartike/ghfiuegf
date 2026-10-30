# Repository Structure

## UK Wind Generation Forecast Analytics

The tree below documents the established scaffold based on the current
project setup. Verify exact filenames against the repository before
treating it as a generated directory listing.

``` text
wind-analytics/
├── .github/
│   └── workflows/
│       └── ci.yml
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── actual.py
│   │   │   └── forecast.py
│   │   ├── main.py
│   │   ├── database.py
│   │   └── db_connection_check.py
│   ├── migrations/
│   │   ├── versions/
│   │   │   ├── ec2937e248d9_initial_database_setup.py
│   │   │   └── 00147372cffd_create_wind_data_tables.py
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── tests/
│   │   └── test_health.py
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── types.ts
│   │   ├── App.tsx
│   │   ├── index.css
│   │   └── main.tsx
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── vite.config.ts
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Top-Level Directories

### `.github/workflows/`

GitHub Actions CI configuration. - `ci.yml`: backend tests, frontend
build, and Docker image build.

### `backend/`

Python API and data layer. - `app/main.py`: FastAPI application and
middleware. - `app/core/config.py`: environment-based application
settings. - `app/database.py`: SQLAlchemy engine, session factory, and
declarative base. - `app/models/`: SQLAlchemy database models. -
`app/db_connection_check.py`: manual database connectivity diagnostic. -
`migrations/`: Alembic configuration and schema history. - `tests/`:
automated backend tests. - `Dockerfile`: backend image definition. -
`requirements.txt`: Python dependencies.

### `frontend/`

React and TypeScript application. - `src/lib/api.ts`: API client. -
`src/lib/types.ts`: frontend API types. - `src/App.tsx`: root
application component. - `src/main.tsx`: frontend entry point. -
`src/index.css`: global styles and Tailwind import. - `public/`: static
assets. - `Dockerfile`: multi-stage frontend build and Nginx runtime. -
`package.json`: scripts and dependencies. - `pnpm-lock.yaml`: locked
dependency versions.

### Root files

-   `docker-compose.yml`: local frontend, backend, and PostgreSQL
    services.
-   `.gitignore`: excludes local dependencies, secrets, and generated
    files.
-   `README.md`: project overview and setup instructions.

## Planned Backend Expansion

The following is a proposed future layout, not a description of
implemented files:

``` text
backend/app/
├── api/
│   └── v1/
│       ├── routes/
│       │   ├── health.py
│       │   ├── forecasts.py
│       │   ├── accuracy.py
│       │   └── overview.py
│       └── router.py
├── core/
│   └── config.py
├── models/
│   ├── actual.py
│   └── forecast.py
├── schemas/
│   ├── forecast.py
│   └── accuracy.py
├── services/
│   ├── ingestion.py
│   ├── forecast_selection.py
│   ├── actuals.py
│   └── accuracy.py
├── repositories/
├── database.py
└── main.py
```

## Planned Frontend Expansion

The following is a proposed future layout. Add folders as features are
implemented rather than creating empty structure prematurely.

``` text
frontend/src/
├── components/
│   ├── layout/
│   ├── charts/
│   └── common/
├── pages/
│   ├── Overview/
│   ├── ForecastExplorer/
│   └── ForecastAccuracy/
├── lib/
│   ├── api.ts
│   └── types.ts
├── hooks/
├── types/
├── App.tsx
├── index.css
└── main.tsx
```

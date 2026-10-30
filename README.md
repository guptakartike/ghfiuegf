# UK Wind Generation Analytics

A full-stack analytics platform for exploring UK wind generation forecasts, actual generation, and forecast accuracy. The project uses Elexon data and is designed to support electricity purchasing decisions through reliable, time-aware forecast analysis.

## Project Status

**Infrastructure and development environment established.**

- React + TypeScript frontend
- FastAPI backend
- PostgreSQL database
- SQLAlchemy ORM and Alembic migrations
- Docker-based local development
- GitHub Actions CI pipeline
- Cloud deployment configured

Application analytics and data-processing features are under development.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Styling | Tailwind CSS |
| Charts | Recharts |
| Icons | Lucide React |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Data Processing | Pandas, NumPy |
| Testing | Pytest, HTTPX |
| Containerization | Docker, Docker Compose |
| Frontend Deployment | Vercel |
| Backend Deployment | Render |
| Database Hosting | Neon PostgreSQL |
| CI/CD | GitHub Actions |

## Architecture

The application follows a modular monolithic architecture.

```text
                 ┌──────────────────────┐
                 │      React UI        │
                 │   TypeScript + Vite  │
                 └──────────┬───────────┘
                            │ HTTP / REST
                            ▼
                 ┌──────────────────────┐
                 │     FastAPI API      │
                 │                      │
                 │  Routes / Services   │
                 │  Data Processing     │
                 │  Validation          │
                 └──────────┬───────────┘
                            │ SQLAlchemy
                            ▼
                 ┌──────────────────────┐
                 │     PostgreSQL       │
                 │                      │
                 │  wind_forecasts      │
                 │  actual_generation   │
                 └──────────────────────┘
```

Docker Compose orchestrates the frontend, backend, and PostgreSQL services during local development.

## Repository Structure

```text
wind-analytics/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── actual.py
│   │   │   └── forecast.py
│   │   ├── main.py
│   │   └── database.py
│   │
│   ├── migrations/
│   │   └── versions/
│   ├── tests/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── alembic.ini
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   ├── App.tsx
│   │   └── index.css
│   ├── public/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── package.json
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

Install the following:

- Git
- Python 3.12+
- Node.js 22+
- pnpm 10+
- Docker Desktop

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd wind-analytics
```

### 2. Run with Docker

Docker Compose is the recommended way to start the complete local environment.

Build the images:

```bash
docker compose build
```

Start the services:

```bash
docker compose up -d
```

Apply database migrations:

```bash
docker compose exec backend alembic upgrade head
```

Check container status:

```bash
docker compose ps
```

The services will be available at:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API Health | http://localhost:8000/api/v1/health |
| PostgreSQL | localhost:5432 |

Stop the services:

```bash
docker compose down
```

Stop services and remove the local database volume:

```bash
docker compose down -v
```

**Warning:** The second command permanently deletes the local PostgreSQL container data.

## Local Development Without Docker

### Backend

Navigate to the backend:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/wind_analytics
```

Make sure PostgreSQL is running and the database exists.

Apply migrations:

```bash
alembic upgrade head
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend: http://localhost:8000

### Frontend

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
pnpm install
```

Create `.env.development`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Start the development server:

```bash
pnpm dev
```

Frontend: http://localhost:5173

## Database

PostgreSQL is used for persistent storage.

### Current Tables

**wind_forecasts**

Stores forecast versions and their corresponding delivery timestamps.

| Column | Description |
|---|---|
| id | Primary key |
| publish_time | Forecast publication timestamp |
| start_time | Forecast delivery timestamp |
| generation | Forecast wind generation |
| created_at | Record creation timestamp |

A unique constraint exists on `(publish_time, start_time)`.

**actual_generation**

Stores actual wind generation observations.

| Column | Description |
|---|---|
| id | Primary key |
| start_time | Delivery timestamp |
| settlement_date | Settlement date |
| settlement_period | Settlement period |
| generation | Actual wind generation |
| publish_time | Publication timestamp |
| created_at | Record creation timestamp |

A unique constraint exists on `start_time`.

### Database Migrations

Generate a migration:

```bash
alembic revision --autogenerate -m "migration description"
```

Apply migrations:

```bash
alembic upgrade head
```

Check the current migration:

```bash
alembic current
```

Revert one migration:

```bash
alembic downgrade -1
```

## API

API base path:

```text
/api/v1
```

### Current Endpoint

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Backend health check |

Interactive API documentation:

```text
http://localhost:8000/docs
```

Additional analytics endpoints will be introduced as application development progresses.

## Testing

Run backend tests:

```bash
cd backend
python -m pytest -v
```

Build the frontend:

```bash
cd frontend
pnpm build
```

## CI/CD

GitHub Actions automatically validates changes through three jobs:

1. **Backend Tests** — installs Python dependencies and runs pytest.
2. **Frontend Build** — installs pnpm dependencies and builds the React application.
3. **Docker Build** — validates Docker image builds using Docker Compose.

The workflow runs on pushes to `main` and feature branches, as well as pull requests targeting `main`.

### Development Workflow

```text
Create Feature Branch
        ↓
Implement Changes
        ↓
Commit and Push
        ↓
Open Pull Request
        ↓
GitHub Actions CI
        ↓
Review and Merge
        ↓
Deployment
```

## Deployment

| Component | Platform | URL |
|---|---|---|
| Frontend | Vercel | https://wind-analytics-bay.vercel.app/ |
| Backend | Render | https://wind-analytics-api-d6st.onrender.com/ |
| Database | Neon | PostgreSQL |

Production environment variables are configured through the respective hosting platforms.

Do not commit database credentials, API keys, or `.env` files.

## Data Source

The project uses the UK electricity market data provided by Elexon:

- **FUELHH:** Actual half-hourly generation data.
- **WINDFOR:** Wind generation forecast data, including publication timestamps and delivery timestamps.

The intended analysis focuses on January 2026 and evaluates forecast information available at the relevant purchasing decision time.

## AI Assistance Disclosure

AI tools were used during development for technical guidance, debugging, documentation assistance, and implementation support. Architecture decisions, code integration, testing, and project validation are part of the development workflow.

## License

This project is developed as part of a software engineering internship assignment.
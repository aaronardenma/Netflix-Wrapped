# Netflix Wrapped

Netflix Wrapped turns a Netflix viewing history export into a personal recap. It parses viewing activity by profile and year, generates watch-time insights, visualizations, title-level stats, Wrapped-style highlight cards, and personalized recommendations.

Netflix data can be requested from <https://www.netflix.com/account/getmyinfo>. Netflix's export help page is available at <https://help.netflix.com/en/node/100624>.

## Features

- Profile and year recaps from Netflix `ViewingActivity.csv` exports
- Anonymous one-session recaps and saved recaps for logged-in users
- Fast first-year processing with Redis/RQ backfill for heavier sections
- Overview stats, title insights, genre/content insights, profile comparisons, and visualizations
- Wrapped-style highlight cards
- Personalized recommendations for logged-in users
- TMDB/OMDB-ready metadata enrichment and cached title metadata
- Account registration, login, password change, account data wipe, and account deletion
- Health checks and request logging for local debugging and deployment

## Tech Stack

- Frontend: React 18, Vite, Tailwind CSS, Axios, Plotly
- Backend: Django 5, Django REST Framework, PostgreSQL
- Jobs/cache: Redis, Django RQ
- Data/recommendations: pandas, NumPy, scikit-learn
- Local tooling: Makefile, Docker Compose

## Project Layout

```text
backend/                 Django API, data processing, jobs, notebooks
frontend/                React/Vite app
backend/notebooks/       Recommender workflow and evaluation notebooks
backend/REDIS_WORKFLOW.md
backend/RECOMMENDER_WORKFLOW.md
compose.yaml             Lightweight Docker frontend/backend startup
Makefile                 Local development commands
```

## Quick Start

The smoothest local workflow is the Makefile-based setup. It starts Redis, the Django server, the RQ worker, and Vite from your local environment.

### Prerequisites

- Python virtual environment at `backend/.venv`
- Node.js and npm
- PostgreSQL
- Redis, usually installed with `brew install redis` on macOS

### Environment Files

Create local env files from the examples:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Update `backend/.env` with your PostgreSQL credentials. `TMDB_API_KEY` and `OMDB_API_KEY` are optional, but metadata enrichment and recommendation quality improve when TMDB is configured.

### Install And Start

```bash
make setup-dev
make migrate
make dev
```

Open the Vite app at:

```text
http://localhost:5173
```

The Django API runs at:

```text
http://localhost:8000
```

## Common Commands

```bash
make help          # Show available commands
make setup         # Install backend runtime dependencies
make setup-dev     # Install runtime + notebook/dev dependencies
make migrate       # Apply Django migrations
make backend       # Start Redis, RQ worker, and Django
make frontend      # Start Vite
make dev           # Start Redis, RQ worker, Django, and Vite
make health        # Check backend database/cache/RQ health
make check         # Run Django system checks
make test          # Run backend tests
make deploy-check  # Run backend checks/tests and frontend build
make eval-recs     # Execute the recommender benchmark notebook
```

Use JSON backend logs when you want structured request output:

```bash
make dev-json
```

## Processing Workflow

Uploads are optimized for a quick first result:

1. Django validates the viewing history and extracts profiles/years.
2. The backend generates a lightweight recap for the default profile's most recent year.
3. The frontend redirects to the recap page with the returned profile, year, and job ID.
4. The Redis/RQ worker fills heavier sections in the background, including content insights, profile comparisons, visualizations, and remaining years.
5. Logged-in users get persisted viewing history, saved recaps, and warmed recommendations.

See [backend/REDIS_WORKFLOW.md](backend/REDIS_WORKFLOW.md) for the detailed backend flow.

## Recommendations

Logged-in users can generate a personalized "what to watch next" playlist. The recommender uses saved viewing history, enriched title metadata, cached external catalog titles, and optional TMDB candidate discovery.

The current recommender:

- weights recent viewing more heavily than older history
- generates profile-specific scoring hyperparameters
- scores unseen candidates using content similarity and structured affinity signals
- diversifies results by genre, language, origin country, media type, and release era
- stores user feedback to filter or boost future picks
- caches generated playlists for reuse and refresh

Recommendations may include titles that are not currently available on Netflix in your region.

See [backend/RECOMMENDER_WORKFLOW.md](backend/RECOMMENDER_WORKFLOW.md) for the recommendation generation flow, current capabilities, and roadmap.

## Recommender Evaluation

Run the benchmark notebook from the repo root:

```bash
make eval-recs
```

The executed notebook and result exports are ignored by git:

```text
backend/notebooks/recommender_evaluation_workflow.executed.ipynb
backend/notebooks/results/
```

The notebook exports raw metrics, profile diagnostics, inspection rows, and compact best-model summaries:

- best by recall
- best by metadata fit
- diagnostics for profiles with weak candidate coverage or missing metadata

## Docker

Docker Compose is available for a lightweight frontend/backend startup:

```bash
docker compose up --build
```

It starts:

- Django at `http://localhost:8000`
- nginx-served frontend at `http://localhost:3000`

Current Docker limitations:

- PostgreSQL is expected to run on your host machine.
- The backend container connects to host PostgreSQL through `host.docker.internal`.
- The compose file does not start Redis or an RQ worker.

For the full background processing workflow, prefer `make dev` locally or add Redis and worker services to compose before relying on Docker for complete recap processing.

Stop the Docker stack with:

```bash
docker compose down
```

## Deployment

Use Vercel for the React frontend. Deploy Django separately on a host that supports a persistent web process, PostgreSQL, Redis, and an RQ worker, such as Render, Railway, Fly.io, a Heroku-style platform, or a VPS. Vercel serverless functions are not a good fit for the current Django/RQ worker setup.

### Backend

Provision:

- PostgreSQL
- Redis
- one Django web process
- one RQ worker process running `python manage.py rqworker recaps`

Set production backend environment variables:

```env
SECRET_KEY=replace-with-production-secret
DEBUG=False
ALLOWED_HOSTS=your-backend-domain.example.com
POSTGRESQL_DB=...
POSTGRESQL_USER=...
POSTGRESQL_PASSWORD=...
POSTGRESQL_HOST=...
POSTGRESQL_PORT=5432
REDIS_URL=redis://...
FRONTEND_URL=https://your-vercel-app.vercel.app
FRONTEND_ORIGINS=https://your-vercel-app.vercel.app
TMDB_API_KEY=optional-tmdb-api-key
LOG_LEVEL=INFO
LOG_FORMAT=json
```

After deploying backend code:

```bash
python manage.py migrate
python manage.py check
```

Confirm the backend is reachable:

```text
https://your-backend-domain.example.com/api/observability/health/
```

### Vercel Frontend

In Vercel:

- Import the GitHub repository.
- Set the project root directory to `frontend`.
- Use the Vite framework preset.
- Use install command `npm install`.
- Use build command `npm run build`.
- Use output directory `dist`.

Set the frontend environment variable:

```env
VITE_API_BASE_URL=https://your-backend-domain.example.com
```

`frontend/vercel.json` rewrites frontend routes to `index.html`, so direct visits to React Router routes such as `/recap`, `/create`, and `/auth/login` work correctly.

After Vercel assigns the final frontend domain, update the backend:

```env
FRONTEND_URL=https://your-production-frontend-domain
FRONTEND_ORIGINS=https://your-production-frontend-domain
```

If you use both a Vercel preview URL and a custom domain, use a comma-separated list:

```env
FRONTEND_ORIGINS=https://your-app.vercel.app,https://www.your-custom-domain.com
```

Restart the backend after changing frontend origins. CORS, CSRF, and secure cookie-based auth depend on those values.

## Observability

The backend emits request logs with:

- request ID
- path
- method
- status code
- latency

Set `LOG_FORMAT=json` for structured logs. Every response includes an `X-Request-ID` header.

Health and runtime checks are available at:

```text
http://localhost:8000/api/observability/health/
```

The health response includes database, cache, RQ queue, and recent recap job state. A degraded response usually means Redis, PostgreSQL, or the RQ worker is not available.

## Troubleshooting

If recap generation starts but heavier sections do not fill in, check that Redis is running and the RQ worker is active:

```bash
make redis-status
make backend
```

If tests cannot connect to PostgreSQL, confirm the local database is running and that `backend/.env` has valid `POSTGRESQL_*` values.

If frontend requests fail in local dev, confirm `frontend/.env` points at the Django API:

```env
VITE_API_BASE_URL=http://localhost:8000
```

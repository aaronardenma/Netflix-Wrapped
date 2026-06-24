# Netflix Wrapped

Netflix Wrapped is a web app for turning your Netflix viewing history export into a personal recap. Upload the `ViewingActivity.csv` file from Netflix, choose a profile and year, and the app generates watch-time stats, charts, profile comparisons, genre insights, title-level insights, and shareable Wrapped-style cards.

Netflix data can be requested from Netflix at <https://www.netflix.com/account/getmyinfo>. Netflix also documents the export process on its help page: <https://help.netflix.com/en/node/100624>.

## What The App Does

- Accepts Netflix viewing activity CSV uploads.
- Extracts profiles, viewing events, titles, dates, durations, and yearly recap data.
- Stores authenticated user uploads and generated viewing data in PostgreSQL.
- Supports anonymous one-session CSV analysis for quick recaps.
- Uses Redis and RQ to return a fast first recap, then backfill heavier insights in the background.
- Generates interactive frontend views for overall stats, profile/year selection, profile comparisons, genre/content insights, title-level analysis, visualizations, and recommendations.
- Provides account features including registration, login, password changes, account data wipe, and account deletion.

## Tech Stack

- React 18 and Vite frontend
- Tailwind CSS UI styling
- Axios API client
- Django 5 backend
- Django REST Framework
- PostgreSQL
- Redis and Django RQ for background recap work
- pandas, NumPy, and scikit-learn for backend data processing and recommendations
- Plotly for frontend visualizations
- Docker Compose for local app startup

## Processing Workflow

Uploads are optimized for a fast first result:

1. Django validates the viewing history and extracts available profiles/years.
2. The backend generates a lightweight recap for the default profile's most recent year.
3. The frontend redirects to `/recap` using the returned profile, year, and job ID.
4. A Redis/RQ worker fills in heavier sections such as profile comparisons, content insights, visualizations, and remaining years.
5. For logged-in users, the worker also persists viewing history to PostgreSQL and warms personalized recommendations.

See [backend/REDIS_WORKFLOW.md](backend/REDIS_WORKFLOW.md) for the detailed backend flow.

## Recommendations

Logged-in users can generate a personalized "what to watch next" playlist. The recommender uses saved viewing history, enriched title metadata, cached external catalog titles, and optional TMDB candidate discovery.

The current recommender:

- weights recent viewing more heavily than older history
- generates profile-specific scoring hyperparameters
- scores unseen candidates using content similarity plus structured affinity signals
- diversifies results by genre, language, origin country, media type, and release era
- uses recommendation feedback to filter or boost future picks
- stores generated playlists so they can be reused and refreshed

Recommendations may include titles that are not currently available on Netflix in your region.

See [backend/RECOMMENDER_WORKFLOW.md](backend/RECOMMENDER_WORKFLOW.md) for the detailed recommendation generation flow, current capabilities, and future roadmap.

## Launch With Docker

### Prerequisites

- Docker Desktop or Docker Engine with Docker Compose
- A local PostgreSQL database running on your machine
- A backend environment file at `backend/.env`

The Docker Compose setup runs the backend and frontend containers, but it does not create a PostgreSQL container. The backend container connects to PostgreSQL on your host machine through `host.docker.internal`.

### 1. Create The Database

Create a local PostgreSQL database for the app. The default database name used by Django is:

```bash
netflixwrapped
```

You can use another database name as long as it matches `POSTGRESQL_DB` in `backend/.env`.

### 2. Configure Backend Environment Variables

Create or update `backend/.env` with your local settings:

```env
SECRET_KEY=replace-with-a-local-development-secret
DEBUG=True
POSTGRESQL_DB=netflixwrapped
POSTGRESQL_USER=your-postgres-user
POSTGRESQL_PASSWORD=your-postgres-password
POSTGRESQL_HOST=localhost
POSTGRESQL_PORT=5432
FRONTEND_URL=http://localhost:3000
REDIS_URL=redis://127.0.0.1:6379/0
TMDB_API_KEY=optional-tmdb-api-key
LOG_LEVEL=INFO
LOG_FORMAT=text
```

The compose file overrides `POSTGRESQL_HOST` to `host.docker.internal` inside the backend container, so keep your normal local host value in `.env`.

### 3. Build And Start The App

From the repository root, run:

```bash
docker compose up --build
```

Docker Compose will:

- build the Django backend image from `backend/Dockerfile`
- install Python dependencies from `backend/requirements.txt`
- run Django migrations
- start the backend at `http://localhost:8000`
- build the React frontend from `frontend/Dockerfile`
- serve the frontend through nginx at `http://localhost:3000`

### 4. Open The App

Visit:

```text
http://localhost:3000
```

The frontend sends API requests to:

```text
http://localhost:8000
```

### 5. Stop The App

Press `Ctrl+C` in the Docker Compose terminal, then run:

```bash
docker compose down
```

## Local Development Without Docker

Backend:

```bash
make setup
make migrate
make backend
```

Notebook and evaluation tools:

```bash
make setup-dev
```

Frontend:

```bash
make frontend
```

Or run Redis, the RQ worker, Django, and Vite together:

```bash
make dev
```

The Vite dev server usually runs at `http://localhost:5173`. The production Docker frontend runs at `http://localhost:3000`.

## Deploy With Vercel

Use Vercel for the React frontend. The Django backend should run on a host that
supports a persistent web process, PostgreSQL, Redis, and an RQ worker, such as
Render, Railway, Fly.io, Heroku-style platforms, or your own VPS. Vercel
serverless functions are not a good fit for the current Django/RQ worker setup.

### 1. Deploy The Backend First

Provision:

- PostgreSQL
- Redis
- one Django web process
- one RQ worker process running `python manage.py rqworker recaps`

Set backend environment variables:

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

After deploying backend code, run:

```bash
python manage.py migrate
python manage.py check
```

Confirm the backend is reachable:

```text
https://your-backend-domain.example.com/api/observability/health/
```

### 2. Create The Vercel Project

In Vercel:

- Import the GitHub repository.
- Set the project root directory to `frontend`.
- Use framework preset `Vite`.
- Use install command `npm install`.
- Use build command `npm run build`.
- Use output directory `dist`.

Set Vercel environment variables:

```env
VITE_API_BASE_URL=https://your-backend-domain.example.com
```

The file `frontend/vercel.json` rewrites all frontend routes to
`index.html`, which allows direct visits to React Router routes such as
`/recap`, `/create`, and `/auth/login`.

### 3. Update Backend Origins After Vercel Assigns A Domain

Once Vercel gives you the final production URL, update the backend:

```env
FRONTEND_URL=https://your-production-frontend-domain
FRONTEND_ORIGINS=https://your-production-frontend-domain
```

If you use both a Vercel preview URL and a custom domain, provide a comma-separated list:

```env
FRONTEND_ORIGINS=https://your-app.vercel.app,https://www.your-custom-domain.com
```

Restart the backend after changing those values. This is required for CORS,
CSRF, and secure cookie-based auth to work from the Vercel frontend.

## Observability

The backend emits request logs with an `X-Request-ID` response header, request path, status code, and latency. Set `LOG_FORMAT=json` for structured logs that are easier to ship into a log collector.

Health and runtime checks are available at:

```text
http://localhost:8000/api/observability/health/
```

The health response includes database, cache, RQ queue, and recent recap job state. A degraded response usually means Redis, PostgreSQL, or the RQ worker is not available.

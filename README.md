# Netflix Wrapped

Netflix Wrapped is a web app for turning your Netflix viewing history export into a personal recap. Upload the `ViewingActivity.csv` file from Netflix, choose a profile and year, and the app generates watch-time stats, charts, profile comparisons, genre insights, title-level insights, and shareable Wrapped-style cards.

Netflix data can be requested from Netflix at <https://www.netflix.com/account/getmyinfo>. Netflix also documents the export process on its help page: <https://help.netflix.com/en/node/100624>.

## What The App Does

- Accepts Netflix viewing activity CSV uploads.
- Extracts profiles, viewing events, titles, dates, durations, and yearly recap data.
- Stores authenticated user uploads and generated viewing data in PostgreSQL.
- Supports anonymous one-session CSV analysis for quick recaps.
- Generates interactive frontend views for overall stats, profile/year selection, profile comparisons, genre/content insights, and title-level analysis.
- Provides account features including registration, login, password reset, account data wipe, and account deletion.

## Tech Stack

- React 18 and Vite frontend
- Tailwind CSS UI styling
- Axios API client
- Django 5 backend
- Django REST Framework
- PostgreSQL
- pandas, NumPy, Plotly, D3, and Recharts for data processing and visualization
- Docker Compose for local app startup

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
```

For password reset emails, also add SMTP settings:

```env
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-smtp-user
EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=no-reply@example.com
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
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server usually runs at `http://localhost:5173`. The production Docker frontend runs at `http://localhost:3000`.

# Redis and RQ workflow

Anonymous recap processing uses Redis for shared cache state and RQ for queued
background work.

## Runtime flow

1. Django validates the uploaded viewing history.
2. Authenticated uploads are written directly to PostgreSQL and return
   immediately without a queued job.
3. Anonymous uploads are cached in Redis with a 24-hour expiry.
4. Django enqueues one `recaps` RQ job and returns the profile/year list.
5. The RQ worker processes profile/year combinations sequentially.
6. Progress and generated recap payloads are written to Redis.
7. The frontend polls Django, which reads the shared Redis state.

## Local processes

Start the complete backend stack from the repository root:

```bash
make backend
```

This starts Redis, the RQ worker, and Django. Stopping the command also stops
the worker process. Redis remains available as a Homebrew service.

To run each process separately:

```bash
make redis-start
make worker
make server
```

Run the frontend separately:

```bash
cd ../frontend
npm run dev
```

Check Redis:

```bash
make redis-status
```

The expected response is `PONG`.

## Configuration

The default Redis connection is:

```text
redis://127.0.0.1:6379/0
```

Override it with:

```bash
REDIS_URL=redis://host:6379/0
```

Tests use Django's local-memory cache and synchronous RQ execution, so they do
not require a running Redis server.

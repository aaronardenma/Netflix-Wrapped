# Redis, RQ, and recommendation workflow

Recap processing uses Redis for shared cache state and RQ for queued background
work. This applies to both anonymous and authenticated uploads.

## Upload-to-recap flow

1. Django validates the uploaded viewing history and extracts profile/year
   options.
2. The cleaned upload dataframe is cached in Redis under a job-specific owner
   key.
3. Django synchronously generates one small partial recap: the default profile's
   most recent year.
4. That first result is written to Redis with status `partial_ready`.
5. The upload response returns `job_id`, `profile_years`, and
   `ready_profile_years` so the frontend can redirect to `/recap` immediately.
6. Django enqueues one `recaps` RQ job for the remaining work.
7. The frontend polls `/api/processing-status/<job_id>/` and refetches the
   selected recap while the job is running.
8. The worker backfills the partial result with the complete recap payload and
   processes the remaining profile/year combinations.

The partial recap intentionally contains only the fast sections needed for the
initial landing page:

- core stats
- wrapped cards
- title-level insights
- basic title/type/month/rating summaries

The worker adds the heavier sections later:

- profile comparisons
- content insights
- visualizations

This keeps upload-to-first-recap latency low while still producing the full
recap in the background.

## Authenticated upload flow

Authenticated uploads also use the Redis/RQ path. The request does not block on
full PostgreSQL ingestion.

1. The request returns after the partial recap is cached.
2. The RQ worker persists viewing events to PostgreSQL with
   `ingest_viewing_dataframe`.
3. The worker generates full recap cache entries.
4. The worker warms recommendation sets for the uploaded profiles.

The frontend includes the returned `job_id` in the recap URL for logged-in
uploads too. This lets the stats page use the fast Redis result while the saved
database copy is still being written.

## Anonymous upload flow

Anonymous uploads use the same cache and worker path, but the cached upload and
generated recaps expire after 24 hours. No PostgreSQL viewing events are saved
for anonymous users.

## Processing states

The processing state lives in Redis and tracks every profile/year combination.

- `queued`: waiting for the worker.
- `processing`: currently being generated.
- `partial_ready`: enough data exists for the frontend to show the first recap.
- `ready`: full recap data is available.
- `error`: processing failed for that profile/year.

`ready_profile_years` treats both `partial_ready` and `ready` as visible years,
so users can open a recap as soon as the first lightweight payload exists.

## Recommendation warmup

After authenticated ingestion finishes, the worker calls
`generate_recommendations` for each uploaded profile. Recommendation generation:

- builds a profile from the recent 90 days plus a one-year baseline
- generates profile-specific scoring hyperparameters
- discovers candidates from cached catalog data and TMDB
- scores candidates with TF-IDF and structured affinity signals
- diversifies by genre, language, origin country, media type, and release era
- stores the result in `RecommendationSet`

If recommendation warmup fails for a profile, the recap job continues. The
recommendations tab can still generate or refresh picks later.

See `backend/RECOMMENDER_WORKFLOW.md` for the detailed scoring, candidate
discovery, hyperparameter, and diversification flow.

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
make frontend
```

Or run backend and frontend together:

```bash
make dev
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

## Useful debugging notes

- If upload redirects are slow for logged-in users, check that the RQ worker is
  running. Full database ingestion should happen in the worker, not in the
  request.
- If the recap page lands quickly but some tabs are empty, the selected recap is
  probably still `partial_ready`. Wait for polling to fetch the full result.
- If recommendations are missing after upload, open the recommendations tab or
  click refresh. Warmup is best-effort and does not block recap completion.

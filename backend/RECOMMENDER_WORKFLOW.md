# Recommendation workflow

The recommender builds a "what to watch next" playlist for saved profiles. It
uses the user's viewing history plus an external catalog cache. Recommendations
may not be available on Netflix in the user's region.

## When recommendations are generated

Recommendations can be generated in two ways:

- The authenticated upload worker warms recommendations after viewing history is
  persisted.
- The frontend recommendations tab requests or refreshes recommendations on
  demand.

Generated playlists are stored in `RecommendationSet` and reused when the
profile history period and algorithm version match the current data.

## Data window

The profile model uses:

- a primary 90-day recent window
- a one-year baseline window

Each watched title receives a weight based on duration, recency, and whether it
falls inside the primary window. Recent long watches carry the most influence,
while older baseline watches still provide context.

## Candidate discovery

Candidates are unseen titles from `ExternalCatalogTitle`. The recommender avoids
titles the profile has already watched by comparing TMDB IDs and normalized
title names.

Candidate sources:

- fresh cached TMDB catalog titles
- older cached catalog titles when the fresh pool is too small
- TMDB seed recommendations from high-weight watched titles
- TMDB seed recommendations from recently watched titles
- TMDB seed recommendations from comfort/repeat titles
- TMDB discover results by preferred media type
- TMDB discover results filtered by preferred genres
- TMDB trending results
- TMDB popular results

The candidate pool intentionally uses cached titles first to avoid unnecessary
TMDB calls. TMDB calls are capped per recommendation run.

## Generated hyperparameters

Each run generates profile-specific hyperparameters and stores them in
`RecommendationSet.profile_summary.hyperparameters`.

Current generated values include:

- `metadata_richness`: share of watched titles with useful metadata
- `seed_count`: number of watched titles used as TMDB recommendation seeds
- `recent_seed_count`: number of recent titles used as TMDB seeds
- `comfort_seed_count`: number of high-watch-time titles used as TMDB seeds
- `candidate_cache_limit`: maximum cached candidates loaded
- `minimum_candidate_pool`: fallback threshold for older cached titles
- `max_tmdb_calls`: per-run TMDB call cap
- `profile_mode`: standard, sparse, or cold-start scoring mode
- `score_weights`: score component weights
- `diversity_caps`: maximum repeated values by genre, language, country, media
  type, and release decade

The scoring weights shift based on profile sparsity and metadata richness. If a
profile has strong metadata coverage, content similarity gets more weight. If a
profile is sparse, structured affinity, quality, and source-strength signals
carry more weight.

## Scoring

Scoring combines text similarity and structured affinity:

- content similarity from TF-IDF over watched title metadata and candidate
  metadata
- genre affinity
- original language affinity
- origin country affinity
- media type affinity
- release decade affinity
- runtime bucket affinity
- rating/certification affinity
- quality confidence from vote average and vote count
- source strength from seed, discovery, trending, or popular sources
- feedback affinity from saved or positive user feedback

The final score and individual contributing signals are stored on each
`Recommendation`.

## Diversification

After scoring, the recommender applies diversity caps so a playlist does not
collapse into one narrow cluster. Caps are applied across:

- primary genre
- original language
- origin country
- media type
- release decade

If the capped pass returns fewer than the target playlist size, the recommender
fills the remaining slots by score. This preserves useful variety without
returning an undersized playlist.

## Explanations

Recommendation explanations are generated from the strongest available signal.
Examples:

- seed-related title relationship from recent, top, or comfort titles
- saved or positive-feedback similarity
- matching top genre
- matching language preference
- matching origin country preference
- matching release era
- matching media type

The frontend also shows top signal chips from `profile_summary`, such as genre,
language, format, and origin.

## Feedback loop

Logged-in users can now mark recommendations as:

- looks good
- save
- not interested
- already watched

Feedback is stored in `RecommendationFeedback` with one current action per
profile/title. Negative actions remove the title from future recommendation
sets. Positive actions add a scoring boost and can influence explanations.

The feedback endpoint is:

```text
POST /api/recommendations/feedback/
```

Required payload fields:

- `profile_name`
- `media_type`
- `tmdb_id`
- `action`

Supported actions are `looks_good`, `saved`, `not_interested`, and
`already_watched`.

## Refresh behavior

Recommendation sets are invalidated when title metadata enrichment changes
titles watched by a profile. This lets better metadata influence the next
generated playlist instead of reusing stale recommendation sets.

Saved recommendations can also be refreshed manually or on a schedule:

```bash
python manage.py refresh_recommendations
```

Options:

- `--days 30`: refresh sets older than this many days
- `--force`: refresh every profile with viewing history
- `--profile-id <uuid>`: refresh one profile

From the repository root, the equivalent Makefile command is:

```bash
make refresh-recs
```

## Failure behavior

Recommendation warmup is best-effort. If warmup fails during upload processing,
the recap job continues. Users can still open the recommendations tab later to
generate or refresh picks.

Common reasons recommendations are unavailable:

- the profile has no saved viewing history
- too few watched titles have usable metadata
- the external catalog cache is empty
- TMDB is disabled and cached catalog candidates are insufficient

## Tuning notes

Useful constants live in `backend/api/services/recommendations.py`:

- `PLAYLIST_SIZE`
- `PRIMARY_WINDOW_DAYS`
- `BASELINE_WINDOW_DAYS`
- `CATALOG_CACHE_DAYS`
- `MAX_TMDB_CALLS`
- `CACHED_CANDIDATE_LIMIT`
- `MIN_CANDIDATE_POOL`

When changing score semantics, bump `ALGORITHM_VERSION`. This prevents old
stored playlists from being reused with incompatible scoring behavior.

## What exists today

The recommender is currently a content-based system with a cached external
catalog. It can already:

- build profile preference summaries from saved viewing history
- weight viewing by recency, duration, and a recent 90-day window
- use enriched title metadata such as genre, media type, release year, rating,
  origin country, and original language
- discover unseen candidates from cached TMDB catalog rows
- optionally call TMDB recommendations and discover endpoints when a TMDB API
  key is configured
- cap TMDB calls per recommendation run
- exclude already watched titles by TMDB ID and normalized title name
- score candidates with TF-IDF content similarity plus structured affinity
  signals
- generate profile-specific hyperparameters based on history size and metadata
  richness
- adjust scoring mode for sparse and cold-start profiles
- diversify the final playlist across genre, language, country, media type, and
  release decade
- store recommendation feedback and use it to filter or boost future picks
- store recommendation sets and reuse them while the history snapshot and
  algorithm version still match
- warm recommendations after authenticated uploads without blocking recap
  generation
- refresh saved playlists through `refresh_recommendations`
- invalidate stale playlists after metadata enrichment
- expose recommendation reasons and contributing signals to the frontend
- run an offline evaluation workflow from
  `backend/notebooks/recommender_evaluation_workflow.ipynb`

The main current limitation is availability. TMDB can suggest relevant movies
and shows, but it does not confirm whether a title is on Netflix in a user's
region.

## Roadmap

These are the next practical steps for improving the recommendation pipeline.

### 1. Run offline evaluation

Use `backend/notebooks/recommender_evaluation_workflow.ipynb` to compare
algorithm versions against temporal holdout data. The notebook now benchmarks
the production recommender against simple baselines:

- popular cached titles
- random eligible titles
- genre-only matching
- language/country matching

It reports metrics at `k = 5, 10, 20`:

- `hit_rate@k`
- `recall@k`
- genre coverage
- language and origin-country overlap
- diversity
- novelty
- candidate count
- eligible candidate count
- candidate source breakdown

Exact title hits may stay low because Netflix exports, local title parsing, and
TMDB catalog IDs are imperfect. Metadata-fit metrics should carry real weight
when deciding whether a change is better.

The notebook also exports CSV and JSON benchmark artifacts under
`backend/notebooks/results/`, including summary, per-profile metrics,
diagnostics, and top recommendation inspection rows.

### 2. Continue improving candidate sourcing

Candidate discovery now includes top, recent, comfort, discover, trending, and
popular sources. Future improvements:

- test which source types produce the strongest holdout metrics
- add keyword/company/network discovery when metadata coverage is strong
- add country-specific popular or trending content when a reliable region signal
  exists
- tune source-strength weights by profile mode

The goal is to increase the useful candidate pool before tuning score weights
too aggressively.

### 3. Add availability awareness

TMDB is not a Netflix availability source. Future options:

- integrate an availability provider such as JustWatch-style data
- import a static Netflix catalog snapshot
- maintain a local availability table by region
- show availability as unknown when no provider is configured

Until this exists, keep the frontend disclaimer that recommended titles may not
be on Netflix.

### 4. Tune scoring weights

Use notebook experiments to compare:

- content similarity weight
- genre affinity weight
- language and country affinity weights
- recency decay half-life
- quality confidence weight
- diversity caps

Only promote new weights after comparing multiple profiles. Bump
`ALGORITHM_VERSION` for any scoring behavior change that should invalidate old
stored playlists.

### 5. Continue improving cold start

Sparse profiles now use lower content-similarity weight and higher quality/source
weight. Additional options:

- lean more heavily on popular cached catalog titles
- add optional onboarding preferences for genres or liked titles
- use household-level viewing patterns if privacy expectations are clear
- display a lower-confidence explanation when history is insufficient

### 6. Expand feedback signals

The first feedback actions are implemented. Future additions:

- feedback history instead of only current action
- stronger reranking from saved titles
- profile-level disliked genre/language patterns
- "show me more like this" seed expansion

### 7. Automate refreshes

Manual refresh support exists through `refresh_recommendations`. Next steps are
to run it from cron, a hosted scheduler, or a periodic worker when:

- a new upload finishes
- title metadata enrichment improves coverage
- the profile's latest quarter changes
- the user manually refreshes recommendations

### 8. Move toward a hybrid recommender

Collaborative signals should come later, after content-based evaluation is
stable. Potential hybrid inputs:

- users or profiles with similar taste vectors
- titles that commonly appear together across profiles
- profile similarity graph features

This should only be added after privacy, sparsity, and cold-start behavior are
well understood.

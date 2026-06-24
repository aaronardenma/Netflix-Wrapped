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
- TMDB discover results by preferred media type
- TMDB discover results filtered by preferred genres

The candidate pool intentionally uses cached titles first to avoid unnecessary
TMDB calls. TMDB calls are capped per recommendation run.

## Generated hyperparameters

Each run generates profile-specific hyperparameters and stores them in
`RecommendationSet.profile_summary.hyperparameters`.

Current generated values include:

- `metadata_richness`: share of watched titles with useful metadata
- `seed_count`: number of watched titles used as TMDB recommendation seeds
- `candidate_cache_limit`: maximum cached candidates loaded
- `minimum_candidate_pool`: fallback threshold for older cached titles
- `max_tmdb_calls`: per-run TMDB call cap
- `score_weights`: score component weights
- `diversity_caps`: maximum repeated values by genre, language, country, media
  type, and release decade

The scoring weights shift based on profile sparsity and metadata richness. If a
profile has strong metadata coverage, content similarity gets more weight. If a
profile is sparse, structured affinity signals carry more weight.

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
- TMDB seed relationship bonus

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

- seed-related title relationship
- matching top genre
- matching language preference
- matching origin country preference
- matching release era
- matching media type

The frontend also shows top signal chips from `profile_summary`, such as genre,
language, format, and origin.

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

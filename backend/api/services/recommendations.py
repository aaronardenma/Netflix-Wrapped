from collections import Counter, defaultdict
from datetime import timedelta
from math import exp, log

import numpy as np
import requests
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from api.models import (
    ExternalCatalogTitle,
    Recommendation,
    RecommendationFeedback,
    RecommendationSet,
    Title,
    ViewingEvent,
)
from api.services.title_metadata import TmdbClient


ALGORITHM_VERSION = "content-tfidf-v3"
PLAYLIST_SIZE = 20
PRIMARY_WINDOW_DAYS = 90
BASELINE_WINDOW_DAYS = 365
CATALOG_CACHE_DAYS = 30
MAX_TMDB_CALLS = 14
CACHED_CANDIDATE_LIMIT = 500
MIN_CANDIDATE_POOL = 80
NEGATIVE_FEEDBACK_ACTIONS = {
    RecommendationFeedback.Action.NOT_INTERESTED,
    RecommendationFeedback.Action.ALREADY_WATCHED,
}
POSITIVE_FEEDBACK_ACTIONS = {
    RecommendationFeedback.Action.LOOKS_GOOD,
    RecommendationFeedback.Action.SAVED,
}

TMDB_GENRES = {
    12: "Adventure",
    14: "Fantasy",
    16: "Animation",
    18: "Drama",
    27: "Horror",
    28: "Action",
    35: "Comedy",
    36: "History",
    37: "Western",
    53: "Thriller",
    80: "Crime",
    99: "Documentary",
    878: "Science Fiction",
    9648: "Mystery",
    10402: "Music",
    10749: "Romance",
    10751: "Family",
    10752: "War",
    10759: "Action & Adventure",
    10762: "Kids",
    10763: "News",
    10764: "Reality",
    10765: "Sci-Fi & Fantasy",
    10766: "Soap",
    10767: "Talk",
    10768: "War & Politics",
    10770: "TV Movie",
}
TMDB_GENRE_IDS = {genre: genre_id for genre_id, genre in TMDB_GENRES.items()}


class RecommendationError(Exception):
    pass


def _media_type_for_title(title):
    if title.media_type == Title.MediaType.TV_SHOW:
        return ExternalCatalogTitle.MediaType.TV
    if title.media_type == Title.MediaType.MOVIE:
        return ExternalCatalogTitle.MediaType.MOVIE
    return ""


def _release_year(row, media_type):
    value = row.get("first_air_date") if media_type == "tv" else row.get("release_date")
    try:
        return int(str(value)[:4]) if value else None
    except ValueError:
        return None


def _catalog_defaults(row, media_type, source_kind):
    poster_path = row.get("poster_path")
    return {
        "title": row.get("name") or row.get("title") or "Untitled",
        "original_title": row.get("original_name") or row.get("original_title") or "",
        "overview": row.get("overview") or "",
        "genres": [
            TMDB_GENRES[genre_id]
            for genre_id in row.get("genre_ids", [])
            if genre_id in TMDB_GENRES
        ],
        "origin_countries": row.get("origin_country") or [],
        "original_language": row.get("original_language") or "",
        "release_year": _release_year(row, media_type),
        "popularity": float(row.get("popularity") or 0),
        "vote_average": float(row.get("vote_average") or 0),
        "vote_count": int(row.get("vote_count") or 0),
        "poster_url": (
            f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        ),
        "metadata": {"candidate_sources": [source_kind]},
    }


def _cache_tmdb_results(rows, media_type, source_kind):
    cached = []
    for row in rows:
        external_id = row.get("id")
        if not external_id:
            continue
        catalog_title, created = ExternalCatalogTitle.objects.get_or_create(
            source="tmdb",
            media_type=media_type,
            external_id=str(external_id),
            defaults=_catalog_defaults(row, media_type, source_kind),
        )
        if not created:
            defaults = _catalog_defaults(row, media_type, source_kind)
            existing_sources = set(
                catalog_title.metadata.get("candidate_sources", [])
            )
            defaults["metadata"]["candidate_sources"] = sorted(
                existing_sources | {source_kind}
            )
            for field, value in defaults.items():
                setattr(catalog_title, field, value)
            catalog_title.save()
        cached.append(catalog_title)
    return cached


def _feedback_map(profile):
    return {
        feedback.catalog_title_id: feedback.action
        for feedback in RecommendationFeedback.objects.filter(profile=profile)
    }


def _top_preferences(weighted_titles, field, limit=5):
    totals = Counter()
    for row in weighted_titles:
        values = getattr(row["title"], field, None)
        if not values:
            continue
        if not isinstance(values, list):
            values = [values]
        for value in values:
            if value:
                totals[str(value)] += row["weight"]
    total = sum(totals.values()) or 1
    return [
        {"value": value, "share": round(weight / total, 3)}
        for value, weight in totals.most_common(limit)
    ]


def _load_profile_history(profile):
    latest_at = (
        ViewingEvent.objects.filter(profile=profile).aggregate(latest=Max("started_at"))[
            "latest"
        ]
    )
    if not latest_at:
        raise RecommendationError("This profile has no viewing history.")

    period_end = latest_at.date()
    period_start = period_end - timedelta(days=PRIMARY_WINDOW_DAYS - 1)
    baseline_start = period_end - timedelta(days=BASELINE_WINDOW_DAYS - 1)
    events = (
        ViewingEvent.objects.filter(
            profile=profile,
            started_at__date__gte=baseline_start,
            started_at__date__lte=period_end,
            title__isnull=False,
        )
        .select_related("title")
        .order_by("started_at")
    )

    title_rows = defaultdict(
        lambda: {"title": None, "weight": 0.0, "seconds": 0, "latest": None}
    )
    for event in events:
        age_days = max(0, (period_end - event.started_at.date()).days)
        recency = exp(-log(2) * age_days / 45)
        window_weight = 1.0 if event.started_at.date() >= period_start else 0.25
        row = title_rows[event.title_id]
        row["title"] = event.title
        row["seconds"] += event.duration_seconds
        row["weight"] += max(event.duration_seconds, 60) * recency * window_weight
        row["latest"] = event.started_at

    weighted_titles = sorted(
        title_rows.values(), key=lambda row: row["weight"], reverse=True
    )
    if not weighted_titles:
        raise RecommendationError("This profile has no usable title history.")
    return period_start, period_end, weighted_titles


def _seed_titles(weighted_titles, hyperparameters):
    oldest_possible = timezone.now() - timedelta(days=36500)
    top_weighted = weighted_titles[: hyperparameters["seed_count"]]
    recent = sorted(
        weighted_titles,
        key=lambda row: row["latest"] or oldest_possible,
        reverse=True,
    )[: hyperparameters["recent_seed_count"]]
    comfort = [
        row
        for row in sorted(
            weighted_titles,
            key=lambda row: row["seconds"],
            reverse=True,
        )
        if row["title"] not in {seed["title"] for seed in top_weighted}
    ][: hyperparameters["comfort_seed_count"]]

    seeds = []
    seen_title_ids = set()
    for source_kind, rows in (
        ("top-title-related", top_weighted),
        ("recent-related", recent),
        ("comfort-related", comfort),
    ):
        for row in rows:
            title_id = row["title"].id
            if title_id in seen_title_ids:
                continue
            seeds.append((row, source_kind))
            seen_title_ids.add(title_id)
    return seeds


def _tmdb_call_allowed(client, hyperparameters):
    return client.calls < hyperparameters["max_tmdb_calls"]


def _discover_candidates(weighted_titles, preferences, hyperparameters):
    client = TmdbClient()
    fresh_after = timezone.now() - timedelta(days=CATALOG_CACHE_DAYS)
    cached = list(
        ExternalCatalogTitle.objects.filter(
            source="tmdb", last_refreshed_at__gte=fresh_after
        ).order_by("-popularity")[: hyperparameters["candidate_cache_limit"]]
    )
    if len(cached) < hyperparameters["minimum_candidate_pool"]:
        older_cached = list(
            ExternalCatalogTitle.objects.filter(source="tmdb")
            .exclude(id__in=[candidate.id for candidate in cached])
            .order_by("-popularity")[
                : hyperparameters["candidate_cache_limit"] - len(cached)
            ]
        )
        cached.extend(older_cached)
    if not client.enabled():
        return cached

    discovered = {title.id: title for title in cached}
    for seed, source_kind in _seed_titles(weighted_titles, hyperparameters):
        title = seed["title"]
        media_type = _media_type_for_title(title)
        if not media_type or not title.tmdb_id or not _tmdb_call_allowed(client, hyperparameters):
            continue
        try:
            payload = client.get(
                f"/{media_type}/{title.tmdb_id}/recommendations",
                {"page": 1},
            ) or {}
        except requests.RequestException:
            continue
        for candidate in _cache_tmdb_results(
            payload.get("results", []), media_type, source_kind
        ):
            discovered[candidate.id] = candidate

    language_preferences = preferences["languages"]
    preferred_language = (
        language_preferences[0]["value"] if language_preferences else ""
    )
    preferred_genres = [
        row["value"]
        for row in preferences["genres"]
        if row["value"] in TMDB_GENRE_IDS
    ][:3]
    preferred_types = [
        row["value"]
        for row in sorted(
            preferences["media_types"],
            key=lambda item: item["share"],
            reverse=True,
        )
    ]
    for media_type in preferred_types or ["movie", "tv"]:
        if not _tmdb_call_allowed(client, hyperparameters):
            break
        params = {
            "sort_by": "vote_count.desc",
            "vote_count.gte": 100,
            "include_adult": "false",
            "page": 1,
        }
        if preferred_language:
            params["with_original_language"] = preferred_language
        try:
            payload = client.get(f"/discover/{media_type}", params) or {}
        except requests.RequestException:
            continue
        for candidate in _cache_tmdb_results(
            payload.get("results", []), media_type, "taste-discovery"
        ):
            discovered[candidate.id] = candidate

    for genre in preferred_genres:
        if not _tmdb_call_allowed(client, hyperparameters):
            break
        for media_type in preferred_types or ["movie", "tv"]:
            if not _tmdb_call_allowed(client, hyperparameters):
                break
            params = {
                "sort_by": "vote_count.desc",
                "vote_count.gte": 50,
                "include_adult": "false",
                "with_genres": TMDB_GENRE_IDS[genre],
                "page": 1,
            }
            if preferred_language:
                params["with_original_language"] = preferred_language
            try:
                payload = client.get(f"/discover/{media_type}", params) or {}
            except requests.RequestException:
                continue
            for candidate in _cache_tmdb_results(
                payload.get("results", []), media_type, "genre-discovery"
            ):
                discovered[candidate.id] = candidate

    for media_type in preferred_types or ["movie", "tv"]:
        if not _tmdb_call_allowed(client, hyperparameters):
            break
        try:
            payload = client.get(f"/trending/{media_type}/week", {"page": 1}) or {}
        except requests.RequestException:
            continue
        for candidate in _cache_tmdb_results(
            payload.get("results", []), media_type, "trending"
        ):
            discovered[candidate.id] = candidate

    for media_type in preferred_types or ["movie", "tv"]:
        if not _tmdb_call_allowed(client, hyperparameters):
            break
        try:
            payload = client.get(
                f"/{media_type}/popular",
                {"page": 1},
            ) or {}
        except requests.RequestException:
            continue
        for candidate in _cache_tmdb_results(
            payload.get("results", []), media_type, "popular"
        ):
            discovered[candidate.id] = candidate

    return list(discovered.values())


def _title_document(title):
    return " ".join(
        [
            title.canonical_name or title.name,
            " ".join(title.genres or []),
            " ".join(title.origin_countries or []),
            title.original_language or "",
            title.media_type or "",
            str(title.release_year or ""),
        ]
    )


def _candidate_document(candidate):
    return " ".join(
        [
            candidate.title,
            candidate.overview,
            " ".join(candidate.genres or []),
            " ".join(candidate.keywords or []),
            " ".join(candidate.origin_countries or []),
            candidate.original_language or "",
            candidate.media_type,
            str(candidate.release_year or ""),
        ]
    )


def _affinity(values, preferences):
    return min(1.0, sum(preferences.get(value, 0.0) for value in values if value))


def _preference_map(preferences):
    return {row["value"]: row["share"] for row in preferences}


def _release_decade(year):
    if not year:
        return ""
    return f"{int(year) // 10 * 10}s"


def _runtime_bucket(minutes):
    if not minutes:
        return ""
    if minutes < 35:
        return "short"
    if minutes <= 75:
        return "medium"
    if minutes <= 120:
        return "feature"
    return "long"


def _scalar_preferences(weighted_titles, extractor, limit=5):
    totals = Counter()
    for row in weighted_titles:
        value = extractor(row["title"])
        if value:
            totals[str(value)] += row["weight"]
    total = sum(totals.values()) or 1
    return [
        {"value": value, "share": round(weight / total, 3)}
        for value, weight in totals.most_common(limit)
    ]


def _media_type_preferences(weighted_titles):
    total = sum(row["weight"] for row in weighted_titles) or 1
    return [
        {
            "value": media_type,
            "share": round(
                sum(
                    row["weight"]
                    for row in weighted_titles
                    if _media_type_for_title(row["title"]) == media_type
                )
                / total,
                3,
            ),
        }
        for media_type in ("movie", "tv")
    ]


def _profile_preferences(weighted_titles):
    return {
        "genres": _top_preferences(weighted_titles, "genres"),
        "languages": _top_preferences(weighted_titles, "original_language", limit=3),
        "countries": _top_preferences(weighted_titles, "origin_countries", limit=4),
        "media_types": _media_type_preferences(weighted_titles),
        "ratings": _scalar_preferences(weighted_titles, lambda title: title.rating, limit=4),
        "release_decades": _scalar_preferences(
            weighted_titles,
            lambda title: _release_decade(title.release_year),
            limit=4,
        ),
        "runtime_buckets": _scalar_preferences(
            weighted_titles,
            lambda title: _runtime_bucket(title.runtime_minutes),
            limit=4,
        ),
    }


def _metadata_richness(weighted_titles):
    if not weighted_titles:
        return 0
    titles = [row["title"] for row in weighted_titles]
    rich_count = sum(
        1
        for title in titles
        if title.genres
        and title.original_language
        and title.media_type != Title.MediaType.UNKNOWN
    )
    return rich_count / len(titles)


def _generate_hyperparameters(weighted_titles):
    richness = _metadata_richness(weighted_titles)
    title_count = len(weighted_titles)
    sparse_profile = title_count < 8
    cold_start_profile = title_count < 3
    text_weight = 0.44 if richness >= 0.65 else 0.32
    if sparse_profile:
        text_weight -= 0.08
    if cold_start_profile:
        text_weight = 0.20

    weights = {
        "content_similarity": round(text_weight, 2),
        "genre_affinity": 0.17,
        "language_affinity": 0.10,
        "country_affinity": 0.08,
        "type_affinity": 0.07,
        "release_decade_affinity": 0.04,
        "runtime_affinity": 0.03,
        "rating_affinity": 0.02,
        "quality_confidence": 0.08 if cold_start_profile else 0.06,
        "source_strength": 0.07 if cold_start_profile else 0.04,
        "feedback_affinity": 0.04,
    }
    remaining = round(1 - sum(weights.values()), 2)
    if remaining:
        weights["genre_affinity"] = round(weights["genre_affinity"] + remaining, 2)

    return {
        "algorithm_version": ALGORITHM_VERSION,
        "metadata_richness": round(richness, 3),
        "seed_count": min(8, max(3, title_count // 2)),
        "recent_seed_count": min(4, max(1, title_count // 3)),
        "comfort_seed_count": min(3, max(1, title_count // 4)),
        "candidate_cache_limit": CACHED_CANDIDATE_LIMIT,
        "minimum_candidate_pool": MIN_CANDIDATE_POOL,
        "max_tmdb_calls": MAX_TMDB_CALLS,
        "profile_mode": "cold_start" if cold_start_profile else "sparse" if sparse_profile else "standard",
        "score_weights": weights,
        "diversity_caps": {
            "genre": 6 if cold_start_profile else 5 if sparse_profile else 4,
            "language": 8,
            "country": 8,
            "media_type": 14,
            "decade": 8,
        },
    }


def _source_strength(candidate):
    sources = set(candidate.metadata.get("candidate_sources", []))
    if sources & {"seed-related", "top-title-related", "recent-related", "comfort-related"}:
        return 1.0
    if "genre-discovery" in sources:
        return 0.75
    if "taste-discovery" in sources:
        return 0.65
    if "trending" in sources:
        return 0.5
    if "popular" in sources:
        return 0.4
    return 0.0


def _score_candidates(weighted_titles, candidates, preferences, hyperparameters, feedback_actions=None):
    feedback_actions = feedback_actions or {}
    watched_external_ids = {
        (_media_type_for_title(row["title"]), str(row["title"].tmdb_id))
        for row in weighted_titles
        if row["title"].tmdb_id and _media_type_for_title(row["title"])
    }
    watched_names = {
        (row["title"].canonical_name or row["title"].name).strip().casefold()
        for row in weighted_titles
    }
    eligible = [
        candidate
        for candidate in candidates
        if (candidate.media_type, candidate.external_id) not in watched_external_ids
        and candidate.title.strip().casefold() not in watched_names
        and feedback_actions.get(candidate.id) not in NEGATIVE_FEEDBACK_ACTIONS
        and (candidate.genres or candidate.overview)
    ]
    if not eligible:
        raise RecommendationError(
            "No unseen catalog candidates are available yet. Configure TMDB or refresh the catalog."
        )

    documents = [_title_document(row["title"]) for row in weighted_titles]
    candidate_documents = [_candidate_document(candidate) for candidate in eligible]
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=6000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(documents + candidate_documents)
    watched_matrix = matrix[: len(documents)]
    candidate_matrix = matrix[len(documents) :]
    weights = [row["weight"] for row in weighted_titles]
    weight_total = sum(weights) or 1
    profile_vector = np.asarray(weights, dtype=float) / weight_total
    profile_vector = profile_vector.reshape(1, -1) @ watched_matrix
    similarities = cosine_similarity(profile_vector, candidate_matrix)[0]

    genres = _preference_map(preferences["genres"])
    languages = _preference_map(preferences["languages"])
    countries = _preference_map(preferences["countries"])
    media_types = _preference_map(preferences["media_types"])
    release_decades = _preference_map(preferences["release_decades"])
    runtime_buckets = _preference_map(preferences["runtime_buckets"])
    ratings = _preference_map(preferences["ratings"])
    score_weights = hyperparameters["score_weights"]

    scored = []
    for candidate, similarity in zip(eligible, similarities):
        genre_score = _affinity(candidate.genres or [], genres)
        language_score = languages.get(candidate.original_language, 0.0)
        country_score = _affinity(candidate.origin_countries or [], countries)
        type_score = media_types.get(candidate.media_type, 0.0)
        decade_score = release_decades.get(
            _release_decade(candidate.release_year),
            0.0,
        )
        runtime_score = runtime_buckets.get(
            _runtime_bucket(candidate.runtime_minutes),
            0.0,
        )
        rating_score = ratings.get(candidate.rating, 0.0)
        feedback_action = feedback_actions.get(candidate.id)
        feedback_score = 1.0 if feedback_action in POSITIVE_FEEDBACK_ACTIONS else 0.0
        quality_score = min(
            1.0,
            (candidate.vote_average / 10) * 0.6
            + min(1.0, log(1 + candidate.vote_count) / log(10001)) * 0.4,
        )
        source_score = _source_strength(candidate)
        final_score = (
            float(similarity) * score_weights["content_similarity"]
            + genre_score * score_weights["genre_affinity"]
            + language_score * score_weights["language_affinity"]
            + country_score * score_weights["country_affinity"]
            + type_score * score_weights["type_affinity"]
            + decade_score * score_weights["release_decade_affinity"]
            + runtime_score * score_weights["runtime_affinity"]
            + rating_score * score_weights["rating_affinity"]
            + quality_score * score_weights["quality_confidence"]
            + source_score * score_weights["source_strength"]
            + feedback_score * score_weights["feedback_affinity"]
        )
        signals = {
            "content_similarity": round(float(similarity), 4),
            "genre_affinity": round(genre_score, 4),
            "language_affinity": round(language_score, 4),
            "country_affinity": round(country_score, 4),
            "type_affinity": round(type_score, 4),
            "release_decade_affinity": round(decade_score, 4),
            "runtime_affinity": round(runtime_score, 4),
            "rating_affinity": round(rating_score, 4),
            "quality_confidence": round(quality_score, 4),
            "source_strength": round(source_score, 4),
            "feedback_affinity": feedback_score,
            "feedback_action": feedback_action or "",
        }
        scored.append((candidate, final_score, signals))
    return sorted(scored, key=lambda row: row[1], reverse=True)


def _explanation(candidate, signals, preferences):
    sources = candidate.metadata.get("candidate_sources", [])
    top_genre = preferences["genres"][0]["value"] if preferences["genres"] else ""
    top_language = preferences["languages"][0]["value"] if preferences["languages"] else ""
    top_country = preferences["countries"][0]["value"] if preferences["countries"] else ""
    if set(sources) & {"seed-related", "top-title-related", "recent-related", "comfort-related"}:
        return "Related to titles you spent the most time with recently."
    if signals.get("feedback_action") == RecommendationFeedback.Action.SAVED:
        return "Similar to titles you have saved from past recommendations."
    if signals.get("feedback_action") == RecommendationFeedback.Action.LOOKS_GOOD:
        return "Similar to recommendations you marked as a good fit."
    if top_genre and top_genre in candidate.genres:
        return f"Matches your recent interest in {top_genre.lower()} titles."
    if top_language and signals["language_affinity"] > 0.15 and candidate.original_language:
        return f"Fits your recent preference for {top_language.upper()} language titles."
    if top_country and signals["country_affinity"] > 0.15 and candidate.origin_countries:
        return f"Lines up with the origin countries you have watched most."
    if signals["release_decade_affinity"] > 0.1 and candidate.release_year:
        return f"Fits the release era that appears most in your recent history."
    if signals["type_affinity"] > 0.2:
        return f"Matches the format you have been watching most."
    return "A strong content match based on your recent viewing patterns."


def _diversify(scored, hyperparameters, limit=PLAYLIST_SIZE):
    selected = []
    selected_ids = set()
    genre_counts = Counter()
    language_counts = Counter()
    country_counts = Counter()
    media_type_counts = Counter()
    decade_counts = Counter()
    caps = hyperparameters["diversity_caps"]
    for candidate, score, signals in scored:
        primary_genre = candidate.genres[0] if candidate.genres else "Other"
        primary_country = (
            candidate.origin_countries[0] if candidate.origin_countries else "Unknown"
        )
        decade = _release_decade(candidate.release_year) or "Unknown"
        if genre_counts[primary_genre] >= caps["genre"]:
            continue
        if language_counts[candidate.original_language or "Unknown"] >= caps["language"]:
            continue
        if country_counts[primary_country] >= caps["country"]:
            continue
        if media_type_counts[candidate.media_type] >= caps["media_type"]:
            continue
        if decade_counts[decade] >= caps["decade"]:
            continue
        selected.append((candidate, score, signals))
        selected_ids.add(candidate.id)
        genre_counts[primary_genre] += 1
        language_counts[candidate.original_language or "Unknown"] += 1
        country_counts[primary_country] += 1
        media_type_counts[candidate.media_type] += 1
        decade_counts[decade] += 1
        if len(selected) == limit:
            break
    if len(selected) < limit:
        for candidate, score, signals in scored:
            if candidate.id in selected_ids:
                continue
            selected.append((candidate, score, signals))
            selected_ids.add(candidate.id)
            if len(selected) == limit:
                break
    return selected


def serialize_recommendation_set(recommendation_set):
    feedback_actions = _feedback_map(recommendation_set.profile)
    return {
        "id": str(recommendation_set.id),
        "profile": recommendation_set.profile.name,
        "period_start": recommendation_set.period_start.isoformat(),
        "period_end": recommendation_set.period_end.isoformat(),
        "algorithm_version": recommendation_set.algorithm_version,
        "generated_at": recommendation_set.generated_at.isoformat(),
        "profile_summary": recommendation_set.profile_summary,
        "recommendations": [
            {
                "rank": recommendation.rank,
                "score": round(recommendation.score, 4),
                "segment": recommendation.segment,
                "explanation": recommendation.explanation,
                "signals": recommendation.contributing_signals,
                "feedback_action": feedback_actions.get(recommendation.catalog_title_id, ""),
                "title": recommendation.catalog_title.title,
                "media_type": recommendation.catalog_title.media_type,
                "genres": recommendation.catalog_title.genres,
                "release_year": recommendation.catalog_title.release_year,
                "original_language": recommendation.catalog_title.original_language,
                "rating": recommendation.catalog_title.rating,
                "poster_url": recommendation.catalog_title.poster_url,
                "overview": recommendation.catalog_title.overview,
                "tmdb_id": recommendation.catalog_title.external_id,
            }
            for recommendation in recommendation_set.recommendations.select_related(
                "catalog_title"
            ).all()
        ],
    }


def generate_recommendations(profile, force=False):
    period_start, period_end, weighted_titles = _load_profile_history(profile)
    existing = (
        RecommendationSet.objects.filter(
            profile=profile,
            period_start=period_start,
            period_end=period_end,
            algorithm_version=ALGORITHM_VERSION,
            status=RecommendationSet.Status.READY,
        )
        .prefetch_related("recommendations__catalog_title")
        .first()
    )
    if existing and not force:
        return existing

    preferences = _profile_preferences(weighted_titles)
    hyperparameters = _generate_hyperparameters(weighted_titles)
    feedback_actions = _feedback_map(profile)
    candidates = _discover_candidates(weighted_titles, preferences, hyperparameters)
    scored = _score_candidates(
        weighted_titles,
        candidates,
        preferences,
        hyperparameters,
        feedback_actions=feedback_actions,
    )
    selected = _diversify(scored, hyperparameters)
    if not selected:
        raise RecommendationError("Not enough diverse unseen titles were found.")

    profile_summary = {
        "window": "Recent 90 days with a one-year baseline",
        "top_genres": preferences["genres"],
        "top_languages": preferences["languages"],
        "top_countries": preferences["countries"],
        "top_media_types": preferences["media_types"],
        "top_release_decades": preferences["release_decades"],
        "top_runtime_buckets": preferences["runtime_buckets"],
        "top_ratings": preferences["ratings"],
        "hyperparameters": hyperparameters,
        "titles_considered": len(weighted_titles),
        "candidate_count": len(candidates),
        "eligible_candidate_count": len(scored),
        "feedback_counts": dict(Counter(feedback_actions.values())),
    }

    with transaction.atomic():
        recommendation_set, _ = RecommendationSet.objects.update_or_create(
            profile=profile,
            period_start=period_start,
            period_end=period_end,
            algorithm_version=ALGORITHM_VERSION,
            defaults={
                "status": RecommendationSet.Status.READY,
                "profile_summary": profile_summary,
            },
        )
        recommendation_set.recommendations.all().delete()
        Recommendation.objects.bulk_create(
            [
                Recommendation(
                    recommendation_set=recommendation_set,
                    catalog_title=candidate,
                    rank=index,
                    score=score,
                    segment=(
                        "because_you_watched"
                        if signals["source_strength"] >= 1
                        else "saved_signal"
                        if signals["feedback_affinity"]
                        else "top_match"
                    ),
                    explanation=_explanation(candidate, signals, preferences),
                    contributing_signals=signals,
                )
                for index, (candidate, score, signals) in enumerate(
                    selected, start=1
                )
            ]
        )
    return recommendation_set

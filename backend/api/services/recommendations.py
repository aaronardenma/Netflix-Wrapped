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
    RecommendationSet,
    Title,
    ViewingEvent,
)
from api.services.title_metadata import TmdbClient


ALGORITHM_VERSION = "content-tfidf-v1"
PLAYLIST_SIZE = 20
PRIMARY_WINDOW_DAYS = 90
BASELINE_WINDOW_DAYS = 365
CATALOG_CACHE_DAYS = 30
MAX_TMDB_CALLS = 10

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


def _discover_candidates(weighted_titles):
    client = TmdbClient()
    fresh_after = timezone.now() - timedelta(days=CATALOG_CACHE_DAYS)
    cached = list(
        ExternalCatalogTitle.objects.filter(
            source="tmdb", last_refreshed_at__gte=fresh_after
        ).order_by("-popularity")[:300]
    )
    if not client.enabled():
        return cached

    discovered = {title.id: title for title in cached}
    for seed in weighted_titles[:4]:
        title = seed["title"]
        media_type = _media_type_for_title(title)
        if not media_type or not title.tmdb_id or client.calls >= MAX_TMDB_CALLS:
            continue
        try:
            payload = client.get(
                f"/{media_type}/{title.tmdb_id}/recommendations",
                {"page": 1},
            ) or {}
        except requests.RequestException:
            continue
        for candidate in _cache_tmdb_results(
            payload.get("results", []), media_type, "seed-related"
        ):
            discovered[candidate.id] = candidate

    language_preferences = _top_preferences(
        weighted_titles, "original_language", limit=2
    )
    preferred_language = (
        language_preferences[0]["value"] if language_preferences else ""
    )
    for media_type in ("movie", "tv"):
        if client.calls >= MAX_TMDB_CALLS:
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


def _score_candidates(weighted_titles, candidates):
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

    genres = _preference_map(_top_preferences(weighted_titles, "genres"))
    languages = _preference_map(
        _top_preferences(weighted_titles, "original_language")
    )
    media_types = _preference_map(
        [
            {
                "value": media_type,
                "share": sum(
                    row["weight"]
                    for row in weighted_titles
                    if _media_type_for_title(row["title"]) == media_type
                )
                / weight_total,
            }
            for media_type in ("movie", "tv")
        ]
    )

    scored = []
    for candidate, similarity in zip(eligible, similarities):
        genre_score = _affinity(candidate.genres or [], genres)
        language_score = languages.get(candidate.original_language, 0.0)
        type_score = media_types.get(candidate.media_type, 0.0)
        quality_score = min(
            1.0,
            (candidate.vote_average / 10) * 0.6
            + min(1.0, log(1 + candidate.vote_count) / log(10001)) * 0.4,
        )
        source_score = (
            1.0
            if "seed-related" in candidate.metadata.get("candidate_sources", [])
            else 0.0
        )
        final_score = (
            float(similarity) * 0.62
            + genre_score * 0.14
            + language_score * 0.07
            + type_score * 0.07
            + quality_score * 0.06
            + source_score * 0.04
        )
        signals = {
            "content_similarity": round(float(similarity), 4),
            "genre_affinity": round(genre_score, 4),
            "language_affinity": round(language_score, 4),
            "type_affinity": round(type_score, 4),
            "quality_confidence": round(quality_score, 4),
            "seed_relationship": source_score,
        }
        scored.append((candidate, final_score, signals))
    return sorted(scored, key=lambda row: row[1], reverse=True)


def _explanation(candidate, signals, top_genre):
    sources = candidate.metadata.get("candidate_sources", [])
    if "seed-related" in sources:
        return "Related to titles you spent the most time with recently."
    if top_genre and top_genre in candidate.genres:
        return f"Matches your recent interest in {top_genre.lower()}."
    if signals["language_affinity"] > 0.15 and candidate.original_language:
        return "Fits the languages you have been watching most."
    return "A strong content match based on your recent viewing patterns."


def _diversify(scored, limit=PLAYLIST_SIZE):
    selected = []
    genre_counts = Counter()
    for candidate, score, signals in scored:
        primary_genre = candidate.genres[0] if candidate.genres else "Other"
        if genre_counts[primary_genre] >= max(3, int(limit * 0.4)):
            continue
        selected.append((candidate, score, signals))
        genre_counts[primary_genre] += 1
        if len(selected) == limit:
            break
    return selected


def serialize_recommendation_set(recommendation_set):
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

    candidates = _discover_candidates(weighted_titles)
    scored = _score_candidates(weighted_titles, candidates)
    selected = _diversify(scored)
    if not selected:
        raise RecommendationError("Not enough diverse unseen titles were found.")

    top_genres = _top_preferences(weighted_titles, "genres")
    profile_summary = {
        "window": "Recent 90 days with a one-year baseline",
        "top_genres": top_genres,
        "top_languages": _top_preferences(
            weighted_titles, "original_language", limit=3
        ),
        "titles_considered": len(weighted_titles),
        "candidate_count": len(candidates),
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
        top_genre = top_genres[0]["value"] if top_genres else ""
        Recommendation.objects.bulk_create(
            [
                Recommendation(
                    recommendation_set=recommendation_set,
                    catalog_title=candidate,
                    rank=index,
                    score=score,
                    segment=(
                        "because_you_watched"
                        if signals["seed_relationship"]
                        else "top_match"
                    ),
                    explanation=_explanation(candidate, signals, top_genre),
                    contributing_signals=signals,
                )
                for index, (candidate, score, signals) in enumerate(
                    selected, start=1
                )
            ]
        )
    return recommendation_set

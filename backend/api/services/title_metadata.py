import json
import os
import string
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from api.models import RecommendationSet, Title, ViewingEvent


TMDB_API_URL = "https://api.themoviedb.org/3"
SUCCESS_TTL_DAYS = 90
MISS_TTL_DAYS = 7
DEFAULT_MAX_TITLES = 50
DEFAULT_MAX_CALLS = 100


def metadata_key(value):
    text = str(value or "").strip().lower()
    text = text.translate(str.maketrans({char: " " for char in string.punctuation}))
    return " ".join(text.split())


def _override_path():
    return os.path.join(settings.BASE_DIR, "utils", "title_metadata_overrides.json")


def load_manual_overrides():
    try:
        with open(_override_path(), "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}


def display_media_type(value):
    if value == Title.MediaType.TV_SHOW:
        return "TV Show"
    if value == Title.MediaType.MOVIE:
        return "Movie"
    return "Unknown"


def model_media_type(value):
    if value in {Title.MediaType.TV_SHOW, "TV Show", "tv", "tv_show"}:
        return Title.MediaType.TV_SHOW
    if value in {Title.MediaType.MOVIE, "Movie", "movie"}:
        return Title.MediaType.MOVIE
    return Title.MediaType.UNKNOWN


def apply_metadata(title, metadata):
    title.canonical_name = metadata.get("canonical_name") or title.canonical_name or title.name
    title.original_name = metadata.get("original_name") or title.original_name
    title.media_type = model_media_type(metadata.get("media_type"))
    title.genres = metadata.get("genres") or []
    title.origin_countries = metadata.get("origin_countries") or []
    title.original_language = metadata.get("original_language") or title.original_language
    title.popularity = float(metadata.get("popularity") or 0)
    title.release_year = metadata.get("release_year")
    title.runtime_minutes = metadata.get("runtime_minutes")
    title.rating = metadata.get("rating") or title.rating
    title.poster_url = metadata.get("poster_url") or title.poster_url
    title.tmdb_id = str(metadata.get("tmdb_id") or title.tmdb_id or "")
    title.omdb_id = metadata.get("omdb_id") or title.omdb_id
    title.metadata_source = metadata.get("source") or title.metadata_source
    title.metadata_confidence = float(metadata.get("confidence") or 0)
    title.enrichment_status = (
        Title.EnrichmentStatus.MATCHED
        if title.metadata_confidence >= 0.75
        else Title.EnrichmentStatus.NEEDS_REVIEW
    )
    title.last_enriched_at = timezone.now()
    title.retry_after = timezone.now() + timedelta(days=SUCCESS_TTL_DAYS)
    title.save(update_fields=[
        "canonical_name",
        "original_name",
        "media_type",
        "genres",
        "origin_countries",
        "original_language",
        "popularity",
        "release_year",
        "runtime_minutes",
        "rating",
        "poster_url",
        "tmdb_id",
        "omdb_id",
        "metadata_source",
        "metadata_confidence",
        "enrichment_status",
        "last_enriched_at",
        "retry_after",
        "updated_at",
    ])


def mark_unknown(title, source="tmdb-miss"):
    title.metadata_source = source
    title.metadata_confidence = 0
    title.enrichment_status = Title.EnrichmentStatus.UNKNOWN
    title.last_enriched_at = timezone.now()
    title.retry_after = timezone.now() + timedelta(days=MISS_TTL_DAYS)
    title.save(update_fields=[
        "metadata_source",
        "metadata_confidence",
        "enrichment_status",
        "last_enriched_at",
        "retry_after",
        "updated_at",
    ])


def should_attempt_enrichment(title):
    if title.enrichment_status == Title.EnrichmentStatus.MATCHED and not title.poster_url:
        return True
    if title.enrichment_status == Title.EnrichmentStatus.MATCHED and title.retry_after and title.retry_after > timezone.now():
        return False
    if title.enrichment_status == Title.EnrichmentStatus.UNKNOWN and title.retry_after and title.retry_after > timezone.now():
        return False
    return True


class TmdbClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or getattr(settings, "TMDB_API_KEY", None)
        self.calls = 0

    def enabled(self):
        return bool(self.api_key)

    def get(self, path, params=None):
        if not self.enabled():
            return None
        self.calls += 1
        response = requests.get(
            f"{TMDB_API_URL}{path}",
            params={"api_key": self.api_key, **(params or {})},
            timeout=8,
        )
        response.raise_for_status()
        return response.json()

    def search_multi(self, query):
        return self.get("/search/multi", {"query": query, "include_adult": "false"}) or {}

    def details(self, media_type, tmdb_id):
        path_type = "tv" if media_type == "tv" else "movie"
        append = "content_ratings,external_ids" if path_type == "tv" else "release_dates,external_ids"
        return self.get(f"/{path_type}/{tmdb_id}", {"append_to_response": append}) or {}


def _candidate_titles(candidate):
    return [
        candidate.get("title"),
        candidate.get("name"),
        candidate.get("original_title"),
        candidate.get("original_name"),
    ]


def _expected_media_type(title):
    if title.media_type == Title.MediaType.TV_SHOW:
        return "tv"
    if title.media_type == Title.MediaType.MOVIE:
        return "movie"
    return None


def _score_candidate(title, candidate):
    if candidate.get("media_type") not in {"movie", "tv"}:
        return 0

    title_key = metadata_key(title.name)
    candidate_keys = [metadata_key(value) for value in _candidate_titles(candidate) if value]
    if title_key in candidate_keys:
        score = 0.88
    elif any(title_key and (title_key in key or key in title_key) for key in candidate_keys):
        score = 0.68
    else:
        return 0

    expected = _expected_media_type(title)
    if expected and candidate.get("media_type") == expected:
        score += 0.08
    elif expected and candidate.get("media_type") != expected:
        score -= 0.15

    return min(score, 0.96)


def _rating_from_details(media_type, details):
    if media_type == "tv":
        for row in details.get("content_ratings", {}).get("results", []):
            if row.get("iso_3166_1") == "US" and row.get("rating"):
                return row["rating"]
    for country in details.get("release_dates", {}).get("results", []):
        if country.get("iso_3166_1") != "US":
            continue
        for release in country.get("release_dates", []):
            if release.get("certification"):
                return release["certification"]
    return ""


def _metadata_from_tmdb(title, candidate, details, confidence):
    media_type = candidate.get("media_type")
    release_date = details.get("first_air_date") if media_type == "tv" else details.get("release_date")
    release_year = None
    if release_date:
        try:
            release_year = int(str(release_date)[:4])
        except ValueError:
            release_year = None

    runtime = None
    if media_type == "movie":
        runtime = details.get("runtime")
    elif details.get("episode_run_time"):
        runtime = details["episode_run_time"][0]

    poster_path = details.get("poster_path")
    origin_countries = details.get("origin_country") or [
        country.get("iso_3166_1")
        for country in details.get("production_countries", [])
        if country.get("iso_3166_1")
    ]
    return {
        "canonical_name": details.get("name") or details.get("title") or title.name,
        "original_name": details.get("original_name") or details.get("original_title") or "",
        "media_type": "TV Show" if media_type == "tv" else "Movie",
        "genres": [genre["name"] for genre in details.get("genres", []) if genre.get("name")],
        "origin_countries": origin_countries,
        "original_language": details.get("original_language") or "",
        "popularity": details.get("popularity") or candidate.get("popularity") or 0,
        "release_year": release_year,
        "runtime_minutes": runtime,
        "rating": _rating_from_details(media_type, details),
        "poster_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "",
        "tmdb_id": candidate.get("id"),
        "source": "tmdb",
        "confidence": confidence,
    }


def enrich_title_from_tmdb(title, client=None, min_confidence=0.75, max_calls=100):
    client = client or TmdbClient()
    if not client.enabled() or client.calls >= max_calls:
        return False

    search = client.search_multi(title.name)
    candidates = search.get("results", [])
    scored = sorted(
        ((candidate, _score_candidate(title, candidate)) for candidate in candidates),
        key=lambda pair: pair[1],
        reverse=True,
    )
    scored = [(candidate, score) for candidate, score in scored if score >= min_confidence]
    if not scored:
        if title.enrichment_status != Title.EnrichmentStatus.MATCHED:
            mark_unknown(title)
        return False

    candidate, confidence = scored[0]
    if client.calls >= max_calls:
        return False
    details = client.details(candidate["media_type"], candidate["id"])
    apply_metadata(title, _metadata_from_tmdb(title, candidate, details, confidence))
    return True


def apply_manual_overrides(titles):
    overrides = load_manual_overrides()
    applied = 0
    for title in titles:
        override = overrides.get(metadata_key(title.normalized_name)) or overrides.get(metadata_key(title.name))
        if not override:
            continue
        apply_metadata(title, override)
        applied += 1
    return applied


def enrich_titles(titles, watchtime_by_title=None, max_titles=DEFAULT_MAX_TITLES, max_calls=DEFAULT_MAX_CALLS):
    titles = list(titles)
    apply_manual_overrides(titles)

    unresolved = [title for title in titles if should_attempt_enrichment(title)]
    if watchtime_by_title:
        unresolved.sort(key=lambda title: watchtime_by_title.get(str(title.id), 0), reverse=True)
    unresolved = unresolved[:max_titles]

    client = TmdbClient()
    if not client.enabled():
        return {"manual_or_cached": len(titles) - len(unresolved), "tmdb_calls": 0, "tmdb_enabled": False}

    matched = 0
    matched_titles = []
    for title in unresolved:
        if client.calls >= max_calls:
            break
        try:
            if enrich_title_from_tmdb(title, client=client, max_calls=max_calls):
                matched += 1
                matched_titles.append(title)
        except requests.RequestException:
            mark_unknown(title, source="tmdb-error")

    if matched_titles:
        invalidate_recommendations_for_titles(matched_titles)

    return {"matched": matched, "tmdb_calls": client.calls, "tmdb_enabled": True}


def enrich_titles_safely(*args, **kwargs):
    try:
        return enrich_titles(*args, **kwargs)
    except Exception as exc:
        return {"error": str(exc), "tmdb_enabled": bool(getattr(settings, "TMDB_API_KEY", None))}


def invalidate_recommendations_for_titles(titles):
    title_ids = [title.id for title in titles]
    if not title_ids:
        return 0
    profile_ids = (
        ViewingEvent.objects.filter(title_id__in=title_ids)
        .values_list("profile_id", flat=True)
        .distinct()
    )
    deleted_count, _ = RecommendationSet.objects.filter(
        profile_id__in=profile_ids,
    ).delete()
    return deleted_count

import io
import json

import pandas as pd
from django.core.cache import cache
from django.db.models import Count, Max

from api.models import NetflixProfile, ViewingEvent, YearlyRecap
from api.services.recap_cache import (
    ANONYMOUS_CACHE_TTL_SECONDS,
    result_cache_key,
    upload_cache_key,
)
from utils.data_analysis import (
    GRAPH_SCHEMA_VERSION,
    getJsonGraphData,
    getProfileComparisonData,
)


def is_all_years(year):
    return str(year).lower() == "all"


def display_year(year):
    return "all" if is_all_years(year) else int(year)


def recap_year_key(year):
    return "all" if is_all_years(year) else str(int(year))


def profile_events(user, profile_name, year):
    profile = NetflixProfile.objects.filter(
        user=user,
        name=profile_name,
    ).first()
    if not profile:
        return None, ViewingEvent.objects.none()

    events = ViewingEvent.objects.filter(profile=profile)
    if not is_all_years(year):
        events = events.filter(started_at__year=int(year))
    return profile, events


def filter_profile_year(dataframe, profile_name, year):
    mask = dataframe["Profile Name"] == profile_name
    if not is_all_years(year):
        mask &= dataframe["year"] == int(year)
    return dataframe[mask].copy()


def seconds_to_duration(seconds):
    seconds = int(seconds or 0)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def event_rows(events):
    rows = []
    queryset = events.select_related("profile", "title").order_by("started_at")
    for event in queryset:
        title = event.title
        rows.append(
            {
                "Profile Name": event.profile.name,
                "Start Time": event.started_at,
                "Duration": seconds_to_duration(event.duration_seconds),
                "Attributes": "",
                "Title": event.title_raw,
                "Raw Title": event.title_raw,
                "Series Title": event.series_title,
                "Season Label": event.season_label,
                "Episode Title": event.episode_title,
                "Episode Number": event.episode_number,
                "Is Episode": event.is_episode,
                "Parsed Media Type": event.parsed_media_type,
                "Classification Confidence": event.classification_confidence,
                "Classification Source": event.classification_source,
                "Cached Media Type": title.media_type if title else "",
                "Metadata Genres": title.genres if title else [],
                "Metadata Origin Countries": (
                    title.origin_countries if title else []
                ),
                "Metadata Original Language": (
                    title.original_language if title else ""
                ),
                "Metadata Rating": title.rating if title else "",
                "Metadata Release Year": title.release_year if title else None,
                "Metadata Runtime Minutes": (
                    title.runtime_minutes if title else None
                ),
                "Metadata Poster URL": title.poster_url if title else "",
                "Metadata Popularity": title.popularity if title else 0,
                "Metadata Source": title.metadata_source if title else "",
                "Metadata Confidence": (
                    title.metadata_confidence if title else 0
                ),
                "Supplemental Video Type": (
                    event.supplemental_video_type or None
                ),
                "Device Type": event.device_type,
                "Bookmark": "",
                "Latest Bookmark": "",
                "Country": event.country,
            }
        )
    return rows


def graph_data_from_events(events, profile_name, year):
    return getJsonGraphData(
        pd.DataFrame(event_rows(events)),
        profile_name,
        display_year(year),
    )


def event_signature(events):
    signature = events.aggregate(
        event_count=Count("id"),
        latest_event_at=Max("started_at"),
    )
    return {
        "event_count": int(signature["event_count"] or 0),
        "latest_event_at": signature["latest_event_at"],
    }


def profile_comparisons_from_dataframe(dataframe, profile_name, year):
    comparison_df = dataframe.copy()
    if not is_all_years(year):
        if "year" in comparison_df.columns:
            comparison_df = comparison_df[
                comparison_df["year"] == int(year)
            ]
        else:
            comparison_df["parsed_start_time"] = pd.to_datetime(
                comparison_df["Start Time"],
                errors="coerce",
            )
            comparison_df = comparison_df[
                comparison_df["parsed_start_time"].dt.year == int(year)
            ]
    if comparison_df.empty:
        return {}
    return getProfileComparisonData(
        comparison_df,
        profile_name,
        display_year(year),
    )


def profile_comparisons(user, profile_name, year):
    events = ViewingEvent.objects.filter(profile__user=user)
    if not is_all_years(year):
        events = events.filter(started_at__year=int(year))
    if not events.exists():
        return {}
    return getProfileComparisonData(
        pd.DataFrame(event_rows(events)),
        profile_name,
        display_year(year),
    )


def saved_or_generated_recap(user, profile, events, profile_name, year):
    year_key = recap_year_key(year)
    signature = event_signature(events)
    recap = YearlyRecap.objects.filter(
        user=user,
        profile=profile,
        year=year_key,
    ).first()

    if (
        recap
        and recap.event_count == signature["event_count"]
        and recap.latest_event_at == signature["latest_event_at"]
        and "title_level_insights" in recap.data
        and "wrapped_cards" in recap.data
        and recap.data.get("schema_version") == GRAPH_SCHEMA_VERSION
    ):
        return recap.data

    graph_data = graph_data_from_events(events, profile_name, year)
    graph_data["profile_comparisons"] = profile_comparisons(
        user,
        profile_name,
        year,
    )
    YearlyRecap.objects.update_or_create(
        user=user,
        profile=profile,
        year=year_key,
        defaults={
            "data": graph_data,
            "event_count": signature["event_count"],
            "latest_event_at": signature["latest_event_at"],
        },
    )
    return graph_data


def repair_cached_graph_data(
    cached_result,
    owner,
    job_id,
    profile_name,
    year,
):
    required_sections = {
        "profile_comparisons",
        "wrapped_cards",
        "title_level_insights",
    }
    if not job_id or required_sections.issubset(cached_result):
        return cached_result

    cached_upload = cache.get(upload_cache_key(owner, job_id))
    if not cached_upload:
        return cached_result

    upload_data = json.loads(cached_upload)
    dataframe = pd.read_json(
        io.StringIO(upload_data["dataframe_json"]),
        orient="records",
    )
    profile_year_df = filter_profile_year(
        dataframe,
        profile_name,
        year,
    )
    if profile_year_df.empty:
        return cached_result

    repaired = getJsonGraphData(profile_year_df, profile_name, year)
    repaired["profile_comparisons"] = profile_comparisons_from_dataframe(
        dataframe,
        profile_name,
        year,
    )
    cache.set(
        result_cache_key(owner, profile_name, year),
        repaired,
        timeout=ANONYMOUS_CACHE_TTL_SECONDS,
    )
    return repaired


def comparison_summary(graph_data):
    core = graph_data.get("core_stats", {})
    genres = graph_data.get("genre_content_insights", {}).get(
        "genre_watchtime",
        [],
    )
    titles = graph_data.get("total_title_watchtime", [])
    return {
        "total_watchtime_hours": core.get("total_watchtime_hours", 0),
        "total_viewing_events": core.get("total_viewing_events", 0),
        "unique_titles": core.get("unique_titles", 0),
        "unique_movies": core.get("unique_movies", 0),
        "unique_shows": core.get("unique_shows", 0),
        "longest_watch_streak_days": core.get(
            "longest_watch_streak_days",
            0,
        ),
        "top_genres": genres[:5],
        "top_titles": titles[:5],
    }


def year_comparison_payload(year_a, graph_a, year_b, graph_b):
    summary_a = comparison_summary(graph_a)
    summary_b = comparison_summary(graph_b)
    metrics = [
        "total_watchtime_hours",
        "total_viewing_events",
        "unique_titles",
        "unique_movies",
        "unique_shows",
        "longest_watch_streak_days",
    ]
    deltas = {
        metric: round(
            float(summary_b.get(metric, 0))
            - float(summary_a.get(metric, 0)),
            2,
        )
        for metric in metrics
    }
    return {
        "year_a": int(year_a),
        "year_b": int(year_b),
        "summary_a": summary_a,
        "summary_b": summary_b,
        "deltas": deltas,
        "monthly_watchtime": {
            "year_a": graph_a.get("monthly_watchtime", []),
            "year_b": graph_b.get("monthly_watchtime", []),
        },
    }

import pandas as pd
import os
import json
import logging
import string
from time import perf_counter

from utils.workflows import (
    K_NETFLIX_TITLES,
    dataframeSetUp,
    generateMediaType,
    generateRatings,
    generateShowTitles,
    getMonthlyWatchtimeData,
    getMostWatchedRatingsData,
    getTotalTitleWatchtimeData,
    getTotalTypeWatchtimeData,
    preprocessTitles,
)
from utils.recap_payload import DEFAULT_RECAP_SECTIONS, build_recap_payload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_SCHEMA_VERSION = 5
METADATA_OVERRIDES_CACHE = None
logger = logging.getLogger(__name__)
COUNTRY_CODE_LABELS = {
    "US": "United States",
    "KR": "South Korea",
    "JP": "Japan",
    "GB": "United Kingdom",
    "CA": "Canada",
    "CN": "China",
    "FR": "France",
    "DE": "Germany",
    "IN": "India",
    "ES": "Spain",
}


def _round_number(value, digits=2):
    if pd.isna(value):
        return 0
    return round(float(value), digits)


def _format_hour(hour):
    hour = int(hour)
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour} {suffix}"


def _daypart_for_hour(hour):
    hour = int(hour)
    if hour < 6:
        return "Late night", 0
    if hour < 12:
        return "Morning", 1
    if hour < 18:
        return "Afternoon", 2
    return "Evening", 3


def _longest_date_streak(dates):
    if len(dates) == 0:
        return 0

    unique_dates = sorted(pd.to_datetime(pd.Series(dates)).dt.date.unique())
    longest = 1
    current = 1

    for index in range(1, len(unique_dates)):
        if (unique_dates[index] - unique_dates[index - 1]).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return longest


def _metadata_for_title(title):
    if not title or title == "Unknown":
        return {}

    matches = K_NETFLIX_TITLES[K_NETFLIX_TITLES["title"] == title]
    if matches.empty:
        normalized = preprocessTitles(str(title).strip().lower())
        matches = K_NETFLIX_TITLES[K_NETFLIX_TITLES["normalized title"] == normalized]
    if matches.empty:
        return {}
    return matches.iloc[0].to_dict()


def _manual_metadata_for_title(title):
    global METADATA_OVERRIDES_CACHE
    if METADATA_OVERRIDES_CACHE is None:
        overrides_path = os.path.join(BASE_DIR, "title_metadata_overrides.json")
        try:
            with open(overrides_path, "r", encoding="utf-8") as handle:
                METADATA_OVERRIDES_CACHE = json.load(handle)
        except FileNotFoundError:
            METADATA_OVERRIDES_CACHE = {}
    normalized = str(title).strip().lower().translate(
        str.maketrans({char: " " for char in string.punctuation})
    )
    return METADATA_OVERRIDES_CACHE.get(" ".join(normalized.split()), {})


def _split_genres(value):
    if isinstance(value, list):
        return [genre for genre in value if genre] or ["Unknown"]
    if pd.isna(value) or not value:
        return ["Unknown"]
    return [genre.strip() for genre in str(value).split(",") if genre.strip()] or ["Unknown"]


def _cached_value(row, column, fallback=""):
    value = row.get(column, fallback)
    if isinstance(value, list):
        return value or fallback
    if pd.isna(value) or value == "":
        return fallback
    return value


def _release_period(value):
    if pd.isna(value):
        return "Unknown"
    try:
        year = int(value)
        start = year // 5 * 5
        return f"{start}-{start + 4}"
    except (TypeError, ValueError):
        return "Unknown"


def _runtime_bucket(media_type, duration):
    if pd.isna(duration) or not duration:
        return "Unknown"

    duration = str(duration)
    if "Season" in duration:
        return "Series"
    if "min" not in duration:
        return "Unknown"

    try:
        minutes = int(duration.split(" ")[0])
    except (TypeError, ValueError):
        return "Unknown"

    if minutes < 30:
        return "Short"
    if minutes < 60:
        return "Episode-length"
    if media_type == "Movie":
        return "Movie-length"
    return "Long-form"


def _runtime_bucket_from_minutes(media_type, minutes):
    if pd.isna(minutes) or not minutes:
        return "Unknown"
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return "Unknown"

    if minutes < 30:
        return "Short"
    if minutes < 60:
        return "Episode-length"
    if media_type == "Movie":
        return "Movie-length"
    return "Long-form"


def _metadata_country_from_codes(codes):
    if isinstance(codes, list) and codes:
        return COUNTRY_CODE_LABELS.get(str(codes[0]).upper(), codes[0])
    return None


def _metadata_country_label(value):
    if isinstance(value, list):
        return _metadata_country_from_codes(value) or "Unknown"
    if pd.isna(value) or not value:
        return "Unknown"
    country = str(value).split(",")[0].strip()
    return COUNTRY_CODE_LABELS.get(country.upper(), country)


def enrichWithTitleMetadata(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()
    metadata_rows = working_df["New Title"].apply(_metadata_for_title)
    manual_metadata_rows = working_df["New Title"].apply(_manual_metadata_for_title)

    working_df["Genres"] = working_df.apply(
        lambda row: _split_genres(
            _cached_value(
                row,
                "Metadata Genres",
                manual_metadata_rows.loc[row.name].get("genres") or metadata_rows.loc[row.name].get("listed_in"),
            )
        ),
        axis=1,
    )
    working_df["Primary Genre"] = working_df["Genres"].apply(lambda genres: genres[0])
    working_df["Release Year"] = working_df.apply(
        lambda row: _cached_value(
            row,
            "Metadata Release Year",
            manual_metadata_rows.loc[row.name].get("release_year") or metadata_rows.loc[row.name].get("release_year"),
        ),
        axis=1,
    )
    working_df["Release Period"] = working_df["Release Year"].apply(_release_period)
    working_df["Metadata Country"] = working_df.apply(
        lambda row: _cached_value(
            row,
            "Metadata Origin Countries",
            manual_metadata_rows.loc[row.name].get("origin_countries") or metadata_rows.loc[row.name].get("country"),
        ),
        axis=1,
    )
    working_df["Metadata Country"] = working_df["Metadata Country"].apply(
        lambda value: _metadata_country_from_codes(value)
        if isinstance(value, list)
        else _metadata_country_label(value)
    )
    working_df["Runtime Bucket"] = working_df.apply(
        lambda row: (
            _runtime_bucket_from_minutes(row.get("Type"), row.get("Metadata Runtime Minutes"))
            if row.get("Metadata Runtime Minutes")
            else _runtime_bucket(metadata_rows.loc[row.name].get("type"), metadata_rows.loc[row.name].get("duration"))
        ),
        axis=1,
    )
    working_df["Poster URL"] = working_df.apply(
        lambda row: _cached_value(row, "Metadata Poster URL", manual_metadata_rows.loc[row.name].get("poster_url") or ""),
        axis=1,
    )
    return working_df


def _poster_for_title(df: pd.DataFrame, title: str) -> str:
    if not title or "Poster URL" not in df.columns:
        return ""
    series_match = df["Series Title"] == title if "Series Title" in df.columns else False
    matches = df[(df["New Title"] == title) | series_match]
    if len(matches) == 0:
        return ""
    posters = matches["Poster URL"].dropna()
    posters = posters[posters.astype(str).str.strip() != ""]
    return str(posters.iloc[0]) if len(posters) else ""


def _top_title_posters(df: pd.DataFrame, limit=5) -> list:
    if "Poster URL" not in df.columns:
        return []
    grouped = (
        df.groupby("New Title", as_index=False)
        .agg(
            hrs=("Watchtime (hrs)", "sum"),
            poster_url=("Poster URL", lambda values: next(
                (str(value) for value in values if pd.notna(value) and str(value).strip()),
                "",
            )),
        )
        .sort_values("hrs", ascending=False)
    )
    grouped = grouped[grouped["poster_url"] != ""].head(limit)
    return [
        {
            "title": row["New Title"],
            "hrs": _round_number(row["hrs"]),
            "poster_url": row["poster_url"],
        }
        for _, row in grouped.iterrows()
    ]


def _month_label(month):
    return pd.Timestamp(year=2000, month=int(month), day=1).strftime("%B")


def _watching_personality(df):
    avg_session_minutes = df["Watchtime (hrs)"].mean() * 60
    night_hours = df[df["Start Time"].dt.hour >= 21]["Watchtime (hrs)"].sum()
    weekend_hours = df[df["Start Time"].dt.dayofweek >= 5]["Watchtime (hrs)"].sum()
    total_hours = df["Watchtime (hrs)"].sum() or 1

    if night_hours / total_hours >= 0.35:
        return {
            "value": "The Late-Night Binger",
            "description": "Your queue comes alive after dark.",
        }
    if weekend_hours / total_hours >= 0.45:
        return {
            "value": "The Weekend Marathoner",
            "description": "You save your biggest sessions for days off.",
        }
    if avg_session_minutes < 20:
        return {
            "value": "The Snack Watcher",
            "description": "Short sessions, frequent check-ins, low commitment.",
        }
    return {
        "value": "The Steady Streamer",
        "description": "Consistent sessions define your Netflix rhythm.",
    }


def getWrappedCardsData(df: pd.DataFrame) -> dict:
    working_df = enrichWithTitleMetadata(df)
    working_df["Started Date"] = working_df["Start Time"].dt.date

    title_insights = getTitleLevelInsightsData(working_df)
    core_stats = getCoreStatsData(working_df)

    comfort_show = None
    if title_insights.get("rewatched_favorites"):
        top_rewatch = title_insights["rewatched_favorites"][0]
        comfort_show = {
            "value": top_rewatch["title"],
            "description": f"{top_rewatch['watch_count']} watches across {top_rewatch['active_days']} active days.",
            "poster_url": _poster_for_title(working_df, top_rewatch["title"]),
        }
    elif title_insights.get("top_shows"):
        top_show = title_insights["top_shows"][0]
        comfort_show = {
            "value": top_show["show"],
            "description": f"{top_show['hrs']} hours watched.",
            "poster_url": _poster_for_title(working_df, top_show["show"]),
        }

    month_grouped = (
        working_df.groupby("Month", as_index=False)
        .agg(
            hrs=("Watchtime (hrs)", "sum"),
            titles=("New Title", "nunique"),
            genres=("Primary Genre", "nunique"),
        )
    )
    month_grouped["chaos_score"] = month_grouped["hrs"] + month_grouped["titles"] * 0.75 + month_grouped["genres"] * 1.5
    chaotic_month = month_grouped.sort_values("chaos_score", ascending=False).iloc[0]

    genre_era_df = (
        working_df.groupby(["Primary Genre", "Release Period"], as_index=False)["Watchtime (hrs)"]
        .sum()
        .sort_values("Watchtime (hrs)", ascending=False)
    )
    top_genre_era = genre_era_df.iloc[0] if len(genre_era_df) else None

    binge_days = 0
    total_active_days = max(working_df["Started Date"].nunique(), 1)
    if len(working_df):
        binge_days = int(
            working_df.groupby("Started Date").size().loc[lambda values: values >= 3].count()
        )
    binge_rate = binge_days / total_active_days
    binge_percentile = min(99, max(1, round(45 + binge_rate * 95)))

    cards = {
        "watching_personality": _watching_personality(working_df),
        "comfort_show": comfort_show or {
            "value": core_stats["longest_session"]["title"],
            "description": "Your longest single session title.",
        },
        "peak_couch_hour": {
            "value": core_stats["most_active_hour"]["label"],
            "description": f"{core_stats['most_active_hour']['hours']} hours watched in this hour.",
        },
        "most_chaotic_month": {
            "value": _month_label(chaotic_month["Month"]),
            "description": f"{int(chaotic_month['titles'])} titles, {int(chaotic_month['genres'])} genres, {round(float(chaotic_month['hrs']), 2)} hours.",
        },
        "top_genre_era": {
            "value": f"{top_genre_era['Release Period']} {top_genre_era['Primary Genre']}" if top_genre_era is not None else "Unknown",
            "description": f"{_round_number(top_genre_era['Watchtime (hrs)'])} hours watched." if top_genre_era is not None else "Not enough metadata yet.",
        },
        "binge_watcher_percentile": {
            "value": f"Top {100 - binge_percentile}% binge watcher",
            "description": f"{binge_days} binge days out of {total_active_days} active days.",
            "percentile": binge_percentile,
        },
        "shareable_recap": {
            "total_watchtime_hours": core_stats["total_watchtime_hours"],
            "unique_titles": core_stats["unique_titles"],
        },
        "top_title_posters": _top_title_posters(working_df),
    }
    return cards


def getCoreStatsData(df: pd.DataFrame) -> dict:
    working_df = df.copy()
    working_df["Started Date"] = working_df["Start Time"].dt.date
    working_df["Day Of Week"] = working_df["Start Time"].dt.day_name()
    working_df["Hour"] = working_df["Start Time"].dt.hour

    total_watchtime = _round_number(working_df["Watchtime (hrs)"].sum())
    total_events = int(len(working_df))
    unique_titles = int(working_df["New Title"].nunique())
    unique_movies = int(working_df[working_df["Type"] == "Movie"]["New Title"].nunique())
    unique_shows = int(working_df[working_df["Type"] == "TV Show"]["New Title"].nunique())
    average_session_minutes = _round_number(working_df["Watchtime (hrs)"].mean() * 60)

    longest_row = working_df.sort_values("Watchtime (hrs)", ascending=False).iloc[0]
    first_row = working_df.sort_values("Start Time", ascending=True).iloc[0]
    last_row = working_df.sort_values("Start Time", ascending=False).iloc[0]

    active_day = (
        working_df.groupby("Day Of Week")["Watchtime (hrs)"]
        .sum()
        .sort_values(ascending=False)
    )
    active_hour = (
        working_df.groupby("Hour")["Watchtime (hrs)"]
        .sum()
        .sort_values(ascending=False)
    )
    title_counts = working_df.groupby("New Title").size()

    short_watch_count = int((working_df["Watchtime (hrs)"] < (5 / 60)).sum())
    likely_finished_count = int((working_df["Watchtime (hrs)"] >= (20 / 60)).sum())

    return {
        "total_watchtime_hours": total_watchtime,
        "total_viewing_events": total_events,
        "unique_titles": unique_titles,
        "unique_movies": unique_movies,
        "unique_shows": unique_shows,
        "average_session_minutes": average_session_minutes,
        "longest_session": {
            "title": str(longest_row["New Title"]),
            "minutes": _round_number(longest_row["Watchtime (hrs)"] * 60),
            "hours": _round_number(longest_row["Watchtime (hrs)"]),
        },
        "longest_watch_streak_days": _longest_date_streak(working_df["Started Date"]),
        "most_active_day": {
            "day": str(active_day.index[0]),
            "hours": _round_number(active_day.iloc[0]),
        },
        "most_active_hour": {
            "hour": int(active_hour.index[0]),
            "label": _format_hour(active_hour.index[0]),
            "hours": _round_number(active_hour.iloc[0]),
        },
        "first_watched_title": {
            "title": str(first_row["New Title"]),
            "date": first_row["Start Time"].date().isoformat(),
        },
        "last_watched_title": {
            "title": str(last_row["New Title"]),
            "date": last_row["Start Time"].date().isoformat(),
        },
        "rewatched_titles": int((title_counts > 1).sum()),
        "short_watch_count": short_watch_count,
        "likely_finished_count": likely_finished_count,
    }


def _group_watchtime_records(df, group_keys, rename_map, limit=None):
    grouped = (
        df.groupby(group_keys, as_index=False)["Watchtime (hrs)"]
        .sum()
        .sort_values("Watchtime (hrs)", ascending=False)
    )
    if limit:
        grouped = grouped.head(limit)

    records = []
    for _, row in grouped.iterrows():
        record = {target: row[source] for source, target in rename_map.items()}
        record["hrs"] = _round_number(row["Watchtime (hrs)"])
        records.append(record)
    return records


def _prefer_known_rows(df, column):
    if column not in df.columns:
        return df
    known = df[df[column] != "Unknown"]
    return known if len(known) else df


def _title_group_records(df, group_keys, rename_map, limit=None, include_counts=True):
    grouped = (
        df.groupby(group_keys, as_index=False)
        .agg(
            hrs=("Watchtime (hrs)", "sum"),
            watch_count=("Watchtime (hrs)", "size"),
            active_days=("Start Time", lambda values: values.dt.date.nunique()),
        )
        .sort_values(["hrs", "watch_count"], ascending=[False, False])
    )
    if limit:
        grouped = grouped.head(limit)

    records = []
    for _, row in grouped.iterrows():
        record = {target: row[source] for source, target in rename_map.items()}
        record["hrs"] = _round_number(row["hrs"])
        if include_counts:
            record["watch_count"] = int(row["watch_count"])
            record["active_days"] = int(row["active_days"])
        records.append(record)
    return records


def getTitleLevelInsightsData(df: pd.DataFrame) -> dict:
    working_df = df.copy()
    working_df["Series Title"] = working_df.get("Series Title", working_df["New Title"]).fillna(working_df["New Title"])
    working_df["Season Label"] = working_df.get("Season Label", "").fillna("")
    working_df["Episode Title"] = working_df.get("Episode Title", "").fillna("")
    working_df["Is Episode"] = working_df.get("Is Episode", False).fillna(False).astype(bool)
    working_df["Started Date"] = working_df["Start Time"].dt.date

    shows_df = working_df[
        (working_df["Type"] == "TV Show") | (working_df["Is Episode"])
    ].copy()
    movies_df = working_df[working_df["Type"] == "Movie"].copy()

    top_titles = _title_group_records(
        working_df,
        ["New Title", "Type"],
        {"New Title": "title", "Type": "type"},
        limit=10,
    )
    top_shows = _title_group_records(
        shows_df,
        ["Series Title"],
        {"Series Title": "show"},
        limit=10,
    ) if len(shows_df) else []
    top_movies = _title_group_records(
        movies_df,
        ["New Title"],
        {"New Title": "movie"},
        limit=10,
    ) if len(movies_df) else []

    episodes_per_show = []
    if len(shows_df):
        episode_grouped = (
            shows_df.groupby("Series Title", as_index=False)
            .agg(
                episodes=("Episode Title", lambda values: int(values.replace("", pd.NA).dropna().nunique())),
                watches=("Episode Title", "size"),
                hrs=("Watchtime (hrs)", "sum"),
            )
            .sort_values(["episodes", "watches", "hrs"], ascending=[False, False, False])
            .head(10)
        )
        episodes_per_show = [
            {
                "show": row["Series Title"],
                "episodes": int(row["episodes"] or row["watches"]),
                "watches": int(row["watches"]),
                "hrs": _round_number(row["hrs"]),
            }
            for _, row in episode_grouped.iterrows()
        ]

    season_watchtime = []
    season_df = shows_df[shows_df["Season Label"] != ""]
    if len(season_df):
        season_grouped = (
            season_df.groupby(["Series Title", "Season Label"], as_index=False)
            .agg(
                hrs=("Watchtime (hrs)", "sum"),
                watch_count=("Watchtime (hrs)", "size"),
                active_days=("Start Time", lambda values: values.dt.date.nunique()),
            )
            .sort_values("hrs", ascending=False)
            .head(12)
        )
        season_watchtime = [
            {
                "show": row["Series Title"],
                "season": row["Season Label"],
                "label": f"{row['Series Title']} - {row['Season Label']}",
                "hrs": _round_number(row["hrs"]),
                "watch_count": int(row["watch_count"]),
                "active_days": int(row["active_days"]),
            }
            for _, row in season_grouped.iterrows()
        ]

    most_binged_series = []
    if len(shows_df):
        binge_grouped = (
            shows_df.groupby(["Series Title", "Started Date"], as_index=False)
            .agg(
                episode_watches=("Episode Title", "size"),
                hrs=("Watchtime (hrs)", "sum"),
            )
            .sort_values(["episode_watches", "hrs"], ascending=[False, False])
        )
        best_binge_by_show = (
            binge_grouped.sort_values(["Series Title", "episode_watches", "hrs"], ascending=[True, False, False])
            .drop_duplicates("Series Title")
            .sort_values(["episode_watches", "hrs"], ascending=[False, False])
            .head(10)
        )
        most_binged_series = [
            {
                "show": row["Series Title"],
                "date": row["Started Date"].isoformat(),
                "episode_watches": int(row["episode_watches"]),
                "hrs": _round_number(row["hrs"]),
            }
            for _, row in best_binge_by_show.iterrows()
        ]

    rewatch_grouped = (
        working_df.groupby(["New Title", "Type"], as_index=False)
        .agg(
            watch_count=("Watchtime (hrs)", "size"),
            hrs=("Watchtime (hrs)", "sum"),
            active_days=("Start Time", lambda values: values.dt.date.nunique()),
        )
    )
    rewatched = rewatch_grouped[rewatch_grouped["watch_count"] > 1].copy()
    rewatched = rewatched.sort_values(["watch_count", "hrs"], ascending=[False, False]).head(10)
    rewatched_favorites = [
        {
            "title": row["New Title"],
            "type": row["Type"],
            "watch_count": int(row["watch_count"]),
            "repeat_watches": int(row["watch_count"] - 1),
            "active_days": int(row["active_days"]),
            "hrs": _round_number(row["hrs"]),
        }
        for _, row in rewatched.iterrows()
    ]

    hidden_obsession = rewatched_favorites[0] if rewatched_favorites else None

    return {
        "top_titles": top_titles,
        "top_shows": top_shows,
        "top_movies": top_movies,
        "most_binged_series": most_binged_series,
        "episodes_per_show": episodes_per_show,
        "season_watchtime": season_watchtime,
        "rewatched_favorites": rewatched_favorites,
        "hidden_obsession": hidden_obsession,
    }


def getGenreContentInsightsData(df: pd.DataFrame) -> dict:
    working_df = enrichWithTitleMetadata(df)
    exploded_genres = working_df.explode("Genres")
    known_genres = _prefer_known_rows(exploded_genres, "Genres")
    known_periods = _prefer_known_rows(working_df, "Release Period")
    known_countries = _prefer_known_rows(working_df, "Metadata Country")
    known_runtime = _prefer_known_rows(working_df, "Runtime Bucket")
    known_ratings = _prefer_known_rows(working_df, "Rating")

    top_genre_by_month = []
    monthly_genres = (
        exploded_genres.groupby(["Month", "Genres"], as_index=False)["Watchtime (hrs)"]
        .sum()
        .sort_values(["Month", "Watchtime (hrs)"], ascending=[True, False])
    )
    for month, month_df in monthly_genres.groupby("Month"):
        month_df = _prefer_known_rows(month_df, "Genres")
        top = month_df.iloc[0]
        top_genre_by_month.append({
            "month": int(month),
            "month_label": _month_label(month),
            "genre": str(top["Genres"]),
            "hrs": _round_number(top["Watchtime (hrs)"]),
        })

    return {
        "genre_watchtime": _group_watchtime_records(
            known_genres,
            ["Genres"],
            {"Genres": "genre"},
            limit=12,
        ),
        "genre_by_month": _group_watchtime_records(
            known_genres,
            ["Month", "Genres"],
            {"Month": "month", "Genres": "genre"},
        ),
        "top_genre_by_month": top_genre_by_month,
        "release_period_watchtime": _group_watchtime_records(
            known_periods,
            ["Release Period"],
            {"Release Period": "period"},
            limit=10,
        ),
        "release_decade_watchtime": _group_watchtime_records(
            known_periods,
            ["Release Period"],
            {"Release Period": "decade"},
            limit=10,
        ),
        "country_watchtime": _group_watchtime_records(
            known_countries,
            ["Metadata Country"],
            {"Metadata Country": "country"},
            limit=10,
        ),
        "runtime_preference": _group_watchtime_records(
            known_runtime,
            ["Runtime Bucket"],
            {"Runtime Bucket": "bucket"},
        ),
        "rating_watchtime": getMostWatchedRatingsData(known_ratings),
    }


def getVisualizationData(df: pd.DataFrame) -> dict:
    working_df = enrichWithTitleMetadata(df)
    working_df["Started Date"] = working_df["Start Time"].dt.date
    working_df["Date"] = working_df["Started Date"].apply(lambda value: value.isoformat())
    working_df["Day Of Week"] = working_df["Start Time"].dt.day_name()
    working_df["Day Index"] = working_df["Start Time"].dt.dayofweek
    working_df["Hour"] = working_df["Start Time"].dt.hour
    working_df[["Daypart", "Daypart Index"]] = working_df["Hour"].apply(
        lambda hour: pd.Series(_daypart_for_hour(hour))
    )
    working_df["Month Label"] = working_df["Month"].apply(_month_label)

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    daypart_order = ["Late night", "Morning", "Afternoon", "Evening"]

    day_totals = (
        working_df.groupby(["Day Of Week", "Day Index"], as_index=False)["Watchtime (hrs)"]
        .sum()
        .sort_values("Day Index")
    )
    day_of_week = [
        {
            "day": row["Day Of Week"],
            "day_index": int(row["Day Index"]),
            "hrs": _round_number(row["Watchtime (hrs)"]),
        }
        for _, row in day_totals.iterrows()
    ]

    hour_totals = working_df.groupby("Hour", as_index=False)["Watchtime (hrs)"].sum()
    hour_lookup = {int(row["Hour"]): row["Watchtime (hrs)"] for _, row in hour_totals.iterrows()}
    hour_of_day = [
        {
            "hour": hour,
            "label": _format_hour(hour),
            "hrs": _round_number(hour_lookup.get(hour, 0)),
        }
        for hour in range(24)
    ]

    daypart_totals = (
        working_df.groupby(
            ["Day Of Week", "Day Index", "Daypart", "Daypart Index"],
            as_index=False,
        )["Watchtime (hrs)"]
        .sum()
    )
    daypart_lookup = {
        (int(row["Day Index"]), int(row["Daypart Index"])): row["Watchtime (hrs)"]
        for _, row in daypart_totals.iterrows()
    }
    daypart_by_day = [
        {
            "day": day,
            "day_index": day_index,
            "daypart": daypart,
            "daypart_index": daypart_index,
            "hrs": _round_number(daypart_lookup.get((day_index, daypart_index), 0)),
        }
        for day_index, day in enumerate(day_order)
        for daypart_index, daypart in enumerate(daypart_order)
    ]

    calendar_totals = working_df.groupby("Date", as_index=False)["Watchtime (hrs)"].sum()
    calendar = [
        {
            "date": row["Date"],
            "hrs": _round_number(row["Watchtime (hrs)"]),
        }
        for _, row in calendar_totals.sort_values("Date").iterrows()
    ]

    daily_timeline = calendar

    monthly_type_df = (
        working_df.groupby(["Month", "Month Label", "Type"], as_index=False)["Watchtime (hrs)"]
        .sum()
        .sort_values(["Month", "Type"])
    )
    movie_show_by_month = [
        {
            "month": row["Month Label"],
            "month_number": int(row["Month"]),
            "type": row["Type"],
            "hrs": _round_number(row["Watchtime (hrs)"]),
        }
        for _, row in monthly_type_df.iterrows()
    ]

    title_rows = (
        working_df.groupby(["New Title", "Primary Genre", "Type"], as_index=False)["Watchtime (hrs)"]
        .sum()
        .sort_values("Watchtime (hrs)", ascending=False)
    )
    title_bubbles = [
        {
            "title": row["New Title"],
            "genre": row["Primary Genre"],
            "type": row["Type"],
            "hrs": _round_number(row["Watchtime (hrs)"]),
        }
        for _, row in title_rows.head(60).iterrows()
    ]

    genre_title_rows = (
        working_df.groupby(["Primary Genre", "New Title"], as_index=False)["Watchtime (hrs)"]
        .sum()
        .sort_values("Watchtime (hrs)", ascending=False)
    )
    treemap = [
        {
            "genre": row["Primary Genre"],
            "title": row["New Title"],
            "hrs": _round_number(row["Watchtime (hrs)"]),
        }
        for _, row in genre_title_rows.head(120).iterrows()
    ]

    active_dates = set(working_df["Started Date"].unique())
    streak_dates = []
    for active_date in sorted(active_dates):
        before = active_date - pd.Timedelta(days=1)
        after = active_date + pd.Timedelta(days=1)
        if before in active_dates or after in active_dates:
            streak_dates.append(active_date.isoformat())

    return {
        "day_order": day_order,
        "daypart_order": daypart_order,
        "day_of_week_heatmap": day_of_week,
        "hour_of_day_heatmap": hour_of_day,
        "daypart_by_day_heatmap": daypart_by_day,
        "calendar_heatmap": calendar,
        "movie_show_by_month": movie_show_by_month,
        "watchtime_timeline": daily_timeline,
        "title_bubbles": title_bubbles,
        "treemap": treemap,
        "streak_calendar": {
            "days": calendar,
            "streak_dates": streak_dates,
            "longest_streak_days": _longest_date_streak(working_df["Started Date"]),
        },
    }


def getProfileComparisonData(dataframe: pd.DataFrame, selected_profile: str, year: int) -> dict:
    df = dataframeSetUp(dataframe)
    if len(df) == 0:
        return {}

    df = generateShowTitles(df)
    df = generateMediaType(df)
    df = generateRatings(df)

    profile_watchtime = _group_watchtime_records(
        df,
        ["Profile Name"],
        {"Profile Name": "profile"},
    )

    type_split_df = (
        df.groupby(["Profile Name", "Type"], as_index=False)["Watchtime (hrs)"]
        .sum()
        .sort_values(["Profile Name", "Watchtime (hrs)"], ascending=[True, False])
    )
    movie_show_split = [
        {
            "profile": row["Profile Name"],
            "type": row["Type"],
            "hrs": _round_number(row["Watchtime (hrs)"]),
        }
        for _, row in type_split_df.iterrows()
    ]

    profile_titles = {
        profile: set(profile_df["New Title"].dropna().unique())
        for profile, profile_df in df.groupby("Profile Name")
    }
    selected_titles = profile_titles.get(selected_profile, set())

    shared_titles = []
    all_title_profiles = {}
    for profile, titles in profile_titles.items():
        for title in titles:
            all_title_profiles.setdefault(title, set()).add(profile)
    for title, profiles in all_title_profiles.items():
        if len(profiles) > 1:
            shared_titles.append({
                "title": title,
                "profiles": sorted(profiles),
                "profile_count": len(profiles),
            })

    unique_title_counts = []
    for profile, titles in profile_titles.items():
        other_titles = set().union(
            *[other_titles for other_profile, other_titles in profile_titles.items() if other_profile != profile]
        ) if len(profile_titles) > 1 else set()
        unique_title_counts.append({
            "profile": profile,
            "unique_titles": len(titles - other_titles),
            "total_titles": len(titles),
        })

    overlap_scores = []
    for profile, titles in profile_titles.items():
        if profile == selected_profile:
            continue
        union = selected_titles | titles
        overlap_scores.append({
            "profile": profile,
            "overlap_score": _round_number(len(selected_titles & titles) / len(union) * 100 if union else 0),
            "shared_titles": len(selected_titles & titles),
        })

    profile_similarity_links = []
    profile_names = sorted(profile_titles.keys())
    for source_index, source_profile in enumerate(profile_names):
        for target_profile in profile_names[source_index + 1:]:
            source_titles = profile_titles[source_profile]
            target_titles = profile_titles[target_profile]
            union = source_titles | target_titles
            shared_count = len(source_titles & target_titles)
            profile_similarity_links.append({
                "source": source_profile,
                "target": target_profile,
                "similarity": _round_number(shared_count / len(union) * 100 if union else 0),
                "shared_titles": shared_count,
            })

    household_timeline_df = (
        df.groupby(["Profile Name", "Month"], as_index=False)["Watchtime (hrs)"]
        .sum()
        .sort_values(["Profile Name", "Month"])
    )
    household_timeline = [
        {
            "profile": row["Profile Name"],
            "month": int(row["Month"]),
            "hrs": _round_number(row["Watchtime (hrs)"]),
        }
        for _, row in household_timeline_df.iterrows()
    ]

    radar_rows = []
    profile_genre_type_df = enrichWithTitleMetadata(df)
    profile_genre_type_df = profile_genre_type_df.explode("Genres")
    for profile, profile_df in df.groupby("Profile Name"):
        title_set = set(profile_df["New Title"].dropna().unique())
        total_hrs = profile_df["Watchtime (hrs)"].sum()
        event_count = len(profile_df)
        movie_hrs = profile_df.loc[profile_df["Type"] == "Movie", "Watchtime (hrs)"].sum()
        show_hrs = profile_df.loc[profile_df["Type"] == "TV Show", "Watchtime (hrs)"].sum()
        active_days = profile_df["Start Time"].dt.date.nunique()
        radar_rows.append({
            "profile": profile,
            "watchtime_hours": _round_number(total_hrs),
            "unique_titles": len(title_set),
            "viewing_events": event_count,
            "movie_hours": _round_number(movie_hrs),
            "show_hours": _round_number(show_hrs),
            "active_days": int(active_days),
        })

    sankey_grouped = (
        profile_genre_type_df.groupby(["Profile Name", "Genres", "Type"], as_index=False)["Watchtime (hrs)"]
        .sum()
        .sort_values("Watchtime (hrs)", ascending=False)
    )
    sankey = [
        {
            "profile": row["Profile Name"],
            "genre": row["Genres"],
            "type": row["Type"],
            "hrs": _round_number(row["Watchtime (hrs)"]),
        }
        for _, row in sankey_grouped.head(80).iterrows()
    ]

    most_unique_profile = None
    if unique_title_counts:
        most_unique_profile = max(unique_title_counts, key=lambda item: item["unique_titles"])

    return {
        "year": "all" if str(year).lower() == "all" else int(year),
        "selected_profile": selected_profile,
        "profile_watchtime": profile_watchtime,
        "movie_show_split": movie_show_split,
        "shared_titles": sorted(shared_titles, key=lambda item: item["profile_count"], reverse=True)[:20],
        "unique_title_counts": sorted(unique_title_counts, key=lambda item: item["unique_titles"], reverse=True),
        "overlap_scores": sorted(overlap_scores, key=lambda item: item["overlap_score"], reverse=True),
        "profile_similarity_links": sorted(
            profile_similarity_links,
            key=lambda item: item["similarity"],
            reverse=True,
        ),
        "most_unique_profile": most_unique_profile,
        "household_timeline": household_timeline,
        "radar_metrics": radar_rows,
        "sankey_profile_genre_type": sankey,
    }

def getJsonGraphData(dataframe, user, year, sections=None):
    context = {
        "profile": user,
        "year": str(year),
        "input_rows": len(dataframe),
    }
    total_start = perf_counter()
    logger.info("recap generation started", extra=context)

    setup_start = perf_counter()
    df = dataframeSetUp(dataframe)
    setup_ms = round((perf_counter() - setup_start) * 1000, 2)
    logger.info(
        "recap dataframe setup completed",
        extra={**context, "output_rows": len(df), "elapsed_ms": setup_ms},
    )
    
    if len(df) == 0:
        return {"error": "No data found after processing"}

    transform_start = perf_counter()
    df = generateShowTitles(df)
    df = generateMediaType(df)
    df = generateRatings(df)
    transform_ms = round((perf_counter() - transform_start) * 1000, 2)
    logger.info(
        "recap dataframe transforms completed",
        extra={**context, "elapsed_ms": transform_ms},
    )

    requested_sections = set(sections or DEFAULT_RECAP_SECTIONS)
    builders = {
        "total_title_watchtime": lambda: getTotalTitleWatchtimeData(df),
        "total_type_watchtime": lambda: getTotalTypeWatchtimeData(df),
        "monthly_watchtime": lambda: getMonthlyWatchtimeData(df),
        "ratings_watchtime": lambda: getMostWatchedRatingsData(df),
        "core_stats": lambda: getCoreStatsData(df),
        "title_level_insights": lambda: getTitleLevelInsightsData(df),
        "wrapped_cards": lambda: getWrappedCardsData(df),
        "genre_content_insights": lambda: getGenreContentInsightsData(df),
        "visualizations": lambda: getVisualizationData(df),
    }
    
    try:
        graphs = {
            "schema_version": GRAPH_SCHEMA_VERSION,
            **build_recap_payload(builders, requested_sections, context=context),
        }
    except Exception as exc:
        logger.exception(
            "recap graph generation failed",
            extra={**context, "sections": sorted(requested_sections)},
        )
        return {"error": f"Failed to generate graph data: {str(exc)}"}

    graphs["_timings_ms"]["dataframe_setup"] = setup_ms
    graphs["_timings_ms"]["dataframe_transforms"] = transform_ms
    graphs["_timings_ms"]["total"] = round((perf_counter() - total_start) * 1000, 2)
    logger.info(
        "recap generation completed",
        extra={**context, "elapsed_ms": graphs["_timings_ms"]["total"]},
    )
    
    return graphs

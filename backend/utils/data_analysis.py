from rest_framework.response import Response
from utils.workflows import *
import pandas as pd
import os


def _round_number(value, digits=2):
    if pd.isna(value):
        return 0
    return round(float(value), digits)


def _format_hour(hour):
    hour = int(hour)
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour} {suffix}"


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
        return {}
    return matches.iloc[0].to_dict()


def _split_genres(value):
    if pd.isna(value) or not value:
        return ["Unknown"]
    return [genre.strip() for genre in str(value).split(",") if genre.strip()] or ["Unknown"]


def _release_decade(value):
    if pd.isna(value):
        return "Unknown"
    try:
        year = int(value)
        return f"{year // 10 * 10}s"
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


def enrichWithTitleMetadata(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()
    metadata_rows = working_df["New Title"].apply(_metadata_for_title)

    working_df["Genres"] = metadata_rows.apply(lambda row: _split_genres(row.get("listed_in")))
    working_df["Primary Genre"] = working_df["Genres"].apply(lambda genres: genres[0])
    working_df["Release Year"] = metadata_rows.apply(lambda row: row.get("release_year"))
    working_df["Release Decade"] = working_df["Release Year"].apply(_release_decade)
    working_df["Metadata Country"] = metadata_rows.apply(
        lambda row: "Unknown" if pd.isna(row.get("country")) or not row.get("country") else str(row.get("country")).split(",")[0].strip()
    )
    working_df["Runtime Bucket"] = metadata_rows.apply(
        lambda row: _runtime_bucket(row.get("type"), row.get("duration"))
    )
    return working_df


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


def getGenreContentInsightsData(df: pd.DataFrame) -> dict:
    working_df = enrichWithTitleMetadata(df)
    exploded_genres = working_df.explode("Genres")

    top_genre_by_month = []
    monthly_genres = (
        exploded_genres.groupby(["Month", "Genres"], as_index=False)["Watchtime (hrs)"]
        .sum()
        .sort_values(["Month", "Watchtime (hrs)"], ascending=[True, False])
    )
    for month, month_df in monthly_genres.groupby("Month"):
        top = month_df.iloc[0]
        top_genre_by_month.append({
            "month": int(month),
            "genre": str(top["Genres"]),
            "hrs": _round_number(top["Watchtime (hrs)"]),
        })

    return {
        "genre_watchtime": _group_watchtime_records(
            exploded_genres,
            ["Genres"],
            {"Genres": "genre"},
            limit=12,
        ),
        "genre_by_month": _group_watchtime_records(
            exploded_genres,
            ["Month", "Genres"],
            {"Month": "month", "Genres": "genre"},
        ),
        "top_genre_by_month": top_genre_by_month,
        "release_decade_watchtime": _group_watchtime_records(
            working_df,
            ["Release Decade"],
            {"Release Decade": "decade"},
            limit=10,
        ),
        "country_watchtime": _group_watchtime_records(
            working_df,
            ["Metadata Country"],
            {"Metadata Country": "country"},
            limit=10,
        ),
        "runtime_preference": _group_watchtime_records(
            working_df,
            ["Runtime Bucket"],
            {"Runtime Bucket": "bucket"},
        ),
        "rating_watchtime": getMostWatchedRatingsData(working_df),
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
        "most_unique_profile": most_unique_profile,
        "household_timeline": household_timeline,
    }

def getJsonGraphData(dataframe, user, year):
    print(f"Received user: {user}, year: {year}")
    print(f"Pre-filtered dataframe rows: {len(dataframe)}")

    # Since we're receiving pre-filtered data from ExtractCSVView,
    # we can skip the filtering steps and just do the setup
    
    # Set up the dataframe (this should not filter, just transform)
    df = dataframeSetUp(dataframe)
    print(f"After dataframeSetUp rows: {len(df)}")

    # Skip filterUser and filterYear since data is already filtered
    # in ExtractCSVView for performance
    
    if len(df) == 0:
        return {"error": "No data found after processing"}

    # Apply transformations
    df = generateShowTitles(df)
    df = generateMediaType(df)
    df = generateRatings(df)

    # Generate all graphs
    graphs = {}
    
    try:
        graphs["total_title_watchtime"] = getTotalTitleWatchtimeData(df)
        graphs["total_type_watchtime"] = getTotalTypeWatchtimeData(df)
        graphs["monthly_watchtime"] = getMonthlyWatchtimeData(df)
        graphs["ratings_watchtime"] = getMostWatchedRatingsData(df)
        graphs["core_stats"] = getCoreStatsData(df)
        graphs["genre_content_insights"] = getGenreContentInsightsData(df)
    except Exception as e:
        print(f"Error generating graph data: {str(e)}")
        return {"error": f"Failed to generate graph data: {str(e)}"}
    
    return graphs


##### CONSOLE
def runConsoleDataAnalysis(filename):
    df = readData()
    df = dataframeSetUp(df)

    df = startTimeManipulation(df)
    df = convertDurationToHrs(df)
    df = filterUserConsole(df)
    createYearlyWatchtimeGraph(df)
    df = filterYearConsole(df)

    df = generateShowTitles(df)
    df = generateMediaType(df)
    df = generateRatings(df)

    # Graph data
    createTotalTitleWatchtimeGraph(df)
    createTotalTypeWatchtimeGraph(df)
    createMonthlyWatchtimeGraph(df)
    createMostWatchedRatingsGraph(df)

    getResults(df)


def getUserYearsData(filename):
    df = readData(filename)
    df = startTimeManipulation(df)
    users = getUsers(df)
    user_years_data = {}
    for user in users:
        user_years_data[user] = getUserActiveYears(df, user)

    return user_years_data

def readData(filename):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  
    # get backend folder path (one level up)
    backend_dir = os.path.dirname(BASE_DIR)
    # build path to uploads folder in backend
    file_path = os.path.join(backend_dir, 'uploads', filename)
    
    df = pd.read_csv(file_path)
    return df


def selectUserConsole(df: pd.DataFrame) -> str:
    print("Who's viewing data would you like to see?")
    print(getUsers(df))
    userIndex = int(input()) - 1

    return getUsers(df)[userIndex]
    
def selectYearConsole(df: pd.DataFrame) -> int:
    print("Which Year would you like to view?")
    print(getYears(df))
    yearIndex = int(input()) - 1

    return getYears(df)[yearIndex]

def filterUserConsole(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["Profile Name"] == selectUserConsole(df)]

    return df

def filterYearConsole(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["Year"] == selectYearConsole(df)]

    return df

def getUserActiveYears(df: pd.DataFrame, name: str) -> dict:
    df = df[df["Profile Name"] == name]

    return getYears(df)

def getResults(df):
    print("NETFLIX Recap:")
    print("In "  + str(df['Year'].unique()[0]) + ", you watched " + str(getTotalWatchtime(df)) + " hours of Netflix content, and "
          + str(getTotalUniqueTitlesWatched(df)) + " unique pieces of content!")
    print("You watched " + str(getNumOfUniqueMoviesWatched(df)) + " movies and " + str(getNumOfUniqueShowsWatched(df)) + " TV shows!")

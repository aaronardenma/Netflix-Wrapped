import string
import pandas as pd
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(BASE_DIR, 'netflix_titles.csv')



K_NETFLIX_TITLES = pd.read_csv(csv_path)
K_NETFLIX_TITLES['normalized title'] = (
    K_NETFLIX_TITLES['title']
    .astype(str)
    .str.strip()
    .str.lower()
    .apply(lambda value: value.translate(str.maketrans('', '', string.punctuation)))
)
K_TITLE_BY_NORMALIZED = (
    K_NETFLIX_TITLES
    .drop_duplicates('normalized title')
    .set_index('normalized title')['title']
    .to_dict()
)
K_TYPE_BY_TITLE = (
    K_NETFLIX_TITLES
    .drop_duplicates('title')
    .set_index('title')['type']
    .to_dict()
)
K_RATING_BY_TITLE = (
    K_NETFLIX_TITLES
    .drop_duplicates('title')
    .set_index('title')['rating']
    .fillna('Unknown')
    .to_dict()
)

K_TYPE_BY_NORMALIZED = (
    K_NETFLIX_TITLES
    .drop_duplicates('normalized title')
    .set_index('normalized title')['type']
    .to_dict()
)

SEASON_LABEL_PATTERN = re.compile(
    r"^(Season\s+\d+|Series\s+\d+|Book\s+(\d+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)|"
    r"Volume\s+\d+|Part\s+(\d+|I|II|III|IV|V|VI|VII|VIII|IX|X)|Limited Series|Collection)$",
    re.IGNORECASE,
)
EPISODE_NUMBER_PATTERN = re.compile(r"\(Episode\s+(\d+)\)", re.IGNORECASE)
SUPPLEMENTAL_DESCRIPTOR_PATTERN = re.compile(
    r"\b("
    r"trailer|teaser|clip|cinemagraph|hook|promo|promotional|preview|recap|bumper|"
    r"cliffhanger|character intro|genre specific moment|high context|inciting incident|"
    r"informative|main character|moment of high emotion|plot|relatable|sensory|"
    r"supporting character|villain|antagonist|conflict|comedy"
    r")\b",
    re.IGNORECASE,
)

# Read in Personal Viewing Data & Kaggle Netflix Dataset
def dataframeSetUp(df: pd.DataFrame) -> pd.DataFrame:
    # Remove non traditional media from DataFrame (Promos, Trailers)
    df = df[df['Supplemental Video Type'].isna()]
    
    # Drop unneeded columns
    df = df.drop(columns= ['Attributes', 'Bookmark', 'Latest Bookmark'])

    df = preserveTitleParts(df)

    # Manipulate Title column to remove season and episode information
    df['Title'] = df['Title'].apply(splitSecondOccurence)

    df = startTimeManipulation(df)
    df = convertDurationToHrs(df)

    return df


def _canonical_title_for(value: str) -> str:
    normalized = preprocessTitles(str(value).strip().lower())
    return K_TITLE_BY_NORMALIZED.get(normalized, str(value).strip())


def _metadata_type_for(value: str) -> str:
    normalized = preprocessTitles(str(value).strip().lower())
    canonical = K_TITLE_BY_NORMALIZED.get(normalized, str(value).strip())
    return K_TYPE_BY_TITLE.get(canonical) or K_TYPE_BY_NORMALIZED.get(normalized) or "Unknown"


def _season_label_index(parts: list[str]) -> int | None:
    return next(
        (index for index, part in enumerate(parts[1:], start=1) if SEASON_LABEL_PATTERN.match(part)),
        None,
    )


def _is_supplemental_descriptor(part: str) -> bool:
    stripped = str(part).strip()
    return bool(
        SUPPLEMENTAL_DESCRIPTOR_PATTERN.search(stripped)
        or SEASON_LABEL_PATTERN.match(stripped)
        or re.match(r"^(Season|Series|Book|Part|Volume)\s+[\w\d]+(?:\s+.*)?$", stripped, re.IGNORECASE)
    )


def extractSupplementalContentTitle(title: str) -> str:
    raw_title = str(title).strip()
    parts = [part.strip() for part in raw_title.split(":") if part.strip()]
    if len(parts) <= 1:
        return raw_title

    for index in range(len(parts) - 1, 0, -1):
        candidate = ": ".join(parts[:index]).strip()
        if _metadata_type_for(candidate) != "Unknown":
            return _canonical_title_for(candidate)

    for index in range(1, len(parts)):
        candidate = ": ".join(parts[index:]).strip()
        if _metadata_type_for(candidate) != "Unknown":
            return _canonical_title_for(candidate)

    content_start = 0
    while content_start < len(parts) - 1 and _is_supplemental_descriptor(parts[content_start]):
        content_start += 1

    if content_start > 0:
        return ": ".join(parts[content_start:]).strip()

    return splitSecondOccurence(raw_title).strip() or raw_title


def parseNetflixTitleParts(title: str) -> dict:
    raw_title = str(title).strip()
    parts = [part.strip() for part in raw_title.split(":") if part.strip()]
    season_index = _season_label_index(parts)
    episode_number_match = EPISODE_NUMBER_PATTERN.search(raw_title)
    candidate_series_title = (
        ": ".join(parts[:season_index]).strip()
        if season_index is not None
        else splitSecondOccurence(raw_title).strip()
    )
    canonical_candidate = _canonical_title_for(candidate_series_title)
    metadata_type = _metadata_type_for(candidate_series_title)

    score = 0
    score += 5 if metadata_type == "TV Show" else 0
    score -= 5 if metadata_type == "Movie" else 0
    score += 4 if episode_number_match else 0
    score += 3 if season_index is not None else 0

    if season_index is None:
        parsed_type = "TV Show" if score >= 5 else "Movie" if score <= -3 else metadata_type
        return {
            "Raw Title": raw_title,
            "Series Title": canonical_candidate,
            "Season Label": "",
            "Episode Title": "",
            "Episode Number": None,
            "Is Episode": False,
            "Parsed Media Type": parsed_type,
            "Classification Confidence": min(0.99, max(0.35, abs(score) / 10)) if parsed_type != "Unknown" else 0.25,
            "Classification Source": "metadata" if metadata_type != "Unknown" else "title-pattern",
        }

    season_label = parts[season_index]
    episode_parts = parts[season_index + 1:]
    episode_title = ": ".join(episode_parts).strip()
    parsed_type = "TV Show" if score >= 5 else "Movie" if score <= -3 else "Unknown"
    source = "metadata+episode-pattern" if metadata_type != "Unknown" else "episode-pattern"

    return {
        "Raw Title": raw_title,
        "Series Title": canonical_candidate,
        "Season Label": season_label,
        "Episode Title": episode_title,
        "Episode Number": int(episode_number_match.group(1)) if episode_number_match else None,
        "Is Episode": parsed_type == "TV Show" and bool(episode_number_match),
        "Parsed Media Type": parsed_type,
        "Classification Confidence": min(0.99, max(0.35, abs(score) / 10)) if parsed_type != "Unknown" else 0.35,
        "Classification Source": source,
    }


def preserveTitleParts(df: pd.DataFrame) -> pd.DataFrame:
    title_parts = df["Title"].apply(parseNetflixTitleParts).apply(pd.Series)
    for column in title_parts.columns:
        if column in df.columns:
            existing = df[column]
            missing = existing.isna() | (existing.astype(str).str.strip() == "")
            df.loc[missing, column] = title_parts.loc[missing, column]
        else:
            df[column] = title_parts[column]
    return df


# Manipulate Start Time column to gain new columns: Year, Month
def startTimeManipulation(df: pd.DataFrame) -> pd.DataFrame:
    # Convert 'Start Time' to Datetime format
    df['Start Time'] = pd.to_datetime(df['Start Time'])

    # Create Date column from Start Time column
    df['Date'] = df['Start Time'].dt.strftime('%Y-%m-%d')

    # Create Year column from Start Time column
    df['Year'] = df['Start Time'].dt.strftime('%Y').astype(int)

    # Create Month column from Start Time column
    df['Month'] = df['Start Time'].dt.strftime('%m').astype(int)

    return df

# Clean Title column values dependent on title order construction by delimieter
def splitSecondOccurence(str: str) -> str:
    splitList = [part.strip() for part in str.split(":") if part.strip()]
    if len(splitList) <= 1:
        return splitList[0] if splitList else ""

    season_index = _season_label_index(splitList)
    if season_index is not None:
        return ": ".join(splitList[:season_index])

    return ": ".join(splitList)

# Convert Duration Column Format to an hr columns
def convertDurationToHrs(df: pd.DataFrame) -> pd.DataFrame:
    df['Duration'] = df['Duration'].astype(str)

    hr = df['Duration'].str.split(':').str[0].astype(int)
    min = df['Duration'].str.split(':').str[1].astype(int)
    sec = df['Duration'].str.split(':').str[2].astype(int)

    df['Watchtime (hrs)'] = hr + min/60 + sec/3600
        
    return df

# Create new column for more specific Netflix Titles
def generateShowTitles(df: pd.DataFrame) -> pd.DataFrame:
    df['Title'] = df['Title'].astype(str)
    df['Title'] = df['Title'].str.strip()
    normalized_titles = df['Title'].str.lower().apply(preprocessTitles)
    df['New Title'] = normalized_titles.map(K_TITLE_BY_NORMALIZED).fillna(df['Title'])
    if 'Is Episode' in df.columns and 'Series Title' in df.columns:
        episode_mask = df['Is Episode'].fillna(False).astype(bool)
        df.loc[episode_mask, 'New Title'] = df.loc[episode_mask, 'Series Title']

    return df

# Preprocess Netflix Titles by removing punctuation for better matching
def preprocessTitles(text: str) -> str:
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text

# Create new column for Netflix Media Types for content pieces
def generateMediaType(df: pd.DataFrame) -> pd.DataFrame:
    df['Type'] = df['New Title'].map(K_TYPE_BY_TITLE).fillna("Unknown")
    if 'Cached Media Type' in df.columns:
        cached_type = df['Cached Media Type'].fillna("").replace({
            "movie": "Movie",
            "tv_show": "TV Show",
            "unknown": "Unknown",
        })
        cached_mask = cached_type.isin(["Movie", "TV Show"])
        df.loc[cached_mask, 'Type'] = cached_type[cached_mask]
    if 'Parsed Media Type' in df.columns:
        parsed_type = df['Parsed Media Type'].fillna("Unknown")
        confidence = df['Classification Confidence'].fillna(0) if 'Classification Confidence' in df.columns else 0
        df.loc[df['Type'] == "Unknown", 'Type'] = parsed_type[df['Type'] == "Unknown"]
        high_confidence_tv = (
            (parsed_type == "TV Show")
            & (confidence >= 0.7)
        )
        df.loc[high_confidence_tv, 'Type'] = "TV Show"

    return df
        

# Get Rating Type
def generateRatings(df: pd.DataFrame) -> pd.DataFrame:
    df['Rating'] = df['New Title'].map(K_RATING_BY_TITLE).fillna("Unknown")
    if 'Metadata Rating' in df.columns:
        cached_rating = df['Metadata Rating'].fillna("")
        df.loc[cached_rating != "", 'Rating'] = cached_rating[cached_rating != ""]

    return df

### GRAPH CREATION

# Get Most watched Ratings Categories

def getMostWatchedRatings(df: pd.DataFrame) -> pd.DataFrame:
    filtered_df = df[['Rating', 'Watchtime (hrs)']]
    sum_watched_ratings = (filtered_df.groupby(by = ["Rating"], as_index=False)
                           .sum()
                           .sort_values(by= ['Watchtime (hrs)'], ascending = False))
    
    return sum_watched_ratings

# Get most watched ratings data
def getMostWatchedRatingsData(df: pd.DataFrame) -> dict:
    ratings_list = getMostWatchedRatings(df)['Rating'].tolist()
    watchtime_list = getMostWatchedRatings(df)['Watchtime (hrs)'].tolist()

    data = []

    for i in range(len(ratings_list)):
        data.append({
            'rating': ratings_list[i],
            'hrs': watchtime_list[i]
        })
    return data
    # return {'ratings' : ratings_list,
    #         'watchtime': watchtime_list}

def getTitleWatchtime(df: pd.DataFrame) -> pd.DataFrame:
    filtered_title_df = df[['Title', 'Watchtime (hrs)']]
    sum_title_watchtime_df = (filtered_title_df.groupby(by = ['Title'], as_index=False)
                        .sum()
                        .sort_values(by= ['Watchtime (hrs)'], ascending= False)
                        .rename(columns={'Watchtime (hrs)': 'Total Watchtime (hrs)'}))
    return sum_title_watchtime_df

# Get Total Title Watchtime Data
def getTotalTitleWatchtimeData(df: pd.DataFrame) -> dict:
    newdf = getTitleWatchtime(df).head(10)
    titles = newdf['Title'].tolist()
    watchtime = newdf['Total Watchtime (hrs)'].apply(lambda x: round(x, 2)).tolist()

    data = []

    for i in range(len(titles)):
        data.append({
            'title': titles[i],
            'hrs': watchtime[i]
        })
    return data 
    # return {'titles': titles,
    #         'watchtime': watchtime}

# Get total watchtime per media type
def getTotalTypeWatchtime(df: pd.DataFrame) -> pd.DataFrame:
    filtered_type_df = df[['Type', 'Watchtime (hrs)']]

    sum_type_watchtime_df = (filtered_type_df.groupby(by=['Type'], as_index=False)
                            .sum()
                            .sort_values(by= ['Watchtime (hrs)'], ascending = False)
                            .rename(columns = {'Watchtime (hrs)': 'Total Watchtime (hrs)'}))
    return sum_type_watchtime_df

def getTotalTypeWatchtimeData(df: pd.DataFrame) -> dict:
    types = getTotalTypeWatchtime(df)['Type'].tolist()
    total_watchtime = getTotalTypeWatchtime(df)['Total Watchtime (hrs)'].sum()
    watchtime = getTotalTypeWatchtime(df)['Total Watchtime (hrs)'].apply(lambda x: round(x/total_watchtime *100, 2)).tolist()

    data = []
    for i in range(len(types)):
        data.append({
            'type': types[i],
            'hrs': watchtime[i]
        })
    return data

# Get Netflix watchtime per month
def getMonthlyWatchtime(df: pd.DataFrame) -> pd.DataFrame:
    filtered_df = df[['Month', 'Watchtime (hrs)']]
    monthly_watchtime = filtered_df.groupby(by=['Month'], as_index = False).sum()

    return monthly_watchtime


def getMonthlyWatchtimeData(df: pd.DataFrame) -> dict:
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    monthly_df = getMonthlyWatchtime(df)  # has columns 'Month', 'Watchtime (hrs)'

    # Create a dict mapping month number to watchtime
    month_to_watchtime = {row['Month']: row['Watchtime (hrs)'] for _, row in monthly_df.iterrows()}

    data = []
    for i, month_name in enumerate(months, start=1):  # i from 1 to 12
        hrs = month_to_watchtime.get(i, 0)  # default 0 if no data for that month
        data.append({
            'month': month_name,
            'hrs': hrs
        })
    return data

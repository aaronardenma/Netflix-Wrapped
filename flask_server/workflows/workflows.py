import string
import pandas as pd
import plotly.express as px
import nltk


K_NETFLIX_TITLES = pd.read_csv('workflows/netflix_titles.csv')

# Read in Personal Viewing Data & Kaggle Netflix Dataset
def dataframeSetUp(df: pd.DataFrame) -> pd.DataFrame:
    # Remove non traditional media from DataFrame (Promos, Trailers)
    df = df[df['Supplemental Video Type'].isna()]
    
    # Drop unneeded columns
    df = df.drop(columns= ['Attributes', 'Bookmark', 'Latest Bookmark'])

    # Manipulate Title column to remove season and episode information
    df['Title'] = df['Title'].apply(splitSecondOccurence)

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
    splitList = str.split(":")
    if (len(splitList) <= 1):
        return splitList[0]
    elif not ("Season" in splitList[1]):
        return splitList[0] + splitList[1]
    else:
        return splitList[0]

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
    titles = df['Title'].str.lower()

    kaggleTitles = K_NETFLIX_TITLES['title'].str.strip()
    kaggleTitles = K_NETFLIX_TITLES['title'].str.lower()

    df['New Title'] = ""
    df['New Title'] = df['New Title'].astype(str)
    
    df['preprocessed titles'] = titles.apply(preprocessTitles)
    df['tokenized titles'] = df['preprocessed titles'].apply(lambda x: set(nltk.word_tokenize(x)))
    K_NETFLIX_TITLES['preprocessed kaggle titles'] = kaggleTitles.apply(preprocessTitles)
    K_NETFLIX_TITLES['tokenized kaggle titles'] = K_NETFLIX_TITLES['preprocessed kaggle titles'].apply(lambda x: set(nltk.word_tokenize(x)))

    for index, row in K_NETFLIX_TITLES.iterrows():
        kaggleTitle_tokens = set(row['tokenized kaggle titles'])
        
        # Find matches where all tokens from tokenized kaggle titles are in the tokenized titles
        matches = df[df['tokenized titles'].apply(lambda x: kaggleTitle_tokens.issubset(x))]
        
        if not matches.empty:
            for match_index, match_row in matches.iterrows():
                # Check if the new title match is longer than the old one
                if len(row['title']) > len(match_row['New Title']):
                    df.loc[match_index, 'New Title'] = row['title']
    df['New Title'] = df['New Title'].replace("", "Unknown")

    return df

# Preprocess Netflix Titles by removing punctuation for better matching
def preprocessTitles(text: str) -> str:
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text

# Create new column for Netflix Media Types for content pieces
def generateMediaType(df: pd.DataFrame) -> pd.DataFrame:
    kaggleTitles = K_NETFLIX_TITLES['title']
    kaggleTypes = K_NETFLIX_TITLES['type']

    df['Type'] = ""
    df['Type'] = df['Type'].astype(str)

    for idx, kaggleTitle in enumerate(kaggleTitles):
        # Normalize titles
        kaggleTitle = kaggleTitle.strip()

        # Partial matching
        matches = df[df['New Title'] == kaggleTitle]
        
        # Assigning values
        if (len(matches) > 0):
            df.loc[matches.index, 'Type'] = kaggleTypes[idx]
    df['Type'] = df['Type'].replace("", "Unknown")

    return df
        

# Get Rating Type
def generateRatings(df: pd.DataFrame) -> pd.DataFrame:
    kaggleTitles = K_NETFLIX_TITLES['title']
    kaggleRatings = K_NETFLIX_TITLES['rating']

    df['Rating'] = ""
    df['Rating'] = df['Rating'].astype(str)

    for idx, kaggleTitle in enumerate(kaggleTitles):
        # Normalize titles
        kaggleTitle = kaggleTitle.strip()

        # Partial matching
        matches = df[df['New Title'] == kaggleTitle]
        
        # Assigning values
        if (len(matches) > 0):
            df.loc[matches.index, 'Rating'] = kaggleRatings[idx]
    df['Rating'] = df['Rating'].replace("", "Unknown")

    return df

# Get Most watched Ratings Categories

def getMostWatchedRatings(df: pd.DataFrame) -> pd.DataFrame:
    filtered_df = df[['Rating', 'Watchtime (hrs)']]
    sum_watched_ratings = (filtered_df.groupby(by = ["Rating"], as_index=False)
                           .sum()
                           .sort_values(by= ['Watchtime (hrs)'], ascending = False))
    
    return sum_watched_ratings

# Create bar graph for Top 3 Most watched movie/tv show ratings 
def createMostWatchedRatingsGraph(df: pd.DataFrame):
    mostWatchedRatingsDf = getMostWatchedRatings(df)

    mostWatchedRatingsDf = mostWatchedRatingsDf.drop(mostWatchedRatingsDf[mostWatchedRatingsDf['Rating'] == 'Unknown'].index)

    chart = px.bar(mostWatchedRatingsDf.head(10), x= 'Rating', y = 'Watchtime (hrs)',
                labels={'Rating': 'Content Rating'},
                title = 'Most Watched Movie/TV Show Ratings')
    
    chart.update_xaxes(title_font = {"size": 16})
    chart.update_yaxes(tick0 = 0, rangemode="tozero", title_font = {"size": 16})
    chart.update_layout(title={
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top',
        'font': {'size': 20}})

    # chart.show()

    return chart.to_html(full_html=False)

# Get total watchtime per Netflix title

def totalTitleWatchtime(df: pd.DataFrame) -> pd.DataFrame:
    filtered_title_df = df[['New Title', 'Watchtime (hrs)']]
    sum_title_watchtime_df = (filtered_title_df.groupby(by = ['New Title'], as_index=False)
                        .sum()
                        .sort_values(by= ['Watchtime (hrs)'], ascending= False)
                        .rename(columns={'Watchtime (hrs)': 'Total Watchtime (hrs)'}))
    return sum_title_watchtime_df


# Create bar graph for Top 10 Most watched netflix titles 
def createTotalTitleWatchtimeGraph(df: pd.DataFrame):
    totalTitleWatchtimeDf = totalTitleWatchtime(df)

    totalTitleWatchtimeDf = totalTitleWatchtimeDf.drop(totalTitleWatchtimeDf[totalTitleWatchtimeDf['New Title'] == 'Unknown'].index)

    chart = px.bar(totalTitleWatchtimeDf.head(10), x= 'New Title', y = 'Total Watchtime (hrs)',
                labels={'New Title': 'Netflix Title'},
                title = 'Top 10 Most Watched Netflix Titles', hover_name='New Title')
    
    chart.update_xaxes(title_font = {"size": 16})
    chart.update_yaxes(tick0 = 0, rangemode="tozero", title_font = {"size": 16})
    chart.update_layout(title={
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top',
        'font': {'size': 20}})
    
    # chart.show()

    return chart.to_html(full_html=False)


# Get total watchtime per media type
def totalTypeWatchtime(df: pd.DataFrame) -> pd.DataFrame:
    filtered_type_df = df[['Type', 'Watchtime (hrs)']]

    sum_type_watchtime_df = (filtered_type_df.groupby(by=['Type'], as_index=False)
                            .sum()
                            .sort_values(by= ['Watchtime (hrs)'], ascending = False)
                            .rename(columns = {'Watchtime (hrs)': 'Total Watchtime (hrs)'}))
    return sum_type_watchtime_df

# Create pie graph for difference in watchtime for media types watched
def createTotalTypeWatchtimeGraph(df: pd.DataFrame):
    totalTypeWatchtimeDf = totalTypeWatchtime(df)

    totalTypeWatchtimeDf = totalTypeWatchtimeDf.drop(totalTypeWatchtimeDf[totalTypeWatchtimeDf['Type'] == 'Unknown'].index)

    chart = px.pie(totalTypeWatchtimeDf, names= 'Type', values= 'Total Watchtime (hrs)', color='Type', 
               labels={'Total Watchtime (hrs)': 'Hours Watched (hrs)', 'Type': 'Media Type'},
               title = 'Types of Media Watched')
    
    chart.update_traces(textfont_size=18, textfont_color= 'white')
    
    chart.update_layout(title={
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top',
        'font': {'size': 24}}, 
        legend={'x': 0.9,
                'xanchor': 'center',
                'y': 0.5, 
                'yanchor': 'middle',
                'font': {'size': 16}})

    # chart.show()

    return chart.to_html(full_html = False)


# Get Total Netflix Watch Time Watched
def getTotalWatchtime(df: pd.DataFrame) -> float:
    total_hrs_watched = df['Watchtime (hrs)'].sum().round(2)

    return total_hrs_watched


# Get Netflix watchtime per month
def getWatchTimePerMonth(df: pd.DataFrame) -> pd.DataFrame:
    filtered_df = df[['Month', 'Watchtime (hrs)']]
    monthly_watchtime = filtered_df.groupby(by=['Month'], as_index = False).sum()

    return monthly_watchtime


# Create Line Graph for Monthly Watchtime
def createMonthlyWatchtimeGraph(df: pd.DataFrame):
    monthlyWatchtime = getWatchTimePerMonth(df)
    print(monthlyWatchtime)
    chart = px.line(monthlyWatchtime, x = 'Month', y = 'Watchtime (hrs)', title = 'Netflix Hourly Watchtime per Month')
    chart.update_xaxes(tick0=1, dtick=1, title_standoff = 25, title_font = {"size": 16},
                       tickmode='array',
                       tickvals=[1,2,3,4,5,6,7,8,9,10,11,12],
                       ticktext=['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'],
                       range=[1, 12])
    chart.update_yaxes(tick0 = 0, title_standoff = 25, title_font = {"size": 16}, rangemode="tozero")
    chart.update_layout(title={
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top',
        'font': {'size': 20}})
    
    # chart.show()

    return chart.to_html(full_html = False)

# Get Netflix watchtime per year
def getWatchTimePerYear(df: pd.DataFrame) -> pd.DataFrame:
    filtered_df = df[['Year', 'Watchtime (hrs)']]
    yearly_watchtime = filtered_df.groupby(by=['Year'], as_index = False).sum()

    return yearly_watchtime


# Create Line Graph for Monthly Watchtime
def createYearlyWatchtimeGraph(df: pd.DataFrame):
    yearly_watchtime = getWatchTimePerYear(df)
    chart = px.line(yearly_watchtime, x = 'Year', y = 'Watchtime (hrs)', title = 'Netflix Hourly Watchtime per Year')
    chart.update_xaxes(tick0=1, dtick=1, title_standoff = 25, title_font = {"size": 16})
    chart.update_yaxes(tick0 = 0, title_standoff = 25, title_font = {"size": 16}, rangemode="tozero")
    chart.update_layout(title={
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top',
        'font': {'size': 20}})
    
    # chart.show()

    return chart.to_html(full_html = False)


# Number of Unique Titles Watched
def getTotalUniqueTitlesWatched(df: pd.DataFrame) -> int:
    return len(df['New Title'].unique())

def getNumOfUniqueShowsWatched(df: pd.DataFrame) -> int:
    df = df[df["Type"] == "TV Show"]
    return len(df['New Title'].unique())

def getNumOfUniqueMoviesWatched(df:pd.DataFrame) -> int:
    df = df[df["Type"] == "Movie"]
    return len(df['New Title'].unique())

# Get Years of Data included
def getYears(df: pd.DataFrame) -> list:
    return df['Year'].unique().tolist()

# Get Netflix Users
def getUsers(df: pd.DataFrame) -> list:
    return df['Profile Name'].unique().tolist()
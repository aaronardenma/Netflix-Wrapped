from rest_framework.response import Response
from utils.workflows import *
import pandas as pd
import os

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
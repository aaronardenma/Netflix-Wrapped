from src.workflows import *
import pandas as pd

def getJsonGraphData(filename, user, year):
    df = readData(filename)
    df = dataframeSetUp(df)

    df = filterUser(df, user)
    df = filterYear(df, year)

    df = generateShowTitles(df)
    df = generateMediaType(df)
    df = generateRatings(df)

    # Graph Data
    graphs = {}
    graphs["total_title_watchtime"] = getTotalTitleWatchtimeData(df)
    graphs["total_type_watchtime"] = getTotalTypeWatchtimeData(df)
    graphs["monthly_watchtime"] = getMonthlyWatchtimeData(df)
    graphs["ratings_watchtime"] = getMostWatchedRatingsData(df)
    
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
    df = pd.read_csv("/Users/aaronma/Desktop/Netflix Wrapped/flask_server/uploads/" + filename)
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
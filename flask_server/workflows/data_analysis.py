from workflows.workflows import *
import pandas as pd

def runDataAnalysis(filename):
    df = readData(filename)
    df = dataframeSetUp(df)

    df = startTimeManipulation(df)
    df = convertDurationToHrs(df)
    df = filterUser(df)
    createYearlyWatchtimeGraph(df)
    df = filterYear(df)

    df = generateShowTitles(df)
    df = generateMediaType(df)
    df = generateRatings(df)

    # Graph Creation
    graphs = []
    graphs.append(createTotalTitleWatchtimeGraph(df))
    graphs.append(createTotalTypeWatchtimeGraph(df))
    graphs.append(createMonthlyWatchtimeGraph(df))
    graphs.append(createMostWatchedRatingsGraph(df))
    
    return graphs
    # getResults(df)

def getUserYearsData(filename):
    df = readData(filename)
    df = startTimeManipulation(df)
    users = getUsers(df)
    user_years_data = {}
    for user in users:
        user_years_data[user] = getUserActiveYears(df, user)

    return user_years_data

def readData(filename):
    df = pd.read_csv("uploads/" + filename)
    return df

def selectUser(df: pd.DataFrame) -> str:
    print("Who's viewing data would you like to see?")
    print(getUsers(df))
    userIndex = int(input()) - 1

    return getUsers(df)[userIndex]
    
def selectYear(df: pd.DataFrame) -> int:
    print("Which Year would you like to view?")
    print(getYears(df))
    yearIndex = int(input()) - 1

    return getYears(df)[yearIndex]

def filterUser(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["Profile Name"] == selectUser(df)]

    return df

def filterYear(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["Year"] == selectYear(df)]

    return df

def getUserActiveYears(df: pd.DataFrame, name: str) -> dict:
    df = df[df["Profile Name"] == name]

    return getYears(df)

def getResults(df):
    print("NETFLIX Recap:")
    print("In "  + str(df['Year'].unique()[0]) + ", you watched " + str(getTotalWatchtime(df)) + " hours of Netflix content, and "
          + str(getTotalUniqueTitlesWatched(df)) + " unique pieces of content!")
    print("You watched " + str(getNumOfUniqueMoviesWatched(df)) + " movies and " + str(getNumOfUniqueShowsWatched(df)) + " TV shows!")
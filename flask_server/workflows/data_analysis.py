from workflows import *
import pandas as pd

def runDataAnalysis(file):
    df = readData(file)
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

def readData(file):
    df = pd.read_csv(file)
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

def getResults(df):
    print("NETFLIX Recap:")
    print("In "  + str(df['Year'].unique()[0]) + ", you watched " + str(getTotalWatchtime(df)) + " hours of Netflix content, and "
          + str(getTotalUniqueTitlesWatched(df)) + " unique pieces of content!")
    print("You watched " + str(getNumOfUniqueMoviesWatched(df)) + " movies and " + str(getNumOfUniqueShowsWatched(df)) + " TV shows!")
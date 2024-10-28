# Netflix-Wrapped

**Netflix Wrapped** is a work in progress web app that allows Netflix users to visualize their viewing data as provided by Netflix. 

## Current Features:
* Input .csv Netflix viewing data and view select rechart graphs
* View pandas generated dataframes with Plotly through console

## Features To Be Added:
* Add more variety graphs
* Allow user created graphs
* Include drag-and-drop form input

## This web app uses:
* Flask framework
* React framework
* recharts
* Axios
* pandas
* numPy
* Plotly

## How this app works
This web app is created using a React framework as the frontend and Flask framework as the backend. The frontend and backend exist on different domains and are subject to CORS/cross origin resource sharing.

When the web app is first loaded by the user, the user gets to submit .csv files of particular format centered around Netflix distributed viewing data schemas. This submits a POST request to the backend which transforms the .csv file to a pandas dataframe. Pandas workflows are called and graph data is sent back through axios to be used in React with recharts to view.

## Dependencies:
* Install requirements.txt for Flask backend (Python version 3.11.5)
	```
	pip install -r requirements.txt
	```

## Getting Started:
Set up config files for both the frontend and backend for development, staging, and production.
To start backend in development mode:
```
flask run
```
To start frontend in development mode:
```
npm run dev
```

Create Python Virtual Environment:
```
python -m venv .venv
```

Update requirements.txt:
```
pip freeze > requirements.txt
```
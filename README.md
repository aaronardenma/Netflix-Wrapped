# Netflix-Wrapped

**Netflix Wrapped** is a work in progress web app that allows Netflix users to visualize their viewing data as provided by Netflix. Netflix data can downloaded by submitting a request to Netflix [here](https://www.netflix.com/account/getmyinfo), with more details on their [help](https://help.netflix.com/en/node/100624) page.

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
* Install required dependencies from pacakge.json for React frontend (React version 18.3.1)
	```
	npm intall
	```

## Getting Started:
Set up config files for both the frontend and backend for development, staging, and production.

To start the backend and frontend with Docker:
```
docker compose up --build
```

This uses the local Postgres database configured in `backend/.env`. Make sure Postgres is running on your machine first.

The frontend will be available at `http://localhost:3000` and the backend at `http://localhost:8000`.

For password reset emails, configure SMTP values in `backend/.env`:
```
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-smtp-user
EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=no-reply@example.com
FRONTEND_URL=http://localhost:3000
```

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

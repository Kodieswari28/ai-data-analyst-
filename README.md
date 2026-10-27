# Ask Your Data: AI Data Analyst (Text-to-SQL)

Ask questions about a database in plain English. An LLM (Google Gemini) writes the SQL, a safety layer checks it, and the app shows the answer as a table and a chart.

## Features
- English to SQL with Gemini (free API tier)
- Two-layer SQL safety: SELECT-only validation and a read-only database connection
- Self-repair: if the generated SQL fails, the error goes back to the AI for one retry
- Auto chart (bar, line, doughnut) chosen from the question and the result
- Chat history sent as context for follow-up questions
- Demo mode works without an API key
- Unit tests for the safety layer

## Tech stack
Python, FastAPI, SQLite, Gemini API, Chart.js, HTML/CSS/JS

## Run on Windows
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Open `.env` and paste your key from https://aistudio.google.com/apikey, then:
```
uvicorn main:app --reload
```
Open http://127.0.0.1:8000. API docs are at /docs.

## Tests
```
python -m unittest test_safety -v
```

## How the safety layer works
1. `validate_sql()` accepts a single SELECT or WITH query only. It rejects write keywords, comments and multiple statements, and adds a row limit.
2. `run_readonly()` opens SQLite in read-only mode and installs an authorizer that denies every action except reading data. Even if the text check were bypassed, the database cannot change.

## Deploy on Render
Push to GitHub, create a new Web Service on Render from the repo, and add `GEMINI_API_KEY` as an environment variable. `render.yaml` already holds the build and start commands.

## Screenshots
Add 2-3 screenshots here after you run it.

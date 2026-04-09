# PayScope

Local-first salary prediction app with a Decision Tree model, FastAPI `GET /predict`, a separate Python client, a story-first Streamlit dashboard, local Ollama analysis, and optional Supabase persistence.

## Current Run Mode

- Dashboard: local Streamlit app
- API: local FastAPI service
- Deployment: intentionally skipped for this assignment version

## Architecture

```text
DS Salaries CSV
    ->
data cleaning + preprocessing
    ->
Decision Tree training
    ->
saved model artifact + metrics
    ->
FastAPI GET /predict
    ->
Streamlit dashboard
        ->
        plain-English explanation
        AI narrative from Ollama
        optional history from Supabase
```

## What This App Does

- Trains a Decision Tree salary prediction model on the DS Salaries dataset.
- Exposes a required `GET /predict` API with validated query parameters.
- Includes a separate Python client script that calls the API and handles errors safely.
- Presents a polished storytelling dashboard designed for a non-technical audience.
- Adds local LLM narrative analysis through Ollama.
- Can save prediction history to Supabase and read it back into the dashboard.

## Project Files

- `config.py` loads environment variables and shared paths.
- `ml.py` handles cleaning, training, artifact saving, and prediction logic.
- `analysis.py` prepares chart summaries and peer-group explanation data.
- `api.py` runs FastAPI and writes predictions to Supabase when configured.
- `dashboard.py` runs Streamlit and renders the full story-first UI.
- `predict_client.py` is the required standalone API caller.
- `train_model.py` trains the model and saves local artifacts.
- `supabase_schema.sql` contains the SQL to create the Supabase predictions table.
- `render.yaml` prepares the FastAPI app for Render deployment.
- `.streamlit/config.toml` provides Streamlit theme settings for local and cloud runs.

## Local Setup

1. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Train the model:

```bash
python train_model.py
```

3. Start FastAPI:

```bash
uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

4. Start Streamlit in a second terminal:

```bash
streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501
```

5. Optional: run the separate client script:

```bash
python predict_client.py --experience-level SE --employment-type FT --job-title "Data Scientist" --employee-residence US --company-location US --company-size M --remote-ratio 100
```

Local URLs after startup:

- Dashboard: `http://127.0.0.1:8501`
- API docs: `http://127.0.0.1:8000/docs`
- API health: `http://127.0.0.1:8000/health`

## Environment Variables

Core local variables:

```text
APP_ENV
LOG_LEVEL
DATASET_PATH
PROCESSED_DATA_PATH
MODEL_PATH
METRICS_PATH
FASTAPI_HOST
FASTAPI_PORT
FASTAPI_BASE_URL
STREAMLIT_HOST
STREAMLIT_PORT
REQUEST_TIMEOUT_SECONDS
```

Optional integration variables:

```text
OLLAMA_BASE_URL
OLLAMA_MODEL
OLLAMA_TIMEOUT_SECONDS
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_PREDICTIONS_TABLE
```

Copy `.env.example` to `.env` and update only the values you need.

## API Docs

### Health check

```bash
curl "http://127.0.0.1:8000/health"
```

### Prediction endpoint

```bash
curl "http://127.0.0.1:8000/predict?experience_level=SE&employment_type=FT&job_title=Data%20Scientist&employee_residence=US&company_location=US&company_size=M&remote_ratio=100"
```

### Required query parameters

- `experience_level`: `EN`, `MI`, `SE`, `EX`
- `employment_type`: `FT`, `PT`, `CT`, `FL`
- `job_title`: free-text role name
- `employee_residence`: 2-letter country code
- `company_location`: 2-letter country code
- `company_size`: `S`, `M`, `L`
- `remote_ratio`: `0`, `50`, `100`

## Client Script Usage

```bash
python predict_client.py --experience-level SE --employment-type FT --job-title "Data Scientist" --employee-residence US --company-location US --company-size M --remote-ratio 100
```

The script prints:

- predicted salary
- peer group label
- peer group size
- comparison to the peer median

## Ollama Setup

1. Install Ollama locally.
2. Pull a model such as:

```bash
ollama pull llama3.2
```

3. Add this to `.env`:

```text
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT_SECONDS=60
```

4. Restart Streamlit after updating `.env`.

If Ollama is unavailable, the dashboard still works and shows a graceful message instead of breaking.

## Supabase Setup

Run the SQL in `supabase_schema.sql` inside the Supabase SQL editor.

Required env vars for Supabase:

```text
SUPABASE_URL=your_project_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_PREDICTIONS_TABLE=salary_predictions
```

What each key is used for:

- `SUPABASE_SERVICE_ROLE_KEY`: used by `api.py` to write predictions
- `SUPABASE_ANON_KEY`: used by `dashboard.py` to read prediction history
- `SUPABASE_URL`: shared base URL for both paths
- `SUPABASE_PREDICTIONS_TABLE`: current table name

## Final Non-Deployment Checklist

- Train the model and confirm the artifact and metrics exist.
- Start FastAPI and Streamlit locally.
- Run one prediction from the dashboard and one from `predict_client.py`.
- If you want history, run `supabase_schema.sql`, set the Supabase env vars, and confirm one saved prediction appears in the dashboard history section.
- Take screenshots of the hero section, Prediction Studio, and Why This Prediction Makes Sense section before submission.

## Tech Stack

- Python
- pandas
- numpy
- scikit-learn
- FastAPI
- Streamlit
- Plotly
- Ollama
- Supabase
- python-dotenv
- pytest

## Suggested Screenshots

- Hero section with KPI cards
- Prediction Studio with a completed prediction
- Why This Prediction Makes Sense with peer comparison and AI insight

## Testing

```bash
pytest
```

## Author

Yasser Hamdan

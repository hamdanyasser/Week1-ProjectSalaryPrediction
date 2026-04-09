# PayScope

**Predict data-science salaries, explain the estimate, and tell the story — all in one dashboard.**

Built as a Week 1 assignment for the AI Engineering Program: train a Decision Tree model on the Kaggle DS Salaries dataset, serve predictions through a GET API, analyze them with a local LLM, persist results to Supabase, and present everything in a Streamlit dashboard that a non-technical audience can follow.

---

## Architecture

```text
ds_salaries.csv
      |
      v
 Data cleaning + feature selection  (ml.py)
      |
      v
 Decision Tree training + artifact saving  (train_model.py)
      |
      v
 FastAPI GET /predict  (api.py)
      |               \
      v                --> Supabase write (optional, env-gated)
 Streamlit dashboard  (dashboard.py)
      |
      +--> Market charts from cleaned CSV
      +--> Live prediction via FastAPI
      +--> Peer-group explanation from dataset
      +--> AI narrative from Ollama (optional)
      +--> Saved prediction history from Supabase (optional)
```

### Local flow

```
train_model.py  -->  FastAPI (localhost:8000)  -->  Streamlit (localhost:8501)
```

### Deployed flow

```
Railway (FastAPI)  <--  Streamlit Community Cloud (dashboard)
      |
      v
  Supabase (prediction history)
```

---

## Live URLs

| Service | URL |
|---------|-----|
| Dashboard | _Streamlit Community Cloud URL here_ |
| API | _Render URL here_ |
| API Docs | _Render URL here_ `/docs` |

---

## Local Setup

### Prerequisites

- Python 3.10+
- (Optional) Ollama installed with a model pulled
- (Optional) Supabase project with the schema applied

### Steps

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd Week1-ProjectSalaryPrediction

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the environment template
cp .env.example .env
# Edit .env if you want to enable Ollama or Supabase

# 5. Train the model
python train_model.py

# 6. Start FastAPI
uvicorn api:app --reload --host 127.0.0.1 --port 8000

# 7. In a second terminal, start Streamlit
streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501
```

After startup:

- Dashboard: `http://127.0.0.1:8501`
- API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

---

## API Documentation

### `GET /health`

```bash
curl "http://127.0.0.1:8000/health"
```

Returns model and data readiness status.

### `GET /predict`

```bash
curl "http://127.0.0.1:8000/predict?experience_level=SE&employment_type=FT&job_title=Data%20Scientist&employee_residence=US&company_location=US&company_size=M&remote_ratio=100"
```

**Required query parameters:**

| Parameter | Values | Description |
|-----------|--------|-------------|
| `experience_level` | `EN`, `MI`, `SE`, `EX` | Entry / Mid / Senior / Executive |
| `employment_type` | `FT`, `PT`, `CT`, `FL` | Full-time / Part-time / Contract / Freelance |
| `job_title` | free text | Role name (e.g. "Data Scientist") |
| `employee_residence` | 2-letter code | Country where the employee lives |
| `company_location` | 2-letter code | Country where the company is based |
| `company_size` | `S`, `M`, `L` | Small / Medium / Large |
| `remote_ratio` | `0`, `50`, `100` | On-site / Hybrid / Fully remote |

**Response** includes `predicted_salary_usd`, `normalized_inputs`, `model_name`, and `peer_context` with peer median, range, comparison text, and driver messages.

---

## Client Script

The assignment requires a separate Python script that calls the API with proper error handling.

```bash
python predict_client.py \
  --experience-level SE \
  --employment-type FT \
  --job-title "Data Scientist" \
  --employee-residence US \
  --company-location US \
  --company-size M \
  --remote-ratio 100
```

The script handles timeout, connection failure, HTTP errors, and invalid JSON gracefully. It prints the predicted salary, peer group, sample size, and comparison.

---

## Ollama (Local LLM)

The assignment requires narrative insights and at least one supporting visualization using a local LLM.

1. Install Ollama and pull a model:

```bash
ollama pull llama3.2
```

2. Set these in `.env`:

```
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
```

3. Restart Streamlit.

The dashboard sends prediction context to Ollama, asks for structured JSON output (headline, narrative, insights), and renders the result in a premium AI Insight card alongside a comparison chart.

If Ollama is unavailable, the dashboard still works — it shows a graceful message instead of breaking.

---

## Supabase

The assignment requires persisting predictions and reading them back in the dashboard.

### Architecture note: what the dashboard reads from Supabase

The assignment says the dashboard should consume from Supabase. In this project:

- **Prediction history** is read directly from Supabase. Every prediction the API serves is written to the `salary_predictions` table, and the dashboard reads it back for the History section.
- **Market overview charts** use the static training dataset (cleaned CSV). This data does not change between predictions and does not belong in a transactional table. Storing 600+ static rows in Supabase just to re-read them would add complexity without benefit.
- **Live predictions** come from the FastAPI response (which also writes to Supabase). The dashboard shows the result immediately rather than round-tripping through Supabase, because the user is waiting for a response.

This is a deliberate tradeoff: Supabase stores and serves all dynamic prediction data, while static analysis data stays embedded.

### Schema

Run the SQL in `supabase_schema.sql` inside the Supabase SQL editor. It creates the `salary_predictions` table with appropriate columns, constraints, indexes, and row-level security policies.

### Environment variables

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_PREDICTIONS_TABLE=salary_predictions
```

- **API** (`api.py`) uses the service role key to write each prediction to Supabase.
- **Dashboard** (`dashboard.py`) uses the anon key to read saved prediction history.

If Supabase env vars are not set, both paths are silently skipped and the app works fully without them.

---

## Deployment

### FastAPI on Railway

- `Procfile` configures the start command.
- The model artifact (`artifacts/decision_tree_pipeline.joblib`) and dataset are committed to the repo so they're available at deploy time.
- Set these environment variables in Railway's dashboard:

| Variable | Value |
|----------|-------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Your service role key |
| `SUPABASE_PREDICTIONS_TABLE` | `salary_predictions` |

### Streamlit on Community Cloud

- Point to `dashboard.py` as the main file.
- Set `FASTAPI_BASE_URL` in Streamlit secrets to the deployed Railway URL.
- Ollama will not be available in the cloud. The dashboard handles this gracefully — the AI Insight section shows an informational message instead.
- Set Supabase env vars in Streamlit secrets if you want the history section.

---

## Project Files

| File | Purpose |
|------|---------|
| `config.py` | Loads `.env`, resolves paths, exposes `Settings` |
| `ml.py` | Data cleaning, Decision Tree pipeline, training, prediction, label helpers |
| `analysis.py` | KPIs, chart summaries, peer-group explanation, takeaways |
| `api.py` | FastAPI with `GET /health` and `GET /predict`, optional Supabase write |
| `dashboard.py` | Streamlit UI — charts, prediction studio, explanation, AI insight |
| `predict_client.py` | Standalone API client with error handling |
| `train_model.py` | Entry script to train and save artifacts |
| `supabase_schema.sql` | SQL to create the predictions table in Supabase |
| `Procfile` | Railway deployment start command |
| `render.yaml` | Render deployment config (alternative) |
| `.streamlit/config.toml` | Dark theme configuration |
| `requirements.txt` | Python dependencies |

---

## Testing

```bash
pytest
```

Runs 4 tests covering data cleaning, model training, prediction endpoint, and input validation.

---

## Screenshots

_Add screenshots of:_
- _Hero section with KPI cards_
- _Market charts_
- _Prediction Studio with a completed prediction_
- _Why This Prediction Makes Sense with peer comparison and AI insight_

---

## Author

**Yasser Hamdan**

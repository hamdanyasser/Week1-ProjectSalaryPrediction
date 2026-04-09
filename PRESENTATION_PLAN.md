# PayScope — 10-Minute Presentation Plan

## Slide 1: Title (30 seconds)
- **PayScope: Predict Data-Science Salaries with ML + LLM**
- Your name, Week 1 assignment, AI Engineering Program
- One-liner: "Train a model, serve it through an API, explain it with a local LLM, and present it in a dashboard."

## Slide 2: Problem & Dataset (1 minute)
- Kaggle DS Salaries dataset — ~600 real-world records
- Features: experience level, employment type, job title, location, company size, remote ratio
- Target: salary in USD
- Why it matters: salary transparency helps candidates and hiring managers

## Slide 3: Architecture Diagram (1.5 minutes)
- Draw or show the flow:
  ```
  CSV → ml.py (clean + train) → Decision Tree artifact
  artifact → FastAPI /predict → Ollama LLM → Supabase → Streamlit dashboard
  ```
- Emphasize the **local pipeline**: API does prediction + LLM analysis + persistence in one call
- Dashboard **consumes from Supabase** (prediction history) and **API** (live predictions)
- Mention: Railway hosts the API, Streamlit Cloud hosts the dashboard

## Slide 4: Model Choice & Training (1.5 minutes)
- **Decision Tree** with sklearn Pipeline (OneHotEncoder + DecisionTreeRegressor)
- Why Decision Tree: interpretable, handles categorical features well, fast training
- Hyperparameters: max_depth=12, min_samples_leaf=4
- Show the training metrics (R², MAE) from `model_metrics.json`
- Mention: `train_model.py` saves the pipeline as a joblib artifact

## Slide 5: Live Demo — Dashboard (2.5 minutes)
- **Open the live dashboard** (Streamlit Cloud URL)
- Walk through each section:
  1. **Hero + KPI cards** — total records, median salary, top role, model accuracy
  2. **Market Overview charts** — salary distribution, experience breakdown, top roles, remote work
  3. **Prediction Studio** — fill in the form, click Predict, show the result card
  4. **Why This Prediction** — peer comparison bar chart, driver messages, explanation
  5. **AI Insight card** — LLM headline + narrative + insights (explain this came from Ollama via the API)
  6. **Prediction History** — rows read from Supabase
  7. **Takeaways** — auto-generated bullet points from the data
- Tip: have a prediction already saved so History is not empty

## Slide 6: API & Client Script (1 minute)
- Show `GET /predict` in the Swagger docs (Railway URL `/docs`)
- Show the query parameters and response shape
- Show `predict_client.py` running in a terminal: prediction + peer context + LLM analysis
- Mention error handling: timeout, connection error, HTTP error, invalid JSON

## Slide 7: Supabase Integration (1 minute)
- Schema: `salary_predictions` table with prediction inputs, outputs, peer context, LLM columns
- Row-level security: public read (anon key), service-role insert only
- API writes on every prediction; dashboard reads for History section
- Show the Supabase table editor with real rows as proof

## Slide 8: Key Decisions & Tradeoffs (30 seconds)
- LLM in API (not dashboard) — keeps the pipeline local, writes once, dashboard just reads
- Static data stays in CSV — no reason to put 600 unchanging rows in Supabase
- Graceful degradation — if Ollama or Supabase is down, everything still works
- Dark theme — designed for a non-technical audience (clean, minimal, storytelling-first)

## Slide 9: Q&A (30 seconds)
- Open for questions
- Be ready to explain: why Decision Tree over Random Forest, how peer matching works, how the LLM prompt is structured

---

## Preparation Checklist

- [ ] Open the live dashboard URL in a browser tab before presenting
- [ ] Open the API docs URL (`/docs`) in another tab
- [ ] Have a terminal ready with `python predict_client.py` command prepared
- [ ] Run at least one prediction beforehand so Supabase History has data
- [ ] Open Supabase table editor in a tab to show real rows
- [ ] If demoing locally: start Ollama, FastAPI, and Streamlit before the presentation
- [ ] Test the live URLs 10 minutes before — Railway free tier can cold-start

## Key Numbers to Mention
- ~600 training records
- 7 features → 1 target (salary_in_usd)
- Decision Tree with max_depth=12
- 4 passing tests
- 2 API endpoints (GET /health, GET /predict)
- Full deploy: Railway (API) + Streamlit Cloud (dashboard) + Supabase (persistence)

# PayScope — Claude context

Data-science salary prediction app for a Week 1 assignment. Written for non-technical audiences: warm, plain-English copy everywhere, no jargon like R², RMSE, "Decision Tree", "feature importance".

## Stack
- **ml.py** — scikit-learn pipeline (Decision Tree regressor), cleans raw CSV, trains, saves joblib + metrics JSON.
- **api.py** — FastAPI server exposing `/predict`. Calls Ollama (`llama3.2`) for plain-English narrative; logs every call to Supabase.
- **dashboard.py** — Streamlit UI. Editorial design with rainbow categorical palette (TEAL/VIOLET/SKY/AMBER/CORAL/LIME/PINK). CSS lives in a plain-string `_CSS` constant with `:root` variables — not an f-string, to avoid the Python 3.11 tokenize bug with nested `{{}}`.
- **analysis.py** — shared dataset analytics used by both `api.py` and `dashboard.py` (peer matching, distributions, etc.).
- **config.py** — pydantic settings, reads `.env`.
- **make_ppt.py** — python-pptx generator for the 7-slide deck (`PayScope_Presentation.pptx`). Uses editorial signature frame + rainbow accents. Native PPT charts via `XL_CHART_TYPE`. XML-level animations via `lxml`.
- **train_model.py** / **predict_client.py** — standalone CLI helpers.
- **tests/** — pytest (`test_api.py`, `test_ml.py`).
- **data/raw/ds_salaries.csv** — 607-row Kaggle dataset.
- **artifacts/** — trained joblib, metrics JSON, Streamlit QR code.

## How to run
```bash
python train_model.py              # train + save model
uvicorn api:app --reload            # FastAPI on :8000
streamlit run dashboard.py          # Streamlit on :8501
python make_ppt.py                  # regenerate PayScope_Presentation.pptx
pytest                              # tests
```

## Design language (non-negotiable)
- **Tone:** exciting, warm, zero jargon. Aimed at people who don't know anything technical. Never say "Decision Tree", "R²", "RMSE", "feature importance", "FastAPI", "Ollama", "Supabase" in user-facing copy.
- **Colors:** teal is the brand/UI-chrome color, but **charts must use the full categorical palette** — single-teal charts look dead. Rotate TEAL, AMBER, VIOLET, SKY, CORAL, LIME, PINK across categories.
- **Typography:** Inter for prose, JetBrains Mono (or Consolas in PPT) for numerals and eyebrow labels.
- **Data labels:** show `$X,XXX` outside bars where it fits — users shouldn't have to hover.

## Gotchas
- Don't wrap `dashboard.py`'s CSS in an f-string. It breaks Python 3.11's tokenizer on nested braces. Keep it as a plain triple-quoted `_CSS` constant and use `:root` CSS variables for theming.
- `make_ppt.py` falls back to `PayScope_Presentation_NEW.pptx` when PowerPoint holds a lock on the main file. If you see that, close PowerPoint and regenerate.
- `~$PayScope_Presentation.pptx` is a PowerPoint lock file — gitignored, can't be removed while PowerPoint is open.

## Out of scope for edits
- Don't reintroduce technical jargon to user-facing copy (headers, hero, form labels, explanations, PPT slides).
- Don't collapse chart colors back to single-teal — that was an over-correction and got pushback.

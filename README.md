# Predictive Analysis and Management System for Chronic Diseases using Machine Learning

Full-stack demo web app.

- **Backend**: Python Flask
- **ML**: Scikit-learn (Logistic Regression, Random Forest, SVM) with preprocessing (impute + scale + encode)
- **Frontend**: HTML/CSS/JS (responsive dashboard) + **Chart.js**
- **Database**: SQLite (via SQLAlchemy)
- **Deploy**: Render / Railway compatible (Gunicorn + `Procfile`)

> Note: This project is for academic/demo purposes only. It is **not medical advice**.

---

## Folder structure

```
chronic-ml-predictor/
  app.py
  model.py
  config.py
  db.py
  models.py
  requirements.txt
  Procfile
  runtime.txt
  .env.example
  data/
    sample_dataset.csv        # auto-generated if missing
  ml/
    training.py
    schema.py
    recommendations.py
  ml_artifacts/               # auto-generated (model.joblib + metadata.json)
  instance/                   # sqlite db + generated pdf reports
  templates/
  static/
```

---

## Local setup (macOS / Linux / Windows)

From your terminal:

```bash
cd "/Users/shivamgiri/Documents/chronic-ml-predictor"
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create your `.env`:

```bash
cp .env.example .env
```

Run the app:

```bash
python3 app.py
```

Open:

- `http://127.0.0.1:5000`

If port `5000` is already used on your system, run with a different port:

```bash
PORT=5050 python3 app.py
```

Then open:

- `http://127.0.0.1:5050`

### Train/retrain model (optional)

The app auto-trains on first run if `ml_artifacts/` is missing. You can also run:

```bash
python3 model.py
```

---

## Core endpoints (API)

These are session-authenticated (login required):

- `POST /api/register`
- `POST /api/login`
- `POST /api/predict`
- `GET /api/history`

Chatbot:

- `POST /api/chat`

PDF report download:

- `GET /report/<prediction_id>.pdf`

---

## Deployment (Render)

### 1) Create a new Web Service

- Connect your GitHub repo (or upload the project)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

### 2) Environment variables

Add:

- `SECRET_KEY`: a long random string
- `DATABASE_URL`: `sqlite:///instance/app.sqlite3`

### 3) Deploy

Render will run the `Procfile` command (`gunicorn app:app`) automatically if you set it as start command.

---

## Deployment (Railway)

### 1) New Project → Deploy from GitHub

### 2) Variables

- `SECRET_KEY`
- `DATABASE_URL=sqlite:///instance/app.sqlite3`

### 3) Start command

- `gunicorn app:app`

---

## Notes / Design choices

- Auth is **session-based** using `Flask-Login` (simple and production-safe).
- Risk levels are computed from predicted probability:
  - `< 0.33`: Low
  - `< 0.66`: Medium
  - `>= 0.66`: High
- The sample dataset is synthetic but aligned to your form fields and supports:
  - missing-value handling
  - categorical encoding
  - normalization


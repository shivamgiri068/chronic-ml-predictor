from __future__ import annotations

import json
import os
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

from ml.schema import FEATURE_COLUMNS


DATA_COLUMNS = FEATURE_COLUMNS + ["label"]


def ensure_dirs(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def generate_sample_dataset_csv(csv_path: str, n: int = 1200, seed: int = 7) -> None:
    """
    Generates a realistic-ish classification dataset aligned to our app form fields.
    This keeps the project self-contained (no Kaggle download needed).
    """
    rng = np.random.default_rng(seed)

    age = rng.integers(18, 85, size=n)
    gender = rng.choice(["male", "female", "other"], size=n, p=[0.49, 0.49, 0.02])
    bmi = np.clip(rng.normal(26.0, 5.0, size=n), 15, 55)
    blood_pressure = np.clip(rng.normal(125, 18, size=n), 80, 210)
    glucose = np.clip(rng.normal(105, 28, size=n), 60, 260)
    smoking = rng.choice(["never", "occasionally", "often"], size=n, p=[0.65, 0.25, 0.10])
    alcohol = rng.choice(["never", "occasionally", "often"], size=n, p=[0.55, 0.35, 0.10])
    family_history = rng.choice(["no", "yes"], size=n, p=[0.68, 0.32])
    symptom_count = np.clip(rng.poisson(1.8, size=n), 0, 10)

    # Create a probability via a simple logistic recipe, then sample labels
    # (This isn't "medical truth", just a consistent demo signal.)
    # Create probabilities for each disease
    z_diabetes = (
        (glucose - 100) / 20
        + (bmi - 25) / 5
        + (age - 45) / 20
        + 0.5 * (family_history == "yes").astype(float)
    )
    p_diabetes = 1 / (1 + np.exp(-z_diabetes))
    label_diabetes = (rng.random(size=n) < p_diabetes).astype(int)

    z_heart = (
        (blood_pressure - 120) / 20
        + (age - 45) / 15
        + 0.6 * (smoking == "often").astype(float)
        + 0.4 * (alcohol == "often").astype(float)
        + (bmi - 25) / 8
    )
    p_heart = 1 / (1 + np.exp(-z_heart))
    label_heart = (rng.random(size=n) < p_heart).astype(int)

    z_kidney = (
        (blood_pressure - 120) / 22
        + (glucose - 100) / 25
        + (age - 45) / 18
        + 0.3 * symptom_count
    )
    p_kidney = 1 / (1 + np.exp(-z_kidney))
    label_kidney = (rng.random(size=n) < p_kidney).astype(int)

    df = pd.DataFrame(
        {
            "age": age,
            "gender": gender,
            "bmi": bmi.round(2),
            "blood_pressure": blood_pressure.round(1),
            "glucose": glucose.round(1),
            "smoking": smoking,
            "alcohol": alcohol,
            "family_history": family_history,
            "symptom_count": symptom_count,
            "label_diabetes": label_diabetes,
            "label_heart": label_heart,
            "label_kidney": label_kidney,
        }
    )

    # Add a small amount of missingness for imputation demo
    for col in ["bmi", "blood_pressure", "glucose"]:
        mask = rng.random(size=n) < 0.02
        df.loc[mask, col] = np.nan

    ensure_dirs(os.path.dirname(csv_path))
    df.to_csv(csv_path, index=False)


def build_preprocessor():
    numeric_features = ["age", "bmi", "blood_pressure", "glucose", "symptom_count"]
    categorical_features = ["gender", "smoking", "alcohol", "family_history"]

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_features),
            ("cat", categorical_pipeline, categorical_features),
        ]
    )


def train_and_select_model(
    dataset_csv_path: str,
    artifact_dir: str,
    seed: int = 7,
):
    if not os.path.exists(dataset_csv_path):
        generate_sample_dataset_csv(dataset_csv_path, n=1200, seed=seed)

    df = pd.read_csv(dataset_csv_path)
    preprocessor = build_preprocessor()

    candidates = {
        "logistic_regression": LogisticRegression(max_iter=2000),
        "random_forest": RandomForestClassifier(
            n_estimators=300, random_state=seed, n_jobs=-1
        ),
        "svm": SVC(probability=True, kernel="rbf", random_state=seed),
    }

    metrics = {}
    best_names = {}
    
    ensure_dirs(artifact_dir)

    for disease in ["diabetes", "heart", "kidney"]:
        label_col = f"label_{disease}"
        
        X = df[FEATURE_COLUMNS]
        y = df[label_col].astype(int)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=seed, stratify=y
        )
        
        best_acc = -1.0
        best_name = None
        best_pipeline = None
        disease_metrics = {}
        
        for name, model in candidates.items():
            pipeline = Pipeline(steps=[("preprocess", preprocessor), ("model", model)])
            pipeline.fit(X_train, y_train)
            preds = pipeline.predict(X_test)
            acc = float(accuracy_score(y_test, preds))
            disease_metrics[name] = {"accuracy": acc}

            if acc > best_acc:
                best_acc = acc
                best_name = name
                best_pipeline = pipeline

        metrics[disease] = disease_metrics
        best_names[disease] = best_name
        
        joblib.dump(best_pipeline, os.path.join(artifact_dir, f"model_{disease}.joblib"))

    with open(os.path.join(artifact_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "best_models": best_names,
                "metrics": metrics,
                "feature_columns": FEATURE_COLUMNS,
            },
            f,
            indent=2,
        )

    return {"status": "success"}


def load_models(artifact_dir: str):
    models = {}
    for disease in ["diabetes", "heart", "kidney"]:
        path = os.path.join(artifact_dir, f"model_{disease}.joblib")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model artifact not found for {disease}.")
        models[disease] = joblib.load(path)
    return models

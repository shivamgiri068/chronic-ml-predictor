import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///instance/app.sqlite3"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Where we store trained model + metadata
    ARTIFACT_DIR = os.environ.get("ARTIFACT_DIR", "ml_artifacts")

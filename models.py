from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from db import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "patient" | "doctor"
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    predictions = db.relationship("Prediction", back_populates="user", lazy="dynamic")
    medical_history = db.relationship(
        "MedicalHistory", back_populates="user", uselist=False
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class MedicalHistory(db.Model):
    __tablename__ = "medical_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    family_history = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="medical_history")


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Input snapshot
    patient_name = db.Column(db.String(120), nullable=True)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    blood_pressure = db.Column(db.Float, nullable=False)
    glucose = db.Column(db.Float, nullable=False)
    smoking = db.Column(db.String(20), nullable=False)  # never/occasionally/often
    alcohol = db.Column(db.String(20), nullable=False)  # never/occasionally/often
    family_history = db.Column(db.String(10), nullable=False)  # yes/no
    symptoms = db.Column(db.Text, nullable=False)  # comma-separated

    # Outputs
    risk_level = db.Column(db.String(10), nullable=True)  # low/medium/high (legacy)
    probability = db.Column(db.Float, nullable=True)  # 0..1 (legacy)
    
    diabetes_risk = db.Column(db.Float, nullable=True)
    heart_risk = db.Column(db.Float, nullable=True)
    kidney_risk = db.Column(db.Float, nullable=True)
    overall_risk = db.Column(db.String(10), nullable=True)
    most_likely_disease = db.Column(db.String(50), nullable=True)

    model_name = db.Column(db.String(60), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", back_populates="predictions")

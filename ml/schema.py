FEATURE_COLUMNS = [
    "age",
    "gender",
    "bmi",
    "blood_pressure",
    "glucose",
    "smoking",
    "alcohol",
    "family_history",
    "symptom_count",
]


SYMPTOM_OPTIONS = [
    "Frequent urination",
    "Excessive thirst",
    "Fatigue",
    "Blurred vision",
    "Chest pain",
    "Shortness of breath",
    "Headache",
    "Dizziness",
    "Nausea",
    "Unexplained weight loss",
    "Slow healing wounds",
]


def risk_from_probability(p: float) -> str:
    # Simple, interpretable thresholds for demo
    if p < 0.33:
        return "low"
    if p < 0.66:
        return "medium"
    return "high"

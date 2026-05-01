def recommendations_for(risk_level: str) -> dict:
    risk_level = (risk_level or "").lower()

    base = {
        "diet": [
            "Prefer whole foods (vegetables, fruits, legumes, whole grains).",
            "Limit sugary drinks and highly processed snacks.",
            "Keep portion sizes consistent and avoid late-night heavy meals.",
        ],
        "exercise": [
            "Aim for 150 minutes/week of moderate activity (brisk walking/cycling).",
            "Add 2 days/week of strength training (bodyweight exercises are fine).",
        ],
        "tips": [
            "Sleep 7–9 hours and keep a consistent schedule.",
            "Stay hydrated and manage stress (breathing, meditation, journaling).",
        ],
        "doctor": [
            "If you have concerning symptoms, consult a doctor for clinical evaluation.",
        ],
    }

    if risk_level == "low":
        return {
            **base,
            "doctor": ["Maintain routine checkups and annual screening as advised."],
        }

    if risk_level == "medium":
        return {
            **base,
            "diet": base["diet"]
            + ["Reduce refined carbs (white bread, sweets) and increase fiber."],
            "doctor": [
                "Schedule a consultation to review vitals and possible lab tests.",
                "Track BP/glucose trends for 2–4 weeks before your appointment.",
            ],
        }

    # high
    return {
        **base,
        "diet": base["diet"]
        + [
            "Avoid high-sodium foods (processed meats, packaged soups).",
            "Discuss a personalized meal plan with a clinician/dietitian.",
        ],
        "exercise": [
            "Start with low-impact exercise; increase gradually based on tolerance.",
            "Stop and seek help if you experience chest pain, severe breathlessness, or fainting.",
        ],
        "doctor": [
            "Consult a doctor promptly for evaluation and guided next steps.",
            "Bring current medications, past reports, and recent measurements if available.",
        ],
    }

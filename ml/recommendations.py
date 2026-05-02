def recommendations_for(risk_level: str, disease_type: str = "general") -> dict:
    risk_level = (risk_level or "").lower()
    disease_type = (disease_type or "").lower()

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
            "Sleep 7-9 hours and keep a consistent schedule.",
            "Stay hydrated and manage stress (breathing, meditation, journaling).",
        ],
        "doctor": [
            "If you have concerning symptoms, consult a doctor for clinical evaluation.",
        ],
    }

    if disease_type == "diabetes":
        base["diet"].append("Monitor your daily sugar intake strictly.")
    elif disease_type == "heart disease" or disease_type == "heart":
        base["diet"].append("Focus on cholesterol control and heart-healthy fats.")
        base["exercise"].append("Incorporate more cardio if approved by a doctor.")
    elif disease_type == "kidney disease" or disease_type == "kidney":
        base["diet"].append("Monitor sodium and protein intake.")
        base["tips"].append("Maintain proper hydration and monitor BP closely.")

    if risk_level == "low":
        return {
            **base,
            "doctor": base["doctor"] + ["Maintain routine checkups and annual screening as advised."],
        }

    if risk_level == "medium":
        return {
            **base,
            "diet": base["diet"]
            + ["Reduce refined carbs (white bread, sweets) and increase fiber."],
            "doctor": [
                "Schedule a consultation to review vitals and possible lab tests.",
                "Track BP/glucose trends for 2-4 weeks before your appointment.",
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

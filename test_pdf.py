from fpdf import FPDF
from datetime import datetime

class MockPred:
    def __init__(self):
        self.risk_level = "high"
        self.probability = 0.763
        self.model_name = "logistic_regression"
        self.age = 45
        self.gender = "male"
        self.bmi = 27.6
        self.blood_pressure = 120.0
        self.glucose = 100.0
        self.smoking = "never"
        self.alcohol = "occasionally"
        self.family_history = "no"
        self.symptoms = "Fatigue, Headache"

recs = {
    "diet": [
        "Prefer whole foods (vegetables, fruits, legumes, whole grains).",
        "Limit sugary drinks and highly processed snacks.",
        "Keep portion sizes consistent and avoid late-night heavy meals.",
        "Avoid high-sodium foods (processed meats, packaged soups).",
        "Discuss a personalized meal plan with a clinician/dietitian."
    ],
    "exercise": [
        "Start with low-impact exercise; increase gradually based on tolerance.",
        "Stop and seek help if you experience chest pain, severe breathlessness, or fainting."
    ],
    "tips": [
        "Sleep 7-9 hours and keep a consistent schedule.",
        "Stay hydrated and manage stress (breathing, meditation, journaling)."
    ],
    "doctor": [
        "Consult a doctor promptly for evaluation and guided next steps.",
        "Bring current medications, past reports, and recent measurements if available."
    ]
}

try:
    pred = MockPred()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.cell(0, 10, "Chronic Disease Risk Report", ln=1)

    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=1)
    pdf.ln(2)

    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 8, f"Risk level: {pred.risk_level.upper()}", ln=1)
    pdf.cell(0, 8, f"Probability: {pred.probability*100:.1f}%", ln=1)
    pdf.cell(0, 8, f"Model: {pred.model_name}", ln=1)
    pdf.ln(3)

    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, "Inputs:", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(
        0,
        6,
        f"- Age: {pred.age}\n"
        f"- Gender: {pred.gender}\n"
        f"- BMI: {pred.bmi}\n"
        f"- Blood Pressure: {pred.blood_pressure}\n"
        f"- Glucose: {pred.glucose}\n"
        f"- Smoking: {pred.smoking}\n"
        f"- Alcohol: {pred.alcohol}\n"
        f"- Family history: {pred.family_history}\n"
        f"- Symptoms: {pred.symptoms}\n",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.ln(2)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, "Recommendations:", new_x="LMARGIN", new_y="NEXT")
    for k in ["diet", "exercise", "tips", "doctor"]:
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.cell(0, 7, k.capitalize(), ln=1)
        pdf.set_font("Helvetica", size=11)
        for item in recs.get(k, []):
            pdf.multi_cell(0, 6, f"- {item}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    # Test output
    out = pdf.output()
    print(f"Success! Output type: {type(out)}")
except Exception as e:
    import traceback
    traceback.print_exc()

from __future__ import annotations

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from fpdf import FPDF

from config import Config
from db import db
from ml.recommendations import recommendations_for
from ml.schema import SYMPTOM_OPTIONS, risk_from_probability
from ml.training import load_models, train_and_select_model
from models import MedicalHistory, Prediction, User


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["ARTIFACT_DIR"], exist_ok=True)
    # Use Flask's instance folder for SQLite so paths are stable in deployment.
    os.makedirs(app.instance_path, exist_ok=True)
    if str(app.config.get("SQLALCHEMY_DATABASE_URI", "")).startswith("sqlite:///"):
        # If a relative sqlite URI was provided, map it to <instance>/app.sqlite3
        db_path = os.path.join(app.instance_path, "app.sqlite3")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()

        # Ensure ML artifacts exist (self-contained run)
        try:
            _ = load_models(app.config["ARTIFACT_DIR"])
        except FileNotFoundError:
            train_and_select_model(
                dataset_csv_path=os.path.join("data", "sample_dataset.csv"),
                artifact_dir=app.config["ARTIFACT_DIR"],
            )

    def get_models_and_names():
        models = load_models(app.config["ARTIFACT_DIR"])
        meta_path = os.path.join(app.config["ARTIFACT_DIR"], "metadata.json")
        model_names = {d: f"model_{d}" for d in ["diabetes", "heart", "kidney"]}
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                model_names = json.load(f).get("best_models", model_names)
        return models, model_names

    def parse_symptoms(symptoms_raw: list[str]) -> tuple[str, int]:
        chosen = [s for s in symptoms_raw if s in SYMPTOM_OPTIONS]
        chosen = sorted(set(chosen))
        return ",".join(chosen) if chosen else "None", len(chosen)

    def require_doctor():
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role != "doctor":
            abort(403)

    @app.get("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("index.html")

    # -------------------------
    # Auth (HTML + API)
    # -------------------------
    @app.get("/register")
    def register():
        return render_template("register.html")

    @app.post("/register")
    def register_post():
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        role = (request.form.get("role") or "").strip().lower()

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if role not in {"patient", "doctor"}:
            flash("Invalid role.", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please login.", "error")
            return redirect(url_for("login"))

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Create a medical history row for patients
        if role == "patient":
            mh = MedicalHistory(user_id=user.id, family_history="", notes="")
            db.session.add(mh)
            db.session.commit()

        login_user(user)
        return redirect(url_for("dashboard"))

    @app.get("/login")
    def login():
        return render_template("login.html")

    @app.post("/login")
    def login_post():
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("dashboard"))

    @app.get("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("index"))

    # JSON auth endpoints (for the spec)
    @app.post("/api/register")
    def api_register():
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        role = (data.get("role") or "").strip().lower()

        if not name or not email or not password or role not in {"patient", "doctor"}:
            return jsonify({"error": "Invalid payload"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already registered"}), 409

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        if role == "patient":
            mh = MedicalHistory(user_id=user.id, family_history="", notes="")
            db.session.add(mh)
            db.session.commit()

        return jsonify({"ok": True, "user": {"id": user.id, "email": user.email, "role": user.role}})

    @app.post("/api/login")
    def api_login():
        data = request.get_json(force=True, silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid credentials"}), 401

        login_user(user)
        return jsonify({"ok": True, "user": {"id": user.id, "email": user.email, "role": user.role}})

    # -------------------------
    # Dashboard + Predict
    # -------------------------
    @app.get("/dashboard")
    @login_required
    def dashboard():
        # Doctor sees recent predictions across all users; patient sees their own
        if current_user.role == "doctor":
            recent = Prediction.query.order_by(Prediction.created_at.desc()).limit(25).all()
        else:
            recent = (
                Prediction.query.filter_by(user_id=current_user.id)
                .order_by(Prediction.created_at.desc())
                .limit(25)
                .all()
            )

        # For the chart: last 10 probabilities
        chart_rows = recent[:10][::-1]
        chart_labels = [r.created_at.strftime("%m-%d %H:%M") for r in chart_rows]
        chart_probs = []
        for r in chart_rows:
            if r.diabetes_risk is not None:
                max_prob = max(float(r.diabetes_risk), float(r.heart_risk), float(r.kidney_risk))
            else:
                max_prob = float(r.probability or 0)
            chart_probs.append(round(max_prob * 100, 1))

        return render_template(
            "dashboard.html",
            recent=recent,
            symptom_options=SYMPTOM_OPTIONS,
            chart_labels=chart_labels,
            chart_probs=chart_probs,
        )

    def _predict_from_payload(payload: dict) -> dict:
        age = int(payload["age"])
        gender = str(payload["gender"]).lower()
        bmi = float(payload["bmi"])
        blood_pressure = float(payload["blood_pressure"])
        glucose = float(payload["glucose"])
        smoking = str(payload["smoking"]).lower()
        alcohol = str(payload["alcohol"]).lower()
        family_history = str(payload["family_history"]).lower()
        symptoms_raw = payload.get("symptoms", [])

        symptoms_csv, symptom_count = parse_symptoms(symptoms_raw if isinstance(symptoms_raw, list) else [])

        models, model_names = get_models_and_names()

        X = {
            "age": age,
            "gender": gender,
            "bmi": bmi,
            "blood_pressure": blood_pressure,
            "glucose": glucose,
            "smoking": smoking,
            "alcohol": alcohol,
            "family_history": family_history,
            "symptom_count": symptom_count,
        }

        # Our preprocessing pipeline expects a tabular input with column names.
        X_df = pd.DataFrame([X])
        
        probabilities = {}
        for disease in ["diabetes", "heart", "kidney"]:
            model = models[disease]
            proba = float(model.predict_proba(X_df)[0][1])
            probabilities[disease] = float(np.clip(proba, 0.0, 1.0))
            
        most_likely_disease = max(probabilities, key=probabilities.get)
        highest_proba = probabilities[most_likely_disease]
        
        overall_risk = risk_from_probability(highest_proba)
        recs = recommendations_for(overall_risk, most_likely_disease)

        return {
            "inputs": {**X, "symptoms": symptoms_csv},
            "overall_risk": overall_risk,
            "most_likely_disease": most_likely_disease,
            "probabilities": probabilities,
            "recommendations": recs,
            "model_names": model_names,
        }

    @app.post("/predict")
    @login_required
    def predict_post():
        form = request.form
        payload = {
            "patient_name": form.get("patient_name", "").strip(),
            "age": form.get("age", ""),
            "gender": form.get("gender", ""),
            "bmi": form.get("bmi", ""),
            "blood_pressure": form.get("blood_pressure", ""),
            "glucose": form.get("glucose", ""),
            "smoking": form.get("smoking", ""),
            "alcohol": form.get("alcohol", ""),
            "family_history": form.get("family_history", ""),
            "symptoms": request.form.getlist("symptoms"),
        }

        try:
            result = _predict_from_payload(payload)
        except Exception:
            flash("Please check your inputs and try again.", "error")
            return redirect(url_for("dashboard"))

        pred = Prediction(
            user_id=current_user.id,
            patient_name=payload.get("patient_name") or None,
            age=int(result["inputs"]["age"]),
            gender=result["inputs"]["gender"],
            bmi=float(result["inputs"]["bmi"]),
            blood_pressure=float(result["inputs"]["blood_pressure"]),
            glucose=float(result["inputs"]["glucose"]),
            smoking=result["inputs"]["smoking"],
            alcohol=result["inputs"]["alcohol"],
            family_history=result["inputs"]["family_history"],
            symptoms=result["inputs"]["symptoms"],
            diabetes_risk=result["probabilities"]["diabetes"],
            heart_risk=result["probabilities"]["heart"],
            kidney_risk=result["probabilities"]["kidney"],
            overall_risk=result["overall_risk"],
            most_likely_disease=result["most_likely_disease"],
            model_name="multi_models",

            created_at=datetime.utcnow(),
        )
        db.session.add(pred)
        db.session.commit()

        flash("Prediction completed.", "success")
        return redirect(url_for("result", prediction_id=pred.id))

    @app.get("/result/<int:prediction_id>")
    @login_required
    def result(prediction_id: int):
        pred = db.session.get(Prediction, prediction_id)
        if not pred:
            abort(404)

        if current_user.role != "doctor" and pred.user_id != current_user.id:
            abort(403)

        recs = recommendations_for(pred.risk_level)
        return render_template("result.html", pred=pred, recs=recs)

    # API endpoints (for the spec)
    @app.post("/api/predict")
    @login_required
    def api_predict():
        data = request.get_json(force=True, silent=True) or {}
        try:
            result = _predict_from_payload(data)
        except Exception:
            return jsonify({"error": "Invalid input"}), 400

        pred = Prediction(
            user_id=current_user.id,
            patient_name=(data.get("patient_name") or "").strip() or None,
            age=int(result["inputs"]["age"]),
            gender=result["inputs"]["gender"],
            bmi=float(result["inputs"]["bmi"]),
            blood_pressure=float(result["inputs"]["blood_pressure"]),
            glucose=float(result["inputs"]["glucose"]),
            smoking=result["inputs"]["smoking"],
            alcohol=result["inputs"]["alcohol"],
            family_history=result["inputs"]["family_history"],
            symptoms=result["inputs"]["symptoms"],
            diabetes_risk=result["probabilities"]["diabetes"],
            heart_risk=result["probabilities"]["heart"],
            kidney_risk=result["probabilities"]["kidney"],
            overall_risk=result["overall_risk"],
            most_likely_disease=result["most_likely_disease"],
            model_name="multi_models",

        )
        db.session.add(pred)
        db.session.commit()

        return jsonify({"ok": True, "prediction_id": pred.id, **result})

    @app.get("/api/history")
    @login_required
    def api_history():
        if current_user.role == "doctor":
            rows = Prediction.query.order_by(Prediction.created_at.desc()).limit(100).all()
        else:
            rows = (
                Prediction.query.filter_by(user_id=current_user.id)
                .order_by(Prediction.created_at.desc())
                .limit(100)
                .all()
            )

        return jsonify(
            {
                "ok": True,
                "items": [
                    {
                        "id": r.id,
                        "user_id": r.user_id,
                        "overall_risk": r.overall_risk,
                        "most_likely_disease": r.most_likely_disease,
                        "diabetes_risk": r.diabetes_risk,
                        "heart_risk": r.heart_risk,
                        "kidney_risk": r.kidney_risk,
                        "model_name": r.model_name,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in rows
                ],
            }
        )

    # Backward-compatible alias for the spec's `/history`
    @app.get("/history")
    @login_required
    def history_alias():
        return api_history()

    # -------------------------
    # Doctor view: patient list
    # -------------------------
    @app.get("/doctor/patients")
    @login_required
    def doctor_patients():
        require_doctor()
        patients = User.query.filter_by(role="patient").order_by(User.created_at.desc()).all()
        return render_template("doctor_patients.html", patients=patients)

    @app.get("/doctor/patient/<int:user_id>")
    @login_required
    def doctor_patient(user_id: int):
        require_doctor()
        patient = db.session.get(User, user_id)
        if not patient or patient.role != "patient":
            abort(404)
        preds = (
            Prediction.query.filter_by(user_id=patient.id)
            .order_by(Prediction.created_at.desc())
            .limit(50)
            .all()
        )
        return render_template("doctor_patient.html", patient=patient, preds=preds)

    # -------------------------
    # Bonus: chatbot (rule-based)
    # -------------------------
    @app.post("/api/chat")
    @login_required
    def chat():
        data = request.get_json(force=True, silent=True) or {}
        msg = (data.get("message") or "").lower().strip()

        def reply(text: str):
            return jsonify({"ok": True, "reply": text})

        if not msg:
            return reply("Tell me what you’re feeling or ask for a health tip.")

        if "diet" in msg or "food" in msg:
            return reply("Tip: Prefer whole foods, limit sugar, and add fiber (vegetables/legumes).")
        if "exercise" in msg or "workout" in msg:
            return reply("Tip: Aim for 30 minutes of brisk walking 5 days/week + 2 strength days.")
        if "bp" in msg or "pressure" in msg:
            return reply("Tip: Reduce sodium, stay active, and monitor BP at consistent times.")
        if "glucose" in msg or "sugar" in msg:
            return reply("Tip: Avoid sugary drinks, choose complex carbs, and track fasting glucose if advised.")
        if "symptom" in msg:
            return reply("If symptoms are severe or sudden, consult a doctor promptly. Want to run a prediction?")

        return reply("I can help with diet, exercise, BP, glucose, and general prevention tips. What do you need?")

    # -------------------------
    # Bonus: PDF report download
    # -------------------------
    @app.get("/report/<int:prediction_id>.pdf")
    @login_required
    def report_pdf(prediction_id: int):
        pred = db.session.get(Prediction, prediction_id)
        if not pred:
            abort(404)
        if current_user.role != "doctor" and pred.user_id != current_user.id:
            abort(403)

        recs = recommendations_for(pred.risk_level)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=14)
        pdf.cell(0, 10, "Chronic Disease Risk Report", ln=1)

        pdf.set_font("Helvetica", size=11)
        display_name = pred.patient_name if pred.patient_name else pred.user.name
        pdf.cell(0, 8, f"Patient Name: {display_name}", ln=1)
        pdf.cell(0, 8, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=1)
        pdf.ln(2)

        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 8, f"Overall Risk: {str(pred.overall_risk).upper()}", ln=1)
        pdf.cell(0, 8, f"Most likely disease: {str(pred.most_likely_disease).capitalize()}", ln=1)
        pdf.ln(3)

        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 8, "Individual Risks:", ln=1)
        pdf.cell(0, 8, f"  - Diabetes: {pred.diabetes_risk*100:.1f}%", ln=1)
        pdf.cell(0, 8, f"  - Heart Disease: {pred.heart_risk*100:.1f}%", ln=1)
        pdf.cell(0, 8, f"  - Kidney Disease: {pred.kidney_risk*100:.1f}%", ln=1)
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

        import io
        pdf_bytes = pdf.output()
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"report_{prediction_id}.pdf",
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))

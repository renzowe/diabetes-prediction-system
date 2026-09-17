import pandas as pd
import joblib

from app.config import settings
from app.schemas.diabetes import DiabetesInput

# Se carga una sola vez, al iniciar el proceso (no en cada request)
_artifact = joblib.load(settings.MODEL_PATH)
_model = _artifact["model"]
_scaler = _artifact["scaler"]
_num_cols = _artifact["num_cols"]
_feature_names = _artifact["feature_names"]
_smoking_map = _artifact["smoking_map"]


def _build_feature_row(data: DiabetesInput) -> pd.DataFrame:
    """Replica exactamente el preprocesamiento aplicado en el notebook 02
    (codificacion de smoking_history y gender) para una unica fila de entrada."""

    row = {
        "age": data.edad,
        "hypertension": data.hipertension,
        "heart_disease": data.enfermedad_cardiaca,
        "smoking_history": _smoking_map[data.historial_tabaquismo],
        "bmi": data.imc,
        "HbA1c_level": data.hba1c,
        "blood_glucose_level": data.glucosa,
        "gender_Male": 1 if data.genero == "Male" else 0,
        "gender_Other": 1 if data.genero == "Other" else 0,
    }

    df = pd.DataFrame([row])
    df = df[_feature_names]  # asegura el mismo orden de columnas usado al entrenar
    df[_num_cols] = _scaler.transform(df[_num_cols])
    return df


def predict(data: DiabetesInput) -> tuple[int, float]:
    """Devuelve (prediccion 0/1, probabilidad de riesgo)."""
    df = _build_feature_row(data)
    proba = float(_model.predict_proba(df)[0, 1])
    pred = int(proba >= 0.5)
    return pred, proba


def nivel_riesgo(probabilidad: float) -> str:
    if probabilidad < 0.30:
        return "bajo"
    elif probabilidad < 0.60:
        return "moderado"
    return "alto"

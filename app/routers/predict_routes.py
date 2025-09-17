# app/routers/predict_routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import pickle
import numpy as np
import os

from app.database import supabase   # your supabase client

router = APIRouter()

MODELS_DIR = "app/models"

# Input schema (sensor readings only)
class SensorInput(BaseModel):
    temperature: float
    mq3_ppm: float
    as7263_r: float
    as7263_s: float
    as7263_t: float
    as7263_u: float
    as7263_v: float
    as7263_w: float

def load_models(factory_medicine_id: str):
    """Load scaler and models from local MODELS_DIR. Raises FileNotFoundError if missing."""
    paths = {
        "scaler": os.path.join(MODELS_DIR, f"{factory_medicine_id}_scaler.pkl"),
        "taste": os.path.join(MODELS_DIR, f"{factory_medicine_id}_taste.pkl"),
        "quality": os.path.join(MODELS_DIR, f"{factory_medicine_id}_quality.pkl"),
        "dilution": os.path.join(MODELS_DIR, f"{factory_medicine_id}_dilution.pkl"),
    }

    models = {}
    for key, p in paths.items():
        if not os.path.exists(p):
            raise FileNotFoundError(f"Model file not found: {p}. Please run /train/{factory_medicine_id} first.")
        with open(p, "rb") as f:
            models[key] = pickle.load(f)
    return models

@router.post("/{factory_medicine_id}")
def predict(factory_medicine_id: str, data: SensorInput):
    try:
        # 1) Load models
        models = load_models(factory_medicine_id)

        # 2) Prepare input and scale
        X = np.array([[data.temperature, data.mq3_ppm, data.as7263_r, data.as7263_s,
                       data.as7263_t, data.as7263_u, data.as7263_v, data.as7263_w]])
        X_scaled = models["scaler"].transform(X)

        # 3) Predict
        taste_pred = models["taste"].predict(X_scaled).tolist()[0]          # list of 5 floats
        quality_pred = models["quality"].predict(X_scaled).tolist()[0]     # maybe single float or array
        dilution_pred = models["dilution"].predict(X_scaled).tolist()[0]

        # normalize outputs to python floats
        taste_pred = [float(x) for x in taste_pred]
        # if quality_pred/dilution_pred are arrays, extract first element
        if isinstance(quality_pred, (list, tuple, np.ndarray)):
            quality_val = float(quality_pred[0])
        else:
            quality_val = float(quality_pred)

        if isinstance(dilution_pred, (list, tuple, np.ndarray)):
            dilution_val = float(dilution_pred[0])
        else:
            dilution_val = float(dilution_pred)

        # 4) Build DB row for predicted_data
        timestamp = datetime.utcnow().isoformat()  # use UTC timestamp
        row = {
            "factory_medicine_id": factory_medicine_id,
            "timestamp": timestamp,
            "temperature": float(data.temperature),
            "mq3_ppm": float(data.mq3_ppm),
            "as7263_r": float(data.as7263_r),
            "as7263_s": float(data.as7263_s),
            "as7263_t": float(data.as7263_t),
            "as7263_u": float(data.as7263_u),
            "as7263_v": float(data.as7263_v),
            "as7263_w": float(data.as7263_w),
            "taste_sweet": taste_pred[0],
            "taste_salty": taste_pred[1],
            "taste_bitter": taste_pred[2],
            "taste_sour": taste_pred[3],
            "taste_umami": taste_pred[4],
            "quality": quality_val,
            "dilution": dilution_val,
            # optional:
            "model_version": f"{factory_medicine_id}_v1"
        }

        # 5) Insert into Supabase
        res = supabase.table("predicted_data").insert(row).execute()

        # supabase response handling
        if hasattr(res, "error") and res.error:
            # supabase-py sometimes returns .error; handle gracefully
            raise Exception(f"DB insert error: {res.error}")

        # 6) Return predictions + DB metadata
        return {
            "status": "success",
            "prediction": {
                "taste": {
                    "sweet": taste_pred[0],
                    "salty": taste_pred[1],
                    "bitter": taste_pred[2],
                    "sour": taste_pred[3],
                    "umami": taste_pred[4]
                },
                "quality": quality_val,
                "dilution": dilution_val
            },
            "db_response": res.data if hasattr(res, "data") else str(res)
        }

    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

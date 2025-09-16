from fastapi import APIRouter
from pydantic import BaseModel
import pickle
import numpy as np
import os

router = APIRouter()

MODELS_DIR = "app/models"

# Input schema
class SensorInput(BaseModel):
    temperature: float
    mq3_ppm: float
    as7263_r: float
    as7263_s: float
    as7263_t: float
    as7263_u: float
    as7263_v: float
    as7263_w: float

# Load models utility
def load_models(factory_medicine_id):
    paths = ["scaler", "taste", "quality", "dilution"]
    models = {}
    for p in paths:
        file_path = os.path.join(MODELS_DIR, f"{factory_medicine_id}_{p}.pkl")
        with open(file_path, "rb") as f:
            models[p] = pickle.load(f)
    return models

@router.post("/predict/{factory_medicine_id}")
def predict(factory_medicine_id: str, data: SensorInput):
    models = load_models(factory_medicine_id)
    X = np.array([[data.temperature, data.mq3_ppm, data.as7263_r, data.as7263_s,
                   data.as7263_t, data.as7263_u, data.as7263_v, data.as7263_w]])
    X_scaled = models["scaler"].transform(X)
    
    taste_pred = models["taste"].predict(X_scaled).tolist()[0]
    quality_pred = models["quality"].predict(X_scaled).tolist()[0]
    dilution_pred = models["dilution"].predict(X_scaled).tolist()[0]
    
    return {
        "taste": taste_pred,
        "quality": quality_pred,
        "dilution": dilution_pred
    }

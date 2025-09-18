# app/routers/predict_routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import pickle
import numpy as np
import os
import requests

from app.database import supabase   # your supabase client

router = APIRouter()

MODELS_DIR = "app/models"

# 🔹 Your Telegram Bot Token
TELEGRAM_BOT_TOKEN = "8347556033:AAFfDhKFNGBOk7qag0zdi9Jfj5y2sm54THI"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


# ======================
# Schema for input
# ======================
class SensorInput(BaseModel):
    temperature: float
    mq3_ppm: float
    as7263_r: float
    as7263_s: float
    as7263_t: float
    as7263_u: float
    as7263_v: float
    as7263_w: float


# ======================
# Helpers
# ======================
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


def send_telegram(factory_medicine_id: str, message: dict):
    """Send prediction message to all Telegram chat_ids for this factory."""
    try:
        # 1) Fetch chat_ids from Supabase
        res = supabase.table("telegram_factory_map") \
            .select("chat_id") \
            .eq("factory_medicine_id", factory_medicine_id) \
            .execute()

        chat_ids = [row["chat_id"] for row in res.data]
        if not chat_ids:
            print(f"⚠️ No chat_ids found for {factory_medicine_id}")
            return

        # 2) Format message nicely
        text_message = (
            f"📢 *Prediction Update* for `{factory_medicine_id}`\n\n"
            f"🍬 Sweet: {message['taste']['sweet']}\n"
            f"🧂 Salty: {message['taste']['salty']}\n"
            f"🍋 Sour: {message['taste']['sour']}\n"
            f"☕ Bitter: {message['taste']['bitter']}\n"
            f"🍄 Umami: {message['taste']['umami']}\n\n"
            f"✨ Quality: {message['quality']}\n"
            f"💧 Dilution: {message['dilution']}"
        )

        # 3) Send to all chat_ids
        for chat_id in chat_ids:
            payload = {
                "chat_id": chat_id,
                "text": text_message,
                "parse_mode": "Markdown"
            }
            r = requests.post(TELEGRAM_API_URL, json=payload)
            if r.status_code != 200:
                print(f"⚠️ Failed to send to {chat_id}: {r.text}")

        print(f"✅ Sent Telegram notifications to {chat_ids}")

    except Exception as e:
        print(f"⚠️ Telegram error: {e}")


# ======================
# Routes
# ======================

# POST → Predict and insert into DB + Telegram notify
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
        taste_pred = models["taste"].predict(X_scaled).tolist()[0]
        quality_pred = models["quality"].predict(X_scaled).tolist()[0]
        dilution_pred = models["dilution"].predict(X_scaled).tolist()[0]

        # normalize outputs
        taste_pred = [float(x) for x in taste_pred]
        quality_val = float(quality_pred[0]) if isinstance(quality_pred, (list, tuple, np.ndarray)) else float(quality_pred)
        dilution_val = float(dilution_pred[0]) if isinstance(dilution_pred, (list, tuple, np.ndarray)) else float(dilution_pred)

        # 4) Build DB row
        timestamp = datetime.utcnow().isoformat()
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
            "model_version": f"{factory_medicine_id}_v1"
        }

        # 5) Insert into Supabase
        res = supabase.table("predicted_data").insert(row).execute()
        if hasattr(res, "error") and res.error:
            raise Exception(f"DB insert error: {res.error}")

        # 6) Send Telegram Notification
        send_telegram(factory_medicine_id, {
            "taste": {
                "sweet": taste_pred[0],
                "salty": taste_pred[1],
                "bitter": taste_pred[2],
                "sour": taste_pred[3],
                "umami": taste_pred[4]
            },
            "quality": quality_val,
            "dilution": dilution_val
        })

        # 7) Return predictions
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


# GET → Fetch predictions from DB
@router.get("/{factory_medicine_id}")
def get_predictions(factory_medicine_id: str):
    try:
        print(f"🔹 Fetching predictions for {factory_medicine_id}...")

        res = supabase.table("predicted_data") \
            .select("*") \
            .eq("factory_medicine_id", factory_medicine_id) \
            .order("timestamp", desc=True) \
            .limit(20) \
            .execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="No predictions found for this factory_medicine_id")

        print("✅ Retrieved predictions")
        return {"status": "success", "data": res.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

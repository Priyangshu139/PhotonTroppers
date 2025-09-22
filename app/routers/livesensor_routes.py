# app/routers/livesensor_routes.py

from fastapi import APIRouter, HTTPException
from app.database import supabase
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# ✅ Schema for live sensor data
class LiveSensorData(BaseModel):
    timestamp: datetime
    mq3_ppm: float
    as7263_r: float
    as7263_s: float
    as7263_t: float
    as7263_u: float
    as7263_v: float
    as7263_w: float


TABLE_NAME = "live_sensor"   # 🔹 Make sure this exists in Supabase


@router.post("/")
def upsert_live_sensor(data: LiveSensorData):
    """
    Upsert (insert or update) live sensor row.
    Always overwrites the same row (id=1).
    """
    try:
        payload = data.dict()
        payload["timestamp"] = payload["timestamp"].isoformat()

        # Always keep a single row with id=1
        payload["id"] = 1

        res = supabase.table(TABLE_NAME).upsert(payload, on_conflict="id").execute()
        return {"status": "success", "data": res.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/")
def get_live_sensor():
    """
    Fetch the single latest live sensor row (id=1).
    """
    try:
        res = supabase.table(TABLE_NAME).select("*").eq("id", 1).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="No live sensor data found")
        return {"status": "success", "data": res.data[0]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

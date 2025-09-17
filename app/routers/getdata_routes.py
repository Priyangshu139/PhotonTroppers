# app/routers/getdata_routes.py

from fastapi import APIRouter, HTTPException
from app.database import supabase

router = APIRouter()

@router.get("/{factory_medicine_id}")
def get_sensor_data(factory_medicine_id: str):
    try:
        print(f"🔹 Fetching sensor_data for {factory_medicine_id}...")

        res = supabase.table("sensor_data") \
                      .select("*") \
                      .eq("factory_medicine_id", factory_medicine_id) \
                      .order("timestamp", desc=True) \
                      .execute()

        if not res.data:
            return {
                "status": "success",
                "message": f"No data found for {factory_medicine_id}",
                "data": []
            }

        print(f"✅ Retrieved {len(res.data)} rows.")
        return {
            "status": "success",
            "count": len(res.data),
            "data": res.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

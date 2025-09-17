from fastapi import APIRouter, HTTPException
from app.database import supabase
from app.schemas import SensorData

router = APIRouter()

@router.post("/")
def insert_data(data: SensorData):
    try:
        # Convert the Pydantic model to dict and handle datetime serialization
        # Try Pydantic v2 method first, fallback to v1
        try:
            payload = data.model_dump()
        except AttributeError:
            payload = data.dict()
        
        # Convert datetime to ISO string format for Supabase
        if 'timestamp' in payload:
            payload['timestamp'] = payload['timestamp'].isoformat()
        
        res = supabase.table("sensor_data").insert(payload).execute()
        return {"status": "success", "data": res.data}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
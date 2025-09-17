from fastapi import APIRouter, HTTPException
from app.database import supabase
from app.schemas import PicronData

router = APIRouter()

@router.post("/{factory_medicine_id}")
def upsert_picron(factory_medicine_id: str, data: PicronData):
    try:
        payload = data.dict()
        payload["factory_medicine_id"] = factory_medicine_id

        print(f"🔹 Upserting picron data for {factory_medicine_id}...")

        res = supabase.table("picron_data")\
                      .upsert(payload, on_conflict="factory_medicine_id")\
                      .execute()

        print("✅ Upserted into picron_data")
        return {"status": "success", "data": res.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

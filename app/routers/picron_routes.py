# app/routers/picron_routes.py
from fastapi import APIRouter, HTTPException
from app.database import supabase
from app.schemas import PicronData

router = APIRouter()

# POST → Upsert Picron Data
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


# GET → Fetch Picron Data
@router.get("/{factory_medicine_id}")
def get_picron(factory_medicine_id: str):
    try:
        print(f"🔹 Fetching picron data for {factory_medicine_id}...")

        res = supabase.table("picron_data")\
                      .select("*")\
                      .eq("factory_medicine_id", factory_medicine_id)\
                      .execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="No data found for this factory_medicine_id")

        print("✅ Retrieved picron_data")
        return {"status": "success", "data": res.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

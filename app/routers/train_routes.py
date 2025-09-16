from fastapi import APIRouter, HTTPException
from app.utils.trainer import fetch_data, train_models, upload_model

router = APIRouter()

@router.post("/train/{factory_medicine_id}")
def train(factory_medicine_id: str):
    try:
        df = fetch_data(factory_medicine_id)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found for this factory_medicine_id")

        model_paths = train_models(df, factory_medicine_id)

        uploaded_urls = []
        for path in model_paths:
            url = upload_model(path)
            uploaded_urls.append(url)

        return {"status": "success", "uploaded_models": uploaded_urls}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

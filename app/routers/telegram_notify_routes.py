from fastapi import APIRouter, HTTPException, Body
import requests
import os
from app.database import supabase

router = APIRouter()

# 🔹 Your Telegram Bot Token
TELEGRAM_BOT_TOKEN = "8347556033:AAFfDhKFNGBOk7qag0zdi9Jfj5y2sm54THI"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

@router.post("/telegramnotify/{factory_medicine_id}")
def notify_factory(factory_medicine_id: str, message: dict = Body(...)):
    """
    Send notification message (JSON body) to all chat_ids registered
    for a given factory_medicine_id in Supabase.
    """
    try:
        # 🔹 1. Fetch all chat_ids for this factory
        res = supabase.table("telegram_factory_map")\
                      .select("chat_id")\
                      .eq("factory_medicine_id", factory_medicine_id)\
                      .execute()

        chat_ids = [row["chat_id"] for row in res.data]
        if not chat_ids:
            raise HTTPException(status_code=404, detail="No chat_ids found for this factory_medicine_id")

        # 🔹 2. Prepare message (convert dict to text for Telegram)
        text_message = f"📢 Notification for {factory_medicine_id}:\n{message}"

        # 🔹 3. Send to each chat_id
        for chat_id in chat_ids:
            payload = {
                "chat_id": chat_id,
                "text": text_message
            }
            r = requests.post(TELEGRAM_API_URL, json=payload)
            if r.status_code != 200:
                print(f"⚠️ Failed to send to {chat_id}: {r.text}")

        return {
            "status": "success",
            "factory_medicine_id": factory_medicine_id,
            "sent_to": chat_ids
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

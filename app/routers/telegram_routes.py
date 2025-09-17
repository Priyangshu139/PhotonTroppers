import time
from fastapi import APIRouter, HTTPException
import requests
from app.database import supabase, TELEGRAM_BOT_TOKEN

router = APIRouter()

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

@router.get("/{factory_medicine}")
def check_telegram(factory_medicine: str):
    try:
        print(f"🔹 Checking Telegram for message: {factory_medicine}")

        timeout = 30
        start = time.time()
        last_update_id = None
        collected_data = []  # store all chat_ids here

        while time.time() - start < timeout:
            url = f"{BASE_URL}/getUpdates"
            if last_update_id:
                url += f"?offset={last_update_id + 1}"

            res = requests.get(url).json()

            if "result" in res:
                for update in res["result"]:
                    last_update_id = update["update_id"]
                    if "message" in update:
                        text = update["message"].get("text", "").strip()
                        chat_id = update["message"]["chat"]["id"]

                        print(f"📩 Received: {text} from chat_id={chat_id}")

                        if text == factory_medicine:
                            collected_data.append({
                                "factory_medicine_id": factory_medicine,
                                "chat_id": str(chat_id)
                            })

            time.sleep(2)  # avoid flooding

        # ✅ After 30 sec, insert into Supabase
        if collected_data:
            response = supabase.table("telegram_factory_map").insert(collected_data).execute()
            print(f"✅ Inserted {len(collected_data)} rows into Supabase")
            return {"status": "success", "inserted": collected_data}
        else:
            return {"status": "timeout", "message": f"No matches for {factory_medicine} in 30s"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Telegram error: {str(e)}")

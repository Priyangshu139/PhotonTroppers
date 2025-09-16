import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Test connection: fetch 1 row from sensor_data
try:
    res = supabase.table("sensor_data").select("*").limit(1).execute()
    if res.data is not None:
        print("✅ Connected to Supabase successfully!")
        print("Sample row:", res.data)
    else:
        print("⚠️ Table exists but no rows found yet.")
except Exception as e:
    print("❌ Connection failed:", e)

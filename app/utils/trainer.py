import pandas as pd
import pickle
from sklearn.svm import SVR
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler
from app.database import supabase
import os

# Local models directory
MODELS_DIR = "app/models"
os.makedirs(MODELS_DIR, exist_ok=True)

# Columns
INPUT_COLS = ["temperature", "mq3_ppm", "as7263_r", "as7263_s", "as7263_t", "as7263_u", "as7263_v", "as7263_w"]
TASTE_COLS = ["taste_sweet", "taste_salty", "taste_bitter", "taste_sour", "taste_umami"]
QUALITY_COL = "quality"
DILUTION_COL = "dilution"


def fetch_data(factory_medicine_id: str) -> pd.DataFrame:
    """Fetch all rows for a given factory_medicine_id from Supabase."""
    print(f"🔹 Fetching data for {factory_medicine_id} from Supabase...")
    res = supabase.table("sensor_data").select("*").eq("factory_medicine_id", factory_medicine_id).execute()
    data = res.data
    if not data:
        print("⚠️ No data found!")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    print(f"✅ Fetched {len(df)} rows.")
    return df


def train_models(df: pd.DataFrame, factory_medicine_id: str):
    """Train 3 SVM models and save locally."""
    
    X = df[INPUT_COLS]
    
    # Scale inputs
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    scaler_path = os.path.join(MODELS_DIR, f"{factory_medicine_id}_scaler.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"✅ Scaler saved: {scaler_path}")

    # ---- Taste Model ----
    y_taste = df[TASTE_COLS]
    taste_model = MultiOutputRegressor(SVR())
    taste_model.fit(X_scaled, y_taste)
    taste_path = os.path.join(MODELS_DIR, f"{factory_medicine_id}_taste.pkl")
    with open(taste_path, "wb") as f:
        pickle.dump(taste_model, f)
    print(f"✅ Taste model trained and saved: {taste_path}")

    # ---- Quality Model ----
    y_quality = df[QUALITY_COL]
    quality_model = SVR()
    quality_model.fit(X_scaled, y_quality)
    quality_path = os.path.join(MODELS_DIR, f"{factory_medicine_id}_quality.pkl")
    with open(quality_path, "wb") as f:
        pickle.dump(quality_model, f)
    print(f"✅ Quality model trained and saved: {quality_path}")

    # ---- Dilution Model ----
    y_dilution = df[DILUTION_COL]
    dilution_model = SVR()
    dilution_model.fit(X_scaled, y_dilution)
    dilution_path = os.path.join(MODELS_DIR, f"{factory_medicine_id}_dilution.pkl")
    with open(dilution_path, "wb") as f:
        pickle.dump(dilution_model, f)
    print(f"✅ Dilution model trained and saved: {dilution_path}")

    return [taste_path, quality_path, dilution_path, scaler_path]


def upload_model(file_path: str):
    """Upload a local .pkl file to Supabase Storage bucket 'models'."""
    file_name = os.path.basename(file_path)
    print(f"🔹 Uploading {file_name} to Supabase Storage...")
    
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
            
        # Try simple upload first (without upsert for new files)
        try:
            res = supabase.storage.from_("models").upload(
                path=file_name,
                file=file_content
            )
            print(f"✅ Uploaded {file_name}")
        except Exception as upload_err:
            # If file exists, try to remove and re-upload
            if "already exists" in str(upload_err).lower() or "duplicate" in str(upload_err).lower():
                print(f"🔄 File exists, replacing {file_name}...")
                try:
                    # Remove existing file
                    supabase.storage.from_("models").remove([file_name])
                    # Upload again
                    res = supabase.storage.from_("models").upload(
                        path=file_name,
                        file=file_content
                    )
                    print(f"✅ Replaced {file_name}")
                except Exception as replace_err:
                    print(f"❌ Replace failed: {str(replace_err)}")
                    raise replace_err
            else:
                raise upload_err
        
        # Return public URL for reference
        try:
            public_url = supabase.storage.from_("models").get_public_url(file_name)
            return public_url.data if hasattr(public_url, 'data') else str(public_url)
        except:
            return f"File uploaded as {file_name}"
        
    except Exception as e:
        print(f"❌ Upload failed for {file_name}: {str(e)}")
        raise e
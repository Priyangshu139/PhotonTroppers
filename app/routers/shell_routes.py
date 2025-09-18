from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import io

router = APIRouter()

@router.get("/{factory_medicine}")
def get_picron_script_installer(factory_medicine: str, request: Request):
    """
    Generates a shell script that creates and runs the Picron Python script.
    """
    # Dynamically determine the base URL from the incoming request
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    python_filename = f"{factory_medicine}.py"

    # The full Python script content is defined first.
    # Note: All curly braces {} are doubled to {{}} to escape them in the f-string.
    python_script_content = f'''
import smbus
import time
import struct
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import RPi.GPIO as GPIO
import requests
from datetime import datetime
import sys

# --- API Configuration ---
BASE_URL = "{base_url}"
FACTORY_MEDICINE_ID = "{factory_medicine}"

# --- Hardware Configuration ---
IR_SENSOR_PIN = 16
IR_SENSOR_ACTIVE_LOW = True
ACCESS_DOOR_PIN = 25
DELAY_AFTER_TRIGGER = 2
READING_INTERVAL = 0.005
NUM_READINGS = 10
ALPHA = 0.3

# --- AS726X Sensor Constants (abbreviated for clarity) ---
AS726X_ADDR = 0x49
AS726x_CONTROL_SETUP = 0x04
AS726x_LED_CONTROL = 0x07
AS726x_INT_T = 0x05
AS726x_HW_VERSION = 0x01
AS72XX_SLAVE_STATUS_REG = 0x00
AS72XX_SLAVE_WRITE_REG = 0x01
AS72XX_SLAVE_READ_REG = 0x02
AS72XX_SLAVE_TX_VALID = 0x02
AS72XX_SLAVE_RX_VALID = 0x01
SENSORTYPE_AS7263 = 0x3F
AS7263_R_CAL = 0x14
AS7263_S_CAL = 0x18
AS7263_T_CAL = 0x1C
AS7263_U_CAL = 0x20
AS7263_V_CAL = 0x24
AS7263_W_CAL = 0x28
POLLING_DELAY = 0.005
MAX_RETRIES = 3
TIMEOUT = 3.0

class AS726X:
    """Abridged AS726X sensor class for brevity. Assumes AS7263."""
    def __init__(self, i2c_bus=1, address=AS726X_ADDR):
        self.bus = smbus.SMBus(i2c_bus)
        self.address = address
        self.sensor_version = 0

    def begin(self, gain=3, measurement_mode=3):
        try:
            self.sensor_version = self.virtual_read_register(AS726x_HW_VERSION)
            if self.sensor_version != SENSORTYPE_AS7263:
                print(f"❌ Invalid sensor version: {{self.sensor_version:02X}}")
                return False
            self.virtual_write_register(AS726x_INT_T, 50)
            value = self.virtual_read_register(AS726x_CONTROL_SETUP)
            value &= 0b11000011
            value |= (gain << 4) | (measurement_mode << 2)
            self.virtual_write_register(AS726x_CONTROL_SETUP, value)
            value = self.virtual_read_register(AS726x_LED_CONTROL)
            value &= 0b11111110
            self.virtual_write_register(AS726x_LED_CONTROL, value)
            return True
        except Exception as e:
            print(f"❌ Error initializing sensor: {{e}}")
            return False

    def take_measurements(self):
        try:
            value = self.virtual_read_register(AS726x_CONTROL_SETUP)
            value &= ~(1 << 1)
            self.virtual_write_register(AS726x_CONTROL_SETUP, value)
            value |= (3 << 2)
            self.virtual_write_register(AS726x_CONTROL_SETUP, value)
            start_time = time.time()
            while not (self.virtual_read_register(AS726x_CONTROL_SETUP) & (1 << 1)):
                time.sleep(POLLING_DELAY)
                if time.time() - start_time > TIMEOUT:
                    raise Exception("Timeout waiting for data")
            return True
        except Exception as e:
            print(f"❌ Error taking measurements: {{e}}")
            return False

    def get_calibrated_values(self):
        cal_addresses = [AS7263_R_CAL, AS7263_S_CAL, AS7263_T_CAL, AS7263_U_CAL, AS7263_V_CAL, AS7263_W_CAL]
        values = [self.get_calibrated_value(addr) for addr in cal_addresses]
        return values

    def get_calibrated_value(self, cal_address):
        try:
            b0 = self.virtual_read_register(cal_address + 0)
            b1 = self.virtual_read_register(cal_address + 1)
            b2 = self.virtual_read_register(cal_address + 2)
            b3 = self.virtual_read_register(cal_address + 3)
            cal_bytes = (b0 << 24) | (b1 << 16) | (b2 << 8) | b3
            return struct.unpack('>f', cal_bytes.to_bytes(4, 'big'))[0]
        except Exception:
            return -1.0

    def virtual_read_register(self, virtual_addr):
        for _ in range(MAX_RETRIES + 1):
            status = self.read_register(AS72XX_SLAVE_STATUS_REG)
            if status & AS72XX_SLAVE_RX_VALID: self.read_register(AS72XX_SLAVE_READ_REG)
            while self.read_register(AS72XX_SLAVE_STATUS_REG) & AS72XX_SLAVE_TX_VALID: time.sleep(POLLING_DELAY)
            self.write_register(AS72XX_SLAVE_WRITE_REG, virtual_addr)
            while not (self.read_register(AS72XX_SLAVE_STATUS_REG) & AS72XX_SLAVE_RX_VALID): time.sleep(POLLING_DELAY)
            result = self.read_register(AS72XX_SLAVE_READ_REG)
            if result != 0xFF: return result
        return 0xFF

    def virtual_write_register(self, virtual_addr, data_to_write):
        for _ in range(MAX_RETRIES + 1):
            while self.read_register(AS72XX_SLAVE_STATUS_REG) & AS72XX_SLAVE_TX_VALID: time.sleep(POLLING_DELAY)
            self.write_register(AS72XX_SLAVE_WRITE_REG, virtual_addr | 0x80)
            while self.read_register(AS72XX_SLAVE_STATUS_REG) & AS72XX_SLAVE_TX_VALID: time.sleep(POLLING_DELAY)
            if self.write_register(AS72XX_SLAVE_WRITE_REG, data_to_write) == 0: return 0
        return -1

    def read_register(self, addr):
        try: return self.bus.read_byte_data(self.address, addr)
        except Exception: return 0xFF

    def write_register(self, addr, val):
        try:
            self.bus.write_byte_data(self.address, addr, val)
            return 0
        except Exception: return -1

def exponential_weighted_average(previous, current, alpha):
    if previous is None: return current
    return alpha * current + (1 - alpha) * previous

def is_ir_sensor_active():
    ir_state = GPIO.input(IR_SENSOR_PIN)
    return not ir_state if IR_SENSOR_ACTIVE_LOW else ir_state

def reset_status():
    print("\\n🔄 Attempting to reset status to 0...")
    try:
        url_get = f"{{BASE_URL}}/picron/{{FACTORY_MEDICINE_ID}}"
        res = requests.get(url_get, timeout=5)
        if res.status_code != 200:
            print(f"❌ Failed fetching current picron row for reset: {{res.text}}")
            return
        row = res.json().get("data", [{{}}])[0]
        payload = {{k: row.get(k) for k in ["factory_medicine_id", "taste_sweet", "taste_salty", "taste_bitter", "taste_sour", "taste_umami", "quality", "dilution", "factory"]}}
        payload["status"] = 0
        
        url_post = f"{{BASE_URL}}/picron/{{FACTORY_MEDICINE_ID}}"
        res = requests.post(url_post, json=payload, timeout=5)
        if res.status_code == 200:
            print("✅ Status successfully reset to 0.")
        else:
            print(f"❌ Failed to reset status: {{res.text}}")
    except requests.exceptions.RequestException as e:
        print(f"💥 API connection error during reset: {{e}}")

def handle_status_reset_with_countdown():
    print("\\n✅ Measurement complete. Please remove the sample.")
    while is_ir_sensor_active():
        time.sleep(0.2)
    
    print("🕒 Sample removed. Starting 15-second countdown to reset status.")
    for i in range(15, 0, -1):
        print(f"Resetting in {{i}} seconds... (Do not re-insert sample)")
        time.sleep(1)
        if is_ir_sensor_active():
            print("\\n⚠️ Countdown aborted! Sample re-detected. Reset cancelled.")
            return
    reset_status()

def take_all_readings():
    print("Waiting for sample placement...")
    while not is_ir_sensor_active():
        time.sleep(0.2)
    
    print(f"🔬 Sample detected. Waiting {{DELAY_AFTER_TRIGGER}}s before measurement...")
    time.sleep(DELAY_AFTER_TRIGGER)

    if not is_ir_sensor_active():
        print("❌ Sample removed prematurely. Aborting.")
        return None, None

    weighted_spectral_values = None
    weighted_alcohol_value = None
    readings_taken = 0

    for i in range(NUM_READINGS):
        if not is_ir_sensor_active():
            print(f"❌ Sample removed after {{readings_taken}} readings. Aborting.")
            return None, None
        
        print(f"    Reading {{i+1}}/{{NUM_READINGS}}...")
        
        spectral_values = sensor.get_calibrated_values() if sensor.take_measurements() else [-1.0] * 6
        alcohol_value = alcohol_chan.voltage if alcohol_sensor_available else -1.0
        
        if weighted_spectral_values is None:
            weighted_spectral_values = spectral_values
        else:
            for j in range(6):
                weighted_spectral_values[j] = exponential_weighted_average(weighted_spectral_values[j], spectral_values[j], ALPHA)
        
        weighted_alcohol_value = exponential_weighted_average(weighted_alcohol_value, alcohol_value, ALPHA)
        readings_taken += 1
        if i < NUM_READINGS - 1:
            time.sleep(READING_INTERVAL)
            
    return weighted_spectral_values, weighted_alcohol_value

def handle_dataset_flow(row):
    print("\\n--- STATUS 1: DATASET ENTRY ---")
    spectral, alcohol = take_all_readings()
    
    if spectral is None or alcohol is None:
        print("Measurement failed. Skipping API post.")
        reset_status()
        return

    payload = {{
        "factory_medicine_id": FACTORY_MEDICINE_ID,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "temperature": 0,
        "mq3_ppm": alcohol,
        "as7263_r": spectral[0], "as7263_s": spectral[1], "as7263_t": spectral[2],
        "as7263_u": spectral[3], "as7263_v": spectral[4], "as7263_w": spectral[5],
        "taste_sweet": row.get("taste_sweet", 0), "taste_salty": row.get("taste_salty", 0),
        "taste_bitter": row.get("taste_bitter", 0), "taste_sour": row.get("taste_sour", 0),
        "taste_umami": row.get("taste_umami", 0), "quality": row.get("quality", "N/A"),
        "dilution": row.get("dilution", 1.0),
    }}

    try:
        url = f"{{BASE_URL}}/data/"
        print("📤 Sending data to API...")
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("✅ Dataset POST successful:", res.json())
        else:
            print(f"❌ Dataset POST failed: {{res.status_code}} {{res.text}}")
    except requests.exceptions.RequestException as e:
        print(f"💥 API connection error: {{e}}")

    handle_status_reset_with_countdown()

def handle_predict_flow():
    print("\\n--- STATUS 2: PREDICTION ---")
    spectral, alcohol = take_all_readings()
    
    if spectral is None or alcohol is None:
        print("Measurement failed. Skipping API post.")
        reset_status()
        return

    payload = {{
        "temperature": 0, "mq3_ppm": alcohol, "as7263_r": spectral[0],
        "as7263_s": spectral[1], "as7263_t": spectral[2], "as7263_u": spectral[3],
        "as7263_v": spectral[4], "as7263_w": spectral[5],
    }}
    
    try:
        url = f"{{BASE_URL}}/predict/{{FACTORY_MEDICINE_ID}}"
        print("📤 Sending data to API for prediction...")
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("✅ Predict POST successful:", res.json())
        else:
            print(f"❌ Predict POST failed: {{res.status_code}} {{res.text}}")
    except requests.exceptions.RequestException as e:
        print(f"💥 API connection error: {{e}}")

    handle_status_reset_with_countdown()

def poll_picron():
    while True:
        try:
            url = f"{{BASE_URL}}/picron/{{FACTORY_MEDICINE_ID}}"
            res = requests.get(url, timeout=5)
            
            if res.status_code == 200:
                data = res.json().get("data", [])
                if not data:
                    print(f"⚠️ No picron row found for {{FACTORY_MEDICINE_ID}}")
                else:
                    row = data[0]
                    status = row.get("status", 0)
                    if status == 1:
                        handle_dataset_flow(row)
                    elif status == 2:
                        handle_predict_flow()
                    else:
                        print(f"⏳ Waiting... current status is {{status}}.")
            else:
                print(f"❌ Failed to fetch picron: {{res.text}}")
        except requests.exceptions.RequestException as e:
            print(f"💥 API connection error while polling: {{e}}")
        
        time.sleep(5)

if __name__ == "__main__":
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(IR_SENSOR_PIN, GPIO.IN)
        GPIO.setup(ACCESS_DOOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        try:
            i2c_ads = busio.I2C(board.SCL, board.SDA)
            ads = ADS.ADS1115(i2c_ads)
            ads.gain = 1
            alcohol_chan = AnalogIn(ads, ADS.P0)
            alcohol_sensor_available = True
            print("✅ Alcohol sensor initialized.")
        except Exception as e:
            print(f"⚠️ Failed to initialize alcohol sensor: {{e}}")
            alcohol_sensor_available = False

        try:
            sensor = AS726X()
            if sensor.begin():
                print("✅ AS7263 sensor initialized.")
            else:
                raise RuntimeError("Failed to begin AS7263 sensor.")
        except Exception as e:
            print(f"❌ CRITICAL: Could not initialize AS7263 sensor: {{e}}. Exiting.")
            sys.exit(1)

        print("\\n--- System Ready ---")
        poll_picron()

    except KeyboardInterrupt:
        print("\\nProgram terminated by user.")
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up. Exiting.")
'''

    # Now, create the shell script that will contain the Python script
    # A 'here document' (cat <<'EOF') is used to safely write the multi-line Python script to a file.
    shell_script_content = f"""#!/bin/bash
# Installer and runner script for Picron device

echo "--- Creating Python script: {python_filename} ---"

# Use a 'here document' to write the Python script to a file.
# The 'EOF' is quoted to prevent the shell from expanding variables ($) inside the block.
cat > "{python_filename}" <<'EOF'
{python_script_content}
EOF

echo "--- Python script created successfully. ---"
echo "--- Making the script executable (optional, for consistency) ---"
chmod +x "{python_filename}"

echo "--- Running the Python script... ---"
# Run the newly created Python file
python3 "{python_filename}"
"""

    # Create an in-memory file-like object from the shell script content
    file_like = io.BytesIO(shell_script_content.encode("utf-8"))

    # Return the shell script as a downloadable file
    return StreamingResponse(
        file_like,
        media_type="application/x-sh",
        headers={"Content-Disposition": f"attachment; filename={factory_medicine}.sh"}
    )
import google.generativeai as genai
from prediction_service.utils import generate_rul_prompt
from datetime import datetime, timedelta
import json
import sys
import os
import time
import numpy as np
import paho.mqtt.client as mqtt
import config
from influxdb_client import InfluxDBClient
from configs.config import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET


# Tự động chọn module dựa trên Config
if config.USE_SIMULATION:
    from mock_lora_worker import LoRaWorker
    # Mock mode không cần BOARD setup của Raspberry Pi

    class DummyBoard:
        def setup(self): pass
        def teardown(self): pass
    BOARD = DummyBoard()
else:
    from lora_worker import LoRaWorker
    from SX127x.board_config import BOARD
    from SX127x.LoRa import MODE  # Chỉ import MODE khi dùng thật

# --- BỘ NHỚ TRẠNG THÁI (Source of Truth) ---
next_time = datetime.min
INTERVAL = 60  # seconds

device_states = {
    1: {"auto_mode": False, "yellow_color": False, "led_brightness": 0},
    2: {"auto_mode": False, "yellow_color": False, "led_brightness": 0},
    3: {"auto_mode": False, "yellow_color": False, "led_brightness": 0}
}

lora = None
tb_client = mqtt.Client()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# --- XỬ LÝ DỮ LIỆU NHẬN ĐƯỢC TỪ LORA (Real Data) ---

def safe_extract_text(response):
    if not response.candidates:
        return None

    candidate = response.candidates[0]

    if not candidate.content or not candidate.content.parts:
        return None

    return "".join(
        part.text for part in candidate.content.parts if hasattr(part, "text")
    )


def query_last_1h(device_name):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()

    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -5h)
      |> filter(fn: (r) => r["_measurement"] == "street_light")
      |> filter(fn: (r) => r["_field"] == "voltage" or r["_field"] == "current" or r["_field"] == "power" or r["_field"] == "brightness" or r["_field"] == "light")
      |> filter(fn: (r) => r["device"] == "{device_name}")
      |> aggregateWindow(
            every: 5m,
            fn: mean,
            createEmpty: true
        )
        |> fill(usePrevious: true)
        |> sort(columns: ["_time"])
    '''

    df = query_api.query_data_frame(query)
    df = df[["_time", "_field", "_value"]]

    # Keep only needed columns
    df_pivot = df.pivot(
        index="_time",
        columns="_field",
        values="_value"
    )
    df_pivot = (
        df_pivot
        .sort_index()
        .ffill()
        .bfill()
    )

    timestamps = df_pivot.index.to_list()

    values = {
        "voltage": df_pivot["voltage"].to_list() if "voltage" in df_pivot else [],
        "current": df_pivot["current"].to_list() if "current" in df_pivot else [],
        "power": df_pivot["power"].to_list() if "power" in df_pivot else [],
        "brightness": df_pivot["brightness"].to_list() if "brightness" in df_pivot else [],
        "light": df_pivot["light"].to_list() if "light" in df_pivot else []
    }

    return timestamps, values


def predict_rul_with_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.5-flash")

    response = model.generate_content(
        contents=[
            {
                "role": "user",
                "parts": [
                    {"text": prompt['instruction']},
                    {"text": prompt['input']}
                ]
            }
        ],
        generation_config={
            "temperature": 0.2,
            "top_p": 0.9,
            "max_output_tokens": 128
        }
    )

    # Gemini returns text – extract integer safely
    text = safe_extract_text(response)

    predicted_rul = int("".join(c for c in text if c.isdigit()))

    return predicted_rul


def process_lora_data(data):
    global next_time
    current_time = datetime.now()
    # Data này là JSON thật từ ESP32 gửi lên
    # Ví dụ: {"deviceID":1, "vol":220, "cur":2...}

    if current_time > next_time:
        dev_id = data.get("deviceID")

        if dev_id in config.DEVICE_MAP:
            dev_name = config.DEVICE_MAP[dev_id]

            # 2️⃣ Query past 1 hour data from Influx
            timestamps, sensor_data = query_last_1h(dev_name.replace(" ", "_"))
            sensor_data["last_rul"] = [data["rul"]]
            # sensor_data = {
            #     "voltage": [1],
            #     "current": [1.19],
            #     "power": [20]
            # }

            rul_prompt = generate_rul_prompt(
                device_id=dev_id, values=sensor_data, timestamps=timestamps)
            print(rul_prompt)

            # 3️⃣ Predict RUL
            rul = predict_rul_with_gemini(rul_prompt)

            # 2. Đóng gói Telemetry (Thông số cảm biến)
            telemetry = {
                "rul":  rul  # rul
            }
            print(telemetry)

            # 4. Gửi lên ThingsBoard
            tb_client.publish("v1/gateway/telemetry",
                              json.dumps({dev_name: [telemetry]}))

            next_time = current_time + timedelta(seconds=INTERVAL)

            print(f"-> Synced {dev_name} to Cloud.")

# --- MQTT HANDLERS ---


def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected code: {rc}")
    client.subscribe("v1/gateway/rpc")
    for name in config.DEVICE_MAP.values():
        client.publish("v1/gateway/connect", json.dumps({"device": name}))


def on_message(client, userdata, msg):
    try:
        pass

    except Exception as e:
        print(f"RPC Error: {e}")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    try:
        # 1. Setup LoRa
        BOARD.setup()
        # Truyền hàm process_lora_data vào để LoRa gọi khi có tin mới
        lora = LoRaWorker(verbose=False, callback=process_lora_data)

        if not config.USE_SIMULATION:
            lora.set_mode(MODE.STDBY)
            lora.set_freq(config.LORA_FREQUENCY)
            lora.set_sync_word(config.LORA_SYNC_WORD)
            lora.set_pa_config(pa_select=1)
            lora.set_mode(MODE.RXCONT)
            print("--- REAL LoRa Hardware Started ---")
        else:
            print("--- MOCK Simulation Started ---")

        # 2. Setup MQTT
        tb_client.username_pw_set(config.ACCESS_TOKEN)
        tb_client.on_connect = on_connect
        tb_client.on_message = on_message
        tb_client.connect(config.THINGSBOARD_HOST, 1883, 60)
        tb_client.loop_start()
        print("--- MQTT Connected ---")

        # 3. Vòng lặp chính (Giờ chỉ cần giữ chương trình chạy)
        while True:
            time.sleep(3)

    except KeyboardInterrupt:
        print("Exit.")
        if hasattr(lora, 'close'):
            lora.close()  # Dừng thread giả lập nếu có
        BOARD.teardown()
        tb_client.disconnect()

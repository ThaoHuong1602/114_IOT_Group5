from datetime import datetime, timedelta
import json
import sys
import time
import numpy as np
import paho.mqtt.client as mqtt
import config

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

# --- XỬ LÝ DỮ LIỆU NHẬN ĐƯỢC TỪ LORA (Real Data) ---


# def query_last_1h(device_name):
#     query = f'''
#     from(bucket: "{INFLUX_BUCKET}")
#       |> range(start: -1h)
#       |> filter(fn: (r) => r["device"] == "{device_name}")
#       |> filter(fn: (r) => r["_measurement"] == "telemetry")
#       |> filter(fn: (r) => r["_field"] == "vol" or r["_field"] == "cur")
#     '''

#     tables = query_api.query(query)
#     values = {"vol": [], "cur": []}

#     for table in tables:
#         for record in table.records:
#             values[record.get_field()].append(record.get_value())

#     return values


def predict_rul(sensor_data):
    """
    sensor_data = {
        "voltage": [...],
        "current": [...],
        "power":   [...]
    }
    Returns:
        RUL (hours)
    """

    # Safety check
    if len(sensor_data.get("voltage", [])) == 0:
        return 0

    # Averages over last 1 hour
    vol_avg = np.mean(sensor_data["voltage"])
    cur_avg = np.mean(sensor_data["current"])
    pow_avg = np.mean(sensor_data["power"])

    # ===== Degradation components =====
    # 1. Voltage stress (deviation from nominal)
    voltage_stress = abs(vol_avg - 220) / 220          # normalized

    # 2. Current stress (normalized to rated current, e.g. 5A)
    rated_current = 5.0
    current_stress = cur_avg / rated_current

    # 3. Power stress (normalized to rated power, e.g. 100W)
    rated_power = 100.0
    power_stress = pow_avg / rated_power

    # ===== Total degradation score =====
    degradation = (
        0.4 * voltage_stress +
        0.35 * current_stress +
        0.25 * power_stress
    )

    # Clamp degradation
    degradation = min(degradation, 1.5)

    # ===== Convert to RUL =====
    # Assume max useful life = 100 hours (demo)
    max_life = 100
    rul = max(0, int(max_life * (1 - degradation)))

    return rul


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
            # sensor_data = query_last_1h(dev_name)
            sensor_data = {
                "voltage": [1],
                "current": [1.19],
                "power": [20]
            }

            # 3️⃣ Predict RUL
            rul = predict_rul(sensor_data)

            # 2. Đóng gói Telemetry (Thông số cảm biến)
            telemetry = {
                "rul":  800  # rul
            }

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

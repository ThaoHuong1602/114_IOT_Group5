import time
import json
import sys
import paho.mqtt.client as mqtt
import config
from influx_worker import InfluxWorker

# --- CẤU HÌNH PHẦN CỨNG ---
# Tự động chọn module dựa trên Config
if config.USE_SIMULATION:
    from mock_lora_worker import LoRaWorker

    class DummyBoard:
        def setup(self): pass
        def teardown(self): pass
    BOARD = DummyBoard()
else:
    from lora_worker import LoRaWorker
    from SX127x.board_config import BOARD
    from SX127x.LoRa import MODE

# --- BỘ NHỚ TRẠNG THÁI (Source of Truth) ---
device_states = {
    1: {"auto_mode": False, "yellow_color": False, "led_brightness": 0},
    2: {"auto_mode": False, "yellow_color": False, "led_brightness": 0},
    3: {"auto_mode": False, "yellow_color": False, "led_brightness": 0}
}

client = mqtt.Client()
lora = None

# --- KHỞI TẠO INFLUX WORKER ---
try:
    influx_worker = InfluxWorker()
    print("[INIT] InfluxDB Worker initialized.")
except Exception as e:
    print(f"[ERROR] Failed to init InfluxDB: {e}")
    influx_worker = None

# --- XỬ LÝ DỮ LIỆU TỪ LORA GỬI LÊN (UPLINK) ---


def process_lora_data(data):
    # data: {"deviceID":1, "vol":220, "cur":2...}
    dev_id = data.get("deviceID")

    if dev_id in config.DEVICE_MAP:
        dev_name = config.DEVICE_MAP[dev_id]

        # 1. Cập nhật bộ nhớ trạng thái Gateway
        if "auto_mode" in data:
            device_states[dev_id]["auto_mode"] = data["auto_mode"]
        if "ledBrightness" in data:
            device_states[dev_id]["led_brightness"] = data["ledBrightness"]
        if "yellow_color" in data:
            device_states[dev_id]["yellow_color"] = data["yellow_color"]

        # 2. Đóng gói Telemetry
        telemetry = {
            "light": data.get("ambientLightIntensity", 0),
            "voltage": data.get("voltage", 0),
            "current": data.get("current", -1),
            "power": data.get("power", 0),
            "motion": data.get("isMotion", False),
            "raining": data.get("isRain", False),
            "led_brightness": device_states[dev_id]["led_brightness"]
        }

        # 3. Đóng gói Attributes
        attributes = {
            "auto_mode": device_states[dev_id]["auto_mode"],
            "yellow_color": device_states[dev_id]["yellow_color"],
            "led_brightness": device_states[dev_id]["led_brightness"]
        }

        # 4. Gửi ThingsBoard
        client.publish("v1/gateway/telemetry",
                       json.dumps({dev_name: [telemetry]}))
        client.publish("v1/gateway/attributes",
                       json.dumps({dev_name: attributes}))

        # 5. Gửi InfluxDB
        # if influx_worker:
        #     influx_worker.send_data(dev_name, data, device_states[dev_id])

        # print(f"-> Synced {dev_name} to Cloud.")

# --- MQTT HANDLERS ---


def on_connect(client, userdata, flags, rc):
    # print(f"[MQTT] Connected code: {rc}")
    client.subscribe("v1/gateway/rpc")
    for name in config.DEVICE_MAP.values():
        client.publish("v1/gateway/connect", json.dumps({"device": name}))

# --- [QUAN TRỌNG] HÀM XỬ LÝ LỆNH TỪ CLOUD (DOWNLINK) ---


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"\n[RPC RAW] {payload}")  # In ra để debug xem JSON hay Value

        device_name = payload.get("device")
        data = payload.get("data")
        method = data.get("method")
        raw_params = data.get("params")

        # --- BÓC TÁCH DỮ LIỆU (PARSING) ---
        # Mặc định coi params là giá trị đơn (dùng cho Widget)
        val = raw_params

        # Nếu params là Dictionary (dùng cho Rule Chain) -> Lấy giá trị bên trong
        if isinstance(raw_params, dict):
            if method == "setAutoMode":
                val = raw_params.get("auto_mode", False)
            elif method == "setYellowColor":
                val = raw_params.get("yellow_color", False)
            elif method == "setBrightness":
                val = raw_params.get("led_brightness", 0)

        # Tìm ID thiết bị
        target_id = 0
        for pid, pname in config.DEVICE_MAP.items():
            if pname == device_name:
                target_id = pid
                break

        if target_id != 0:
            # --- CẬP NHẬT TRẠNG THÁI & GỬI LORA ---

            if method == "setAutoMode":
                device_states[target_id]["auto_mode"] = val
                # Gửi lệnh AUTO: 1=ON, 0=OFF
                if lora:
                    lora.send_command(target_id, "AUTO", 1 if val else 0)

            elif method == "setYellowColor":
                device_states[target_id]["yellow_color"] = val
                # Gửi lệnh COLOR: 2=Yellow, 1=White
                if lora:
                    lora.send_command(target_id, "COLOR", 2 if val else 1)

            elif method == "setBrightness":
                # Ép kiểu int để tránh lỗi
                int_val = int(val)
                device_states[target_id]["led_brightness"] = int_val
                if lora:
                    lora.send_command(target_id, "DIM", int_val)

            # Phản hồi lại Thingsboard để cập nhật giao diện
            force_update_attributes(target_id)

    except Exception as e:
        print(f"[ERROR] RPC Processing: {e}")


def force_update_attributes(device_id):
    dev_name = config.DEVICE_MAP[device_id]
    attr = {
        "auto_mode": device_states[device_id]["auto_mode"],
        "yellow_color": device_states[device_id]["yellow_color"],
        "led_brightness": device_states[device_id]["led_brightness"]
    }

    print(
        f"[RPC/To Thingsboard] Forcing attribute update for {dev_name}: {attr}")
    client.publish("v1/gateway/attributes", json.dumps({dev_name: attr}))


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    try:
        # 1. Setup LoRa
        BOARD.setup()
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
        client.username_pw_set(config.ACCESS_TOKEN)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(config.THINGSBOARD_HOST, 1883, 60)
        client.loop_start()
        print("--- MQTT Connected ---")

        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("Exit.")
        if hasattr(lora, 'close'):
            lora.close()
        BOARD.teardown()
        client.disconnect()

from datetime import timedelta
from typing import Dict
import numpy as np
import pandas as pd
import datetime as dt
from prediction_service.template import RUL_TEMPLATE

# Load once


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


def build_online_features(points):
    df = pd.DataFrame([{
        "_time": dt.datetime.utcfromtimestamp(p.ts / 1000),
        "brightness": p.brightness,
        "temperature": p.temperature,
        "power": p.power
    } for p in points]).set_index("_time")

    window = min(5, len(df))

    tmp = df.copy()
    for col in ["brightness", "temperature", "power"]:
        tmp[f"{col}_roll_mean_{window}"] = tmp[col].rolling(
            window, min_periods=1).mean()
        tmp[f"{col}_roll_std_{window}"] = tmp[col].rolling(
            window, min_periods=1).std()

    max_lag = 3
    for lag in range(1, max_lag + 1):
        for col in ["brightness", "temperature", "power"]:
            tmp[f"{col}_lag_{lag}"] = tmp[col].shift(lag)

    tmp = tmp.dropna()

    if tmp.empty:
        row = df.iloc[[-1]].copy()
        for col in ["brightness", "temperature", "power"]:
            row[f"{col}_roll_mean_{window}"] = row[col]
            row[f"{col}_roll_std_{window}"] = 0
            for lag in range(1, max_lag + 1):
                row[f"{col}_lag_{lag}"] = row[col]
        tmp = row

    for col in FEATURE_COLUMNS:
        if col not in tmp.columns:
            tmp[col] = 0

    return tmp[FEATURE_COLUMNS].iloc[[-1]]


def build_rul_series(value_list: Dict):
    """
    Convert RUL list into comma-separated string
    """
    value_str_list = []
    for key, values in value_list.items():
        value_str = key + ": " + ",".join(str(int(v))
                                          for v in values)
        value_str_list.append(value_str)

    return "\n".join(value_str_list)


def build_additional_context(values):
    return (
        f"Average voltage: {np.mean(values['voltage']):.2f} V\n"
        f"Average current: {np.mean(values['current']):.2f} A\n"
        f"Average power: {np.mean(values['power']):.2f} W\n"
        f"Brightness level: {values['brightness'][-1]}\n"
        f"Ambient light: {values['light'][-1]}"
    )


def generate_rul_prompt(device_id, timestamps, values):
    historical_data = build_rul_series(values)
    additional_indicator = build_additional_context(values)
    additional_data = build_additional_context(values)

    prediction_ts = timestamps[-1] + timedelta(minutes=5)

    prompt = RUL_TEMPLATE["input"].format(
        device_id=device_id,
        data_frequency=5,
        start_timestamp=timestamps[0],
        end_timestamp=timestamps[-1],
        input_series=historical_data,
        additional_data_content=additional_data + "\n" + additional_indicator,
        prediction_timestamp=prediction_ts
    )

    return {
        "instruction": RUL_TEMPLATE["instruction"],
        "input": prompt
    }

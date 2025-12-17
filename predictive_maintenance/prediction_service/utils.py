import pandas as pd
import datetime as dt
import joblib
from config.config import MODEL_PATH

# Load once
bundle = joblib.load(MODEL_PATH)
MODEL = bundle["model"]
FEATURE_COLUMNS = bundle["feature_columns"]


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

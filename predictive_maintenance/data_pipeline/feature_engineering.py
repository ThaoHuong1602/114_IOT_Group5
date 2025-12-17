import pandas as pd


def build_training_features(df, window=5):
    df = df.dropna(subset=["light", "brightness", "current", "power"])

    for col in ["light", "brightness", "current", "power"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["light", "brightness", "current", "power"]:
        df[f"{col}_roll_mean_{window}"] = df[col].rolling(
            window, min_periods=1).mean()
        df[f"{col}_roll_std_{window}"] = df[col].rolling(
            window, min_periods=1).std()

    max_lag = 2
    for lag in range(1, max_lag + 1):
        for col in ["light", "brightness", "current", "power"]:
            df[f"{col}_lag_{lag}"] = df[col].shift(lag)

    df = df.dropna()

    X = df.drop(columns=["rul"])
    y = df["rul"].astype(int)

    return X, y

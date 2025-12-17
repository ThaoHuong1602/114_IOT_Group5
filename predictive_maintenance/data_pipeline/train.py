import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from config.config import MODEL_PATH, DEFAULT_DEVICE
from data_pipeline.influx_client import query_influx
from data_pipeline.feature_engineering import build_training_features


def train_and_save_model():
    df = query_influx(
        device=DEFAULT_DEVICE,
        start="-30d"
    )
    X, y = build_training_features(df, window=5)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced"
    )

    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    print(classification_report(y_test, preds))

    joblib.dump(
        {"model": model, "feature_columns": list(X.columns)},
        MODEL_PATH
    )

    print(f"Model saved → {MODEL_PATH}")


if __name__ == "__main__":
    train_and_save_model()

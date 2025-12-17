from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from prediction_service.utils import MODEL, build_online_features

app = FastAPI(title="LED Maintenance Prediction API")


class TelemetryPoint(BaseModel):
    ts: int
    brightness: float
    temperature: float
    power: float


class PredictRequest(BaseModel):
    device: str
    data: List[TelemetryPoint]


class PredictResponse(BaseModel):
    device: str
    prediction: int
    probability: float


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    X = build_online_features(req.data)

    prob = MODEL.predict_proba(X)[0][1]
    pred = int(prob >= 0.5)

    return PredictResponse(
        device=req.device,
        prediction=pred,
        probability=float(prob)
    )

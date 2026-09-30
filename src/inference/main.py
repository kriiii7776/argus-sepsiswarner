from fastapi import FastAPI

app = FastAPI(title="SepsisGuard Inference API")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
def predict(data: dict):
    # Placeholder for model inference
    return {"risk_score": 0.42, "prediction": "no_sepsis"}

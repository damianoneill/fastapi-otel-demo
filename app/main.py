import random

from fastapi import FastAPI, HTTPException
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from .telemetry import setup_telemetry

# Initialize telemetry
setup_telemetry()

# Create FastAPI app
app = FastAPI(title="FastAPI OTEL Demo")

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    # Simulate random errors for demonstration
    if random.random() < 0.1:  # 10% chance of error
        raise HTTPException(status_code=500, detail="Random server error")
    return {"item_id": item_id, "name": f"Item {item_id}"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(
    title="ClipPilot AI",
    description="AI Automated Video Clipping System",
    version="1.0.0",
)


@app.get("/")
def home():
    return {
        "app": "ClipPilot AI",
        "status": "Running",
        "message": "Your AI clipping system is ready!",
    }


@app.get("/health")
def health():
    return {"status": "healthy", "gpu": "RTX 3050", "time": datetime.now().isoformat()}

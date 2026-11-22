from fastapi import FastAPI
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.upload import router as upload_router

app = FastAPI(
    title="ClipPilot AI",
    description="AI Automated Video Clipping System",
    version="1.0.0",
)
app.mount("/clips", StaticFiles(directory="storage/clips"), name="clips")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api/videos", tags=["Video Upload"])


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

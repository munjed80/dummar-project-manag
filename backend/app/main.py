from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.api import auth, complaints, tasks, contracts, locations, dashboard, users, uploads, reports
from app.core.config import settings

app = FastAPI(
    title="Dummar Project Management API",
    description="Production-grade API for Damascus Dummar Project Management Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(tasks.router)
app.include_router(contracts.router)
app.include_router(locations.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(uploads.router)
app.include_router(reports.router)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {
        "message": "Dummar Project Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}

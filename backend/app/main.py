from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analogs, health, targets
from app.core.config import settings

app = FastAPI(
    title="AstroTerrain Module 3 API",
    version="0.1.0",
    description="Earth analog data access and Module 4 scoring integration gateway",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(health.router)
app.include_router(targets.router)
app.include_router(analogs.router)

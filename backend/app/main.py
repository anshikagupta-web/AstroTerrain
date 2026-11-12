from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import analogs, health, targets
from app.core.config import settings

app = FastAPI(title=settings.app_name, description="AstroTerrain Module 3 API: planetary target profiles and Earth-analog search.", version="0.1.0", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(targets.router, prefix=settings.api_v1_prefix)
app.include_router(analogs.router, prefix=settings.api_v1_prefix)

@app.get("/", tags=["root"])
def root():
    return {"service": "AstroTerrain API", "status": "running", "docs": "/docs", "health": f"{settings.api_v1_prefix}/health"}

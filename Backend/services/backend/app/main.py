from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_agent_lab import router as agent_lab_router
from app.api.routes_audit import router as audit_router
from app.api.routes_arth import router as arth_router
from app.api.routes_behavioral import router as behavioral_router
from app.api.routes_documents import router as documents_router
from app.api.routes_fire import router as fire_router
from app.api.routes_ingestion import router as ingestion_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_onboard import router as onboard_router
from app.api.routes_portfolio import router as portfolio_router
from app.api.routes_tax import router as tax_router
from app.api.routes_ws import router as ws_router
from app.core.config import settings
from app.core.database import db_manager
from app.services.job_registry import job_service
from app.services.websocket_service import ws_manager

app = FastAPI(title=settings.app_name, debug=settings.app_debug)

# CORS configuration for Frontend (Vercel) access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (Vercel, Localhost, etc.)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS)
    allow_headers=["*"],  # Allows all headers
)

app.mount("/artifacts", StaticFiles(directory="artifacts", check_dir=False), name="artifacts")

app.include_router(onboard_router)
app.include_router(jobs_router)
app.include_router(fire_router)
app.include_router(tax_router)
app.include_router(portfolio_router)
app.include_router(documents_router)
app.include_router(audit_router)
app.include_router(behavioral_router)
app.include_router(arth_router)
app.include_router(ws_router)
app.include_router(ingestion_router)
app.include_router(agent_lab_router)


@app.get("/health")
async def health():
    atlas_configured = settings.mongodb_uri.startswith("mongodb+srv://")
    return {
        "status": "ok",
        "db": {
            "mongo_ready": db_manager.is_mongo_ready,
            "redis_ready": db_manager.is_redis_ready,
            "atlas_configured": atlas_configured,
            "mongo_error": db_manager.mongo_last_error,
            "redis_error": db_manager.redis_last_error,
        },
    }


@app.on_event("startup")
async def startup_event():
    await db_manager.connect()
    job_service.set_listener(ws_manager.publish_job_update)


@app.on_event("shutdown")
async def shutdown_event():
    job_service.set_listener(None)
    await db_manager.close()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": {
                "code": "internal_error",
                "message": "Unexpected error occurred",
                "details": {"path": str(request.url.path), "reason": str(exc)},
            },
        },
    )

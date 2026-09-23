"""
NagarSetu FastAPI Application Entrypoint
Provides foundation health checks and route registrations.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.complaints import router as complaints_router
from app.api.triage import router as triage_router
from app.api.config_routes import router as config_router
from app.api.clusters import router as clusters_router
from app.api.operator import router as operator_router
from app.api.analytics import router as analytics_router
from app.api.evaluation import router as evaluation_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Operator-facing read-only AI civic complaint triage and accountability engine.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(complaints_router, prefix=settings.API_V1_PREFIX)
app.include_router(triage_router, prefix=settings.API_V1_PREFIX)
app.include_router(config_router, prefix=settings.API_V1_PREFIX)
app.include_router(clusters_router, prefix=settings.API_V1_PREFIX)
app.include_router(operator_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(evaluation_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
def health_check():
    """
    Lightweight internal readiness and health check.
    Covers database connectivity, AI status, required configuration files, and table schemas.
    Never exposes API keys, credentials, or sensitive secrets.
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text, inspect
    from app.services.classification.gemini_client import GeminiClassificationClient

    checks = {
        "database": "unknown",
        "ai_configuration": "unknown",
        "configuration_files": "unknown",
        "database_tables": "unknown"
    }
    details = {}

    # 1. Database Connectivity Check
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            checks["database"] = "healthy"
    except Exception as exc:
        checks["database"] = f"error: {str(exc)}"

    # 2. AI Configuration Check (Without Exposing Key)
    gemini_client = GeminiClassificationClient()
    is_configured = gemini_client.is_configured()
    checks["ai_configuration"] = "configured" if is_configured else "fallback_mode"
    details["ai_service"] = {
        "model_version": settings.MODEL_VERSION,
        "prompt_version": settings.PROMPT_VERSION,
        "mode": "Live Gemini API" if is_configured else "Deterministic Fallback Mode (Graceful)"
    }

    # 3. Core Configuration Files Check
    config_files = [
        ("departments", settings.CONFIG_DIR / "departments.json"),
        ("categories", settings.CONFIG_DIR / "categories.json"),
        ("urgency_rules", settings.CONFIG_DIR / "urgency_rules.json"),
        ("routing_rules", settings.CONFIG_DIR / "routing_rules.json"),
        ("alerts_config", settings.CONFIG_DIR / "alerts_config.json"),
        ("gazetteer", settings.GAZETTEER_PATH)
    ]
    missing_configs = [name for name, p in config_files if not p.exists()]
    if not missing_configs:
        checks["configuration_files"] = "all_present"
    else:
        checks["configuration_files"] = f"missing: {', '.join(missing_configs)}"

    # 4. Required Database Tables Check
    try:
        from app.db.session import engine
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        required_tables = [
            "raw_complaints", "triaged_complaints", "departments",
            "categories", "locality_gazetteer", "duplicate_clusters",
            "cluster_members", "acknowledgements", "complaint_audits",
            "weekly_reports", "evaluation_results"
        ]
        missing_tables = [t for t in required_tables if t not in existing_tables]
        if not missing_tables:
            checks["database_tables"] = "all_present"
        else:
            checks["database_tables"] = f"missing: {', '.join(missing_tables)}"
        details["tables_verified"] = len(existing_tables)
    except Exception as exc:
        checks["database_tables"] = f"error: {str(exc)}"

    overall_status = "healthy" if (
        checks["database"] == "healthy" and
        checks["configuration_files"] == "all_present" and
        "missing" not in str(checks.get("database_tables", ""))
    ) else "degraded"

    return {
        "status": overall_status,
        "service": "nagarsetu-backend",
        "version": "0.6.0",
        "phase": "Phase 6 / Final Release QA",
        "checks": checks,
        "details": details,
        "scope": "Operator-facing read-only municipal triage engine"
    }


@app.get(f"{settings.API_V1_PREFIX}/status", tags=["Status"])
def api_status():
    """API V1 operational status and primary endpoint directory."""
    return {
        "status": "operational",
        "active_phase": "Phase 6: Complete Pipeline, Digests & Evaluation",
        "endpoints": [
            f"{settings.API_V1_PREFIX}/complaints",
            f"{settings.API_V1_PREFIX}/complaints/batch-ingest",
            f"{settings.API_V1_PREFIX}/clusters",
            f"{settings.API_V1_PREFIX}/clusters/detect",
            f"{settings.API_V1_PREFIX}/analytics/weekly-digest",
            f"{settings.API_V1_PREFIX}/analytics/repeat-localities",
            f"{settings.API_V1_PREFIX}/analytics/emerging-alerts",
            f"{settings.API_V1_PREFIX}/eval/benchmark",
            f"{settings.API_V1_PREFIX}/eval/latest"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

"""Minimal production HTTP boundary for OpenMaster service probes and future routes."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .analysis_routes import router as analysis_router

app = FastAPI(title="OpenMaster API", version="2.3.1")
app.include_router(analysis_router)


@app.get("/health/live", include_in_schema=False)
def live() -> JSONResponse:
    """Report process liveness without depending on external infrastructure."""
    return JSONResponse({"status": "live"})


@app.get("/health/ready", include_in_schema=False)
def ready() -> JSONResponse:
    """Report that the HTTP application has finished startup."""
    return JSONResponse({"status": "ready"})

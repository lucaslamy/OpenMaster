"""Production HTTP boundary, account bootstrap, and service probes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .analysis_routes import router as analysis_router
from .auth_routes import get_auth_service
from .auth_routes import router as auth_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Ensure the deployment administrator exists before accepting traffic."""
    get_auth_service().bootstrap_admin_from_environment()
    yield


app = FastAPI(title="OpenMaster API", version="3.6.1", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(analysis_router)


@app.get("/health/live", include_in_schema=False)
async def live() -> JSONResponse:
    """Report process liveness without depending on external infrastructure."""
    return JSONResponse({"status": "live"})


@app.get("/health/ready", include_in_schema=False)
async def ready() -> JSONResponse:
    """Report that the HTTP application has finished startup."""
    return JSONResponse({"status": "ready"})

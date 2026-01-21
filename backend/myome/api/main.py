"""FastAPI application entry point"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from myome.api.routes import (
    alerts,
    auth,
    clinical,
    devices,
    health,
    hereditary,
    oauth,
    users,
)
from myome.core.config import settings
from myome.core.exceptions import MyomeException
from myome.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info("API docs available at /api/docs")
    yield
    # Shutdown
    logger.info("Shutting down application")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="An Open-Source Living Health Record Framework",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS middleware - permissive in development, restricted in production
if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "https://app.myome.health",  # Production frontend
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Exception handlers
@app.exception_handler(MyomeException)
async def myome_exception_handler(
    request: Request, exc: MyomeException
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "details": exc.details,
        },
    )


# Include routers
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(devices.router, prefix=settings.api_prefix)
app.include_router(alerts.router, prefix=settings.api_prefix)
app.include_router(oauth.router, prefix=settings.api_prefix)
app.include_router(clinical.router, prefix=settings.api_prefix)
app.include_router(hereditary.router, prefix=settings.api_prefix)


@app.get("/")
async def root() -> dict:
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "docs": "/api/docs",
    }


@app.get("/api/v1/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
    }

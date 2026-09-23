"""
PolicySetu AI Microservice FastAPI Application.
Coordinates production-oriented API infrastructure, middleware stack, exception handlers,
and route endpoints.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import DEFAULT_SERVICE_CONFIG, ServiceConfig
from .errors import register_exception_handlers
from .middleware import RequestCorrelationMiddleware, StructuredLoggingMiddleware
from .routes.applications import router as applications_router
from .routes.chat import router as chat_router
from .routes.documents import router as documents_router
from .routes.eligibility import router as eligibility_router
from .routes.health import router as health_router
from .routes.schemes import router as schemes_router

logger = logging.getLogger("policysetu.api.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown lifecycle."""
    logger.info("Initializing PolicySetu AI Microservice (version %s)...", DEFAULT_SERVICE_CONFIG.api_version)
    logger.info("Environment: %s", DEFAULT_SERVICE_CONFIG.environment)
    logger.info("Rate limiting enabled: %s", DEFAULT_SERVICE_CONFIG.rate_limit_enabled)
    logger.info("Provider mode: %s", DEFAULT_SERVICE_CONFIG.default_provider_mode)
    yield
    logger.info("Shutting down PolicySetu AI Microservice cleanly.")


def create_app(config: ServiceConfig = DEFAULT_SERVICE_CONFIG) -> FastAPI:
    """Factory creating and configuring the FastAPI microservice instance."""
    app = FastAPI(
        title="PolicySetu AI Microservice",
        description=(
            "Production-oriented AI microservice providing document ingestion, grounded chat, "
            "hybrid scheme retrieval, deterministic eligibility checks, and 21-step application analysis."
        ),
        version=config.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Register global exception handlers
    register_exception_handlers(app)

    # 2. Register middleware stack (outer-to-inner execution)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(RequestCorrelationMiddleware)

    # 3. Mount routers
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(applications_router)
    app.include_router(schemes_router)
    app.include_router(eligibility_router)
    app.include_router(chat_router)

    return app


# Default app instance for ASGI runners (uvicorn src.api.app:app)
app = create_app()

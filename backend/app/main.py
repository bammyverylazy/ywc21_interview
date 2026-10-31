import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_client, ensure_indexes
from app.routers import activity, dashboard, health, inventory, matches, notices, products, sync

logger = logging.getLogger("lotshield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # A missing MONGODB_URI raises ConfigurationError here and stops startup.
    settings = get_settings()

    client = create_client(settings)
    db = client[settings.database_name]
    app.state.settings = settings
    app.state.db = db
    app.state.mongo_client = client

    logger.info(
        "Thai FDA sync is %s (FDA_SYNC_ENABLED=%s)",
        "ENABLED" if settings.fda_sync_enabled else "DISABLED — set FDA_SYNC_ENABLED=true to enable",
        settings.fda_sync_enabled,
    )

    # An unreachable database should not crash the app: /api/health reports it.
    try:
        ensure_indexes(db)
        logger.info("Connected to MongoDB; indexes ensured on '%s'", settings.database_name)
    except Exception:
        logger.exception("Could not initialize MongoDB indexes at startup")

    yield

    client.close()


@asynccontextmanager
async def test_lifespan(app: FastAPI):
    yield


def create_app(*, manage_database: bool = True) -> FastAPI:
    app = FastAPI(
        title="LotShield API",
        description="Medicine recall and safety monitoring for independent pharmacies.",
        version="1.0.0",
        lifespan=lifespan if manage_database else test_lifespan,
    )

    # CORS origin comes from env; read directly so the app can be built
    # before settings are validated by the lifespan.
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").strip()
    cors_origins = tuple(
        dict.fromkeys(
            (
                frontend_url,
                *(
                    origin.strip()
                    for origin in os.getenv("CORS_ORIGINS", "").split(",")
                    if origin.strip()
                ),
            )
        )
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(products.router, prefix="/api")
    app.include_router(inventory.router, prefix="/api")
    app.include_router(notices.router, prefix="/api")
    app.include_router(matches.router, prefix="/api")
    app.include_router(activity.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(sync.router, prefix="/api")
    return app


app = create_app()

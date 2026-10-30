import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_client, ensure_indexes
from app.routers import health, inventory, notices, products

logger = logging.getLogger("lotshield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # A missing MONGODB_URI raises ConfigurationError here and stops startup.
    settings = get_settings()

    client = create_client(settings)
    db = client[settings.database_name]
    app.state.settings = settings
    app.state.db = db

    # An unreachable database should not crash the app: /api/health reports it.
    try:
        ensure_indexes(db)
        logger.info("Connected to MongoDB; indexes ensured on '%s'", settings.database_name)
    except Exception:
        logger.exception("Could not initialize MongoDB indexes at startup")

    yield

    client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="LotShield API",
        description="Medicine recall and safety monitoring for independent pharmacies.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS origin comes from env; read directly so the app can be built
    # before settings are validated by the lifespan.
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").strip()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(products.router, prefix="/api")
    app.include_router(inventory.router, prefix="/api")
    app.include_router(notices.router, prefix="/api")
    return app


app = create_app()

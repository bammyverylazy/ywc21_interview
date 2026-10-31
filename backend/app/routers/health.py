import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pymongo.database import Database

from app.database import ping_database
from app.dependencies import get_db

logger = logging.getLogger("YaSafe.health")

router = APIRouter(tags=["health"])

SERVICE_NAME = "YaSafe API"


@router.get("/health")
def health_check(db: Database = Depends(get_db)):
    """Report API availability and whether MongoDB is reachable."""
    try:
        ping_database(db)
    except Exception:
        logger.exception("Database ping failed")
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "service": SERVICE_NAME,
                "database": "unavailable",
            },
        )
    return {"status": "ok", "service": SERVICE_NAME, "database": "connected"}

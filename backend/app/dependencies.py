"""FastAPI dependencies."""

from fastapi import Request
from pymongo.database import Database


def get_db(request: Request) -> Database:
    """Return the database handle created at application startup."""
    return request.app.state.db

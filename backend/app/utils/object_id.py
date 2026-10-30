"""
Utilities for working with MongoDB ObjectIds in FastAPI + Pydantic v2.

MongoDB stores primary keys as ObjectId (a 12-byte BSON type). FastAPI uses
Pydantic for request/response validation, which works with Python types. We
need a clean bridge between the two so that:

  - API responses serialize ObjectId as a plain string (e.g. "6620abc...")
  - Route parameters accept a string and validate it is a valid ObjectId
  - Invalid IDs return a clear 422 or 404 rather than a cryptic BSON error
"""

from __future__ import annotations

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status


def parse_object_id(value: str) -> ObjectId:
    """
    Convert a URL path parameter string to a MongoDB ObjectId.

    Raises HTTPException 422 if the string is not a valid 24-hex-char ObjectId,
    so the caller gets a sensible error response rather than a BSON exception.
    """
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{value}' is not a valid id.",
        )


def doc_to_dict(doc: dict) -> dict:
    """
    Convert a raw MongoDB document so it is safe for JSON serialisation.

    - Renames '_id' → 'id' and converts ObjectId → str.
    - Converts any other ObjectId values (e.g. product_id) → str.

    This is done on the raw dict *before* it is passed to the Pydantic
    response model, which means the response model only needs to declare
    normal str fields for ids.
    """
    if doc is None:
        return doc
    result = {}
    for key, value in doc.items():
        if key == "_id":
            result["id"] = str(value)
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        else:
            result[key] = value
    return result

"""
Generic pagination wrapper used by list endpoints.

  PaginatedResponse[T] wraps a list of items with total count and
  the pagination parameters that were used, so the frontend can render
  page controls without a second request.

Usage in a router:
    return PaginatedResponse[ProductOut](
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )
"""

from __future__ import annotations

from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int

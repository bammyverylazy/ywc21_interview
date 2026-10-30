"""
Pydantic v2 schemas for the inventory_items collection.

Each inventory record represents one manufacturing batch of a product held
by the pharmacy. A product may have multiple inventory records with different
lot numbers (see spec §6.4).

  InventoryCreate — POST /api/inventory
  InventoryUpdate — PUT  /api/inventory/{id}
  InventoryOut    — returned by every inventory endpoint, with embedded
                    product info so the UI doesn't need a second request
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class InventoryCreate(BaseModel):
    product_id: str = Field(..., description="ObjectId of the related product")
    lot_number: Optional[str] = Field(default=None, max_length=100)
    quantity: int = Field(..., ge=0, description="Non-negative integer")
    expiry_date: Optional[date] = None

    @field_validator("product_id")
    @classmethod
    def product_id_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("product_id must not be blank")
        return v.strip()

    @field_validator("lot_number", mode="before")
    @classmethod
    def strip_lot_number(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None


class InventoryUpdate(BaseModel):
    lot_number: Optional[str] = Field(default=None, max_length=100)
    quantity: Optional[int] = Field(default=None, ge=0)
    expiry_date: Optional[date] = None

    @field_validator("lot_number", mode="before")
    @classmethod
    def strip_lot_number(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None

    def non_none_fields(self) -> dict:
        """Return only the fields explicitly set by the caller."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class ProductSummary(BaseModel):
    """Lightweight product info embedded in InventoryOut."""

    id: str
    brand_name: str
    generic_name: Optional[str] = None
    registration_no: Optional[str] = None
    manufacturer: Optional[str] = None


class InventoryOut(BaseModel):
    """
    Full inventory record returned by the API.

    The 'product' field is populated by the service layer via a join so the
    caller has all the information needed for a list row or detail view.
    """

    id: str
    product_id: str
    product: Optional[ProductSummary] = None
    lot_number: Optional[str] = None
    quantity: int
    expiry_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

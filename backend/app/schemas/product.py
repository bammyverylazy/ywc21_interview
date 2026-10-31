"""
Pydantic v2 schemas for the products collection.

Three schemas follow the create / response pattern:

  ProductCreate  — accepted by POST /api/products
  ProductUpdate  — accepted by PUT /api/products/{id}  (all fields optional)
  ProductOut     — returned by every product endpoint

Internal values (field names, enum keys) stay in English.
Thai display labels live only in the frontend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProductCreate(BaseModel):
    brand_name: str = Field(..., min_length=1, max_length=200)
    generic_name: Optional[str] = Field(default=None, max_length=200)
    registration_no: Optional[str] = Field(default=None, max_length=100)
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    strength: Optional[str] = Field(default=None, max_length=100)
    dosage_form: Optional[str] = Field(default=None, max_length=100)
    data_origin: str = Field(default="manual", pattern="^(manual|demo|verified_source)$")

    @field_validator("brand_name")
    @classmethod
    def brand_name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("brand_name must not be blank")
        return v.strip()

    @field_validator("generic_name", "registration_no", "manufacturer", "strength", "dosage_form", mode="before")
    @classmethod
    def strip_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None


class ProductUpdate(BaseModel):
    """All fields are optional so the caller can PATCH individual fields."""

    brand_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    generic_name: Optional[str] = Field(default=None, max_length=200)
    registration_no: Optional[str] = Field(default=None, max_length=100)
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    strength: Optional[str] = Field(default=None, max_length=100)
    dosage_form: Optional[str] = Field(default=None, max_length=100)

    @field_validator("brand_name")
    @classmethod
    def brand_name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("brand_name must not be blank")
        return v.strip() if v is not None else None

    @field_validator("generic_name", "registration_no", "manufacturer", "strength", "dosage_form", mode="before")
    @classmethod
    def strip_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None

    def non_none_fields(self) -> dict:
        """Return only the fields explicitly set by the caller."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class ProductOut(BaseModel):
    """
    Response schema. 'id' is the string representation of MongoDB _id.
    """

    id: str
    brand_name: str
    generic_name: Optional[str] = None
    registration_no: Optional[str] = None
    manufacturer: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    data_origin: str = "manual"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

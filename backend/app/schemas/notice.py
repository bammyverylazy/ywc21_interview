"""
Pydantic v2 schemas for the safety_notices collection.

Safety notices come from official Thai FDA sources. Fields vary between
announcements — not every notice includes lot numbers or a registration
number. The schema is designed to accept partial data gracefully rather
than reject a real official notice because one optional field is missing.

NoticeType enum matches spec §6.5: RECALL or WARNING.

data_completeness is computed automatically from the payload fields rather
than requiring the caller to provide it, so it stays consistent.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator


class NoticeType(str, Enum):
    RECALL = "RECALL"
    WARNING = "WARNING"


class DataCompleteness(BaseModel):
    """Computed availability flags for the three key matching fields."""

    has_registration_no: bool
    has_lot_information: bool
    has_manufacturer: bool


class NoticeCreate(BaseModel):
    """
    Accepted by POST /api/notices.

    Required fields (minimum viable import):
      title, notice_type, product_name, source_url, published_at

    All other fields are optional because official notices sometimes omit
    them. Missing lot information must not cause an import failure (spec §12
    Phase 3 acceptance criteria).
    """

    title: str = Field(..., min_length=1, max_length=500)
    notice_type: NoticeType
    product_name: str = Field(..., min_length=1, max_length=200)
    generic_name: Optional[str] = Field(default=None, max_length=200)
    registration_no: Optional[str] = Field(default=None, max_length=100)
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    affected_lots: List[str] = Field(default_factory=list)
    reason: Optional[str] = Field(default=None, max_length=2000)
    published_at: date
    source_name: Optional[str] = Field(default=None, max_length=200)
    source_url: AnyHttpUrl

    @field_validator("title", "product_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank.")
        return v.strip()

    @field_validator("generic_name", "registration_no", "manufacturer", "reason", "source_name", mode="before")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        return s if s else None

    @field_validator("affected_lots", mode="before")
    @classmethod
    def clean_lot_list(cls, v) -> List[str]:
        if not v:
            return []
        cleaned = [lot.strip() for lot in v if isinstance(lot, str) and lot.strip()]
        return cleaned

    @property
    def data_completeness(self) -> DataCompleteness:
        return DataCompleteness(
            has_registration_no=bool(self.registration_no),
            has_lot_information=bool(self.affected_lots),
            has_manufacturer=bool(self.manufacturer),
        )


class NoticeUpdate(BaseModel):
    """
    Accepted by PUT /api/notices/{id}.

    All fields optional. Primarily used to correct import errors or add
    information that was unavailable at import time.
    """

    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    notice_type: Optional[NoticeType] = None
    product_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    generic_name: Optional[str] = Field(default=None, max_length=200)
    registration_no: Optional[str] = Field(default=None, max_length=100)
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    affected_lots: Optional[List[str]] = None
    reason: Optional[str] = Field(default=None, max_length=2000)
    published_at: Optional[date] = None
    source_name: Optional[str] = Field(default=None, max_length=200)

    @field_validator("title", "product_name", mode="before")
    @classmethod
    def not_blank_if_set(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Field must not be blank.")
        return v.strip() if v is not None else None

    @field_validator("generic_name", "registration_no", "manufacturer", "reason", "source_name", mode="before")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        return s if s else None

    @field_validator("affected_lots", mode="before")
    @classmethod
    def clean_lot_list(cls, v) -> Optional[List[str]]:
        if v is None:
            return None
        return [lot.strip() for lot in v if isinstance(lot, str) and lot.strip()]

    def non_none_fields(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class NoticeOut(BaseModel):
    """Response schema for a safety notice."""

    id: str
    title: str
    notice_type: NoticeType
    product_name: str
    generic_name: Optional[str] = None
    registration_no: Optional[str] = None
    manufacturer: Optional[str] = None
    affected_lots: List[str] = []
    reason: Optional[str] = None
    published_at: date
    source_name: Optional[str] = None
    source_url: str
    imported_at: datetime
    data_completeness: DataCompleteness

    model_config = {"from_attributes": True}

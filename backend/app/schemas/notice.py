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
from typing import Any, List, Literal, Optional, Union

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


class NoticeType(str, Enum):
    RECALL = "RECALL"
    WARNING = "WARNING"


class DataCompleteness(BaseModel):
    """Computed availability flags for the three key matching fields."""

    has_registration_no: bool
    has_lot_information: bool
    has_manufacturer: bool


class FieldProvenance(BaseModel):
    origin: Literal[
        "source_provided",
        "machine_classified",
        "machine_extracted",
        "manually_verified",
        "manual_unverified",
        "missing",
    ]
    extraction_method: str
    source_fields: list[str] = Field(default_factory=list)
    source_reference: Optional[str] = None
    verification_status: Literal["manual_review", "verified"] = "manual_review"


class NoticeAttachment(BaseModel):
    name: Optional[str] = None
    original_filename: Optional[str] = None
    file_url: AnyHttpUrl
    source_reference: Optional[str] = None
    extraction_method: str
    verification_status: Literal["manual_review", "verified"] = "manual_review"


class AffectedLot(BaseModel):
    lot_number: str = Field(..., min_length=1, max_length=100)
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    extraction_method: Optional[str] = None
    verification_status: Optional[Literal["manual_review", "verified"]] = None
    source_reference: Optional[str] = None

    @field_validator("lot_number")
    @classmethod
    def lot_number_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("lot_number must not be blank")
        return value.strip()


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
    dosage_form: Optional[str] = Field(default=None, max_length=200)
    product_strength: Optional[str] = Field(default=None, max_length=200)
    affected_lots: List[Union[str, AffectedLot]] = Field(default_factory=list)
    attachments: List[NoticeAttachment] = Field(default_factory=list)
    reason: Optional[str] = Field(default=None, max_length=2000)
    published_at: Optional[date] = None
    source_name: Optional[str] = Field(default=None, max_length=200)
    source_url: AnyHttpUrl
    source_id: Optional[str] = Field(default=None, max_length=300)
    source_detail_id: Optional[str] = Field(default=None, max_length=300)
    source_detail_status: Optional[
        Literal["not_requested", "available", "partial", "failed"]
    ] = None
    source_attachments_status: Optional[
        Literal["not_requested", "available", "none", "failed"]
    ] = None
    product_name_th: Optional[str] = Field(default=None, max_length=200)
    product_name_en: Optional[str] = Field(default=None, max_length=200)
    recall_action: Optional[str] = Field(default=None, max_length=1000)
    impact: Optional[str] = Field(default=None, max_length=2000)
    updated_at_source: Optional[datetime] = None
    source_created_at: Optional[datetime] = None
    raw_source_data: Optional[dict[str, Any]] = None
    record_origin: str = Field(default="manual", pattern="^(manual|verified_import|automatic_sync)$")
    verification_status: str = Field(default="manual_review", pattern="^(manual_review|verified)$")

    @field_validator("title", "product_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank.")
        return v.strip()

    @field_validator(
        "generic_name", "registration_no", "manufacturer", "reason", "source_name",
        "source_id", "product_name_th", "product_name_en", "recall_action", "impact",
        "dosage_form", "product_strength",
        mode="before",
    )
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        return s if s else None

    @field_validator("affected_lots", mode="before")
    @classmethod
    def clean_lot_list(cls, v) -> List[Union[str, AffectedLot]]:
        if not v:
            return []
        cleaned: List[Union[str, AffectedLot]] = []
        for lot in v:
            if isinstance(lot, str) and lot.strip():
                cleaned.append(lot.strip())
            elif isinstance(lot, dict):
                cleaned.append(AffectedLot.model_validate(lot))
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
    dosage_form: Optional[str] = Field(default=None, max_length=200)
    product_strength: Optional[str] = Field(default=None, max_length=200)
    affected_lots: Optional[List[Union[str, AffectedLot]]] = None
    attachments: Optional[List[NoticeAttachment]] = None
    reason: Optional[str] = Field(default=None, max_length=2000)
    published_at: Optional[date] = None
    source_name: Optional[str] = Field(default=None, max_length=200)
    product_name_th: Optional[str] = Field(default=None, max_length=200)
    product_name_en: Optional[str] = Field(default=None, max_length=200)
    recall_action: Optional[str] = Field(default=None, max_length=1000)
    impact: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("title", "product_name", mode="before")
    @classmethod
    def not_blank_if_set(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Field must not be blank.")
        return v.strip() if v is not None else None

    @field_validator(
        "generic_name", "registration_no", "manufacturer", "reason", "source_name",
        "product_name_th", "product_name_en", "recall_action", "impact",
        "dosage_form", "product_strength",
        mode="before",
    )
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        return s if s else None

    @field_validator("affected_lots", mode="before")
    @classmethod
    def clean_lot_list(cls, v) -> Optional[List[Union[str, AffectedLot]]]:
        if v is None:
            return None
        return [
            lot.strip() if isinstance(lot, str) else AffectedLot.model_validate(lot)
            for lot in v
            if (isinstance(lot, str) and lot.strip()) or isinstance(lot, dict)
        ]

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
    dosage_form: Optional[str] = None
    product_strength: Optional[str] = None
    affected_lots: List[Union[str, AffectedLot]] = []
    attachments: List[NoticeAttachment] = Field(default_factory=list)
    reason: Optional[str] = None
    published_at: Optional[date] = None
    source_name: Optional[str] = None
    source_url: str
    imported_at: datetime
    data_completeness: DataCompleteness
    source_id: Optional[str] = None
    source_detail_id: Optional[str] = None
    source_detail_status: Optional[
        Literal["not_requested", "available", "partial", "failed"]
    ] = None
    source_attachments_status: Optional[
        Literal["not_requested", "available", "none", "failed"]
    ] = None
    product_name_th: Optional[str] = None
    product_name_en: Optional[str] = None
    recall_action: Optional[str] = None
    impact: Optional[str] = None
    updated_at_source: Optional[datetime] = None
    source_created_at: Optional[datetime] = None
    raw_source_data: Optional[dict[str, Any]] = None
    record_origin: str = "manual"
    verification_status: str = "manual_review"
    last_checked_at: Optional[datetime] = None
    source_changed_at: Optional[datetime] = None
    source_content_hash: Optional[str] = None
    field_provenance: dict[str, FieldProvenance] = Field(default_factory=dict)

    model_config = {"from_attributes": True}

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.provenance import build_field_provenance

_BANGKOK_TIMEZONE = timezone(timedelta(hours=7))
LISTING_PAGE_URL = (
    "https://apres.fda.moph.go.th/FDA_POST_VIEW_CENTER/PUBLIC/DRUG_ALERT"
)
LISTING_SERVICE_URL = (
    "https://apres.fda.moph.go.th/POST_CENTER_SERVICE_DRUG/"
    "GATE_WAY/WS_SAFETY_ALERT"
)
DETAIL_SERVICE_URL = (
    "https://apres.fda.moph.go.th/POST_CENTER_SERVICE_DRUG/"
    "GATE_WAY/GATEWAY_EXCHANGE"
)
ATTACHMENT_SERVICE_URL = (
    "https://apres.fda.moph.go.th/POST_CENTER_SERVICE_DRUG/"
    "GATE_WAY/GET_ITEM_FILE_ATTACH"
)
SOURCE_NAME = "Thai FDA Drug Alert"
_PRIVATE_SOURCE_FIELDS = {
    "CITIZEN_ID",
    "CITIZEN_NAME",
    "COMPLAIN_BY",
    "CREATE_BY",
    "CREATE_BY_TH",
    "DEPARTMENT",
    "EMAIL",
    "FULL_ADDR",
    "INFORM_EMAIL",
    "INFORM_NAME",
    "INFORM_TEL",
    "INFORM_TEL1",
    "LINE_ID",
    "STAFF_ID",
    "STAFF_LASTNAME",
    "STAFF_NAME",
    "STAFF_POSITION",
    "TEL",
    "TEL1",
    "TEL_CONTACT",
    "EMAIL_CONTACT",
    "NAME_CONTACT",
    "ATTACH_LINK",
    "ATTACH_PATH",
    "UPDATE_BY",
}


class SourceRetrievalError(RuntimeError):
    """The official listing could not be retrieved."""


class SourceParsingError(ValueError):
    """The official listing response did not match its observed shape."""


def parse_source_datetime(value: Any) -> datetime | None:
    """Parse only known date encodings; do not infer publication dates."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    if not isinstance(value, str) or not value.strip():
        return None

    text = value.strip()
    dotnet_date = re.fullmatch(r"/Date\((-?\d+)(?:[+-]\d{4})?\)/", text)
    if dotnet_date:
        try:
            return datetime.fromtimestamp(
                int(dotnet_date.group(1)) / 1000, tz=timezone.utc
            )
        except (OverflowError, OSError, ValueError):
            return None

    patterns = (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
    )
    for pattern in patterns:
        try:
            parsed = datetime.strptime(text, pattern)
            if pattern.startswith("%d/") and parsed.year >= 2400:
                parsed = parsed.replace(year=parsed.year - 543)
            if parsed.tzinfo is None:
                source_timezone = (
                    _BANGKOK_TIMEZONE
                    if pattern.startswith("%d/")
                    else timezone.utc
                )
                parsed = parsed.replace(tzinfo=source_timezone)
            return parsed
        except ValueError:
            pass

    for pattern in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(text, pattern)
            year = parsed.year - 543 if parsed.year >= 2400 else parsed.year
            return parsed.replace(year=year, tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def parse_source_date(value: Any) -> date | None:
    parsed = parse_source_datetime(value)
    return parsed.astimezone(_BANGKOK_TIMEZONE).date() if parsed else None


def _text(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _detail_text(record: dict[str, Any], key: str) -> str | None:
    value = _text(record, key)
    if value in {"-", "--", "—", "N/A"}:
        return None
    return value


def _redact_source_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _redact_source_fields(item)
            for key, item in value.items()
            if key.upper() not in _PRIVATE_SOURCE_FIELDS
        }
    if isinstance(value, list):
        return [_redact_source_fields(item) for item in value]
    return value


def _detail_sections(payload: dict[str, Any]) -> tuple[dict[str, Any], list[Any]]:
    model = payload.get("MODEL_DRUG")
    if not isinstance(model, dict):
        raise SourceParsingError("FDA detail response had no MODEL_DRUG object.")
    report = model.get("REPORT_QLY_PROBLEM")
    lots = model.get("REPORT_QLY_PROBLEM_DETAIL")
    if not isinstance(report, dict) or not isinstance(lots, list):
        raise SourceParsingError(
            "FDA detail response did not contain the observed report and LOT fields."
        )
    return report, lots


def normalize_attachments(
    payload: dict[str, Any],
    *,
    source_reference: str,
) -> list[dict[str, Any]]:
    """Map only official attachment metadata and source-served file URLs."""
    groups = payload.get("LIST_ATTACH")
    if not isinstance(groups, list):
        raise SourceParsingError("FDA attachment response had no LIST_ATTACH array.")

    attachments: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            raise SourceParsingError("FDA attachment group was not an object.")
        files = group.get("LIST_FILE_ATTACH")
        if not isinstance(files, list):
            raise SourceParsingError(
                "FDA attachment group had no LIST_FILE_ATTACH array."
            )
        for item in files:
            if not isinstance(item, dict):
                raise SourceParsingError("FDA attachment item was not an object.")
            fake_name = _detail_text(item, "ATTACH_FILE_NM_FAKE")
            original_name = _detail_text(item, "ATTACH_FILE_NM_ORIGINAL")
            if not fake_name:
                raise SourceParsingError(
                    "FDA attachment item had no source file identifier."
                )
            attachments.append({
                "name": _detail_text(group, "ATTACH_NM"),
                "original_filename": original_name,
                "file_url": (
                    f"{ATTACHMENT_SERVICE_URL}?"
                    f"{urlencode({'NAME_FAKE': fake_name})}"
                ),
                "source_reference": source_reference,
                "extraction_method": "thai_fda_public_attachment_list",
                "verification_status": "manual_review",
            })
    return attachments


def _source_identity(record: dict[str, Any]) -> tuple[str, str, str]:
    transaction_id = _text(record, "TR_ID")
    item_id = _text(record, "IDA") or _text(record, "NEWCODE")
    if not transaction_id or not item_id:
        raise SourceParsingError("Listing record has no stable TR_ID and IDA/NEWCODE.")
    source_id = f"{transaction_id}:{item_id}"
    source_url = f"{LISTING_PAGE_URL}?{urlencode({'TR_ID': transaction_id, 'IDA': item_id})}"
    return source_id, source_url, transaction_id


def normalize_listing_record(record: dict[str, Any]) -> dict[str, Any]:
    """Map the fields observed in the FDA's public listing response."""
    source_id, source_url, _ = _source_identity(record)
    product_name_th = _text(record, "PROD_NAME")
    product_name_en = _text(record, "PROD_NAME_EN")
    product_name = product_name_th or product_name_en
    if not product_name:
        raise SourceParsingError(f"Listing record {source_id} has no product name.")

    case_alert = _text(record, "CASE_ALERT")
    recall_flags = (
        "VOLUNTARY_BILLING",
        "REFUND_STIPULATED",
    )
    is_recall = any(_text(record, field) == "1" for field in recall_flags)
    if case_alert and any(term in case_alert for term in ("เรียกคืน", "เรียกเก็บยาคืน")):
        is_recall = True

    affected_lots: list[dict[str, Any]] = []
    lot_number = _text(record, "LOTNO")
    if lot_number:
        affected_lots.append({
            "lot_number": lot_number,
            "manufacturing_date": parse_source_date(record.get("MFT_DATE")),
            "expiry_date": parse_source_date(record.get("EXP_DATE")),
        })

    mapped = {
        "title": product_name,
        "notice_type": "RECALL" if is_recall else "WARNING",
        "product_name": product_name,
        "product_name_th": product_name_th,
        "product_name_en": product_name_en,
        "generic_name": None,
        "registration_no": _text(record, "REGISTER"),
        "manufacturer": _text(record, "COMPANY_NAME"),
        "dosage_form": None,
        "product_strength": None,
        "affected_lots": affected_lots,
        "reason": case_alert or _text(record, "REMARK_DETAIL"),
        "recall_action": _text(record, "OPERATION") or _text(record, "REMARK"),
        "impact": _text(record, "IMPACT_PROD"),
        "published_at": None,
        "source_name": SOURCE_NAME,
        "source_url": source_url,
        "source_id": source_id,
        "source_detail_id": _text(record, "MAIN_TR"),
        "source_detail_status": "not_requested",
        "source_attachments_status": "not_requested",
        "dosage_form": None,
        "product_strength": None,
        "source_created_at": parse_source_datetime(record.get("CREATE_DATE")),
        "record_origin": "automatic_sync",
        "verification_status": "manual_review",
        "raw_source_data": record,
    }
    mapped["field_provenance"] = build_field_provenance(
        {
            "title": product_name,
            "product_name": product_name,
            "product_name_th": product_name_th,
            "product_name_en": product_name_en,
            "generic_name": None,
            "registration_no": mapped["registration_no"],
            "manufacturer": mapped["manufacturer"],
            "dosage_form": mapped["dosage_form"],
            "product_strength": mapped["product_strength"],
            "notice_type": mapped["notice_type"],
            "reason": mapped["reason"],
            "recall_action": mapped["recall_action"],
            "impact": mapped["impact"],
            "affected_lots": affected_lots,
            "published_at": None,
            "source_created_at": mapped["source_created_at"],
            "source_url": source_url,
        },
        origin="source_provided",
        extraction_method="thai_fda_public_listing_json",
        source_reference=source_url,
        source_fields={
            "title": ["PROD_NAME", "PROD_NAME_EN"],
            "product_name": ["PROD_NAME", "PROD_NAME_EN"],
            "product_name_th": ["PROD_NAME"],
            "product_name_en": ["PROD_NAME_EN"],
            "registration_no": ["REGISTER"],
            "manufacturer": ["COMPANY_NAME"],
            "notice_type": [
                "CASE_ALERT",
                "VOLUNTARY_BILLING",
                "REFUND_STIPULATED",
            ],
            "reason": ["CASE_ALERT", "REMARK_DETAIL"],
            "recall_action": ["OPERATION", "REMARK"],
            "impact": ["IMPACT_PROD"],
            "affected_lots": ["LOTNO", "MFT_DATE", "EXP_DATE"],
            "published_at": ["WRITE_DATE", "STATUS_DATE", "RECALL_DATE", "REPORT_DATE"],
            "source_created_at": ["CREATE_DATE"],
            "source_url": ["TR_ID", "IDA" if _text(record, "IDA") else "NEWCODE"],
        },
        origin_overrides={"notice_type": "machine_classified"},
    )
    mapped["field_provenance"]["generic_name"]["extraction_method"] = (
        "not_present_in_observed_listing_schema"
    )
    mapped["field_provenance"]["published_at"]["extraction_method"] = (
        "publication_date_fields_empty_in_observed_listing"
    )
    return mapped


def enrich_listing_record(
    record: dict[str, Any],
    detail_payload: dict[str, Any],
    attachment_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge official detail data without inferring absent notice fields."""
    report, lot_rows = _detail_sections(detail_payload)
    enriched = dict(record)
    source_reference = str(record["source_url"])

    detail_name_th = _detail_text(report, "DRUG_NM")
    detail_name_en = _detail_text(report, "DRUG_NMM")
    detail_registration = _detail_text(report, "DRUG_REGISTER")
    detail_manufacturer = _detail_text(report, "DRUG_MANUF")
    detail_form = _detail_text(report, "DRUG_FORMAT")
    detail_form_other = _detail_text(report, "DRUG_FORMAT_OTHER")
    detail_strength = _detail_text(report, "DRUG_CRITICON")
    detail_reason = (
        _detail_text(report, "PHYSICAL13_OTHER")
        or _detail_text(report, "OTHER_PLOBLEM")
        or _detail_text(report, "EX_PLOBLEM_TEXT")
    )
    detail_action = _detail_text(report, "PRE_ACTION")

    if detail_name_th:
        enriched["product_name_th"] = detail_name_th
    if detail_name_en:
        enriched["product_name_en"] = detail_name_en
    enriched["product_name"] = (
        enriched.get("product_name_th")
        or enriched.get("product_name_en")
        or enriched["product_name"]
    )
    enriched["title"] = enriched["product_name"]
    enriched["registration_no"] = detail_registration or enriched.get("registration_no")
    enriched["manufacturer"] = detail_manufacturer or enriched.get("manufacturer")
    enriched["dosage_form"] = " / ".join(
        value for value in (detail_form, detail_form_other) if value
    ) or None
    enriched["product_strength"] = detail_strength
    enriched["reason"] = enriched.get("reason") or detail_reason
    enriched["recall_action"] = enriched.get("recall_action") or detail_action
    enriched["source_detail_id"] = (
        _detail_text(report, "TR_ID") or enriched.get("source_detail_id")
    )

    detail_lots: list[dict[str, Any]] = []
    for lot_row in lot_rows:
        if not isinstance(lot_row, dict):
            raise SourceParsingError("FDA LOT detail row was not an object.")
        lot_number = _detail_text(lot_row, "LOT_NO")
        if not lot_number:
            continue
        detail_lots.append({
            "lot_number": lot_number,
            "manufacturing_date": parse_source_date(lot_row.get("MFD_DATE")),
            "expiry_date": parse_source_date(lot_row.get("EXP_DATE")),
            "extraction_method": "thai_fda_public_detail_json",
            "verification_status": "manual_review",
            "source_reference": source_reference,
        })
    if detail_lots:
        enriched["affected_lots"] = detail_lots

    attachments = (
        normalize_attachments(attachment_payload, source_reference=source_reference)
        if attachment_payload is not None
        else list(record.get("attachments", []))
    )
    enriched["attachments"] = attachments
    enriched["source_attachments_status"] = (
        ("available" if attachments else "none")
        if attachment_payload is not None
        else record.get("source_attachments_status", "not_requested")
    )
    result = detail_payload.get("RESULT")
    has_detail_data = bool(
        detail_name_th
        or detail_name_en
        or detail_registration
        or detail_manufacturer
        or detail_lots
        or detail_reason
        or detail_action
    )
    enriched["source_detail_status"] = (
        "available" if result == "SUCCESS" and has_detail_data else "partial"
    )

    provenance = dict(record.get("field_provenance", {}))
    for field, value, source_field in (
        ("product_name_th", detail_name_th, "DRUG_NM"),
        ("product_name_en", detail_name_en, "DRUG_NMM"),
        ("product_name", detail_name_th or detail_name_en, "DRUG_NM/DRUG_NMM"),
        ("registration_no", detail_registration, "DRUG_REGISTER"),
        ("manufacturer", detail_manufacturer, "DRUG_MANUF"),
        ("dosage_form", enriched["dosage_form"], "DRUG_FORMAT/DRUG_FORMAT_OTHER"),
        ("product_strength", detail_strength, "DRUG_CRITICON"),
        (
            "reason",
            detail_reason if not record.get("reason") else None,
            "PHYSICAL13_OTHER/OTHER_PLOBLEM/EX_PLOBLEM_TEXT",
        ),
        (
            "recall_action",
            detail_action if not record.get("recall_action") else None,
            "PRE_ACTION",
        ),
        ("affected_lots", detail_lots, "REPORT_QLY_PROBLEM_DETAIL"),
    ):
        if value is not None and value != []:
            provenance[field] = {
                "origin": "source_provided",
                "extraction_method": "thai_fda_public_detail_json",
                "source_fields": [source_field],
                "source_reference": source_reference,
                "verification_status": "manual_review",
            }
    if attachment_payload is not None and attachments:
        provenance["attachments"] = {
            "origin": "source_provided",
            "extraction_method": "thai_fda_public_attachment_list",
            "source_fields": ["LIST_ATTACH.LIST_FILE_ATTACH"],
            "source_reference": source_reference,
            "verification_status": "manual_review",
        }
    enriched["field_provenance"] = provenance

    original_listing = record.get("raw_source_data", {})
    response_hash = hashlib.sha256(
        json.dumps(
            detail_payload,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    raw_source_data = {
        "listing": original_listing,
        "detail_response": _redact_source_fields(detail_payload),
        "detail_response_sha256": response_hash,
    }
    if attachment_payload is not None:
        raw_source_data["attachment_response"] = _redact_source_fields(
            attachment_payload
        )
    enriched["raw_source_data"] = raw_source_data
    return enriched


class ThaiFdaSource:
    """Client for public, read-only Thai FDA listing and detail calls."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 20,
        max_retries: int = 2,
        request_delay_seconds: float = 1,
        client: httpx.Client | None = None,
    ):
        self.max_retries = max_retries
        self.request_delay_seconds = request_delay_seconds
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout_seconds)
        self._session_initialized = False
        self._last_request_at: float | None = None
        self.client.headers.update({
            "User-Agent": "YaSafe/1.0 (+https://github.com/bammyverylazy/ywc21_interview)",
            "Accept": "application/json",
        })

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def fetch_listing(self) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._wait_for_request()
            try:
                response = self.client.post(
                    LISTING_SERVICE_URL,
                    params={"SYSTEM_ID": "DRUG"},
                )
                response.raise_for_status()
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise SourceParsingError("FDA listing response was not valid JSON.") from exc
                if not isinstance(payload, list) or not all(
                    isinstance(item, dict) for item in payload
                ):
                    raise SourceParsingError(
                        "FDA listing response was not an array of notice records."
                    )
                return payload
            except SourceParsingError:
                raise
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if (
                    isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code < 500
                    and exc.response.status_code != 429
                ):
                    break

        if isinstance(last_error, httpx.HTTPStatusError):
            raise SourceRetrievalError(
                f"FDA listing request failed with HTTP {last_error.response.status_code}."
            ) from last_error
        if isinstance(last_error, httpx.TimeoutException):
            raise SourceRetrievalError("FDA listing request timed out.") from last_error
        raise SourceRetrievalError(
            f"FDA listing request failed ({type(last_error).__name__ if last_error else 'unknown error'})."
        ) from last_error

    def _wait_for_request(self) -> None:
        now = time.monotonic()
        if self._last_request_at is not None:
            wait_seconds = self.request_delay_seconds - (now - self._last_request_at)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
        self._last_request_at = time.monotonic()

    def _ensure_public_session(self) -> None:
        if self._session_initialized:
            return
        last_error: Exception | None = None
        for _attempt in range(self.max_retries + 1):
            self._wait_for_request()
            try:
                response = self.client.get(LISTING_PAGE_URL)
                response.raise_for_status()
                self._session_initialized = True
                return
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if (
                    isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code < 500
                    and exc.response.status_code != 429
                ):
                    break
        raise SourceRetrievalError(
            "FDA public-page session bootstrap failed."
        ) from last_error

    def _post_model(self, model: dict[str, Any], *, label: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for _attempt in range(self.max_retries + 1):
            self._wait_for_request()
            try:
                response = self.client.post(
                    DETAIL_SERVICE_URL,
                    json={"MODEL": json.dumps(model, separators=(",", ":"))},
                )
                response.raise_for_status()
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if (
                    isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code < 500
                    and exc.response.status_code != 429
                ):
                    break
                continue
            try:
                payload = response.json()
            except ValueError as exc:
                raise SourceParsingError(
                    f"FDA {label} response was not valid JSON."
                ) from exc
            if not isinstance(payload, dict):
                raise SourceParsingError(
                    f"FDA {label} response was not a JSON object."
                )
            return payload

        status = (
            f"HTTP {last_error.response.status_code}"
            if isinstance(last_error, httpx.HTTPStatusError)
            else "request failure"
        )
        raise SourceRetrievalError(
            f"FDA {label} request failed ({status})."
        ) from last_error

    def fetch_detail(self, main_transaction_id: str) -> dict[str, Any]:
        """Use the MAIN_TR value passed by the public page's detail click handler."""
        model = {
            "TR_ID": main_transaction_id,
            "PROCESS_ID": "REQ_QLY_PROB_10100",
            "FUNC_CODE": "FUNC-CORE-001-73,FUNC-CORE-001-40,FUNC-CORE-001-86",
        }
        self._ensure_public_session()
        payload = self._post_model(model, label="notice detail")
        if payload.get("RESULT") != "SUCCESS":
            try:
                report, lot_rows = _detail_sections(payload)
            except SourceParsingError as exc:
                raise SourceRetrievalError(
                    f"FDA detail service returned RESULT={payload.get('RESULT')} "
                    "without usable detail data."
                ) from exc
            detail_fields = (
                "DRUG_NM",
                "DRUG_NMM",
                "DRUG_REGISTER",
                "DRUG_MANUF",
                "DRUG_CRITICON",
                "PRE_ACTION",
                "PHYSICAL13_OTHER",
            )
            has_usable_data = any(
                _detail_text(report, key) for key in detail_fields
            ) or any(
                isinstance(row, dict) and _detail_text(row, "LOT_NO")
                for row in lot_rows
            )
            if not has_usable_data:
                raise SourceRetrievalError(
                    f"FDA detail service returned RESULT={payload.get('RESULT')} "
                    "without usable detail data."
                )
        return payload

    def fetch_attachments(self, main_transaction_id: str) -> dict[str, Any]:
        """Call the page's separate, observed attachment-list helper."""
        self._ensure_public_session()
        model = {
            "TR_ID": main_transaction_id,
            "PROCESS_ID": "SFTY_ALT_10100",
            "FUNC_CODE": "FUNC-CORE-001-68",
        }
        payload = self._post_model(model, label="attachment list")
        if not isinstance(payload.get("LIST_ATTACH"), list):
            raise SourceParsingError(
                "FDA attachment response did not contain the observed LIST_ATTACH array."
            )
        return payload

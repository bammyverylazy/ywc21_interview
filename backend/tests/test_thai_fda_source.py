import json
from pathlib import Path

import httpx
import pytest

from app.ingestion.thai_fda_source import (
    ATTACHMENT_SERVICE_URL,
    DETAIL_SERVICE_URL,
    LISTING_PAGE_URL,
    LISTING_SERVICE_URL,
    SourceParsingError,
    SourceRetrievalError,
    ThaiFdaSource,
    enrich_listing_record,
    normalize_attachments,
    normalize_listing_record,
    parse_source_date,
    parse_source_datetime,
)


def source_row(**overrides):
    return {
        "TR_ID": "REQ_QLY_PROB_10100-2569-0001_SFTY_ALT",
        "MAIN_TR": "REQ_QLY_PROB_10100-2569-0001",
        "IDA": 123,
        "PROD_NAME": "ชื่อยา",
        "PROD_NAME_EN": "Example Medicine",
        "CASE_ALERT": "เรียกคืนโดยสมัครใจ",
        "REGISTER": "REG-123",
        "LOTNO": "",
        "MFT_DATE": "",
        "EXP_DATE": "",
        "CREATE_DATE": "/Date(1791171930653)/",
        "ACTIVE": "ACTIVE",
        **overrides,
    }


def test_listing_uses_observed_read_only_post_and_parses_array():
    def handler(request):
        assert request.method == "POST"
        assert str(request.url) == f"{LISTING_SERVICE_URL}?SYSTEM_ID=DRUG"
        assert "YaSafe/" in request.headers["user-agent"]
        return httpx.Response(200, json=[source_row()])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    records = ThaiFdaSource(client=client).fetch_listing()

    assert len(records) == 1
    assert records[0]["TR_ID"].endswith("SFTY_ALT")


def test_listing_retries_timeout_then_succeeds():
    attempts = 0

    def handler(_request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("timeout")
        return httpx.Response(200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    records = ThaiFdaSource(
        client=client,
        max_retries=1,
        request_delay_seconds=0.001,
    ).fetch_listing()

    assert records == []
    assert attempts == 2


def test_listing_reports_http_and_malformed_response_failures():
    status_client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(503))
    )
    with pytest.raises(SourceRetrievalError, match="HTTP 503"):
        ThaiFdaSource(
            client=status_client,
            max_retries=0,
            request_delay_seconds=0.001,
        ).fetch_listing()

    malformed_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, content=b"not-json")
        )
    )
    with pytest.raises(SourceParsingError, match="valid JSON"):
        ThaiFdaSource(client=malformed_client).fetch_listing()

    wrong_shape_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"items": []})
        )
    )
    with pytest.raises(SourceParsingError, match="array"):
        ThaiFdaSource(client=wrong_shape_client).fetch_listing()


def test_normalization_preserves_thai_name_and_does_not_infer_dates_or_lots():
    result = normalize_listing_record(source_row())

    assert result["product_name_th"] == "ชื่อยา"
    assert result["product_name_en"] == "Example Medicine"
    assert result["product_name"] == "ชื่อยา"
    assert result["published_at"] is None
    assert result["affected_lots"] == []
    assert result["verification_status"] == "manual_review"
    assert result["source_id"].endswith(":123")
    assert result["source_created_at"] == parse_source_datetime("/Date(1791171930653)/")


def test_normalization_uses_explicit_lot_and_thai_be_date():
    result = normalize_listing_record(source_row(
        LOTNO="LOT-A",
        MFT_DATE="01/02/2568",
        EXP_DATE="02/02/2569",
    ))

    assert result["affected_lots"] == [{
        "lot_number": "LOT-A",
        "manufacturing_date": parse_source_date("01/02/2568"),
        "expiry_date": parse_source_date("02/02/2569"),
    }]
    assert str(result["affected_lots"][0]["manufacturing_date"]) == "2025-02-01"
    assert result["notice_type"] == "RECALL"
    assert result["field_provenance"]["affected_lots"]["origin"] == "source_provided"
    assert result["field_provenance"]["notice_type"]["origin"] == "machine_classified"


def test_normalization_requires_stable_identity_and_product_name():
    with pytest.raises(SourceParsingError, match="stable"):
        normalize_listing_record({"PROD_NAME": "medicine"})
    with pytest.raises(SourceParsingError, match="no product name"):
        normalize_listing_record(source_row(PROD_NAME=None, PROD_NAME_EN=None))


def test_source_datetime_parses_current_listing_date_format_and_keeps_provenance_missing():
    record = source_row(CREATE_DATE="07/09/2026 09:03:39")
    normalized = normalize_listing_record(record)

    assert normalized["source_created_at"].isoformat() == "2026-09-07T09:03:39+07:00"
    assert normalized["published_at"] is None
    assert normalized["field_provenance"]["published_at"]["origin"] == "missing"
    assert normalized["field_provenance"]["generic_name"]["origin"] == "missing"


def _fixture(name):
    return json.loads(
        (Path(__file__).parent / "fixtures" / "thai_fda" / name).read_text(
            encoding="utf-8"
        )
    )


def test_source_date_uses_bangkok_calendar_day_for_dotnet_timestamps():
    assert str(parse_source_date("/Date(1620579600000)/")) == "2021-05-10"


def test_detail_request_uses_page_main_tr_and_accepts_populated_fail_response():
    main_transaction_id = "REQ_QLY_PROB_10100-2569-0079"

    def handler(request):
        if request.method == "GET":
            assert str(request.url) == LISTING_PAGE_URL
            return httpx.Response(
                200,
                text="<html>public listing</html>",
                headers={"set-cookie": "cookiesession1=test-session; Path=/; HttpOnly"},
            )
        assert request.method == "POST"
        assert str(request.url) == DETAIL_SERVICE_URL
        assert request.headers.get("cookie") == "cookiesession1=test-session"
        outer = json.loads(request.content)
        assert json.loads(outer["MODEL"]) == {
            "TR_ID": main_transaction_id,
            "PROCESS_ID": "REQ_QLY_PROB_10100",
            "FUNC_CODE": "FUNC-CORE-001-73,FUNC-CORE-001-40,FUNC-CORE-001-86",
        }
        return httpx.Response(200, json=_fixture("detail-populated-sanitized.json"))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    payload = ThaiFdaSource(
        client=client,
        request_delay_seconds=0,
    ).fetch_detail(main_transaction_id)

    assert payload["RESULT"] == "FAIL"
    assert payload["MODEL_DRUG"]["REPORT_QLY_PROBLEM"]["DRUG_REGISTER"] == "1C 99/99"


def test_detail_failure_without_usable_fields_is_explicit():
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, text="public page")
        return httpx.Response(200, json=_fixture("detail-failed-sanitized.json"))

    source = ThaiFdaSource(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        request_delay_seconds=0,
    )
    with pytest.raises(SourceRetrievalError, match="RESULT=FAIL"):
        source.fetch_detail("REQ_QLY_PROB_10100-TEST-EMPTY")

    assert [request.method for request in requests] == ["GET", "POST"]


def test_attachment_request_and_metadata_use_observed_public_fields():
    main_transaction_id = "REQ_QLY_PROB_10100-6400222"

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, text="public page")
        assert str(request.url) == DETAIL_SERVICE_URL
        outer = json.loads(request.content)
        assert json.loads(outer["MODEL"]) == {
            "TR_ID": main_transaction_id,
            "PROCESS_ID": "SFTY_ALT_10100",
            "FUNC_CODE": "FUNC-CORE-001-68",
        }
        return httpx.Response(200, json=_fixture("attachments-sanitized.json"))

    source = ThaiFdaSource(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        request_delay_seconds=0,
    )
    payload = source.fetch_attachments(main_transaction_id)
    attachments = normalize_attachments(
        payload,
        source_reference="https://apres.fda.moph.go.th/FDA_POST_VIEW_CENTER/PUBLIC/DRUG_ALERT",
    )

    assert len(attachments) == 1
    assert attachments[0]["name"] == "Official attachment"
    assert attachments[0]["original_filename"] == "notice-image.jpg"
    assert attachments[0]["file_url"] == (
        f"{ATTACHMENT_SERVICE_URL}?NAME_FAKE=PUBLIC-ATTACHMENT-TEST.jpg"
    )
    assert attachments[0]["verification_status"] == "manual_review"


def test_malformed_attachment_payload_is_rejected():
    with pytest.raises(SourceParsingError, match="LIST_ATTACH"):
        normalize_attachments(
            _fixture("attachments-malformed-sanitized.json"),
            source_reference="https://apres.fda.moph.go.th/FDA_POST_VIEW_CENTER/PUBLIC/DRUG_ALERT",
        )


def test_detail_enrichment_preserves_multiple_lots_dates_provenance_and_redaction():
    listing = normalize_listing_record(source_row())
    enriched = enrich_listing_record(
        listing,
        _fixture("detail-populated-sanitized.json"),
        _fixture("attachments-sanitized.json"),
    )

    assert enriched["source_detail_status"] == "partial"
    assert enriched["source_attachments_status"] == "available"
    assert enriched["generic_name"] is None
    assert enriched["published_at"] is None
    assert enriched["registration_no"] == "1C 99/99"
    assert enriched["manufacturer"] == "Example Manufacturer"
    assert enriched["dosage_form"] == "CAPSULE HARD"
    assert enriched["product_strength"] == "18 MCG"
    assert [lot["lot_number"] for lot in enriched["affected_lots"]] == [
        "LOT-TEST-1",
        "LOT-TEST-2",
    ]
    assert str(enriched["affected_lots"][0]["manufacturing_date"]) == "2021-05-10"
    assert str(enriched["affected_lots"][0]["expiry_date"]) == "2021-11-09"
    assert enriched["affected_lots"][1]["manufacturing_date"] is None
    assert enriched["affected_lots"][0]["verification_status"] == "manual_review"
    assert enriched["field_provenance"]["affected_lots"]["origin"] == "source_provided"
    assert enriched["field_provenance"]["manufacturer"]["extraction_method"] == (
        "thai_fda_public_detail_json"
    )
    assert "CITIZEN_ID" not in enriched["raw_source_data"]["detail_response"][
        "MODEL_DRUG"
    ]["REPORT_QLY_PROBLEM"]
    assert enriched["raw_source_data"]["detail_response_sha256"]


def test_detail_with_missing_fields_does_not_replace_listing_values():
    listing = normalize_listing_record(
        source_row(
            REGISTER="LIST-REG-1",
            COMPANY_NAME="Listing Manufacturer",
        )
    )
    detail = _fixture("detail-populated-sanitized.json")
    detail["MODEL_DRUG"]["REPORT_QLY_PROBLEM"].update({
        "DRUG_REGISTER": "",
        "DRUG_MANUF": "",
        "DRUG_NM": "-",
        "DRUG_NMM": "",
    })
    detail["MODEL_DRUG"]["REPORT_QLY_PROBLEM_DETAIL"] = []

    enriched = enrich_listing_record(listing, detail)

    assert enriched["registration_no"] == "LIST-REG-1"
    assert enriched["manufacturer"] == "Listing Manufacturer"
    assert enriched["affected_lots"] == []
    assert enriched["generic_name"] is None
    assert enriched["published_at"] is None

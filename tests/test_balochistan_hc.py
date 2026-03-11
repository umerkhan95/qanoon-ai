"""Tests for the Balochistan HC crawler pipeline.

All tests use offline sample data — no live website hits.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.pipelines.balochistan_hc.constants import (
    COURT_CODE,
    COURT_TYPE_HC_BENCH,
    COURT_TYPE_TRIBUNAL,
    HC_BENCH_TYPES,
    PORTAL_URL,
    SEARCH_BY_CASE_ID,
    SEARCH_BY_COURT,
    SEARCH_BY_JUDGE,
)
from src.pipelines.balochistan_hc.listing import (
    API_BASE_URL,
    CrawlResult,
    JudgmentRecord,
    _build_pdf_url,
    _build_search_js,
    _clean_html_entities,
    _extract_api_result,
    _parse_date,
    parse_api_response,
)


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_API_RECORD = {
    "FILE_ID": 225535,
    "FILE_FOLDER": "2025",
    "FILE_NAME": "100107804897_97bcbd69f9b646b0add9c77386812f65",
    "FILE_EXT": "doc",
    "CASE_ID": 100107804897,
    "CASE_TITLE": "Muhammad Younas S/O Noor Muhammad vs Chief Election Commissoner And&nbsp;Another",
    "REGISTER_NUMBER": "CP-2191/2025",
    "AUTHOR_JUDGE": "Hon'ble Chief Justice Muhammad Kamran Khan Malakhail",
    "TYPE_NAME": "Short Order",
    "ORDER_DATE": "24/12/2025",
}

SAMPLE_API_RECORD_NO_PDF = {
    "FILE_ID": 0,
    "FILE_FOLDER": "",  # Empty folder means no PDF URL
    "FILE_NAME": "",
    "FILE_EXT": "",
    "CASE_ID": 999,
    "CASE_TITLE": "Test Case",
    "REGISTER_NUMBER": "CP-1/2024",
    "AUTHOR_JUDGE": "Judge X",
    "TYPE_NAME": "Judgment",
    "ORDER_DATE": "",
}

SAMPLE_API_RECORD_MINIMAL = {
    "FILE_ID": 12345,
    "FILE_FOLDER": "2023",
    "FILE_NAME": "test_file_abc123",
    "FILE_EXT": "pdf",
    "CASE_ID": 456,
    "CASE_TITLE": "Simple vs Case",
    "REGISTER_NUMBER": "WP-100/2023",
    "AUTHOR_JUDGE": "",
    "TYPE_NAME": "",
    "ORDER_DATE": "01/01/2023",
}

SAMPLE_HTML_WITH_RESULT = '''
<html><body>
<div id="bhc-api-result" style="display:none">{"success":true,"count":2,"records":[
{"FILE_ID":100,"FILE_FOLDER":"2024","FILE_NAME":"test1","FILE_EXT":"pdf",
"CASE_ID":1,"CASE_TITLE":"A vs B","REGISTER_NUMBER":"CP-1/2024",
"AUTHOR_JUDGE":"Judge A","TYPE_NAME":"Judgment","ORDER_DATE":"15/06/2024"},
{"FILE_ID":101,"FILE_FOLDER":"2024","FILE_NAME":"test2","FILE_EXT":"doc",
"CASE_ID":2,"CASE_TITLE":"C vs D&amp;nbsp;E","REGISTER_NUMBER":"WP-2/2024",
"AUTHOR_JUDGE":"Judge B","TYPE_NAME":"Short Order","ORDER_DATE":"20/07/2024"}
],"auth_token":"Bearer test123","api_base_url":"https://api.bhc.gov.pk/"}</div>
</body></html>
'''


# ---------------------------------------------------------------------------
# Tests: _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_valid_date(self) -> None:
        assert _parse_date("24/12/2025") == date(2025, 12, 24)

    def test_first_of_year(self) -> None:
        assert _parse_date("01/01/2023") == date(2023, 1, 1)

    def test_empty_string(self) -> None:
        assert _parse_date("") is None

    def test_whitespace(self) -> None:
        assert _parse_date("  ") is None

    def test_invalid_format(self) -> None:
        assert _parse_date("2025-12-24") is None

    def test_invalid_date(self) -> None:
        assert _parse_date("32/13/2025") is None

    def test_partial_date(self) -> None:
        assert _parse_date("24/12") is None


# ---------------------------------------------------------------------------
# Tests: _clean_html_entities
# ---------------------------------------------------------------------------

class TestCleanHtmlEntities:
    def test_nbsp(self) -> None:
        assert _clean_html_entities("A&nbsp;B") == "A\u00a0B"

    def test_amp(self) -> None:
        assert _clean_html_entities("A&amp;B") == "A&B"

    def test_no_entities(self) -> None:
        assert _clean_html_entities("plain text") == "plain text"

    def test_whitespace_trim(self) -> None:
        assert _clean_html_entities("  hello  ") == "hello"

    def test_empty(self) -> None:
        assert _clean_html_entities("") == ""


# ---------------------------------------------------------------------------
# Tests: _build_pdf_url
# ---------------------------------------------------------------------------

class TestBuildPdfUrl:
    def test_valid_record(self) -> None:
        url = _build_pdf_url(SAMPLE_API_RECORD)
        expected = (
            f"{API_BASE_URL}/v2/downloadpdf/2025/"
            "100107804897_97bcbd69f9b646b0add9c77386812f65.doc"
        )
        assert url == expected

    def test_no_file_folder(self) -> None:
        assert _build_pdf_url({"FILE_FOLDER": "", "FILE_NAME": "x", "FILE_EXT": "pdf"}) == ""

    def test_no_file_name(self) -> None:
        assert _build_pdf_url({"FILE_FOLDER": "2024", "FILE_NAME": "", "FILE_EXT": "pdf"}) == ""

    def test_missing_fields(self) -> None:
        assert _build_pdf_url({}) == ""


# ---------------------------------------------------------------------------
# Tests: parse_api_response
# ---------------------------------------------------------------------------

class TestParseApiResponse:
    def test_single_record(self) -> None:
        records = parse_api_response([SAMPLE_API_RECORD], "https://test.url")
        assert len(records) == 1
        r = records[0]
        assert r.file_id == 225535
        assert r.case_id == 100107804897
        assert r.case_number == "CP-2191/2025"
        assert "Muhammad Younas" in r.case_title
        assert "\u00a0" in r.case_title  # &nbsp; decoded
        assert r.order_date == "24/12/2025"
        assert r.order_date_parsed == date(2025, 12, 24)
        assert r.type_name == "Short Order"
        assert "downloadpdf/2025" in r.pdf_url
        assert r.source_url == "https://test.url"

    def test_empty_list(self) -> None:
        assert parse_api_response([], "url") == []

    def test_no_pdf_url(self) -> None:
        records = parse_api_response([SAMPLE_API_RECORD_NO_PDF], "url")
        assert len(records) == 1
        assert records[0].pdf_url == ""
        assert records[0].order_date_parsed is None

    def test_minimal_record(self) -> None:
        records = parse_api_response([SAMPLE_API_RECORD_MINIMAL], "url")
        assert len(records) == 1
        r = records[0]
        assert r.case_number == "WP-100/2023"
        assert r.author_judge == ""
        assert r.order_date_parsed == date(2023, 1, 1)

    def test_multiple_records(self) -> None:
        records = parse_api_response(
            [SAMPLE_API_RECORD, SAMPLE_API_RECORD_MINIMAL], "url",
        )
        assert len(records) == 2
        assert records[0].case_number == "CP-2191/2025"
        assert records[1].case_number == "WP-100/2023"


# ---------------------------------------------------------------------------
# Tests: _extract_api_result
# ---------------------------------------------------------------------------

class TestExtractApiResult:
    def test_valid_html(self) -> None:
        data = _extract_api_result(SAMPLE_HTML_WITH_RESULT)
        assert data["success"] is True
        assert data["count"] == 2
        assert len(data["records"]) == 2

    def test_missing_element(self) -> None:
        from src.pipelines.balochistan_hc.errors import CrawlError
        with pytest.raises(CrawlError, match="Could not find"):
            _extract_api_result("<html><body></body></html>")

    def test_invalid_json(self) -> None:
        from src.pipelines.balochistan_hc.errors import CrawlError
        html = '<div id="bhc-api-result">not valid json</div>'
        with pytest.raises(CrawlError, match="Failed to parse"):
            _extract_api_result(html)

    def test_error_response(self) -> None:
        html = '<div id="bhc-api-result">{"error":"API call failed"}</div>'
        data = _extract_api_result(html)
        assert "error" in data


# ---------------------------------------------------------------------------
# Tests: _build_search_js
# ---------------------------------------------------------------------------

class TestBuildSearchJs:
    def test_search_by_judge(self) -> None:
        js = _build_search_js(search_by=SEARCH_BY_JUDGE, judge_id=1038)
        assert "/v2/judgments" in js
        assert '"searchBy": 3' in js
        assert '"judgeId": 1038' in js

    def test_search_by_court(self) -> None:
        js = _build_search_js(
            search_by=SEARCH_BY_COURT, court_id=100, category_id="Bail",
        )
        assert '"searchBy": 2' in js
        assert '"courtId": 100' in js
        assert '"categoryId": "Bail"' in js

    def test_custom_date_range(self) -> None:
        js = _build_search_js(
            search_by=SEARCH_BY_JUDGE,
            judge_id=1,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        assert "2024-01-01" in js
        assert "2024-12-31" in js

    def test_default_date_range(self) -> None:
        js = _build_search_js(search_by=SEARCH_BY_CASE_ID)
        assert "2001-01-01" in js
        assert "2026-12-31" in js


# ---------------------------------------------------------------------------
# Tests: JudgmentRecord model
# ---------------------------------------------------------------------------

class TestJudgmentRecord:
    def test_serialization(self) -> None:
        record = JudgmentRecord(
            file_id=100,
            case_id=1,
            case_number="CP-1/2024",
            case_title="A vs B",
            author_judge="Judge A",
            type_name="Judgment",
            order_date="15/06/2024",
            order_date_parsed=date(2024, 6, 15),
            pdf_url="https://portal.bhc.gov.pk/v2/downloadpdf/100/test.pdf",
            source_url="https://portal.bhc.gov.pk/judgments",
        )
        d = record.model_dump()
        assert d["file_id"] == 100
        assert d["case_number"] == "CP-1/2024"
        assert d["order_date_parsed"] == date(2024, 6, 15)

    def test_optional_date(self) -> None:
        record = JudgmentRecord(
            file_id=1,
            case_id=1,
            case_number="X",
            case_title="Y",
            author_judge="Z",
            type_name="T",
            order_date="",
            pdf_url="",
            source_url="",
        )
        assert record.order_date_parsed is None


# ---------------------------------------------------------------------------
# Tests: Constants
# ---------------------------------------------------------------------------

class TestCrawlResult:
    def test_with_auth(self) -> None:
        result = CrawlResult(
            records=[],
            auth_token="Bearer abc123",
            api_base_url="https://api.bhc.gov.pk/",
        )
        assert result.auth_token == "Bearer abc123"
        assert result.api_base_url == "https://api.bhc.gov.pk/"

    def test_defaults(self) -> None:
        result = CrawlResult(records=[])
        assert result.auth_token == ""
        assert result.api_base_url == ""


class TestConstants:
    def test_court_code(self) -> None:
        assert COURT_CODE == "BHC"

    def test_hc_bench_types(self) -> None:
        assert COURT_TYPE_HC_BENCH in HC_BENCH_TYPES
        assert COURT_TYPE_TRIBUNAL in HC_BENCH_TYPES

    def test_search_by_values(self) -> None:
        assert SEARCH_BY_CASE_ID == 1
        assert SEARCH_BY_COURT == 2
        assert SEARCH_BY_JUDGE == 3

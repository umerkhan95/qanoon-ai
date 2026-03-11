"""Tests for the Supreme Court of Pakistan crawler pipeline.

Tests parsing logic with sample data based on Wayback Machine recon.
Does NOT hit the live website — all tests use offline sample data.
"""

from datetime import date

import pytest

from src.pipelines.supreme_court.constants import (
    BASE_URL,
    COURT_CODE,
    JUDGMENTS_URL,
    MAINTENANCE_MARKERS,
    PAGINATION_TEMPLATE,
)
from src.pipelines.supreme_court.errors import (
    CrawlError,
    ExtractionError,
    SiteMaintenanceError,
)
from src.pipelines.supreme_court.listing import (
    JudgmentRecord,
    _has_next_page,
    _is_maintenance_page,
    _parse_case_number,
    _parse_date,
    parse_listing_rows,
)


class TestConstants:
    def test_base_url(self):
        assert "supremecourt.gov.pk" in BASE_URL

    def test_court_code(self):
        assert COURT_CODE == "SC"

    def test_pagination_template(self):
        url = PAGINATION_TEMPLATE.format(page=3)
        assert "/page/3/" in url

    def test_judgments_url(self):
        assert JUDGMENTS_URL.endswith("/category/judgements/")


class TestErrors:
    def test_crawl_error_is_exception(self):
        with pytest.raises(CrawlError):
            raise CrawlError("test")

    def test_extraction_error_is_exception(self):
        with pytest.raises(ExtractionError):
            raise ExtractionError("test")

    def test_maintenance_error_is_crawl_error(self):
        err = SiteMaintenanceError("down")
        assert isinstance(err, CrawlError)


class TestParseCaseNumber:
    def test_constitution_petition(self):
        result = _parse_case_number("Constitution Petition No. 39 of 2019")
        assert result == "Constitution Petition No. 39 of 2019"

    def test_civil_appeal(self):
        result = _parse_case_number("Civil Appeal No. 1234 of 2023")
        assert result == "Civil Appeal No. 1234 of 2023"

    def test_criminal_appeal(self):
        result = _parse_case_number("Criminal Appeal No. 567 of 2022")
        assert result == "Criminal Appeal No. 567 of 2022"

    def test_smc(self):
        result = _parse_case_number("SMC No. 1 of 2024")
        assert result == "SMC No. 1 of 2024"

    def test_hrc(self):
        result = _parse_case_number("HRC No. 42 of 2020")
        assert result == "HRC No. 42 of 2020"

    def test_writ_petition(self):
        result = _parse_case_number("W.P No. 100 of 2023")
        assert result == "W.P No. 100 of 2023"

    def test_abbreviated_criminal(self):
        result = _parse_case_number("Cr. Appeal No. 200 of 2021")
        assert result == "Cr. Appeal No. 200 of 2021"

    def test_no_match_returns_full_title(self):
        title = "Some random announcement"
        assert _parse_case_number(title) == title

    def test_empty_string(self):
        assert _parse_case_number("") == ""

    def test_whitespace_stripped(self):
        result = _parse_case_number("  Civil Appeal No. 5 of 2024  ")
        assert result == "Civil Appeal No. 5 of 2024"


class TestParseDate:
    def test_wordpress_format(self):
        assert _parse_date("December 23, 2024") == date(2024, 12, 23)

    def test_wordpress_format_no_comma(self):
        assert _parse_date("January 5 2023") == date(2023, 1, 5)

    def test_abbreviated_month(self):
        assert _parse_date("Jan 15, 2024") == date(2024, 1, 15)

    def test_dd_mm_yyyy(self):
        assert _parse_date("23-12-2024") == date(2024, 12, 23)

    def test_iso_format(self):
        assert _parse_date("2024-12-23") == date(2024, 12, 23)

    def test_empty(self):
        assert _parse_date("") is None

    def test_invalid(self):
        assert _parse_date("not-a-date") is None

    def test_whitespace(self):
        assert _parse_date("  December 23, 2024  ") == date(2024, 12, 23)


class TestIsMaintenancePage:
    def test_maintenance_detected(self):
        html = "<h1>Site Under Maintenance</h1><p>We apologize...</p>"
        assert _is_maintenance_page(html) is True

    def test_back_soon_detected(self):
        html = "<h1>We'll Be Back Soon</h1>"
        assert _is_maintenance_page(html) is True

    def test_down_for_maintenance(self):
        html = "This site is currently down for maintenance."
        assert _is_maintenance_page(html) is True

    def test_normal_page_not_detected(self):
        html = "<html><body><h1>Supreme Court of Pakistan</h1></body></html>"
        assert _is_maintenance_page(html) is False

    def test_empty_html(self):
        assert _is_maintenance_page("") is False

    def test_case_insensitive(self):
        html = "<h1>SITE UNDER MAINTENANCE</h1>"
        assert _is_maintenance_page(html) is True


class TestParseListingRows:
    @pytest.fixture
    def sample_rows(self):
        return [
            {
                "title": "Constitution Petition No. 39 of 2019",
                "post_url": "https://www.supremecourt.gov.pk/constitution-petition-no-39-of-2019/",
                "date": "August 6, 2024",
                "date_attr": "2024-08-06",
                "summary": "The court examined the constitutional validity...",
                "pdf_url": "https://www.supremecourt.gov.pk/wp-content/uploads/2024/08/cp39-2019.pdf",
            },
            {
                "title": "Civil Appeal No. 1500 of 2023",
                "post_url": "https://www.supremecourt.gov.pk/civil-appeal-no-1500-of-2023/",
                "date": "July 15, 2024",
                "date_attr": "",
                "summary": "Appeal against High Court decision in property dispute.",
                "pdf_url": "",
            },
        ]

    def test_parses_records(self, sample_rows):
        records = parse_listing_rows(sample_rows, "test_source")
        assert len(records) == 2
        assert all(isinstance(r, JudgmentRecord) for r in records)

    def test_case_number_extracted(self, sample_rows):
        records = parse_listing_rows(sample_rows, "test_source")
        assert records[0].case_number == "Constitution Petition No. 39 of 2019"
        assert records[1].case_number == "Civil Appeal No. 1500 of 2023"

    def test_date_prefers_datetime_attr(self, sample_rows):
        records = parse_listing_rows(sample_rows, "test_source")
        assert records[0].decision_date == "2024-08-06"
        assert records[0].decision_date_parsed == date(2024, 8, 6)

    def test_date_falls_back_to_text(self, sample_rows):
        records = parse_listing_rows(sample_rows, "test_source")
        assert records[1].decision_date == "July 15, 2024"
        assert records[1].decision_date_parsed == date(2024, 7, 15)

    def test_pdf_url_captured(self, sample_rows):
        records = parse_listing_rows(sample_rows, "test_source")
        assert records[0].pdf_url.endswith(".pdf")
        assert records[1].pdf_url == ""

    def test_summary_captured(self, sample_rows):
        records = parse_listing_rows(sample_rows, "test_source")
        assert "constitutional" in records[0].summary.lower()

    def test_source_url_set(self, sample_rows):
        records = parse_listing_rows(sample_rows, "test_source")
        assert all(r.source_url == "test_source" for r in records)

    def test_empty_title_skipped(self):
        rows = [{"title": "", "post_url": "http://example.com"}]
        records = parse_listing_rows(rows, "test")
        assert records == []

    def test_empty_list(self):
        records = parse_listing_rows([], "test")
        assert records == []

    def test_missing_fields(self):
        rows = [{"title": "Civil Appeal No. 5 of 2024"}]
        records = parse_listing_rows(rows, "test")
        assert len(records) == 1
        assert records[0].pdf_url == ""
        assert records[0].post_url == ""

    def test_summary_truncated(self):
        rows = [{"title": "Test Case", "summary": "x" * 1000}]
        records = parse_listing_rows(rows, "test")
        assert len(records[0].summary) <= 500


class TestHasNextPage:
    def test_next_page_link(self):
        html = '<a href="/category/judgements/page/3/" class="next">Next</a>'
        assert _has_next_page(html, 2) is True

    def test_next_class(self):
        html = '<a class="next" href="/page/2/">Next Page</a>'
        assert _has_next_page(html, 1) is True

    def test_no_next_page(self):
        html = '<div class="pagination"><a href="/page/1/">1</a></div>'
        assert _has_next_page(html, 5) is False

    def test_empty_html(self):
        assert _has_next_page("", 1) is False

    def test_page_numbers_class(self):
        html = '<a class="next page-numbers" href="/page/4/">Next</a>'
        assert _has_next_page(html, 3) is True


class TestJudgmentRecordModel:
    def test_create_record(self):
        record = JudgmentRecord(
            title="Constitution Petition No. 39 of 2019",
            case_number="Constitution Petition No. 39 of 2019",
            post_url="https://www.supremecourt.gov.pk/cp-39-2019/",
            pdf_url="https://www.supremecourt.gov.pk/wp-content/uploads/cp39.pdf",
            decision_date="2024-08-06",
            decision_date_parsed=date(2024, 8, 6),
            bench="Justice A, Justice B",
            summary="Constitutional validity examined.",
            source_url="https://www.supremecourt.gov.pk/category/judgements/",
        )
        assert record.title == "Constitution Petition No. 39 of 2019"
        assert record.bench == "Justice A, Justice B"

    def test_optional_date(self):
        record = JudgmentRecord(
            title="Test",
            case_number="Test",
            post_url="",
            pdf_url="",
            decision_date="",
            bench="",
            summary="",
            source_url="test",
        )
        assert record.decision_date_parsed is None

    def test_model_dump(self):
        record = JudgmentRecord(
            title="Test",
            case_number="Test No. 1 of 2024",
            post_url="http://example.com",
            pdf_url="",
            decision_date="2024-01-01",
            decision_date_parsed=date(2024, 1, 1),
            bench="",
            summary="Test summary",
            source_url="test",
        )
        data = record.model_dump()
        assert data["case_number"] == "Test No. 1 of 2024"
        assert data["decision_date_parsed"] == date(2024, 1, 1)

"""Tests for the Lahore HC crawler pipeline.

Tests parsing logic with realistic sample data based on the LHC website structure.
Does NOT hit the live website — all tests use offline sample data.
"""

from datetime import date

import pytest

from src.pipelines.lahore_hc.listing import (
    JudgmentRecord,
    _extract_pdf_url_from_html,
    _normalize_pdf_url,
    _parse_date,
    parse_css_rows,
    parse_table_data,
)


class TestParseDate:
    def test_standard_date_dashes(self):
        assert _parse_date("23-12-2024") == date(2024, 12, 23)

    def test_standard_date_slashes(self):
        assert _parse_date("23/12/2024") == date(2024, 12, 23)

    def test_single_digit_day(self):
        assert _parse_date("5-01-2023") == date(2023, 1, 5)

    def test_empty(self):
        assert _parse_date("") is None

    def test_invalid(self):
        assert _parse_date("not-a-date") is None

    def test_whitespace(self):
        assert _parse_date("  23-12-2024  ") == date(2024, 12, 23)

    def test_none_like(self):
        assert _parse_date("   ") is None


class TestNormalizePdfUrl:
    def test_absolute_https(self):
        url = "https://sys.lhc.gov.pk/appjudgments/2024LHC4177.pdf"
        assert _normalize_pdf_url(url) == url

    def test_absolute_http(self):
        url = "http://sys.lhc.gov.pk/appjudgments/2021LHC630.pdf"
        assert _normalize_pdf_url(url) == url

    def test_relative_path(self):
        result = _normalize_pdf_url("/appjudgments/2024LHC4177.pdf")
        assert result == "https://sys.lhc.gov.pk/appjudgments/2024LHC4177.pdf"

    def test_filename_only(self):
        result = _normalize_pdf_url("2024LHC4177.pdf")
        assert result == "https://sys.lhc.gov.pk/appjudgments/2024LHC4177.pdf"

    def test_empty(self):
        assert _normalize_pdf_url("") == ""

    def test_whitespace(self):
        assert _normalize_pdf_url("  ") == ""

    def test_non_pdf(self):
        result = _normalize_pdf_url("some_path")
        assert result == "some_path"


class TestExtractPdfUrlFromHtml:
    def test_standard_link(self):
        html = '<a href="https://sys.lhc.gov.pk/appjudgments/2024LHC4177.pdf">View</a>'
        result = _extract_pdf_url_from_html(html)
        assert result == "https://sys.lhc.gov.pk/appjudgments/2024LHC4177.pdf"

    def test_relative_link(self):
        html = '<a href="/appjudgments/2021LHC630.pdf">Download</a>'
        result = _extract_pdf_url_from_html(html)
        assert result == "https://sys.lhc.gov.pk/appjudgments/2021LHC630.pdf"

    def test_single_quotes(self):
        html = "<a href='2024LHC100.pdf'>PDF</a>"
        result = _extract_pdf_url_from_html(html)
        assert result == "https://sys.lhc.gov.pk/appjudgments/2024LHC100.pdf"

    def test_no_link(self):
        assert _extract_pdf_url_from_html("No link here") == ""

    def test_empty(self):
        assert _extract_pdf_url_from_html("") == ""


class TestParseTableData:
    """Tests for DefaultTableExtraction output parsing."""

    @pytest.fixture
    def sample_table(self):
        return {
            "headers": [
                "S.No", "Case No", "Case Title", "Judge Name",
                "LHC Citation", "Other Citation", "Category",
                "Decision Date", "Judgment",
            ],
            "rows": [
                [
                    "1",
                    "W.P. No. 12345/2024",
                    "Muhammad Ali Vs Province of Punjab",
                    "Justice Ahmed Khan",
                    "2024 LHC 4177",
                    "2024 CLC 500",
                    "Constitutional",
                    "23-12-2024",
                    '<a href="https://sys.lhc.gov.pk/appjudgments/2024LHC4177.pdf">View</a>',
                ],
                [
                    "2",
                    "Cr.A No. 200/2023",
                    "State Vs Aslam Khan",
                    "Justice Farooq Haider",
                    "2023 LHC 630",
                    "2023 PCrLJ 100",
                    "Criminal",
                    "15-06-2023",
                    '<a href="/appjudgments/2023LHC630.pdf">View</a>',
                ],
            ],
        }

    def test_parses_records(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert len(records) == 2
        assert all(isinstance(r, JudgmentRecord) for r in records)

    def test_case_number_parsed(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].case_number == "W.P. No. 12345/2024"
        assert records[1].case_number == "Cr.A No. 200/2023"

    def test_case_title_parsed(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].case_title == "Muhammad Ali Vs Province of Punjab"

    def test_judge_name(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].judge_name == "Justice Ahmed Khan"
        assert records[1].judge_name == "Justice Farooq Haider"

    def test_date_parsed(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].decision_date_parsed == date(2024, 12, 23)
        assert records[0].decision_date == "23-12-2024"

    def test_category(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].category == "Constitutional"
        assert records[1].category == "Criminal"

    def test_lhc_citation(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].lhc_citation == "2024 LHC 4177"
        assert records[1].lhc_citation == "2023 LHC 630"

    def test_other_citation(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].other_citation == "2024 CLC 500"
        assert records[1].other_citation == "2023 PCrLJ 100"

    def test_pdf_url_extracted(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].pdf_url == "https://sys.lhc.gov.pk/appjudgments/2024LHC4177.pdf"
        assert records[1].pdf_url == "https://sys.lhc.gov.pk/appjudgments/2023LHC630.pdf"

    def test_empty_rows(self):
        table = {"headers": ["S.No", "Case No"], "rows": []}
        records = parse_table_data(table, "test")
        assert records == []

    def test_source_url_set(self, sample_table):
        records = parse_table_data(sample_table, "my_source")
        assert all(r.source_url == "my_source" for r in records)

    def test_positional_fallback(self):
        """When headers are missing, positional access should work."""
        table = {
            "headers": [],
            "rows": [
                [
                    "1",
                    "W.P. No. 100/2024",
                    "Test Vs Test",
                    "Justice X",
                    "2024 LHC 100",
                    "",
                    "Civil",
                    "01-01-2024",
                    "",
                ],
            ],
        }
        records = parse_table_data(table, "test")
        assert len(records) == 1
        assert records[0].case_number == "W.P. No. 100/2024"
        assert records[0].category == "Civil"

    def test_short_row_skipped(self):
        """Rows with too few columns should be skipped."""
        table = {
            "headers": [],
            "rows": [
                ["1", "W.P. No. 100/2024", "Test"],
            ],
        }
        records = parse_table_data(table, "test")
        assert records == []


class TestParseCssRows:
    """Tests for JsonCssExtractionStrategy output parsing."""

    @pytest.fixture
    def sample_rows(self):
        return [
            {
                "serial": "1",
                "case_number": "W.P. No. 12345/2024",
                "case_title": "Muhammad Ali Vs Province of Punjab",
                "judge_name": "Justice Ahmed Khan",
                "lhc_citation": "2024 LHC 4177",
                "other_citation": "2024 CLC 500",
                "category": "Constitutional",
                "decision_date": "23-12-2024",
                "pdf_url": "https://sys.lhc.gov.pk/appjudgments/2024LHC4177.pdf",
            },
            {
                "serial": "2",
                "case_number": "Cr.A No. 200/2023",
                "case_title": "State Vs Aslam Khan",
                "judge_name": "Justice Farooq Haider",
                "lhc_citation": "2023 LHC 630",
                "other_citation": "2023 PCrLJ 100",
                "category": "Criminal",
                "decision_date": "15/06/2023",
                "pdf_url": "/appjudgments/2023LHC630.pdf",
            },
        ]

    def test_parses_records(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source")
        assert len(records) == 2
        assert all(isinstance(r, JudgmentRecord) for r in records)

    def test_pdf_urls_normalized(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source")
        assert records[0].pdf_url == "https://sys.lhc.gov.pk/appjudgments/2024LHC4177.pdf"
        assert records[1].pdf_url == "https://sys.lhc.gov.pk/appjudgments/2023LHC630.pdf"

    def test_case_number_parsed(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source")
        assert records[0].case_number == "W.P. No. 12345/2024"
        assert records[1].case_number == "Cr.A No. 200/2023"

    def test_judge_name(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source")
        assert records[0].judge_name == "Justice Ahmed Khan"

    def test_date_parsed_slash_format(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source")
        assert records[1].decision_date_parsed == date(2023, 6, 15)

    def test_criminal_category(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source")
        assert records[1].category == "Criminal"

    def test_empty_list(self):
        records = parse_css_rows([], "test")
        assert records == []

    def test_missing_fields(self):
        rows = [{"serial": "1", "case_number": "W.P. No. 100/2024"}]
        records = parse_css_rows(rows, "test")
        assert len(records) == 1
        assert records[0].pdf_url == ""
        assert records[0].category == ""
        assert records[0].judge_name == ""

    def test_lhc_citation(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source")
        assert records[0].lhc_citation == "2024 LHC 4177"

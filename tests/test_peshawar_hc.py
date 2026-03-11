"""Tests for the Peshawar HC crawler pipeline.

Tests parsing logic with real sample data from PHC website recon.
Does NOT hit the live website — all tests use offline sample data.
"""

from datetime import date

import pytest

from src.pipelines.peshawar_hc.listing import (
    JudgmentRecord,
    _parse_case_field,
    _parse_date,
    parse_css_rows,
    parse_table_data,
)


class TestParseCaseField:
    def test_standard_case_number(self):
        raw = "W.P No. 1395-M of 2019 Sayyed Mukammal Shah  Vs  Mst. Nasira and others"
        number, title = _parse_case_field(raw)
        assert number == "W.P No. 1395-M of 2019"
        assert title == "Sayyed Mukammal Shah  Vs  Mst. Nasira and others"

    def test_criminal_appeal(self):
        raw = "Cr.A No. 650-P of 2025 Jamil Khan  Vs  The State etc"
        number, title = _parse_case_field(raw)
        assert number == "Cr.A No. 650-P of 2025"
        assert "Jamil Khan" in title

    def test_fao_case(self):
        raw = "F.A.O No. 10-P of 2013 Abdul Qahar  Vs  Haji Taskeen Ahmad"
        number, title = _parse_case_field(raw)
        assert number == "F.A.O No. 10-P of 2013"
        assert "Abdul Qahar" in title

    def test_no_vs_separator(self):
        raw = "W.P No. 4840-P of 2023 Hashmat Ullah omed & others"
        number, title = _parse_case_field(raw)
        assert number == "W.P No. 4840-P of 2023"

    def test_empty_input(self):
        number, title = _parse_case_field("")
        assert number == ""
        assert title == ""

    def test_no_match(self):
        raw = "Some random text without case pattern"
        number, title = _parse_case_field(raw)
        assert number == raw
        assert title == ""


class TestParseDate:
    def test_standard_date(self):
        assert _parse_date("23-12-2024") == date(2024, 12, 23)

    def test_single_digit_day(self):
        assert _parse_date("5-01-2023") == date(2023, 1, 5)

    def test_empty(self):
        assert _parse_date("") is None

    def test_invalid(self):
        assert _parse_date("not-a-date") is None

    def test_whitespace(self):
        assert _parse_date("  23-12-2024  ") == date(2024, 12, 23)


class TestParseTableData:
    """Tests for DefaultTableExtraction output parsing."""

    @pytest.fixture
    def sample_table(self):
        return {
            "headers": [
                "S.No", "Case", "Remarks", "Other Citation",
                "PHC Neutral Citation", "Decision Date", "S.C.Status",
                "Category", "Judgment", "SC Judgment",
            ],
            "rows": [
                [
                    "1",
                    "W.P No. 1395-M of 2019 Sayyed Mukammal Shah  Vs  Mst. Nasira and others",
                    "Relinquishment of dower by the wife",
                    "awaited",
                    "",
                    "23-12-2024",
                    "",
                    "Constitutional",
                    "",  # PDF link not captured by table extraction
                    "",
                ],
                [
                    "2",
                    "WP. No. 883-M of 2018 Akmal Khan etc  vs  Mst. Noorin etc",
                    "Registration of dower deed",
                    "2025 PLJ Pesh. 100",
                    "2024 PHC 50",
                    "13-12-2024",
                    "Dismissed",
                    "Civil",
                    "",
                    "",
                ],
            ],
        }

    def test_parses_records(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert len(records) == 2
        assert all(isinstance(r, JudgmentRecord) for r in records)

    def test_case_number_parsed(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].case_number == "W.P No. 1395-M of 2019"
        assert records[0].case_title == "Sayyed Mukammal Shah  Vs  Mst. Nasira and others"

    def test_date_parsed(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].decision_date_parsed == date(2024, 12, 23)
        assert records[0].decision_date == "23-12-2024"

    def test_category(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].category == "Constitutional"
        assert records[1].category == "Civil"

    def test_citation(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].other_citation == "awaited"
        assert records[1].other_citation == "2025 PLJ Pesh. 100"

    def test_neutral_citation(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[1].neutral_citation == "2024 PHC 50"

    def test_sc_status(self, sample_table):
        records = parse_table_data(sample_table, "test_source")
        assert records[0].sc_status == ""
        assert records[1].sc_status == "Dismissed"

    def test_empty_rows(self):
        table = {"headers": ["S.No", "Case"], "rows": []}
        records = parse_table_data(table, "test")
        assert records == []

    def test_source_url_set(self, sample_table):
        records = parse_table_data(sample_table, "my_source")
        assert all(r.source_url == "my_source" for r in records)


class TestParseCssRows:
    """Tests for JsonCssExtractionStrategy output parsing."""

    @pytest.fixture
    def sample_rows(self):
        return [
            {
                "serial": "1",
                "case": "W.P No. 1395-M of 2019 Sayyed Mukammal Shah  Vs  Mst. Nasira and others",
                "remarks": "Relinquishment of dower by the wife",
                "other_citation": "awaited",
                "neutral_citation": "",
                "decision_date": "23-12-2024",
                "sc_status": "",
                "category": "Constitutional",
                "pdf_url": "https://www.peshawarhighcourt.gov.pk/PHCCMS//judgments/W.P-No.-1395-M-of-2019.pdf",
                "sc_pdf_url": "",
            },
            {
                "serial": "2",
                "case": "Cr.A No. 100-P of 2024 State Vs Accused",
                "remarks": "Murder appeal",
                "other_citation": "2024 PCrLJ 500",
                "neutral_citation": "2024 PHC 123",
                "decision_date": "15-06-2024",
                "sc_status": "Dismissed",
                "category": "Criminal",
                "pdf_url": "https://www.peshawarhighcourt.gov.pk/PHCCMS//judgments/cra100.pdf",
                "sc_pdf_url": "https://www.peshawarhighcourt.gov.pk/sc-judgment.pdf",
            },
        ]

    def test_parses_records(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source")
        assert len(records) == 2
        assert all(isinstance(r, JudgmentRecord) for r in records)

    def test_pdf_urls_captured(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source")
        assert records[0].pdf_url.endswith(".pdf")
        assert "peshawarhighcourt" in records[0].pdf_url
        assert records[1].sc_pdf_url.endswith(".pdf")

    def test_case_number_parsed(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source")
        assert records[0].case_number == "W.P No. 1395-M of 2019"
        assert records[1].case_number == "Cr.A No. 100-P of 2024"

    def test_criminal_category(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source")
        assert records[1].category == "Criminal"
        assert records[1].sc_status == "Dismissed"

    def test_empty_list(self):
        records = parse_css_rows([], "test")
        assert records == []

    def test_missing_fields(self):
        rows = [{"serial": "1", "case": "Test of 2024 Foo Vs Bar"}]
        records = parse_css_rows(rows, "test")
        assert len(records) == 1
        assert records[0].pdf_url == ""
        assert records[0].category == ""

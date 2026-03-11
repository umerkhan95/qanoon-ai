"""Tests for the Federal Shariat Court crawler pipeline.

Tests parsing logic with realistic sample data based on FSC website recon.
Does NOT hit the live website — all tests use offline sample data.
"""

from datetime import date

import pytest

from src.pipelines.federal_shariat.constants import BASE_URL, COURT_CODE
from src.pipelines.federal_shariat.listing import (
    JudgmentRecord,
    _classify_case_type,
    _extract_case_number,
    _extract_date_from_title,
    _normalize_pdf_url,
    _parse_date,
    parse_leading_judgments_rows,
    parse_judgment_search_rows,
)


class TestParseDate:
    def test_dot_separated(self):
        assert _parse_date("19.03.2025") == date(2025, 3, 19)

    def test_dash_separated(self):
        assert _parse_date("23-12-2024") == date(2024, 12, 23)

    def test_slash_separated(self):
        assert _parse_date("05/01/2023") == date(2023, 1, 5)

    def test_single_digit_day(self):
        assert _parse_date("5.01.2023") == date(2023, 1, 5)

    def test_empty(self):
        assert _parse_date("") is None

    def test_invalid(self):
        assert _parse_date("not-a-date") is None

    def test_whitespace(self):
        assert _parse_date("  19.03.2025  ") == date(2025, 3, 19)

    def test_two_digit_year_old(self):
        assert _parse_date("15.06.85") == date(1985, 6, 15)

    def test_two_digit_year_new(self):
        assert _parse_date("15.06.25") == date(2025, 6, 15)


class TestExtractDateFromTitle:
    def test_dated_format(self):
        title = "Judgement on Chaddar or Parchi (Shariat Petition No. 10-I of 2023) dated 19.03.2025"
        assert _extract_date_from_title(title) == "19.03.2025"

    def test_parenthesized_date(self):
        title = "Criminal Appeal No. 15-I of 2018 (23.12.2024)"
        assert _extract_date_from_title(title) == "23.12.2024"

    def test_decision_date_label(self):
        title = "Some case Decision Date: 15-06-2024"
        assert _extract_date_from_title(title) == "15-06-2024"

    def test_standalone_date(self):
        title = "Cr.App.No.15.I.of.2018 some text 01.02.2020"
        assert _extract_date_from_title(title) == "01.02.2020"

    def test_no_date(self):
        title = "Some case without any date"
        assert _extract_date_from_title(title) == ""


class TestExtractCaseNumber:
    def test_shariat_petition(self):
        title = "Judgement on Chaddar or Parchi (Shariat Petition No. 10-I of 2023)"
        result = _extract_case_number(title)
        assert "Shariat Petition" in result
        assert "10-I" in result
        assert "2023" in result

    def test_criminal_appeal_full(self):
        title = "Criminal Appeal No. 23 - Q - of 2005 regarding murder"
        result = _extract_case_number(title)
        assert "Criminal Appeal" in result
        assert "2005" in result

    def test_abbreviated_cr_app(self):
        title = "Cr.App.No.15.I.of.2018 State vs Accused"
        result = _extract_case_number(title)
        assert "Cr.App" in result
        assert "2018" in result

    def test_criminal_revision(self):
        title = "Criminal Revision No. 01-K of 2021 Sadam Hussain"
        result = _extract_case_number(title)
        assert "Criminal Revision" in result
        assert "2021" in result

    def test_jail_criminal_appeal(self):
        title = "Jail Criminal Appeal No. 34-K of 1998"
        result = _extract_case_number(title)
        assert "Jail Criminal Appeal" in result
        assert "1998" in result

    def test_no_match_returns_title(self):
        title = "Some random text"
        assert _extract_case_number(title) == "Some random text"


class TestClassifyCaseType:
    def test_shariat_petition(self):
        assert _classify_case_type("Shariat Petition No. 10-I of 2023") == "Shariat Petition"

    def test_shariat_petition_abbrev(self):
        assert _classify_case_type("Sh.P.No.17 I of 1984") == "Shariat Petition"

    def test_review_shariat_petition(self):
        assert _classify_case_type("Review Shariat Petition No. 5-I of 2020") == "Review Shariat Petition"

    def test_criminal_appeal(self):
        assert _classify_case_type("Criminal Appeal No. 23-Q of 2005") == "Criminal Appeal"

    def test_criminal_appeal_abbrev(self):
        assert _classify_case_type("Cr.App.No.15.I.of.2018") == "Criminal Appeal"

    def test_jail_criminal_appeal(self):
        assert _classify_case_type("Jail Criminal Appeal No. 34-K of 1998") == "Jail Criminal Appeal"

    def test_criminal_revision(self):
        assert _classify_case_type("Criminal Revision No. 01-K of 2021") == "Criminal Revision"

    def test_writ_petition(self):
        assert _classify_case_type("W.P No. 100-I of 2022") == "Writ Petition"

    def test_other(self):
        assert _classify_case_type("Something else") == "Other"


class TestNormalizePdfUrl:
    def test_absolute_url(self):
        url = "https://www.federalshariatcourt.gov.pk/Judgments/test.pdf"
        assert _normalize_pdf_url(url) == url

    def test_relative_with_slash(self):
        url = "/Judgments/test.pdf"
        assert _normalize_pdf_url(url) == f"{BASE_URL}/Judgments/test.pdf"

    def test_relative_without_slash(self):
        url = "Judgments/test.pdf"
        assert _normalize_pdf_url(url) == f"{BASE_URL}/Judgments/test.pdf"

    def test_empty(self):
        assert _normalize_pdf_url("") == ""

    def test_whitespace(self):
        assert _normalize_pdf_url("  ") == ""


class TestParseLeadingJudgmentsRows:
    @pytest.fixture
    def sample_rows(self):
        return [
            {
                "serial": "1",
                "title": "Judgement on Chaddar or Parchi (Shariat Petition No. 10-I of 2023) dated 19.03.2025",
                "pdf_url": "/Judgments/Shariat-Petition-No-10-I-of-2023.pdf",
            },
            {
                "serial": "2",
                "title": "Criminal Appeal No. 15-I of 2018 State vs Muhammad Akram dated 25.12.2024",
                "pdf_url": "https://www.federalshariatcourt.gov.pk/Judgments/Cr.App.No.15.I.of.2018.pdf",
            },
            {
                "serial": "3",
                "title": "Jail Criminal Appeal No. 34-K of 1998 regarding Hudood Ordinance (01.06.2000)",
                "pdf_url": "/Judgments/Jail%20Criminal%20Appeal%20No.%2034%20-%20K%20-%20of%201998.pdf",
            },
        ]

    def test_parses_all_records(self, sample_rows):
        records = parse_leading_judgments_rows(sample_rows, "test_source")
        assert len(records) == 3
        assert all(isinstance(r, JudgmentRecord) for r in records)

    def test_case_number_extracted(self, sample_rows):
        records = parse_leading_judgments_rows(sample_rows, "test_source")
        assert "Shariat Petition" in records[0].case_number
        assert "10-I" in records[0].case_number
        assert "2023" in records[0].case_number

    def test_case_type_classified(self, sample_rows):
        records = parse_leading_judgments_rows(sample_rows, "test_source")
        assert records[0].case_type == "Shariat Petition"
        assert records[1].case_type == "Criminal Appeal"
        assert records[2].case_type == "Jail Criminal Appeal"

    def test_date_parsed(self, sample_rows):
        records = parse_leading_judgments_rows(sample_rows, "test_source")
        assert records[0].decision_date == "19.03.2025"
        assert records[0].decision_date_parsed == date(2025, 3, 19)

    def test_pdf_url_normalized(self, sample_rows):
        records = parse_leading_judgments_rows(sample_rows, "test_source")
        assert records[0].pdf_url.startswith("https://")
        assert records[0].pdf_url.endswith(".pdf")
        # Absolute URL should be kept as-is
        assert records[1].pdf_url == (
            "https://www.federalshariatcourt.gov.pk/Judgments/Cr.App.No.15.I.of.2018.pdf"
        )

    def test_source_url_set(self, sample_rows):
        records = parse_leading_judgments_rows(sample_rows, "my_source")
        assert all(r.source_url == "my_source" for r in records)

    def test_empty_input(self):
        records = parse_leading_judgments_rows([], "test")
        assert records == []

    def test_skips_empty_title(self):
        rows = [{"serial": "1", "title": "", "pdf_url": "/test.pdf"}]
        records = parse_leading_judgments_rows(rows, "test")
        assert records == []

    def test_parenthesized_date(self, sample_rows):
        records = parse_leading_judgments_rows(sample_rows, "test")
        # Record 3 has date in parentheses
        assert records[2].decision_date == "01.06.2000"
        assert records[2].decision_date_parsed == date(2000, 6, 1)


class TestParseJudgmentSearchRows:
    @pytest.fixture
    def sample_rows(self):
        return [
            {
                "serial": "1",
                "case_number": "Shariat Petition No. 28-I of 1990",
                "title": "Court Fees Act 1870",
                "decision_date": "15.06.1992",
                "pdf_url": "/Judgments/S.P.NO.28I.1990.pdf",
            },
            {
                "serial": "2",
                "case_number": "",
                "title": "Criminal Revision No. 01-K of 2021 Sadam Hussain",
                "decision_date": "10.03.2023",
                "pdf_url": "/Judgments/Cr. Revision No.01-K of 2021.pdf",
            },
        ]

    def test_parses_records(self, sample_rows):
        records = parse_judgment_search_rows(sample_rows, "test")
        assert len(records) == 2

    def test_case_number_from_field(self, sample_rows):
        records = parse_judgment_search_rows(sample_rows, "test")
        assert records[0].case_number == "Shariat Petition No. 28-I of 1990"

    def test_case_number_extracted_from_title(self, sample_rows):
        records = parse_judgment_search_rows(sample_rows, "test")
        # When case_number field is empty, extracted from title
        assert "Criminal Revision" in records[1].case_number
        assert "2021" in records[1].case_number

    def test_pdf_url_normalized(self, sample_rows):
        records = parse_judgment_search_rows(sample_rows, "test")
        assert records[0].pdf_url.startswith("https://")

    def test_date_parsed(self, sample_rows):
        records = parse_judgment_search_rows(sample_rows, "test")
        assert records[0].decision_date_parsed == date(1992, 6, 15)

    def test_empty_list(self):
        records = parse_judgment_search_rows([], "test")
        assert records == []

    def test_skips_empty_row(self):
        rows = [{"serial": "1", "case_number": "", "title": ""}]
        records = parse_judgment_search_rows(rows, "test")
        assert records == []

    def test_missing_fields(self):
        rows = [{"serial": "1", "title": "Shariat Petition No. 5-I of 2020 some case"}]
        records = parse_judgment_search_rows(rows, "test")
        assert len(records) == 1
        assert records[0].pdf_url == ""
        assert records[0].decision_date == ""


class TestCourtCode:
    def test_court_code(self):
        assert COURT_CODE == "FSC"

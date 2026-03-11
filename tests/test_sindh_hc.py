"""Tests for the Sindh HC crawler pipeline.

Tests parsing logic with real sample data from SHC caselaw website recon.
Does NOT hit the live website — all tests use offline sample data.
"""

from datetime import date

import pytest

from src.pipelines.sindh_hc.listing import (
    JudgmentRecord,
    _parse_case_number,
    _parse_date,
    _resolve_pdf_url,
    parse_css_rows,
    parse_judge_rows,
)


class TestParseDate:
    def test_standard_date_short_year(self):
        assert _parse_date("15-MAY-23") == date(2023, 5, 15)

    def test_standard_date_full_year(self):
        assert _parse_date("22-AUG-2019") == date(2019, 8, 22)

    def test_january(self):
        assert _parse_date("26-JAN-24") == date(2024, 1, 26)

    def test_december(self):
        assert _parse_date("31-DEC-22") == date(2022, 12, 31)

    def test_empty(self):
        assert _parse_date("") is None

    def test_whitespace(self):
        assert _parse_date("  15-MAY-23  ") == date(2023, 5, 15)

    def test_invalid(self):
        assert _parse_date("not-a-date") is None

    def test_partial(self):
        assert _parse_date("15-MAY") is None


class TestParseCaseNumber:
    def test_standard(self):
        assert _parse_case_number("Criminal Appeal 91/2023 (S.B.)") == "Criminal Appeal 91/2023 (S.B.)"

    def test_extra_whitespace(self):
        assert _parse_case_number("  Const.  P.  1608/2015  ") == "Const. P. 1608/2015"

    def test_empty(self):
        assert _parse_case_number("") == ""


class TestResolvePdfUrl:
    def test_relative_url(self):
        url = _resolve_pdf_url("download-file.php?doc=MTk0ODc3&citation=2023+SHC+KHI+1139")
        assert url == "https://caselaw.shc.gov.pk/caselaw/download-file.php?doc=MTk0ODc3&citation=2023+SHC+KHI+1139"

    def test_absolute_url(self):
        url = _resolve_pdf_url("https://example.com/file.pdf")
        assert url == "https://example.com/file.pdf"

    def test_empty(self):
        assert _resolve_pdf_url("") == ""

    def test_whitespace(self):
        url = _resolve_pdf_url("  download-file.php?doc=abc  ")
        assert "download-file.php" in url


class TestParseCssRows:
    """Tests for JsonCssExtractionStrategy output parsing."""

    @pytest.fixture
    def sample_rows(self):
        return [
            {
                "serial": "1",
                "citation": "2023 SHC KHI 1139",
                "case_number": "Criminal Appeal 91/2023 (S.B.)",
                "pdf_url": "download-file.php?doc=MTk0ODc3Y2Ztcy1kYzgz&citation=2023+SHC+KHI+1139",
                "case_type": "Original Side",
                "case_year": "2023",
                "parties": "Umair Qadeer v. Muhammad Nasir & Another",
                "order_date": "15-MAY-23",
                "afr": "Yes",
                "head_notes": "Challenge to show cause notice",
                "bench": "Hon'ble Mr. Justice Amjad Ali Bohio(Author)",
                "apex_court": "",
                "apex_status": "",
            },
            {
                "serial": "2",
                "citation": "2023 SBLR Sindh 1613",
                "case_number": "Criminal Appeal 582/2022 (S.B.)",
                "pdf_url": "download-file.php?doc=abc123&citation=2023+SBLR+Sindh+1613",
                "case_type": "Original Side",
                "case_year": "2022",
                "parties": "Zainab Bibi v. Syed Kamal Shah & Another",
                "order_date": "18-MAY-23",
                "afr": "No",
                "head_notes": "Family matter",
                "bench": "Hon'ble Mr. Justice Amjad Ali Bohio(Author)",
                "apex_court": "Supreme Court",
                "apex_status": "Dismissed",
            },
            {
                "serial": "3",
                "citation": "Nil",
                "case_number": "R.A (Civil Revision) 12/2023 (S.B.)",
                "pdf_url": "",
                "case_type": "Civil Appellate Jurisdictions",
                "case_year": "2023",
                "parties": "Basit Ahmed v. Shakeel & Others",
                "order_date": "26-JAN-24",
                "afr": "No",
                "head_notes": "",
                "bench": "Hon'ble Mr. Justice Amjad Ali Bohio(Author)",
                "apex_court": "",
                "apex_status": "",
            },
        ]

    def test_parses_records(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert len(records) == 3
        assert all(isinstance(r, JudgmentRecord) for r in records)

    def test_case_number_parsed(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert records[0].case_number == "Criminal Appeal 91/2023 (S.B.)"
        assert records[2].case_number == "R.A (Civil Revision) 12/2023 (S.B.)"

    def test_citation_captured(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert records[0].citation == "2023 SHC KHI 1139"
        assert records[1].citation == "2023 SBLR Sindh 1613"
        assert records[2].citation == "Nil"

    def test_date_parsed(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert records[0].order_date_parsed == date(2023, 5, 15)
        assert records[0].order_date == "15-MAY-23"

    def test_pdf_url_resolved(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert records[0].pdf_url.startswith("https://caselaw.shc.gov.pk")
        assert "download-file.php" in records[0].pdf_url

    def test_empty_pdf_url(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert records[2].pdf_url == ""

    def test_case_type(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert records[0].case_type == "Original Side"
        assert records[2].case_type == "Civil Appellate Jurisdictions"

    def test_parties(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert "Umair Qadeer" in records[0].parties
        assert "Muhammad Nasir" in records[0].parties

    def test_afr_field(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert records[0].afr == "Yes"
        assert records[1].afr == "No"

    def test_apex_court(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert records[1].apex_court == "Supreme Court"
        assert records[1].apex_status == "Dismissed"
        assert records[0].apex_court == ""

    def test_judge_metadata(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert all(r.judge_id == 1261 for r in records)
        assert all(r.judge_name == "Amjad Ali Bohio" for r in records)

    def test_source_url(self, sample_rows):
        records = parse_css_rows(sample_rows, "test_source", 1261, "Amjad Ali Bohio")
        assert all(r.source_url == "test_source" for r in records)

    def test_empty_list(self):
        records = parse_css_rows([], "test", 1261, "Test Judge")
        assert records == []

    def test_missing_fields(self):
        rows = [{"serial": "1", "case_number": "Test 123/2024"}]
        records = parse_css_rows(rows, "test", 1261, "Test Judge")
        assert len(records) == 1
        assert records[0].pdf_url == ""
        assert records[0].citation == ""
        assert records[0].case_type == ""


class TestParseJudgeRows:
    """Tests for judges report table parsing."""

    @pytest.fixture
    def sample_judge_rows(self):
        return [
            {
                "serial": "1",
                "judge_name": "Hon'ble Mr. Justice Zafar Ahmed Rajput",
                "total_url": "public/reported-judgements-detail-all/844/-1",
                "total": "3,672",
                "afr_url": "public/reported-judgements-detail-all/844/AFR/AFR",
                "afr": "119",
            },
            {
                "serial": "2",
                "judge_name": "Hon'ble Mr. Justice Muhammad Iqbal Kalhoro",
                "total_url": "public/reported-judgements-detail-all/883/-1",
                "total": "5,929",
                "afr_url": "public/reported-judgements-detail-all/883/AFR/AFR",
                "afr": "658",
            },
            {
                "serial": "3",
                "judge_name": "Hon'ble Mr. Justice Adnan-ul-Karim Memon",
                "total_url": "public/reported-judgements-detail-all/1061/-1",
                "total": "8,107",
                "afr_url": "public/reported-judgements-detail-all/1061/AFR/AFR",
                "afr": "3,854",
            },
        ]

    def test_parses_judges(self, sample_judge_rows):
        judges = parse_judge_rows(sample_judge_rows)
        assert len(judges) == 3

    def test_judge_id_extracted(self, sample_judge_rows):
        judges = parse_judge_rows(sample_judge_rows)
        assert judges[0]["judge_id"] == 844
        assert judges[1]["judge_id"] == 883
        assert judges[2]["judge_id"] == 1061

    def test_judge_name(self, sample_judge_rows):
        judges = parse_judge_rows(sample_judge_rows)
        assert "Zafar Ahmed Rajput" in judges[0]["judge_name"]

    def test_total_count(self, sample_judge_rows):
        judges = parse_judge_rows(sample_judge_rows)
        assert judges[0]["total"] == 3672
        assert judges[2]["total"] == 8107

    def test_afr_count(self, sample_judge_rows):
        judges = parse_judge_rows(sample_judge_rows)
        assert judges[0]["afr"] == 119
        assert judges[2]["afr"] == 3854

    def test_empty_list(self):
        judges = parse_judge_rows([])
        assert judges == []

    def test_invalid_url_skipped(self):
        rows = [
            {
                "serial": "1",
                "judge_name": "Test Judge",
                "total_url": "invalid-url",
                "total": "100",
                "afr_url": "",
                "afr": "50",
            },
        ]
        judges = parse_judge_rows(rows)
        assert judges == []

    def test_missing_total_url(self):
        rows = [
            {
                "serial": "1",
                "judge_name": "Test Judge",
                "total_url": "",
                "total": "100",
                "afr_url": "",
                "afr": "50",
            },
        ]
        judges = parse_judge_rows(rows)
        assert judges == []


class TestJudgmentRecordModel:
    """Tests for Pydantic model validation."""

    def test_minimal_valid_record(self):
        record = JudgmentRecord(
            serial=1,
            citation="Nil",
            case_number="C.P. 100/2024",
            case_type="Constitutional",
            case_year="2024",
            parties="A v. B",
            order_date="15-MAY-24",
            afr="Yes",
            head_notes="",
            bench="Justice X",
            apex_court="",
            apex_status="",
            pdf_url="",
            judge_id=1061,
            judge_name="Test Judge",
            source_url="https://example.com",
        )
        assert record.case_number == "C.P. 100/2024"
        assert record.order_date_parsed is None  # Not auto-parsed by model

    def test_model_dump(self):
        record = JudgmentRecord(
            serial=1,
            citation="2024 SHC KHI 500",
            case_number="C.P. 100/2024",
            case_type="Constitutional",
            case_year="2024",
            parties="A v. B",
            order_date="15-MAY-24",
            order_date_parsed=date(2024, 5, 15),
            afr="Yes",
            head_notes="Test note",
            bench="Justice X",
            apex_court="",
            apex_status="",
            pdf_url="https://example.com/file.pdf",
            judge_id=1061,
            judge_name="Test Judge",
            source_url="https://example.com",
        )
        dumped = record.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["citation"] == "2024 SHC KHI 500"
        assert dumped["order_date_parsed"] == date(2024, 5, 15)

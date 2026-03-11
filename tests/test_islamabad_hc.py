"""Tests for the Islamabad HC crawler pipeline.

Tests parsing logic with real sample data from IHC website recon.
Does NOT hit the live website — all tests use offline sample data.
"""

from datetime import date

import pytest

from src.pipelines.islamabad_hc.listing import (
    JudgmentRecord,
    _build_pdf_url,
    _clean_text,
    _parse_date,
    parse_api_records,
)


class TestParseDate:
    def test_standard_date(self):
        assert _parse_date("28-JAN-2026") == date(2026, 1, 28)

    def test_december(self):
        assert _parse_date("12-DEC-2025") == date(2025, 12, 12)

    def test_june(self):
        assert _parse_date("03-JUN-2024") == date(2024, 6, 3)

    def test_september(self):
        assert _parse_date("29-SEP-2021") == date(2021, 9, 29)

    def test_empty(self):
        assert _parse_date("") is None

    def test_whitespace(self):
        assert _parse_date("  28-JAN-2026  ") == date(2026, 1, 28)

    def test_invalid(self):
        assert _parse_date("not-a-date") is None

    def test_invalid_month(self):
        assert _parse_date("28-XYZ-2026") is None

    def test_lowercase_month(self):
        assert _parse_date("28-jan-2026") == date(2026, 1, 28)


class TestBuildPdfUrl:
    def test_standard_path(self):
        path = "/attachments/judgements/78510/1/simple_file.pdf"
        url = _build_pdf_url(path)
        assert url == "https://mis.ihc.gov.pk/attachments/judgements/78510/1/simple_file.pdf"

    def test_path_with_special_chars(self):
        path = "/attachments/judgements/78510/1/S.T.R_No.16_(Approved_for_reporting]_639016783893229981.pdf"
        url = _build_pdf_url(path)
        assert "mis.ihc.gov.pk" in url
        assert "/attachments/judgements/78510/1/" in url
        # Filename should be URL-encoded
        assert "%28" in url  # ( encoded
        assert "%5D" in url  # ] encoded

    def test_empty_path(self):
        assert _build_pdf_url("") == ""

    def test_dash_path(self):
        assert _build_pdf_url("-") == ""

    def test_none_path(self):
        assert _build_pdf_url(None) == ""


class TestCleanText:
    def test_normal_text(self):
        assert _clean_text("Some text") == "Some text"

    def test_dash(self):
        assert _clean_text("-") == ""

    def test_none(self):
        assert _clean_text(None) == ""

    def test_carriage_returns(self):
        assert _clean_text("line1\r\nline2\r\n") == "line1 line2"

    def test_whitespace(self):
        assert _clean_text("  text  ") == "text"


class TestParseApiRecords:
    """Tests for API response parsing."""

    @pytest.fixture
    def sample_records(self):
        """Real sample data from IHC API recon."""
        return [
            {
                "O_ID": 251037,
                "TITLE": "Suleman Khan- VS -The State etc. ",
                "DDATE": "28-JAN-2026",
                "ATTACHMENTS": "/attachments/judgements/205538/1/Criminal_Revision_No.175_of_2025.__Important_639069324883381430.pdf",
                "ISLANDMARK": 0,
                "O_AFR": 0,
                "O_CITATION": "-",
                "PARTIES": "Suleman Khan VS The State etc. ",
                "CASENO": "Criminal Revision-175-2025",
                "CSNO": 175,
                "BENCHNAME": "Honourable Mr. Justice Inaam Ameen Minhas",
                "CREATEDDATE": "/Date(1771317691000)/",
                "AUTHOR_JUDGES": "Honourable Mr. Justice Inaam Ameen Minhas",
                "O_IHC_HEADNOTE": "-",
                "O_UNDERSECTION": "under section 302, PPC |under ATA 1997",
                "O_REMARKS": "Accused of FIR impugns order\r\n",
                "O_SUBJECT": "Against Interim Order, ",
                "APPL_IN": "** JGMNT",
                "CASECODE": 205538,
                "PRNTCASECODE": 205538,
                "USERNAME": "Ahsan.Ullah",
                "VAFR": 0,
                "VISSWS": 0,
                "RPTTYPE": "1",
                "O_SC_STATUS": None,
            },
            {
                "O_ID": 175530,
                "TITLE": "Muhammad Ayyaz Bin Tariq - VS -The State etc. ",
                "DDATE": "03-JUN-2024",
                "ATTACHMENTS": "/attachments/judgements/164907/1/Muhammad_Ayyaz_Bin_Tariq_PECA_638536155567897347.pdf",
                "ISLANDMARK": 0,
                "O_AFR": 1,
                "O_CITATION": "2024 PCrLJ 500",
                "PARTIES": "Muhammad Ayyaz Bin Tariq  VS The State etc. ",
                "CASENO": "Criminal Miscellaneous-1184-2023",
                "CSNO": 1184,
                "BENCHNAME": "Former Honourable Chief Justice Mr. Justice Aamer Farooq, Honourable Mr. Justice Arbab Muhammad Tahir",
                "CREATEDDATE": "/Date(1718000897000)/",
                "AUTHOR_JUDGES": "Honourable Mr. Justice Arbab Muhammad Tahir",
                "O_IHC_HEADNOTE": "Test headnote text",
                "O_UNDERSECTION": "PECA 2016",
                "O_REMARKS": "Post Arrest Bail in FIR\r\n",
                "O_SUBJECT": "Bail, After Arrest",
                "APPL_IN": "** JGMNT",
                "CASECODE": 164907,
                "PRNTCASECODE": 164907,
                "USERNAME": "luqman.khan",
                "VAFR": 0,
                "VISSWS": 0,
                "RPTTYPE": "1",
                "O_SC_STATUS": "Leave Refused",
                "O_SC_CITATION": "2024 SCMR 100",
                "O_SC_ATTACHMENTS": "/attachments/sc/sc_judgment.pdf",
            },
        ]

    @pytest.fixture
    def reported_record_with_citation(self):
        """A reported judgment with full citation details."""
        return {
            "O_ID": 243657,
            "TITLE": "Commissioner of Inland Revenue VS M/s Air Blue Limited",
            "DDATE": "12-DEC-2025",
            "ATTACHMENTS": "/attachments/judgements/78510/1/S.T.R_No.16__of_2017_(Approved_for_reporting]_639016783893229981.pdf",
            "ISLANDMARK": 0,
            "O_AFR": 1,
            "O_CITATION": "Citation Awaited",
            "O_CITATION_IMP": "-",
            "PARTIES": "Commissioner of Inland Revenue VS M/s Air Blue Limited, Islamabad and others.",
            "CASENO": "Sales Tax Reference-16-2017",
            "CSNO": 16,
            "BENCHNAME": "Honourable Mr. Justice Babar Sattar, Honourable Mr. Justice Sardar Ejaz Ishaq Khan",
            "CREATEDDATE": "/Date(1765879854000)/",
            "AUTHOR_JUDGES": "Honourable Mr. Justice Babar Sattar",
            "JUDGENAME": "Honourable Mr. Justice Babar Sattar",
            "O_IHC_HEADNOTE": "-",
            "O_UNDERSECTION": "under section 14(1) of the Federal Excise Act, 2005",
            "O_REMARKS": "Tax dispute regarding input adjustment",
            "O_SUBJECT": "Tax Reference",
            "APPL_IN": "** JGMNT",
            "CASECODE": 78510,
            "PRNTCASECODE": 78510,
            "USERNAME": "test",
            "VAFR": 0,
            "O_SC_STATUS": None,
            "O_SC_ATTACHMENTS": "-",
            "O_SC_CITATION": "-",
        }

    def test_parses_records(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert len(records) == 2
        assert all(isinstance(r, JudgmentRecord) for r in records)

    def test_case_number(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert records[0].case_number == "Criminal Revision-175-2025"
        assert records[1].case_number == "Criminal Miscellaneous-1184-2023"

    def test_case_title(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert "Suleman Khan" in records[0].case_title

    def test_parties(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert "Suleman Khan VS The State" in records[0].parties

    def test_date_parsed(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert records[0].decision_date_parsed == date(2026, 1, 28)
        assert records[0].decision_date == "28-JAN-2026"
        assert records[1].decision_date_parsed == date(2024, 6, 3)

    def test_pdf_url(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert "mis.ihc.gov.pk" in records[0].pdf_url
        assert records[0].pdf_url.endswith(".pdf")

    def test_bench_and_judge(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert "Inaam Ameen Minhas" in records[0].bench
        assert "Inaam Ameen Minhas" in records[0].author_judge

    def test_citation(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert records[0].citation == ""  # "-" gets cleaned to empty
        assert records[1].citation == "2024 PCrLJ 500"

    def test_subject(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert "Against Interim Order" in records[0].subject

    def test_remarks_cleaned(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        # \r\n should be replaced with space
        assert "\r\n" not in records[0].remarks
        assert "Accused of FIR impugns order" in records[0].remarks

    def test_under_section(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert "302, PPC" in records[0].under_section

    def test_headnote(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert records[0].headnote == ""  # "-" cleaned
        assert records[1].headnote == "Test headnote text"

    def test_afr_flag(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert records[0].is_approved_for_reporting is False
        assert records[1].is_approved_for_reporting is True

    def test_sc_status(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert records[0].sc_status == ""  # None cleaned
        assert records[1].sc_status == "Leave Refused"

    def test_sc_citation(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert records[1].sc_citation == "2024 SCMR 100"

    def test_sc_pdf_url(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert records[0].sc_pdf_url == ""
        assert "sc_judgment.pdf" in records[1].sc_pdf_url

    def test_judgment_type(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert all(r.judgment_type == "important" for r in records)

        records_r = parse_api_records(sample_records, "reported", "test_source")
        assert all(r.judgment_type == "reported" for r in records_r)

    def test_source_url(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert all(r.source_url == "test_source" for r in records)

    def test_case_code(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert records[0].case_code == 205538
        assert records[1].case_code == 164907

    def test_o_id(self, sample_records):
        records = parse_api_records(sample_records, "important", "test_source")
        assert records[0].o_id == 251037
        assert records[1].o_id == 175530

    def test_empty_input(self):
        records = parse_api_records([], "reported", "test")
        assert records == []

    def test_reported_with_citation(self, reported_record_with_citation):
        records = parse_api_records(
            [reported_record_with_citation], "reported", "test_source",
        )
        assert len(records) == 1
        rec = records[0]
        assert rec.case_number == "Sales Tax Reference-16-2017"
        assert rec.is_approved_for_reporting is True
        assert rec.citation == "Citation Awaited"
        assert rec.sc_pdf_url == ""  # "-" cleaned
        assert "mis.ihc.gov.pk" in rec.pdf_url
        # URL should have encoded special chars
        assert "%28" in rec.pdf_url or "Approved" in rec.pdf_url

    def test_missing_optional_fields(self):
        """Records with minimal fields should still parse."""
        minimal = {
            "O_ID": 1,
            "CASENO": "Test-1-2024",
            "TITLE": "Test",
            "PARTIES": "A VS B",
            "DDATE": "01-JAN-2024",
            "ATTACHMENTS": "/test.pdf",
            "CASECODE": 100,
        }
        records = parse_api_records([minimal], "reported", "test")
        assert len(records) == 1
        assert records[0].case_number == "Test-1-2024"
        assert records[0].bench == ""
        assert records[0].citation == ""

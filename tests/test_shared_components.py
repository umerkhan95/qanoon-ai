"""Tests for shared extraction components (ticket #34)."""

import time

import pytest

# ── Court Classifier ──────────────────────────────────────────────────────

from src.extractors.common.court_classifier import (
    CourtCode,
    CourtLevel,
    Province,
    classify_court_code,
    classify_court_level,
    classify_province,
    extract_court_name,
)


class TestCourtClassifier:
    def test_extract_court_name_supreme(self):
        text = "IN THE SUPREME COURT OF PAKISTAN\nCriminal Appeal No. 310 of 2006"
        name = extract_court_name(text)
        assert name is not None
        assert "supreme court" in name.lower()

    def test_extract_court_name_peshawar(self):
        text = "IN THE PESHAWAR HIGH COURT\nWrit Petition No. 123 of 2020"
        name = extract_court_name(text)
        assert name is not None
        assert "peshawar" in name.lower()

    def test_extract_court_name_none(self):
        assert extract_court_name("Some random text with no court info") is None

    def test_classify_court_code_from_name(self):
        assert classify_court_code("Supreme Court of Pakistan") == CourtCode.SC
        assert classify_court_code("Lahore High Court") == CourtCode.LHC
        assert classify_court_code("Peshawar High Court") == CourtCode.PHC
        assert classify_court_code("Sindh High Court") == CourtCode.SHC
        assert classify_court_code("Islamabad High Court") == CourtCode.IHC
        assert classify_court_code("Balochistan High Court") == CourtCode.BHC
        assert classify_court_code("Federal Shariat Court") == CourtCode.FSC

    def test_classify_court_code_from_text(self):
        assert classify_court_code(text="judgment of the Supreme Court") == CourtCode.SC

    def test_classify_court_code_unknown(self):
        assert classify_court_code("Random text") == CourtCode.UNKNOWN

    def test_classify_court_level_supreme(self):
        assert classify_court_level("Supreme Court") == CourtLevel.SUPREME_COURT

    def test_classify_court_level_high(self):
        assert classify_court_level("Lahore High Court") == CourtLevel.HIGH_COURT
        assert classify_court_level("Peshawar High Court") == CourtLevel.HIGH_COURT

    def test_classify_court_level_atc(self):
        assert classify_court_level("Anti-Terrorism Court") == CourtLevel.ANTI_TERRORISM_COURT

    def test_classify_province_from_name(self):
        assert classify_province("Lahore High Court") == Province.PUNJAB
        assert classify_province("Peshawar High Court") == Province.KPK
        assert classify_province("Sindh High Court") == Province.SINDH
        assert classify_province("Balochistan High Court") == Province.BALOCHISTAN
        assert classify_province("Islamabad High Court") == Province.ISLAMABAD
        assert classify_province("Supreme Court") == Province.FEDERAL

    def test_classify_province_none(self):
        assert classify_province("Random") is None


# ── Judge Extractor ───────────────────────────────────────────────────────

from src.extractors.common.judge_extractor import extract_judge_names


class TestJudgeExtractor:
    def test_extract_justice_pattern(self):
        text = "PRESENT: Mr. Justice Iftikhar Chaudhry, Mr. Justice Anwar Zaheer Jamali"
        names = extract_judge_names(text)
        assert len(names) >= 2
        assert any("Iftikhar" in n for n in names)
        assert any("Anwar" in n for n in names)

    def test_extract_from_present_block(self):
        text = "PRESENT:\nMr. Justice Asif Saeed Khosa\nMr. Justice Gulzar Ahmed\n\nCRIMINAL APPEAL"
        names = extract_judge_names(text)
        assert len(names) >= 2

    def test_empty_text(self):
        assert extract_judge_names("") == []

    def test_no_judges(self):
        assert extract_judge_names("This text has no judge names at all.") == []

    def test_deduplication(self):
        text = (
            "PRESENT: Mr. Justice Asif Khosa\n"
            "Mr. Justice Asif Khosa delivered the judgment"
        )
        names = extract_judge_names(text)
        assert len(names) == len(set(names))

    def test_all_caps_names(self):
        text = "PRESENT: MR. JUSTICE IFTIKHAR CHAUDHRY, MR. JUSTICE ANWAR ZAHEER JAMALI"
        names = extract_judge_names(text)
        assert len(names) >= 2
        assert any("Iftikhar" in n for n in names)

    def test_none_input(self):
        assert extract_judge_names(None) == []

    def test_empty_string(self):
        assert extract_judge_names("") == []


# ── Quality Validator ─────────────────────────────────────────────────────

from src.extractors.common.quality_validator import QualityReport, validate_extraction


class TestQualityValidator:
    def test_pass_with_required_fields(self):
        text = "x" * 1000
        payload = {
            "case_number": "CRL.A.310_2006",
            "court_name": "Supreme Court of Pakistan",
            "judge_names": ["Justice X"],
            "date_judgment": "2020-01-01",
            "ppc_sections": [302],
            "precedents_cited": ["PLD 2020 SC 1"],
        }
        report = validate_extraction(text, payload, "CRL.A.310_2006")
        assert report.passed
        assert len(report.errors) == 0

    def test_fail_missing_case_number(self):
        text = "x" * 1000
        payload = {"court_name": "Supreme Court"}
        report = validate_extraction(text, payload)
        assert not report.passed
        assert any("case_number" in e for e in report.errors)

    def test_fail_short_text(self):
        report = validate_extraction("short", {"case_number": "X", "court_name": "Y"})
        assert not report.passed
        assert any("too short" in e for e in report.errors)

    def test_warn_missing_expected_fields(self):
        text = "x" * 1000
        payload = {"case_number": "X", "court_name": "Y"}
        report = validate_extraction(text, payload)
        assert report.passed  # warnings don't fail
        assert len(report.warnings) > 0

    def test_field_coverage_calculation(self):
        text = "x" * 1000
        payload = {
            "case_number": "X",
            "court_name": "Y",
            "field_a": None,
            "field_b": "",
            "field_c": [],
            "field_d": 0,  # numeric 0 counts as filled
        }
        report = validate_extraction(text, payload)
        # 3 filled (X, Y, 0) out of 6 = 50%
        assert report.field_coverage == 50.0

    def test_consistency_diyat_conviction(self):
        text = "x" * 1000
        payload = {
            "case_number": "X",
            "court_name": "Y",
            "diyat_compromise": True,
            "judgment_type": "conviction",
        }
        report = validate_extraction(text, payload)
        assert any("diyat" in w for w in report.warnings)

    def test_none_payload(self):
        report = validate_extraction("x" * 1000, None)
        assert not report.passed
        assert any("None" in e for e in report.errors)


# ── Dedup ─────────────────────────────────────────────────────────────────

from src.extractors.common.dedup import (
    find_near_duplicates,
    is_duplicate_case,
    is_duplicate_text,
    normalize_case_number,
    text_hash,
)


class TestDedup:
    def test_text_hash_deterministic(self):
        assert text_hash("hello world") == text_hash("hello world")

    def test_text_hash_normalized(self):
        # Different whitespace should produce same hash
        assert text_hash("hello  world") == text_hash("hello world")
        assert text_hash("  hello world  ") == text_hash("hello world")

    def test_text_hash_empty_raises(self):
        with pytest.raises(ValueError, match="empty text"):
            text_hash("")
        with pytest.raises(ValueError, match="empty text"):
            text_hash("   ")

    def test_text_hash_case_insensitive(self):
        assert text_hash("Hello World") == text_hash("hello world")

    def test_text_hash_differs(self):
        assert text_hash("hello") != text_hash("world")

    def test_normalize_case_number(self):
        assert normalize_case_number("Crl. A. 310/2006") == "CRLA3102006"
        assert normalize_case_number("CRL.A.310_2006") == "CRLA3102006"
        assert normalize_case_number("Criminal Appeal No. 310 of 2006") == "CRIMINALAPPEALNO310OF2006"

    def test_normalize_case_number_empty(self):
        assert normalize_case_number("") == ""

    def test_is_duplicate_text(self):
        h = text_hash("test judgment text")
        assert is_duplicate_text("test judgment text", {h})
        assert not is_duplicate_text("different text", {h})

    def test_is_duplicate_case(self):
        existing = {normalize_case_number("CRL.A.310_2006")}
        assert is_duplicate_case("Crl. A. 310/2006", existing)
        assert not is_duplicate_case("CRL.A.999_2020", existing)

    def test_find_near_duplicates(self):
        h = text_hash("test text")
        cases = {normalize_case_number("CRL.A.310_2006")}
        result = find_near_duplicates("test text", "CRL.A.310/2006", {h}, cases)
        assert result["exact_duplicate"]
        assert result["case_number_match"]


# ── Rate Limiter ──────────────────────────────────────────────────────────

from src.extractors.common.rate_limiter import RateLimiter, backoff_wait


class TestRateLimiter:
    def test_burst_allowed(self):
        limiter = RateLimiter(requests_per_second=10.0, burst=5)
        start = time.monotonic()
        for _ in range(5):
            limiter.wait()
        elapsed = time.monotonic() - start
        # 5 burst requests should be near-instant
        assert elapsed < 1.0

    def test_rate_enforced(self):
        limiter = RateLimiter(requests_per_second=5.0, burst=1)
        limiter.wait()  # consume the burst token
        start = time.monotonic()
        limiter.wait()  # should wait ~0.2s
        elapsed = time.monotonic() - start
        assert elapsed >= 0.15

    def test_request_count(self):
        limiter = RateLimiter(requests_per_second=100.0, burst=10)
        for _ in range(5):
            limiter.wait()
        assert limiter.request_count == 5

    def test_zero_rate_raises(self):
        with pytest.raises(ValueError, match="positive"):
            RateLimiter(requests_per_second=0.0)

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="positive"):
            RateLimiter(requests_per_second=-1.0)


# ── Section Splitter ──────────────────────────────────────────────────────

from src.extractors.common.section_splitter import split_judgment


class TestSectionSplitter:
    def test_always_has_full_text(self):
        result = split_judgment("Short text")
        assert "full_text" in result

    def test_empty_text(self):
        result = split_judgment("")
        assert result == {"full_text": "", "header": ""}

    def test_detects_facts_section(self):
        text = (
            "IN THE SUPREME COURT OF PAKISTAN\n" * 10 +
            "\n\nBRIEF FACTS OF THE CASE\n" +
            "The prosecution story is that on 01.01.2020...\n" * 20 +
            "\n\nFor the foregoing reasons, the appeal is dismissed.\n"
        )
        result = split_judgment(text)
        assert "facts" in result

    def test_detects_order_section(self):
        text = (
            "IN THE SUPREME COURT\n" * 10 +
            "\n\nIn the result, the appeal is accordingly allowed.\n" +
            "The conviction is set aside." * 5
        )
        result = split_judgment(text)
        assert "order" in result

    def test_detects_reasoning(self):
        text = (
            "IN THE SUPREME COURT\n" * 10 +
            "\n\nWe have heard the learned counsel for the parties.\n" +
            "After careful consideration of the evidence...\n" * 20 +
            "\n\nThe appeal is dismissed.\n"
        )
        result = split_judgment(text)
        assert "reasoning" in result

    def test_full_judgment_structure(self):
        text = (
            "IN THE SUPREME COURT OF PAKISTAN\n"
            "Criminal Appeal No. 310 of 2006\n" * 5 +
            "\n\nBrief facts of the case are as follows:\n" +
            "The prosecution story is...\n" * 10 +
            "\n\nLearned counsel for the appellant submitted that...\n" +
            "It was argued...\n" * 10 +
            "\n\nLearned counsel for the respondent/State contended that...\n" +
            "The state argued...\n" * 10 +
            "\n\nWe have heard the learned counsel and examined the record.\n" +
            "Upon analysis...\n" * 10 +
            "\n\nIn the result, the appeal is dismissed.\n" +
            "The conviction is upheld.\n"
        )
        result = split_judgment(text)
        assert "full_text" in result
        assert "header" in result
        # At minimum should detect facts and order
        detected = set(result.keys()) - {"full_text", "header"}
        assert len(detected) >= 2

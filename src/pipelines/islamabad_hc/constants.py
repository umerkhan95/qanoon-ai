"""Shared constants for the Islamabad High Court crawler pipeline."""

BASE_URL = "https://mis.ihc.gov.pk"
API_URL = f"{BASE_URL}/ihc.asmx"
SEARCH_ENDPOINT = f"{API_URL}/srchDecisionClms"
JUDGES_ENDPOINT = f"{API_URL}/Juges_GA"
KEYWORD_SEARCH_ENDPOINT = f"{API_URL}/srchDecision1"

# PDF base URL — ATTACHMENTS field contains path like /attachments/judgements/...
PDF_BASE_URL = BASE_URL

# Court code used in Qdrant point IDs
COURT_CODE = "IHC"

# Judgment types
JUDGMENT_TYPE_REPORTED = "reported"
JUDGMENT_TYPE_IMPORTANT = "important"

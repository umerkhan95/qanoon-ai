"""Shared constants for the Peshawar High Court crawler pipeline."""

BASE_URL = "https://www.peshawarhighcourt.gov.pk"
JUDGMENTS_URL = f"{BASE_URL}/PHCCMS/reportedJudgments.php"
SEARCH_URL = f"{JUDGMENTS_URL}?action=search"
PDF_BASE_URL = f"{BASE_URL}/PHCCMS//judgments/"

# Available filter values discovered via recon
YEARS = list(range(2010, 2027))

# Category name → form <option> value mapping
# The form uses numeric IDs, not text labels
CATEGORY_VALUES = {
    "Criminal": "1",
    "Civil": "2",
    "Revenu": "3",  # sic — typo on the website
    "Constitutional": "4",
    "Service": "5",
    "Corporate": "6",
}

CATEGORIES = list(CATEGORY_VALUES.keys())

# Court code used in Qdrant point IDs
COURT_CODE = "PHC"

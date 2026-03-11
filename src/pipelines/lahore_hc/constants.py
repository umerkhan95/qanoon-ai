"""Shared constants for the Lahore High Court crawler pipeline."""

BASE_URL = "https://data.lhc.gov.pk"
JUDGMENTS_URL = f"{BASE_URL}/reported_judgments/judgments_approved_for_reporting"
FORMER_JUDGES_URL = (
    f"{BASE_URL}/reported_judgments/judgments_approved_for_reporting_by_former_judges"
)
DYNAMIC_RESULTS_URL = f"{BASE_URL}/dynamic/approved_judgments_result_new.php"

# PDF judgments are served from a separate subdomain
PDF_BASE_URL = "https://sys.lhc.gov.pk/appjudgments"

# Available filter values discovered via recon
YEARS = list(range(2010, 2027))

# Court code used in Qdrant point IDs
COURT_CODE = "LHC"

"""Shared constants for the Balochistan High Court crawler pipeline."""

import os

# The main BHC website is behind Incapsula WAF.
# The portal subdomain hosts a Nuxt.js SPA with a proxied JSON API.
BASE_URL = os.environ.get("BHC_BASE_URL", "https://bhc.gov.pk")
PORTAL_URL = os.environ.get("BHC_PORTAL_URL", "https://portal.bhc.gov.pk")
JUDGMENTS_URL = f"{PORTAL_URL}/judgments"

# The Nuxt app proxies API requests to this backend.
# We use the portal URL for API calls (through the browser session)
# because the backend (api.bhc.gov.pk) requires authentication tokens
# that only the Nuxt server-side proxy provides.
API_JUDGMENTS_PATH = "/v2/judgments"
API_DOWNLOAD_PATH = "/v2/downloadpdf"
API_COURTS_PATH = "/v2/courts"
API_JUDGES_PATH = "/v2/judges"
API_CATEGORIES_PATH = "/v2/categories"

# Search mode constants (searchBy parameter)
SEARCH_BY_CASE_ID = 1
SEARCH_BY_COURT = 2
SEARCH_BY_JUDGE = 3

# Court type constants from the BHC portal
COURT_TYPE_SUPREME = 10
COURT_TYPE_HIGH_COURT = 20
COURT_TYPE_HC_BENCH = 21  # Principal Seat Quetta, Sibi Bench, etc.
COURT_TYPE_SESSIONS = 30
COURT_TYPE_TRIBUNAL = 31  # Services Tribunal, Customs Tribunal

# The highCourtBenches getter in the portal filters for types 21 and 31
HC_BENCH_TYPES = {COURT_TYPE_HC_BENCH, COURT_TYPE_TRIBUNAL}

# Court code used in Qdrant point IDs
COURT_CODE = "BHC"

# Years available in the portal (from JS: for loop 2001 to current year)
YEARS = list(range(2001, 2027))

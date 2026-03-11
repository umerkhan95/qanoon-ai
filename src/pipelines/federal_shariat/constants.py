"""Shared constants for the Federal Shariat Court crawler pipeline."""

BASE_URL = "https://www.federalshariatcourt.gov.pk"

# New WordPress-style site structure (post-redesign)
HOME_URL = f"{BASE_URL}/en/home/"
JUDGMENTS_URL = f"{BASE_URL}/en/judgments/"
LEADING_JUDGMENTS_URL = f"{BASE_URL}/en/leading-judgements/"

# Legacy PDF base path (PDFs still served from old path)
PDF_BASE_URL = f"{BASE_URL}/Judgments/"

# FSC case type prefixes discovered via recon
# Criminal Appeals, Shariat Petitions, Criminal Revisions, Jail Criminal Appeals
CASE_TYPE_PREFIXES = [
    "Cr.App",       # Criminal Appeal
    "Cr.A",         # Criminal Appeal (alternate)
    "J.Cr.A",       # Jail Criminal Appeal
    "Cr.Rev",       # Criminal Revision
    "Cr.M",         # Criminal Miscellaneous
    "Sh.P",         # Shariat Petition
    "S.P",          # Shariat Petition (alternate)
    "R.Sr.P",       # Review Shariat Petition
    "W.P",          # Writ Petition
]

# Branch codes used in case numbers (court circuit identifiers)
BRANCH_CODES = [
    "I",    # Islamabad
    "L",    # Lahore
    "K",    # Karachi
    "Q",    # Quetta
    "P",    # Peshawar
    "D",    # D.I. Khan
    "M",    # Mardan / Mingora
]

# Court code used in Qdrant point IDs
COURT_CODE = "FSC"

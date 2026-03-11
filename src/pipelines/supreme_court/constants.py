"""Shared constants for the Supreme Court of Pakistan crawler pipeline.

Site structure (from Wayback Machine recon, Aug 2024):
- WordPress-based site behind Akamai CDN
- Judgments listed at /category/judgements/ as blog posts
- Individual judgments at /constitution-petition-no-39-of-2019/ style slugs
- PDF judgments linked within individual post pages
- No DataTable / server-side search — WordPress category pagination

As of March 2026, the site is down for maintenance (NADRA).
This pipeline is built to handle anti-bot measures (Akamai) when it returns.
"""

BASE_URL = "https://www.supremecourt.gov.pk"
JUDGMENTS_URL = f"{BASE_URL}/category/judgements/"

# Court code used in Qdrant point IDs
COURT_CODE = "SC"

# WordPress pagination: /category/judgements/page/N/
PAGINATION_TEMPLATE = f"{JUDGMENTS_URL}page/{{page}}/"

# Maintenance page detection
MAINTENANCE_MARKERS = [
    "Site Under Maintenance",
    "We'll Be Back Soon",
    "currently down for maintenance",
]

# Crawl settings
REQUEST_DELAY_SECONDS = 2.0
MAX_PAGES = 200  # Safety limit for pagination

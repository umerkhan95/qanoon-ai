"""Custom exceptions for the Peshawar HC crawler pipeline."""


class CrawlError(Exception):
    """Raised when a crawl operation fails irrecoverably."""


class ExtractionError(Exception):
    """Raised when data extraction from HTML/PDF fails."""

"""Custom exceptions for the Balochistan HC crawler pipeline."""


class CrawlError(Exception):
    """Raised when a crawl operation fails irrecoverably."""


class ExtractionError(Exception):
    """Raised when data extraction from the portal API fails."""

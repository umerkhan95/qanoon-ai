"""Custom exceptions for the Federal Shariat Court crawler pipeline."""


class CrawlError(Exception):
    """Raised when a crawl operation fails irrecoverably."""


class ExtractionError(Exception):
    """Raised when data extraction from HTML/PDF fails."""

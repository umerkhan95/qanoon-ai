"""Custom exceptions for the Supreme Court crawler pipeline."""


class CrawlError(Exception):
    """Raised when a crawl operation fails irrecoverably."""


class ExtractionError(Exception):
    """Raised when data extraction from HTML/PDF fails."""


class SiteMaintenanceError(CrawlError):
    """Raised when the Supreme Court site is down for maintenance."""

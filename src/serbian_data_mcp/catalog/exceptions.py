"""Catalog-specific exceptions."""


class CatalogError(Exception):
    """Base exception for catalog errors."""


class CatalogBuildError(CatalogError):
    """Raised when catalog building fails."""


class CatalogLoadError(CatalogError):
    """Raised when catalog loading fails."""


class DatasetNotFound(CatalogError):
    """Raised when a dataset ID is not found in the catalog."""

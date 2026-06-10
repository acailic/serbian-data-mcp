"""Catalog module for dataset caching and semantic search.

This module provides:
- DatasetCatalog: Cache and index all datasets from data.gov.rs
- SearchEngine: Semantic search with relevance scoring
- AlternativeSuggestions: Fallback suggestions when no exact match
- DatasetPreview: Preview dataset structure and sample data
"""

from .cache import DatasetCatalog
from .search import SearchEngine
from .suggestions import AlternativeSuggestions
from .preview import DatasetPreview

__all__ = [
    "DatasetCatalog",
    "SearchEngine",
    "AlternativeSuggestions",
    "DatasetPreview",
]

"""Data models for catalog module."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CachedDataset:
    """A dataset cached from the data.gov.rs API."""

    id: str
    title: str
    description: str
    organization: str
    formats: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    modified_at: str = ""
    resource_count: int = 0
    has_downloadable: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "organization": self.organization,
            "formats": self.formats,
            "tags": self.tags,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "resource_count": self.resource_count,
            "has_downloadable": self.has_downloadable,
        }


@dataclass
class SearchResult:
    """A search result with relevance score."""

    dataset: CachedDataset
    relevance_score: float
    matched_keywords: list[str] = field(default_factory=list)
    match_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "dataset": self.dataset.to_dict(),
            "relevance_score": self.relevance_score,
            "matched_keywords": self.matched_keywords,
            "match_reason": self.match_reason,
        }


@dataclass
class Suggestion:
    """Alternative dataset suggestions."""

    datasets: list[SearchResult]
    explanation: str
    total_alternatives: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "datasets": [ds.to_dict() for ds in self.datasets],
            "explanation": self.explanation,
            "total_alternatives": self.total_alternatives,
        }

"""Data models for Serbian data portal."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class Resource:
    """Data resource (file) within a dataset."""

    id: str
    title: str
    description: Optional[str] = None
    format: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[datetime] = None
    size: Optional[int] = None
    mime_type: Optional[str] = None
    checksum: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Resource":
        """Create Resource from API response dictionary."""
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = None

        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            format=data.get("format"),
            url=data.get("url"),
            created_at=created_at,
            size=data.get("size"),
            mime_type=data.get("mime"),
            checksum=data.get("checksum")
        )


@dataclass
class Organization:
    """Organization that publishes datasets."""

    id: str
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    logo: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Organization":
        """Create Organization from API response dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description"),
            url=data.get("url"),
            logo=data.get("logo")
        )


@dataclass
class Dataset:
    """Dataset from the Serbian data portal."""

    id: str
    title: str
    description: Optional[str] = None
    organization: Optional[Organization] = None
    resources: List[Resource] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    frequency: Optional[str] = None
    temporal_coverage: Optional[str] = None
    spatial_coverage: Optional[str] = None
    license: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dataset":
        """Create Dataset from API response dictionary."""
        # Parse organization
        org_data = data.get("organization")
        organization = None
        if org_data:
            organization = Organization.from_dict(org_data)

        # Parse resources
        resources = []
        for res_data in data.get("resources", []):
            resources.append(Resource.from_dict(res_data))

        # Parse dates
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = None

        modified_at = data.get("modified_at") or data.get("last_modified")
        if modified_at and isinstance(modified_at, str):
            try:
                modified_at = datetime.fromisoformat(modified_at.replace('Z', '+00:00'))
            except ValueError:
                modified_at = None

        # Parse tags
        tags = []
        for tag_data in data.get("tags", []):
            if isinstance(tag_data, str):
                tags.append(tag_data)
            elif isinstance(tag_data, dict):
                tags.append(tag_data.get("name", ""))

        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            organization=organization,
            resources=resources,
            tags=tags,
            created_at=created_at,
            modified_at=modified_at,
            frequency=data.get("frequency"),
            temporal_coverage=data.get("temporal_coverage"),
            spatial_coverage=data.get("spatial_coverage"),
            license=data.get("license")
        )


@dataclass
class SearchResult:
    """Results from a dataset search."""

    datasets: List[Dataset]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1

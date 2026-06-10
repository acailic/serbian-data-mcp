"""Data models for Serbian data portal."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


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
    filetype: Optional[str] = None
    last_modified: Optional[datetime] = None
    latest: Optional[str] = None
    preview_url: Optional[str] = None
    schema: Optional[dict[str, Any]] = None
    type: Optional[str] = None
    checksum_type: Optional[str] = None
    checksum_value: Optional[str] = None
    harvest: Optional[dict[str, Any]] = None
    internal: Optional[dict[str, Any]] = None
    metrics: Optional[dict[str, int]] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Resource":
        """Create Resource from API response dictionary."""
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                created_at = None

        last_modified = data.get("last_modified")
        if last_modified and isinstance(last_modified, str):
            try:
                last_modified = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
            except ValueError:
                last_modified = None

        # Parse checksum - can be dict {type, value} or plain string
        checksum_data = data.get("checksum")
        checksum_type_val: Optional[str] = None
        checksum_value_val: Optional[str] = None
        checksum_val: Optional[str] = None
        if isinstance(checksum_data, dict):
            checksum_type_val = checksum_data.get("type")
            checksum_value_val = checksum_data.get("value")
        else:
            checksum_val = checksum_data

        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            format=data.get("format"),
            url=data.get("url"),
            created_at=created_at,
            size=data.get("size"),
            mime_type=data.get("mime"),
            checksum=checksum_val,
            filetype=data.get("filetype"),
            last_modified=last_modified,
            latest=data.get("latest"),
            preview_url=data.get("preview_url"),
            schema=data.get("schema"),
            type=data.get("type"),
            checksum_type=checksum_type_val,
            checksum_value=checksum_value_val,
            harvest=data.get("harvest"),
            internal=data.get("internal"),
            metrics=data.get("metrics"),
        )


@dataclass
class Organization:
    """Organization that publishes datasets."""

    id: str
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    logo: Optional[str] = None
    acronym: Optional[str] = None
    badges: list[dict[str, str]] = field(default_factory=list)
    business_number_id: Optional[str] = None
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    metrics: Optional[dict[str, int]] = None
    page: Optional[str] = None
    slug: Optional[str] = None
    uri: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Organization":
        """Create Organization from API response dictionary."""
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                created_at = None

        last_modified = data.get("last_modified")
        if last_modified and isinstance(last_modified, str):
            try:
                last_modified = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
            except ValueError:
                last_modified = None

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description"),
            url=data.get("url"),
            logo=data.get("logo"),
            acronym=data.get("acronym"),
            badges=data.get("badges", []),
            business_number_id=data.get("business_number_id"),
            created_at=created_at,
            last_modified=last_modified,
            metrics=data.get("metrics"),
            page=data.get("page"),
            slug=data.get("slug"),
            uri=data.get("uri"),
        )


@dataclass
class Dataset:
    """Dataset from the Serbian data portal."""

    id: str
    title: str
    description: Optional[str] = None
    organization: Optional[Organization] = None
    resources: list[Resource] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    frequency: Optional[str] = None
    temporal_coverage: Optional[str] = None
    spatial_coverage: Optional[str] = None
    license: Optional[str] = None
    acronym: Optional[str] = None
    badges: list[dict[str, str]] = field(default_factory=list)
    archived: Optional[bool] = None
    contact_points: list[dict[str, Any]] = field(default_factory=list)
    deleted: Optional[bool] = None
    extras: dict[str, Any] = field(default_factory=dict)
    frequency_date: Optional[str] = None
    harvest: Optional[dict[str, Any]] = None
    last_update: Optional[str] = None
    metrics: Optional[dict[str, int]] = None
    owner: Optional[dict[str, Any]] = None
    page: Optional[str] = None
    private: bool = False
    quality: Optional[dict[str, Any]] = None
    schema: Optional[dict[str, Any]] = None
    slug: Optional[str] = None
    spatial: Optional[dict[str, Any]] = None
    uri: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Dataset":
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
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                created_at = None

        modified_at = data.get("modified_at") or data.get("last_modified")
        if modified_at and isinstance(modified_at, str):
            try:
                modified_at = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
            except ValueError:
                modified_at = None

        # Parse tags - can be list of strings or list of dicts with "name" key
        tags = []
        for tag_data in data.get("tags", []):
            if isinstance(tag_data, str):
                tags.append(tag_data)
            elif isinstance(tag_data, dict):
                tags.append(tag_data.get("name", ""))

        # Parse temporal_coverage - can be dict {start, end} or string
        temporal_coverage = data.get("temporal_coverage")
        if isinstance(temporal_coverage, dict):
            start = temporal_coverage.get("start", "")
            end = temporal_coverage.get("end", "")
            temporal_coverage = f"{start} to {end}"

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
            temporal_coverage=temporal_coverage,
            spatial_coverage=data.get("spatial_coverage"),
            license=data.get("license"),
            acronym=data.get("acronym"),
            badges=data.get("badges", []),
            archived=data.get("archived"),
            contact_points=data.get("contact_points", []),
            deleted=data.get("deleted"),
            extras=data.get("extras", {}),
            frequency_date=data.get("frequency_date"),
            harvest=data.get("harvest"),
            last_update=data.get("last_update"),
            metrics=data.get("metrics"),
            owner=data.get("owner"),
            page=data.get("page"),
            private=data.get("private", False),
            quality=data.get("quality"),
            schema=data.get("schema"),
            slug=data.get("slug"),
            spatial=data.get("spatial"),
            uri=data.get("uri"),
        )


@dataclass
class SearchResult:
    """Results from a dataset search."""

    datasets: list[Dataset]
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

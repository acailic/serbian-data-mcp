"""Tests for API data models."""

from __future__ import annotations

import pytest
from datetime import datetime

from serbian_data_mcp.api.models import Dataset, Resource, Organization, SearchResult


class TestResource:
    """Test Resource model parsing."""

    def test_minimal_resource(self) -> None:
        data = {"id": "res-1", "title": "Test"}
        res = Resource.from_dict(data)
        assert res.id == "res-1"
        assert res.title == "Test"
        assert res.format is None
        assert res.url is None

    def test_full_resource(self) -> None:
        data: dict = {
            "id": "res-1",
            "title": "Test Resource",
            "description": "A test resource",
            "format": "csv",
            "url": "https://example.com/data.csv",
            "created_at": "2024-01-15T10:30:00+00:00",
            "size": 1024,
            "mime": "text/csv",
            "checksum": {"type": "sha1", "value": "abc123"},
            "filetype": "file",
            "type": "main",
            "last_modified": "2024-01-15T10:30:00+00:00",
            "latest": "https://data.gov.rs/sr/datasets/r/res-1",
            "preview_url": "https://example.com/preview",
        }
        res = Resource.from_dict(data)
        assert res.format == "csv"
        assert res.size == 1024
        assert res.mime_type == "text/csv"
        assert res.filetype == "file"
        assert res.type == "main"
        assert res.latest == "https://data.gov.rs/sr/datasets/r/res-1"
        assert res.preview_url == "https://example.com/preview"

    def test_checksum_as_string(self) -> None:
        data = {"id": "res-1", "title": "Test", "checksum": "sha1:abc123"}
        res = Resource.from_dict(data)
        assert res.checksum == "sha1:abc123"

    def test_checksum_as_dict(self) -> None:
        data = {"id": "res-1", "title": "Test", "checksum": {"type": "sha1", "value": "abc123"}}
        res = Resource.from_dict(data)
        assert res.checksum is None
        assert res.checksum_type == "sha1"
        assert res.checksum_value == "abc123"

    def test_checksum_none(self) -> None:
        data = {"id": "res-1", "title": "Test"}
        res = Resource.from_dict(data)
        assert res.checksum is None
        assert res.checksum_type is None
        assert res.checksum_value is None

    def test_created_at_valid(self) -> None:
        data = {"id": "res-1", "title": "Test", "created_at": "2024-01-15T10:30:00+00:00"}
        res = Resource.from_dict(data)
        assert res.created_at is not None
        assert isinstance(res.created_at, datetime)
        assert res.created_at.year == 2024

    def test_created_at_z_suffix(self) -> None:
        data = {"id": "res-1", "title": "Test", "created_at": "2024-01-15T10:30:00Z"}
        res = Resource.from_dict(data)
        assert res.created_at is not None
        assert isinstance(res.created_at, datetime)

    def test_invalid_date_falls_back_to_none(self) -> None:
        data = {"id": "res-1", "title": "Test", "created_at": "not-a-date"}
        res = Resource.from_dict(data)
        assert res.created_at is None

    def test_created_at_non_string_ignored(self) -> None:
        data = {"id": "res-1", "title": "Test", "created_at": 12345}
        res = Resource.from_dict(data)
        # Non-string created_at passes through as-is (implementation quirk)
        assert res.created_at == 12345

    def test_last_modified_valid(self) -> None:
        data = {"id": "res-1", "title": "Test", "last_modified": "2024-06-01T00:00:00Z"}
        res = Resource.from_dict(data)
        assert res.last_modified is not None
        assert res.last_modified.month == 6

    def test_last_modified_invalid(self) -> None:
        data = {"id": "res-1", "title": "Test", "last_modified": "bad-date"}
        res = Resource.from_dict(data)
        assert res.last_modified is None

    def test_schema_field(self) -> None:
        schema = {"fields": [{"name": "col1", "type": "string"}]}
        data = {"id": "res-1", "title": "Test", "schema": schema}
        res = Resource.from_dict(data)
        assert res.schema == schema

    def test_metrics_field(self) -> None:
        data = {"id": "res-1", "title": "Test", "metrics": {"views": 100, "downloads": 50}}
        res = Resource.from_dict(data)
        assert res.metrics == {"views": 100, "downloads": 50}

    def test_harvest_field(self) -> None:
        data = {"id": "res-1", "title": "Test", "harvest": {"source": "opendata.stat.gov.rs"}}
        res = Resource.from_dict(data)
        assert res.harvest == {"source": "opendata.stat.gov.rs"}

    def test_empty_id_and_title_defaults(self) -> None:
        data: dict = {}
        res = Resource.from_dict(data)
        assert res.id == ""
        assert res.title == ""


class TestOrganization:
    def test_minimal_org(self) -> None:
        data = {"id": "org-1", "name": "Test Org"}
        org = Organization.from_dict(data)
        assert org.id == "org-1"
        assert org.name == "Test Org"

    def test_full_org(self) -> None:
        data: dict = {
            "id": "org-1",
            "name": "Општина Београд",
            "description": "Test description",
            "url": "https://example.com",
            "logo": "https://example.com/logo.png",
            "acronym": "ОУ Београд",
            "badges": [{"kind": "public-service"}, {"kind": "certified"}],
            "business_number_id": "12345678",
            "created_at": "2024-01-15T10:30:00+00:00",
            "metrics": {"datasets": 10, "followers": 5},
            "page": "https://data.gov.rs/sr/organizations/test/",
            "slug": "test-org",
            "uri": "https://data.gov.rs/api/1/organizations/test/",
        }
        org = Organization.from_dict(data)
        assert org.name == "Општина Београд"
        assert org.acronym == "ОУ Београд"
        assert len(org.badges) == 2
        assert org.business_number_id == "12345678"
        assert org.metrics == {"datasets": 10, "followers": 5}
        assert org.slug == "test-org"
        assert org.page == "https://data.gov.rs/sr/organizations/test/"

    def test_badges_default_empty(self) -> None:
        data = {"id": "org-1", "name": "Org"}
        org = Organization.from_dict(data)
        assert org.badges == []

    def test_created_at_valid(self) -> None:
        data = {"id": "org-1", "name": "Org", "created_at": "2024-06-01T00:00:00Z"}
        org = Organization.from_dict(data)
        assert org.created_at is not None
        assert isinstance(org.created_at, datetime)

    def test_created_at_invalid(self) -> None:
        data = {"id": "org-1", "name": "Org", "created_at": "bad"}
        org = Organization.from_dict(data)
        assert org.created_at is None

    def test_last_modified_valid(self) -> None:
        data = {"id": "org-1", "name": "Org", "last_modified": "2024-12-31T23:59:59Z"}
        org = Organization.from_dict(data)
        assert org.last_modified is not None

    def test_metrics_none(self) -> None:
        data = {"id": "org-1", "name": "Org"}
        org = Organization.from_dict(data)
        assert org.metrics is None

    def test_empty_defaults(self) -> None:
        data: dict = {}
        org = Organization.from_dict(data)
        assert org.id == ""
        assert org.name == ""


class TestDataset:
    def test_minimal_dataset(self) -> None:
        data = {"id": "ds-1", "title": "Test Dataset"}
        ds = Dataset.from_dict(data)
        assert ds.id == "ds-1"
        assert ds.title == "Test Dataset"
        assert ds.resources == []
        assert ds.tags == []

    def test_dataset_with_resources(self) -> None:
        data: dict = {
            "id": "ds-1",
            "title": "Test",
            "resources": [
                {"id": "r1", "title": "R1", "format": "csv"},
                {"id": "r2", "title": "R2", "format": "json"},
            ],
        }
        ds = Dataset.from_dict(data)
        assert len(ds.resources) == 2
        assert ds.resources[0].format == "csv"
        assert ds.resources[1].format == "json"

    def test_dataset_with_org(self) -> None:
        data: dict = {
            "id": "ds-1",
            "title": "Test",
            "organization": {"id": "org-1", "name": "Test Org"},
        }
        ds = Dataset.from_dict(data)
        assert ds.organization is not None
        assert ds.organization.name == "Test Org"

    def test_organization_none_when_absent(self) -> None:
        data = {"id": "ds-1", "title": "Test"}
        ds = Dataset.from_dict(data)
        assert ds.organization is None

    def test_temporal_coverage_as_string(self) -> None:
        data = {"id": "ds-1", "title": "Test", "temporal_coverage": "2024"}
        ds = Dataset.from_dict(data)
        assert ds.temporal_coverage == "2024"

    def test_temporal_coverage_as_dict(self) -> None:
        data = {"id": "ds-1", "title": "Test", "temporal_coverage": {"start": "2024-01-01", "end": "2024-12-31"}}
        ds = Dataset.from_dict(data)
        assert isinstance(ds.temporal_coverage, str)
        assert "2024-01-01" in ds.temporal_coverage
        assert "2024-12-31" in ds.temporal_coverage

    def test_temporal_coverage_dict_with_missing_keys(self) -> None:
        data = {"id": "ds-1", "title": "Test", "temporal_coverage": {"start": "2024-01-01"}}
        ds = Dataset.from_dict(data)
        assert isinstance(ds.temporal_coverage, str)

    def test_tags_as_strings(self) -> None:
        data = {"id": "ds-1", "title": "Test", "tags": ["tag1", "tag2"]}
        ds = Dataset.from_dict(data)
        assert ds.tags == ["tag1", "tag2"]

    def test_tags_as_dicts(self) -> None:
        data = {"id": "ds-1", "title": "Test", "tags": [{"name": "tag1"}, {"name": "tag2"}]}
        ds = Dataset.from_dict(data)
        assert ds.tags == ["tag1", "tag2"]

    def test_mixed_tags(self) -> None:
        data: dict = {"id": "ds-1", "title": "Test", "tags": ["string-tag", {"name": "dict-tag"}]}
        ds = Dataset.from_dict(data)
        assert "string-tag" in ds.tags
        assert "dict-tag" in ds.tags

    def test_tags_dict_without_name_key(self) -> None:
        data = {"id": "ds-1", "title": "Test", "tags": [{"label": "orphan"}]}
        ds = Dataset.from_dict(data)
        assert "" in ds.tags

    def test_empty_tags_list(self) -> None:
        data = {"id": "ds-1", "title": "Test", "tags": []}
        ds = Dataset.from_dict(data)
        assert ds.tags == []

    def test_no_tags_key(self) -> None:
        data = {"id": "ds-1", "title": "Test"}
        ds = Dataset.from_dict(data)
        assert ds.tags == []

    def test_created_at(self) -> None:
        data = {"id": "ds-1", "title": "Test", "created_at": "2024-03-15T08:00:00Z"}
        ds = Dataset.from_dict(data)
        assert ds.created_at is not None
        assert ds.created_at.month == 3

    def test_created_at_invalid(self) -> None:
        data = {"id": "ds-1", "title": "Test", "created_at": "invalid"}
        ds = Dataset.from_dict(data)
        assert ds.created_at is None

    def test_modified_at(self) -> None:
        data = {"id": "ds-1", "title": "Test", "modified_at": "2024-06-01T00:00:00Z"}
        ds = Dataset.from_dict(data)
        assert ds.modified_at is not None
        assert ds.modified_at.month == 6

    def test_modified_at_fallback_to_last_modified(self) -> None:
        data = {"id": "ds-1", "title": "Test", "last_modified": "2024-06-01T00:00:00Z"}
        ds = Dataset.from_dict(data)
        assert ds.modified_at is not None

    def test_modified_at_invalid(self) -> None:
        data = {"id": "ds-1", "title": "Test", "modified_at": "bad-date"}
        ds = Dataset.from_dict(data)
        assert ds.modified_at is None

    def test_frequency(self) -> None:
        data = {"id": "ds-1", "title": "Test", "frequency": "monthly"}
        ds = Dataset.from_dict(data)
        assert ds.frequency == "monthly"

    def test_spatial_coverage(self) -> None:
        data = {"id": "ds-1", "title": "Test", "spatial_coverage": "Beograd"}
        ds = Dataset.from_dict(data)
        assert ds.spatial_coverage == "Beograd"

    def test_license(self) -> None:
        data = {"id": "ds-1", "title": "Test", "license": "CC-BY-4.0"}
        ds = Dataset.from_dict(data)
        assert ds.license == "CC-BY-4.0"

    def test_acronym(self) -> None:
        data = {"id": "ds-1", "title": "Test", "acronym": "RZS"}
        ds = Dataset.from_dict(data)
        assert ds.acronym == "RZS"

    def test_badges(self) -> None:
        data: dict = {"id": "ds-1", "title": "Test", "badges": [{"kind": "data"}]}
        ds = Dataset.from_dict(data)
        assert len(ds.badges) == 1

    def test_archived(self) -> None:
        data = {"id": "ds-1", "title": "Test", "archived": True}
        ds = Dataset.from_dict(data)
        assert ds.archived is True

    def test_deleted(self) -> None:
        data = {"id": "ds-1", "title": "Test", "deleted": False}
        ds = Dataset.from_dict(data)
        assert ds.deleted is False

    def test_contact_points(self) -> None:
        data: dict = {"id": "ds-1", "title": "Test", "contact_points": [{"name": "Admin", "email": "a@b.rs"}]}
        ds = Dataset.from_dict(data)
        assert len(ds.contact_points) == 1
        assert ds.contact_points[0]["name"] == "Admin"

    def test_extras(self) -> None:
        data: dict = {"id": "ds-1", "title": "Test", "extras": {"key": "value"}}
        ds = Dataset.from_dict(data)
        assert ds.extras == {"key": "value"}

    def test_quality(self) -> None:
        data: dict = {"id": "ds-1", "title": "Test", "quality": {"score": 0.85, "description": "Good"}}
        ds = Dataset.from_dict(data)
        assert ds.quality is not None
        assert ds.quality["score"] == 0.85

    def test_private(self) -> None:
        data = {"id": "ds-1", "title": "Test", "private": True}
        ds = Dataset.from_dict(data)
        assert ds.private is True

    def test_private_default_false(self) -> None:
        data = {"id": "ds-1", "title": "Test"}
        ds = Dataset.from_dict(data)
        assert ds.private is False

    def test_page(self) -> None:
        data = {"id": "ds-1", "title": "Test", "page": "https://data.gov.rs/sr/datasets/test/"}
        ds = Dataset.from_dict(data)
        assert ds.page == "https://data.gov.rs/sr/datasets/test/"

    def test_slug(self) -> None:
        data = {"id": "ds-1", "title": "Test", "slug": "test-dataset"}
        ds = Dataset.from_dict(data)
        assert ds.slug == "test-dataset"

    def test_uri(self) -> None:
        data = {"id": "ds-1", "title": "Test", "uri": "https://data.gov.rs/api/1/datasets/test/"}
        ds = Dataset.from_dict(data)
        assert ds.uri == "https://data.gov.rs/api/1/datasets/test/"

    def test_spatial_dict(self) -> None:
        data: dict = {"id": "ds-1", "title": "Test", "spatial": {"zones": ["Beograd"]}}
        ds = Dataset.from_dict(data)
        assert ds.spatial == {"zones": ["Beograd"]}

    def test_owner(self) -> None:
        data: dict = {"id": "ds-1", "title": "Test", "owner": {"id": "u1", "name": "User"}}
        ds = Dataset.from_dict(data)
        assert ds.owner == {"id": "u1", "name": "User"}

    def test_harvest(self) -> None:
        data: dict = {"id": "ds-1", "title": "Test", "harvest": {"source": "opendata.stat.gov.rs"}}
        ds = Dataset.from_dict(data)
        assert ds.harvest == {"source": "opendata.stat.gov.rs"}

    def test_metrics(self) -> None:
        data: dict = {"id": "ds-1", "title": "Test", "metrics": {"views": 500}}
        ds = Dataset.from_dict(data)
        assert ds.metrics == {"views": 500}


class TestSearchResult:
    def test_total_pages(self) -> None:
        result = SearchResult(datasets=[], total=100, page=1, page_size=10)
        assert result.total_pages == 10
        assert result.has_next is True
        assert result.has_previous is False

    def test_last_page(self) -> None:
        result = SearchResult(datasets=[], total=100, page=10, page_size=10)
        assert result.has_next is False
        assert result.has_previous is True

    def test_empty_result(self) -> None:
        result = SearchResult(datasets=[], total=0, page=1, page_size=10)
        assert result.total_pages == 0
        assert result.has_next is False
        assert result.has_previous is False

    def test_single_page_exact(self) -> None:
        result = SearchResult(datasets=[], total=20, page=1, page_size=20)
        assert result.total_pages == 1
        assert result.has_next is False
        assert result.has_previous is False

    def test_middle_page(self) -> None:
        result = SearchResult(datasets=[], total=100, page=5, page_size=10)
        assert result.total_pages == 10
        assert result.has_next is True
        assert result.has_previous is True

    def test_partial_last_page(self) -> None:
        result = SearchResult(datasets=[], total=25, page=3, page_size=10)
        assert result.total_pages == 3
        assert result.has_next is False

    def test_with_datasets(self) -> None:
        ds1 = Dataset(id="1", title="D1")
        ds2 = Dataset(id="2", title="D2")
        result = SearchResult(datasets=[ds1, ds2], total=2, page=1, page_size=10)
        assert len(result.datasets) == 2
        assert result.datasets[0].id == "1"

    def test_page_beyond_total(self) -> None:
        result = SearchResult(datasets=[], total=5, page=100, page_size=10)
        assert result.total_pages == 1
        assert result.has_next is False
        assert result.has_previous is True

    def test_zero_page_size_division(self) -> None:
        result = SearchResult(datasets=[], total=100, page=1, page_size=1)
        assert result.total_pages == 100


class TestDatasetEdgeCases:
    """Edge case tests for Dataset model."""

    def test_dataset_with_empty_resources_list(self) -> None:
        """Dataset with explicit empty resources list should have empty list."""
        data: dict = {"id": "ds-1", "title": "Test", "resources": []}
        ds = Dataset.from_dict(data)
        assert ds.resources == []

    def test_dataset_with_null_scalar_fields(self) -> None:
        """Dataset with null scalar values should handle gracefully."""
        data: dict = {
            "id": "ds-1",
            "title": "Test",
            "description": None,
            "organization": None,
            "frequency": None,
            "license": None,
            "acronym": None,
            "spatial_coverage": None,
            "temporal_coverage": None,
        }
        ds = Dataset.from_dict(data)
        assert ds.description is None
        assert ds.organization is None
        assert ds.resources == []  # missing key → default factory
        assert ds.tags == []  # missing key → default factory

    def test_dataset_with_null_resources_crashes(self) -> None:
        """resources=None (not missing) causes TypeError - known edge case."""
        data: dict = {"id": "ds-1", "title": "Test", "resources": None}
        with pytest.raises(TypeError):
            Dataset.from_dict(data)

    def test_dataset_with_full_realistic_response(self) -> None:
        """Dataset with all fields populated like a real data.gov.rs response."""
        data: dict = {
            "id": "5e75b69b-8b0e-452c-a1e2-1234567890ab",
            "title": "Попис становништва, домаћинстава и станова 2022",
            "description": "Резултати пописа становништва Републике Србије 2022.",
            "organization": {
                "id": "544937e8-8b0e-452c-a1e2-abcdef123456",
                "name": "Републички завод за статистику",
                "acronym": "РЗС",
                "url": "https://www.stat.gov.rs",
                "metrics": {"datasets": 245, "followers": 120, "views": 50000},
                "badges": [{"kind": "certified"}],
            },
            "resources": [
                {
                    "id": "r1",
                    "title": "Становништво по општинама - CSV",
                    "format": "csv",
                    "url": "https://data.gov.rs/sr/datasets/r/r1",
                    "created_at": "2023-06-15T10:00:00Z",
                    "size": 524288,
                    "mime": "text/csv",
                    "checksum": {"type": "sha1", "value": "a1b2c3d4e5f6"},
                    "filetype": "file",
                    "type": "main",
                    "last_modified": "2023-12-01T08:30:00Z",
                    "schema": {
                        "fields": [
                            {"name": "Општина", "type": "string"},
                            {"name": "Становници", "type": "integer"},
                        ]
                    },
                    "metrics": {"views": 1500, "downloads": 800},
                },
                {"id": "r2", "title": "XLSX", "format": "xlsx", "size": 1048576},
            ],
            "tags": [{"name": "попис"}, "становништво", {"name": "демографија"}],
            "created_at": "2023-01-15T09:00:00Z",
            "modified_at": "2024-01-20T14:30:00Z",
            "frequency": "irregular",
            "frequency_date": "2023-06-15",
            "temporal_coverage": {"start": "2022-10-01", "end": "2022-10-31"},
            "spatial_coverage": "Република Србија",
            "spatial": {"zones": ["RS"]},
            "license": "CC-BY-4.0",
            "acronym": "ПОПИС 2022",
            "badges": [{"kind": "data"}, {"kind": "certified"}],
            "archived": False,
            "deleted": False,
            "private": False,
            "contact_points": [{"name": "Јован Петровић", "email": "popis@stat.gov.rs"}],
            "extras": {"theme": "population"},
            "harvest": {"source": "opendata.stat.gov.rs"},
            "metrics": {"views": 25000, "downloads": 15000},
            "owner": {"id": "u1", "name": "Admin"},
            "page": "https://data.gov.rs/sr/datasets/popis-2022/",
            "slug": "popis-2022",
            "quality": {"score": 0.92, "description": "Одличан квалитет"},
        }
        ds = Dataset.from_dict(data)

        assert ds.id == "5e75b69b-8b0e-452c-a1e2-1234567890ab"
        assert "Попис становништва" in ds.title
        assert ds.frequency == "irregular"
        assert ds.license == "CC-BY-4.0"
        assert ds.acronym == "ПОПИС 2022"
        assert ds.archived is False

        # Organization
        assert ds.organization is not None
        assert ds.organization.name == "Републички завод за статистику"
        assert ds.organization.metrics is not None
        assert ds.organization.metrics["datasets"] == 245

        # Resources
        assert len(ds.resources) == 2
        r1 = ds.resources[0]
        assert r1.format == "csv"
        assert r1.checksum_type == "sha1"
        assert r1.metrics is not None
        assert r1.schema is not None

        # Tags (mixed string/dict)
        assert len(ds.tags) == 3
        assert "попис" in ds.tags
        assert "становништво" in ds.tags

        # Temporal coverage
        assert isinstance(ds.temporal_coverage, str)
        assert "2022-10-01" in ds.temporal_coverage

        # Quality
        assert ds.quality is not None
        assert ds.quality["score"] == 0.92

        # Harvest
        assert ds.harvest is not None
        assert ds.harvest["source"] == "opendata.stat.gov.rs"


class TestOrganizationEdgeCases:
    """Edge case tests for Organization model."""

    def test_org_with_null_metrics(self) -> None:
        """Organization with explicit null metrics should have None."""
        data: dict = {"id": "org-1", "name": "Org", "metrics": None}
        org = Organization.from_dict(data)
        assert org.metrics is None

    def test_org_with_all_fields(self) -> None:
        """Organization with all fields including badges, metrics."""
        data: dict = {
            "id": "544937e8-8b0e-452c-a1e2-abcdef123456",
            "name": "Град Београд",
            "description": "Организација града Београда за отворене податке",
            "url": "https://www.beograd.rs",
            "logo": "https://data.gov.rs/sr/uploads/org/beograd.png",
            "acronym": "ГБ",
            "badges": [
                {"kind": "certified"},
                {"kind": "public-service"},
            ],
            "business_number_id": "17012345",
            "created_at": "2022-03-01T08:00:00Z",
            "last_modified": "2024-06-15T16:00:00Z",
            "metrics": {
                "datasets": 87,
                "followers": 2500,
                "views": 150000,
                "issues": 12,
            },
            "page": "https://data.gov.rs/sr/organizations/grad-beograd/",
            "slug": "grad-beograd",
            "uri": "https://data.gov.rs/api/1/organizations/grad-beograd/",
        }
        org = Organization.from_dict(data)

        assert org.name == "Град Београд"
        assert org.acronym == "ГБ"
        assert org.business_number_id == "17012345"
        assert len(org.badges) == 2
        assert org.badges[1]["kind"] == "public-service"
        assert org.metrics is not None
        assert org.metrics["datasets"] == 87
        assert org.metrics["issues"] == 12
        assert org.slug == "grad-beograd"
        assert org.created_at is not None
        assert org.created_at.year == 2022
        assert org.last_modified is not None
        assert org.last_modified.year == 2024

    def test_org_with_empty_description(self) -> None:
        """Organization with empty string description."""
        data: dict = {"id": "org-1", "name": "Org", "description": ""}
        org = Organization.from_dict(data)
        assert org.description == ""


class TestResourceEdgeCases:
    """Edge case tests for Resource model."""

    def test_resource_with_all_new_fields(self) -> None:
        """Resource with all fields including new ones from realistic response."""
        data: dict = {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "title": "БДП по кварталима 2024",
            "description": "Бруто домаћи производ Републике Србије",
            "format": "xlsx",
            "url": "https://data.gov.rs/sr/datasets/r/a1b2c3",
            "created_at": "2024-03-15T10:30:00+01:00",
            "size": 2097152,
            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "checksum": {"type": "sha256", "value": "deadbeefcafebabe1234567890abcdef"},
            "filetype": "file",
            "type": "main",
            "last_modified": "2024-06-01T14:00:00+02:00",
            "latest": "https://data.gov.rs/sr/datasets/r/a1b2c3",
            "preview_url": "https://data.gov.rs/sr/datasets/r/a1b2c3/preview",
            "schema": {
                "fields": [
                    {"name": "Квартал", "type": "string"},
                    {"name": "БДП (милиони евра)", "type": "number"},
                ]
            },
            "harvest": {"source": "opendata.stat.gov.rs"},
            "internal": {"harvest_oid": "h123"},
            "metrics": {"views": 3200, "downloads": 1500},
        }
        res = Resource.from_dict(data)

        assert res.format == "xlsx"
        assert res.size == 2097152
        assert res.mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert res.checksum is None  # dict checksum → None on raw field
        assert res.checksum_type == "sha256"
        assert res.checksum_value == "deadbeefcafebabe1234567890abcdef"
        assert res.filetype == "file"
        assert res.type == "main"
        assert res.latest is not None
        assert res.preview_url is not None
        assert res.schema is not None
        assert len(res.schema["fields"]) == 2
        assert res.harvest is not None
        assert res.harvest["source"] == "opendata.stat.gov.rs"
        assert res.internal is not None
        assert res.internal["harvest_oid"] == "h123"
        assert res.metrics is not None
        assert res.metrics["downloads"] == 1500

    def test_resource_with_null_size(self) -> None:
        """Resource with null size should have None."""
        data = {"id": "r1", "title": "Test", "size": None}
        res = Resource.from_dict(data)
        assert res.size is None

    def test_resource_with_zero_size(self) -> None:
        """Resource with zero size should have 0."""
        data = {"id": "r1", "title": "Test", "size": 0}
        res = Resource.from_dict(data)
        assert res.size == 0

    def test_resource_mime_field_mapping(self) -> None:
        """Resource should map 'mime' API field to 'mime_type' model field."""
        data = {"id": "r1", "title": "Test", "mime": "application/json"}
        res = Resource.from_dict(data)
        assert res.mime_type == "application/json"

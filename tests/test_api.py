"""Tests for API client and models."""

import pytest
from serbian_data_mcp.api import UDataClient, Dataset, Resource, Organization


@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = UDataClient()
    assert client.base_url == "https://data.gov.rs"
    assert client.rate_limit == 1.0
    assert client.timeout == 30


@pytest.mark.asyncio
async def test_client_custom_config():
    """Test client with custom configuration."""
    client = UDataClient(base_url="https://custom.example.com", rate_limit=2.0, timeout=60)
    assert client.base_url == "https://custom.example.com"
    assert client.rate_limit == 2.0
    assert client.timeout == 60


def test_resource_from_dict():
    """Test Resource model creation."""
    data = {
        "id": "test-resource",
        "title": "Test Resource",
        "description": "A test resource",
        "format": "json",
        "url": "https://example.com/data.json",
        "created_at": "2025-01-01T00:00:00Z",
        "size": 1024,
        "mime": "application/json",
        "checksum": "abc123",
    }

    resource = Resource.from_dict(data)

    assert resource.id == "test-resource"
    assert resource.title == "Test Resource"
    assert resource.format == "json"
    assert resource.url == "https://example.com/data.json"
    assert resource.size == 1024


def test_organization_from_dict():
    """Test Organization model creation."""
    data = {
        "id": "test-org",
        "name": "Test Organization",
        "description": "A test organization",
        "url": "https://example.com",
        "logo": "https://example.com/logo.png",
    }

    org = Organization.from_dict(data)

    assert org.id == "test-org"
    assert org.name == "Test Organization"
    assert org.description == "A test organization"


def test_dataset_from_dict():
    """Test Dataset model creation."""
    data = {
        "id": "test-dataset",
        "title": "Test Dataset",
        "description": "A test dataset",
        "organization": {"id": "test-org", "name": "Test Organization"},
        "resources": [{"id": "res1", "title": "Resource 1", "format": "json"}],
        "tags": ["tag1", "tag2"],
        "created_at": "2025-01-01T00:00:00Z",
        "modified_at": "2025-01-02T00:00:00Z",
        "frequency": "annual",
        "license": "CC-BY-4.0",
    }

    dataset = Dataset.from_dict(data)

    assert dataset.id == "test-dataset"
    assert dataset.title == "Test Dataset"
    assert dataset.organization is not None
    assert dataset.organization.name == "Test Organization"
    assert len(dataset.resources) == 1
    assert dataset.resources[0].title == "Resource 1"
    assert len(dataset.tags) == 2
    assert dataset.frequency == "annual"


def test_search_result():
    """Test SearchResult model."""
    from serbian_data_mcp.api.models import SearchResult

    datasets = [Dataset(id="1", title="Dataset 1"), Dataset(id="2", title="Dataset 2")]

    result = SearchResult(datasets=datasets, total=100, page=1, page_size=10)

    assert len(result.datasets) == 2
    assert result.total == 100
    assert result.total_pages == 10
    assert result.has_next is True
    assert result.has_previous is False

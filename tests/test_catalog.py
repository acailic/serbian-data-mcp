"""Unit tests for catalog module."""

import pytest
from pathlib import Path
from serbian_data_mcp.catalog.cache import DatasetCatalog
from serbian_data_mcp.catalog.models import CachedDataset


@pytest.fixture
def temp_cache_path(tmp_path):
    """Create temporary cache path."""
    cache_file = tmp_path / "catalog.json"
    return cache_file


@pytest.fixture
def sample_dataset():
    """Sample dataset for testing."""
    return CachedDataset(
        id="test-ds-1",
        title="Test Dataset",
        description="A test dataset",
        organization="Test Org",
        formats=["csv", "json"],
        tags=["test", "sample"],
        created_at="2025-01-01T00:00:00Z",
        modified_at="2025-01-10T00:00:00Z",
        resource_count=2,
        has_downloadable=True,
    )


def test_cached_dataset_to_dict(sample_dataset):
    """Test CachedDataset serialization."""
    result = sample_dataset.to_dict()

    assert result["id"] == "test-ds-1"
    assert result["title"] == "Test Dataset"
    assert result["organization"] == "Test Org"
    assert result["formats"] == ["csv", "json"]
    assert result["has_downloadable"] is True


def test_catalog_initialization(temp_cache_path):
    """Test catalog initialization."""
    catalog = DatasetCatalog(cache_path=temp_cache_path)

    assert catalog.cache_path == temp_cache_path
    assert len(catalog) == 0
    assert catalog._initialized is False


def test_catalog_get_set(temp_cache_path, sample_dataset):
    """Test adding and retrieving datasets."""
    catalog = DatasetCatalog(cache_path=temp_cache_path)

    # Add dataset
    catalog.datasets["test-ds-1"] = sample_dataset

    # Retrieve
    result = catalog.get("test-ds-1")
    assert result is not None
    assert result.id == "test-ds-1"

    # Non-existent dataset
    assert catalog.get("non-existent") is None


def test_catalog_contains(temp_cache_path, sample_dataset):
    """Test __contains__ method."""
    catalog = DatasetCatalog(cache_path=temp_cache_path)

    catalog.datasets["test-ds-1"] = sample_dataset

    assert "test-ds-1" in catalog
    assert "non-existent" not in catalog


def test_catalog_len(temp_cache_path, sample_dataset):
    """Test __len__ method."""
    catalog = DatasetCatalog(cache_path=temp_cache_path)

    assert len(catalog) == 0

    catalog.datasets["test-ds-1"] = sample_dataset
    assert len(catalog) == 1


def test_catalog_get_all(temp_cache_path, sample_dataset):
    """Test get_all method."""
    catalog = DatasetCatalog(cache_path=temp_cache_path)

    catalog.datasets["test-ds-1"] = sample_dataset

    all_datasets = catalog.get_all()
    assert len(all_datasets) == 1
    assert all_datasets[0].id == "test-ds-1"

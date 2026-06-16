"""Unit tests for search engine."""

import pytest
from serbian_data_mcp.catalog.cache import DatasetCatalog
from serbian_data_mcp.catalog.models import CachedDataset
from serbian_data_mcp.catalog.search import SearchEngine


@pytest.fixture
def sample_catalog():
    """Create catalog with sample datasets."""
    catalog = DatasetCatalog()

    # Add sample datasets
    catalog.datasets["pop-1"] = CachedDataset(
        id="pop-1",
        title="Population by Age",
        description="Demographic data showing population distribution by age groups",
        organization="Statistical Office",
        formats=["xlsx"],
        tags=["population", "demographics", "age"],
    )
    catalog.datasets["budg-1"] = CachedDataset(
        id="budg-1",
        title="Government Budget 2024",
        description="Annual budget execution report",
        organization="Ministry of Finance",
        formats=["csv"],
        tags=["budget", "finance"],
    )
    catalog.datasets["health-1"] = CachedDataset(
        id="health-1",
        title="Health Statistics",
        description="Public health indicators and hospital data",
        organization="Ministry of Health",
        formats=["json"],
        tags=["health", "statistics"],
    )

    return catalog


def test_search_engine_initialization(sample_catalog):
    """Test search engine initialization."""
    engine = SearchEngine(sample_catalog)

    assert engine.catalog == sample_catalog
    assert engine.query_expander is not None


@pytest.mark.asyncio
async def test_search_by_title(sample_catalog):
    """Test searching by title."""
    engine = SearchEngine(sample_catalog)

    results = await engine.search("population", max_results=10)

    assert len(results) == 1
    assert results[0].dataset.id == "pop-1"
    assert results[0].relevance_score >= 0.5  # Title match


@pytest.mark.asyncio
async def test_search_by_description(sample_catalog):
    """Test searching by description."""
    engine = SearchEngine(sample_catalog)

    results = await engine.search("demographic", max_results=10)

    assert len(results) == 1
    assert results[0].dataset.id == "pop-1"
    assert "demographic" in results[0].match_reason.lower()


@pytest.mark.asyncio
async def test_search_by_tags(sample_catalog):
    """Test searching by tags."""
    engine = SearchEngine(sample_catalog)

    results = await engine.search("finance", max_results=10, min_score=0.2)

    assert len(results) == 1
    assert results[0].dataset.id == "budg-1"
    assert results[0].relevance_score >= 0.2


@pytest.mark.asyncio
async def test_search_no_results(sample_catalog):
    """Test search with no matching results."""
    engine = SearchEngine(sample_catalog)

    results = await engine.search("xyz123", max_results=10, min_score=0.3)

    assert len(results) == 0


@pytest.mark.asyncio
async def test_search_max_results(sample_catalog):
    """Test max_results parameter."""
    engine = SearchEngine(sample_catalog)

    # Add more datasets
    for i in range(10):
        sample_catalog.datasets[f"test-{i}"] = CachedDataset(
            id=f"test-{i}",
            title=f"Test {i}",
            description="Test dataset",
            organization="Test",
            formats=["csv"],
            tags=["test"],
        )

    results = await engine.search("test", max_results=5)

    assert len(results) <= 5


@pytest.mark.asyncio
async def test_search_organization(sample_catalog):
    """Test search by organization."""
    engine = SearchEngine(sample_catalog)

    results = await engine.search_by_organization("Statistical")

    assert len(results) == 1
    assert results[0].dataset.id == "pop-1"

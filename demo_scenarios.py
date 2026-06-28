"""Real user scenarios for intelligent MCP server demo."""

import asyncio
from serbian_data_mcp.catalog.cache import DatasetCatalog
from serbian_data_mcp.catalog.search import SearchEngine
from serbian_data_mcp.catalog.suggestions import AlternativeSuggestions
from serbian_data_mcp.intelligence.query_expander import QueryExpander


async def scenario_1_english_query():
    """Scenario 1: User searches in plain English."""
    print("\n" + "=" * 60)
    print("SCENARIO 1: Natural Language Search (English)")
    print("=" * 60)
    print("User asks: 'I need data about population by age'\n")

    # Setup catalog with sample data
    catalog = DatasetCatalog()
    # In real usage: await catalog.initialize()

    # Add sample datasets
    from serbian_data_mcp.catalog.models import CachedDataset

    catalog.datasets["pop-001"] = CachedDataset(
        id="pop-001",
        title="Population by Age and Gender",
        description="Demographic data showing population distribution by age groups and gender",
        organization="Statistical Office of Republic of Serbia",
        formats=["xlsx", "csv"],
        tags=["population", "demographics", "age", "gender"],
    )
    catalog.datasets["budg-001"] = CachedDataset(
        id="budg-001",
        title="Government Budget 2024",
        description="Annual budget execution report for Republic of Serbia",
        organization="Ministry of Finance",
        formats=["pdf", "xlsx"],
        tags=["budget", "finance", "economy"],
    )

    # Search
    engine = SearchEngine(catalog)
    results = await engine.search("population by age", max_results=5, min_score=0.3)

    print(f"Found {len(results)} result(s):\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.dataset.title}")
        print(f"   ID: {result.dataset.id}")
        print(f"   Organization: {result.dataset.organization}")
        print(f"   Formats: {', '.join(result.dataset.formats)}")
        print(f"   Relevance: {result.relevance_score:.2f}/1.00")
        print(f"   Match reason: {result.match_reason}")
        print()


async def scenario_2_serbian_query():
    """Scenario 2: User searches in Serbian."""
    print("\n" + "=" * 60)
    print("SCENARIO 2: Natural Language Search (Serbian)")
    print("=" * 60)
    print("User asks: 'Podaci o stanovništvu'\n")

    catalog = DatasetCatalog()
    from serbian_data_mcp.catalog.models import CachedDataset

    catalog.datasets["pop-001"] = CachedDataset(
        id="pop-001",
        title="Population by Age and Gender",
        description="Demographic data showing population distribution by age groups",
        organization="Statistical Office",
        formats=["xlsx"],
        tags=["population", "demographics", "age"],
    )

    # Search with Serbian term
    engine = SearchEngine(catalog)
    results = await engine.search("stanovništvo", max_results=5, min_score=0.3)

    print(f"Found {len(results)} result(s):\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.dataset.title}")
        print(f"   Match reason: {result.match_reason}")
        print(f"   Matched keywords: {', '.join(result.matched_keywords)}")
        print()


async def scenario_3_typo_handling():
    """Scenario 3: User makes a typo."""
    print("\n" + "=" * 60)
    print("SCENARIO 3: Fuzzy Matching (Typo Handling)")
    print("=" * 60)
    print("User types: 'populaton data' (typo: populaton)\n")

    catalog = DatasetCatalog()
    from serbian_data_mcp.catalog.models import CachedDataset

    catalog.datasets["pop-001"] = CachedDataset(
        id="pop-001",
        title="Population Statistics",
        description="Comprehensive population data for Serbia",
        organization="Statistical Office",
        formats=["xlsx"],
        tags=["population", "demographics"],
    )

    # Query expander handles typos
    expander = QueryExpander()

    query = "populaton"
    expanded = await expander.expand(query)

    print(f"Original query: '{query}'")
    print(f"Expanded terms: {expanded}")
    print()

    # Search with expanded terms
    engine = SearchEngine(catalog)
    results = await engine.search(query, max_results=5, min_score=0.3)

    print(f"Found {len(results)} result(s) despite typo:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.dataset.title}")
        print(f"   Match reason: {result.match_reason}")
        print()


async def scenario_4_alternative_suggestions():
    """Scenario 4: No exact match, suggest alternatives."""
    print("\n" + "=" * 60)
    print("SCENARIO 4: Alternative Suggestions")
    print("=" * 60)
    print("User asks: 'xyz123 nonexistent topic'\n")

    catalog = DatasetCatalog()
    from serbian_data_mcp.catalog.models import CachedDataset

    # Add various datasets
    catalog.datasets["budg-001"] = CachedDataset(
        id="budg-001",
        title="Government Budget 2024",
        description="Annual budget execution report",
        organization="Ministry of Finance",
        formats=["xlsx"],
        tags=["budget", "finance"],
    )
    catalog.datasets["health-001"] = CachedDataset(
        id="health-001",
        title="Healthcare Statistics",
        description="Public health indicators",
        organization="Ministry of Health",
        formats=["json"],
        tags=["health", "medical"],
    )
    catalog.datasets["edu-001"] = CachedDataset(
        id="edu-001",
        title="Education Enrollment",
        description="School enrollment data",
        organization="Ministry of Education",
        formats=["csv"],
        tags=["education", "schools"],
    )

    # Search returns no results
    engine = SearchEngine(catalog)
    results = await engine.search("xyz123", max_results=5, min_score=0.3)

    print(f"Exact matches: {len(results)}")

    # Alternative suggestions
    engine = SearchEngine(catalog)
    suggester = AlternativeSuggestions(catalog, engine)
    suggestion = await suggester.suggest("xyz123", max_alternatives=3)

    print(f"\n{suggestion.explanation}\n")

    for i, result in enumerate(suggestion.datasets, 1):
        print(f"{i}. {result.dataset.title}")
        print(f"   Why: {result.match_reason}")
        print(f"   Tags: {', '.join(result.dataset.tags)}")
        print()


async def scenario_5_dataset_preview():
    """Scenario 5: User previews dataset before downloading."""
    print("\n" + "=" * 60)
    print("SCENARIO 5: Dataset Preview")
    print("=" * 60)
    print("User asks: 'Show me preview of dataset pop-001'\n")

    from serbian_data_mcp.catalog.preview import DatasetPreview
    from serbian_data_mcp.catalog.models import CachedDataset

    # Create catalog with sample dataset
    catalog = DatasetCatalog()
    dataset = CachedDataset(
        id="pop-001",
        title="Population by Age",
        description="Demographic data by age groups",
        organization="Statistical Office",
        formats=["csv"],
        tags=["population", "demographics"],
        has_downloadable=True,
    )
    catalog.datasets["pop-001"] = dataset

    # Preview the dataset
    previewer = DatasetPreview(catalog)
    preview = await previewer.preview_dataset("pop-001", nrows=5)

    print(f"Dataset: {preview['metadata']['title']}")
    print(f"Organization: {preview['metadata']['organization']}")
    print(f"Formats: {', '.join(preview['metadata']['formats'])}")
    print(f"Tags: {', '.join(preview['metadata']['tags'])}")
    print(f"Has Downloadable: {preview['metadata']['has_downloadable']}")
    print(f"\nPreview Status: {preview['preview_reason']}")

    if preview["sample_data"]:
        print(f"\nSample Data (first {len(preview['sample_data'])} rows):")
        print(f"Columns: {', '.join(preview['columns'] or [])}")
    print()


async def scenario_6_bilingual_expansion():
    """Scenario 6: Query expansion demonstration."""
    print("\n" + "=" * 60)
    print("SCENARIO 6: Bilingual Query Expansion")
    print("=" * 60)

    expander = QueryExpander()

    test_queries = [
        ("population", "English term"),
        ("stanovništvo", "Serbian term"),
        ("budget", "English term"),
        ("budžet", "Serbian term"),
    ]

    for query, description in test_queries:
        expanded = await expander.expand(query)
        print(f"\n{description}: '{query}'")
        print(f"  Expanded to: {expanded}")


async def main():
    """Run all scenarios."""
    print("\n" + "=" * 60)
    print("INTELLIGENT MCP SERVER - REAL USER SCENARIOS")
    print("=" * 60)

    await scenario_1_english_query()
    await scenario_2_serbian_query()
    await scenario_3_typo_handling()
    await scenario_4_alternative_suggestions()
    await scenario_5_dataset_preview()
    await scenario_6_bilingual_expansion()

    print("\n" + "=" * 60)
    print("All scenarios completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

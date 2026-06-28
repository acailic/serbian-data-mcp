"""Search and discovery tools for data.gov.rs.

Contracts:
  - search_datasets(query, ...) → SearchResult dict (live API, filtered)
  - intelligent_search(query, ...) → semantically-ranked catalog hits (cached, fast)
  - preview_dataset(dataset_id) → metadata + first N rows (inspect before download)
  - list_organizations(page_size, page) → organizations list
"""

from __future__ import annotations

import contextlib
from typing import Any, Optional

from fastmcp.exceptions import ToolError

from .. import mcp
from ..api.models import Dataset
from ..catalog import AlternativeSuggestions, DatasetPreview, SearchEngine
from ..catalog.exceptions import DatasetNotFound
from . import _helpers as h


@mcp.tool()
async def search_datasets(
    query: str = "",
    format: Optional[str] = None,
    organization: Optional[str] = None,
    page_size: int = 10,
    page: int = 1,
) -> dict[str, Any]:
    """Search data.gov.rs datasets. ALWAYS call this first — never guess dataset IDs.

    Returns dataset IDs needed for get_dataset(). Serbian and English both work
    (e.g. 'stanovništvo' or 'population', 'budžet' or 'budget').

    Returns: {datasets: [{id, title, organization, resources, tags, ...}], total, page, page_size, has_next}

    Next steps:
      - get_dataset(id) for full details
      - get_resource_data(resource_id) to download data

    Args:
        query: Search terms (empty = newest datasets). Serbian or English.
        format: Filter by format: json, csv, xlsx, xls, xml
        organization: Filter by org ID (get from list_organizations)
        page_size: Results per page (1-100, default 10)
        page: Page number (1-indexed)
    """
    client = await h.get_client()
    try:
        result = await client.search_datasets(
            query=query,
            format=format,
            organization=organization,
            page_size=min(max(page_size, 1), 100),
            page=max(page, 1),
        )
        return h.search_result_to_dict(result)
    except Exception as e:
        raise ToolError(f"Search failed: {e}") from e


@mcp.tool()
async def list_organizations(page_size: int = 50, page: int = 1) -> dict[str, Any]:
    """List publishers on data.gov.rs. Use returned IDs to filter search_datasets().

    Key orgs: РЗС (statistics), Министарство финансија (budget), Завод за јавно здравље (health).

    Returns: {organizations: [{id, name, description, url, logo}], count, page, page_size}

    Args:
        page_size: Results per page (1-100, default 50)
        page: Page number (1-indexed)
    """
    client = await h.get_client()
    try:
        orgs = await client.list_organizations(page_size=min(max(page_size, 1), 100), page=max(page, 1))
        return {
            "organizations": [h.org_to_dict(org) for org in orgs],
            "count": len(orgs),
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        raise ToolError(f"Failed to list organizations: {e}") from e


@mcp.tool()
async def suggest_datasets(query: str, format: Optional[str] = None, size: int = 10) -> dict[str, Any]:
    """Autocomplete dataset titles. Use when unsure of exact Serbian terms.

    Example: suggest_datasets("stanov") → ["Stanovništvo Republike Srbije", ...]

    Args:
        query: Partial text (2+ chars recommended)
        format: Optional format filter: json, csv, xlsx, xls, xml
        size: Suggestions to return (1-20, default 10)
    """
    client = await h.get_client()
    try:
        suggestions = await client.suggest_datasets(query, format=format, size=min(max(size, 1), 20))
        return {"suggestions": suggestions, "count": len(suggestions)}
    except Exception as e:
        raise ToolError(f"Suggestions failed: {e}") from e


@mcp.tool()
async def search_by_tag(tags: list[str], page_size: int = 10, page: int = 1) -> dict[str, Any]:
    """Find all datasets tagged with specific topics regardless of publisher.

    Common tags: "statistika", "budžet", "obrazovanje", "zdravlje", "saobraćaj",
    "cene", "registar", "ekologija", "stanovništvo".

    Returns: Same shape as search_datasets().

    Args:
        tags: Tag strings to search (joined as query)
        page_size: Results per page (1-100, default 10)
        page: Page number (1-indexed)
    """
    client = await h.get_client()
    try:
        tag_query = " ".join(tags)
        result = await client.search_datasets(query=tag_query, page_size=min(max(page_size, 1), 100), page=max(page, 1))
        return h.search_result_to_dict(result)
    except Exception as e:
        raise ToolError(f"Tag search failed: {e}") from e


@mcp.tool()
async def get_portal_statistics() -> dict[str, Any]:
    """Get dataset and organization counts for the portal overview."""
    client = await h.get_client()
    total = 0
    total_orgs = 0
    with contextlib.suppress(Exception):
        data = await client._request("GET", "/api/1/datasets/", params={"rows": 1})
        total = data.get("total", 0)
    with contextlib.suppress(Exception):
        org_data = await client._request("GET", "/api/1/organizations/", params={"rows": 1})
        total_orgs = org_data.get("total", 0)
    return {
        "total_datasets": total,
        "total_organizations": total_orgs,
        "api_base": client.base_url,
        "portal_url": "https://data.gov.rs",
    }


@mcp.tool()
async def intelligent_search(
    query: str, suggest_alternatives: bool = True, max_results: int = 10, min_score: float = 0.3
) -> dict[str, Any]:
    """Search datasets with semantic understanding and fallback suggestions (RECOMMENDED).

    Uses the cached local catalog for fast results without API rate limits.
    Expands queries with synonyms and Serbian↔English translations, and offers
    related-dataset suggestions when no exact match is found.

    Prefer this over search_datasets() unless you need live API results or
    organization/format filters.

    Example:
        intelligent_search("population by age")
        intelligent_search("stanovništvo")
        intelligent_search("budžet", suggest_alternatives=True)

    Returns: {results: [...], total_found, query, expanded_terms} and, when no
    match is found and suggest_alternatives=True, {suggestions, note}.

    Args:
        query: Search query (Serbian or English both work)
        suggest_alternatives: If True, suggest related datasets when no exact match
        max_results: Maximum results (1-50, default 10)
        min_score: Minimum relevance score 0.0-1.0 (default 0.3)
    """
    max_results = min(max(max_results, 1), 50)
    try:
        catalog = await h.get_catalog()
        search_engine = SearchEngine(catalog)
        results = await search_engine.search(query, max_results=max_results, min_score=min_score)
        response: dict[str, Any] = {
            "results": [r.to_dict() for r in results],
            "total_found": len(results),
            "query": query,
            "expanded_terms": await search_engine.query_expander.expand(query),
        }
        if not results and suggest_alternatives:
            suggestions = AlternativeSuggestions(catalog, search_engine)
            suggestion_result = await suggestions.suggest(query, max_alternatives=max_results)
            response["suggestions"] = suggestion_result.to_dict()
            response["note"] = "No exact match found. See 'suggestions' for related datasets."
        return response
    except Exception as e:
        raise ToolError(f"Intelligent search failed: {e}") from e


@mcp.tool()
async def preview_dataset(dataset_id: str, nrows: int = 10) -> dict[str, Any]:
    """Show dataset metadata with a data preview (first N rows) before downloading.

    Use this BEFORE get_resource_data() to understand structure cheaply. Reads
    metadata and sample rows from the first downloadable resource.

    Workflow:
      1. intelligent_search() → find dataset_id
      2. preview_dataset(dataset_id) → understand structure
      3. get_resource_data(resource_id) → download full data if useful

    Returns: {metadata, sample_data, columns, preview_reason}

    Args:
        dataset_id: Dataset identifier (from intelligent_search or search_datasets)
        nrows: Rows to preview (1-100, default 10)
    """
    nrows = min(max(nrows, 1), 100)
    try:
        catalog = await h.get_catalog()
        preview = DatasetPreview(catalog)
        return await preview.preview_dataset(dataset_id, nrows=nrows)
    except DatasetNotFound as e:
        raise ToolError(f"Dataset '{dataset_id}' not found in catalog. Try intelligent_search() to find it.") from e
    except Exception as e:
        raise ToolError(f"Preview failed: {str(e)[:200]}") from e

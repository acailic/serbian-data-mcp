"""Search and discovery tools for data.gov.rs.

Contracts:
  - search_datasets(query, ...) → SearchResult dict
  - list_organizations(page_size, page) → organizations list
"""

from __future__ import annotations

from typing import Any, Optional

from fastmcp.exceptions import ToolError

from .. import mcp
from ..api.models import Dataset
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
    try:
        data = await client._request("GET", "/api/1/datasets/", params={"rows": 1})
        total = data.get("total", 0)
    except Exception:
        pass
    try:
        org_data = await client._request("GET", "/api/1/organizations/", params={"rows": 1})
        total_orgs = org_data.get("total", 0)
    except Exception:
        pass
    return {
        "total_datasets": total,
        "total_organizations": total_orgs,
        "api_base": client.base_url,
        "portal_url": "https://data.gov.rs",
    }

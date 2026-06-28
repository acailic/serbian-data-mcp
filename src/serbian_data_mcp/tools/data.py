"""Data retrieval tools for data.gov.rs.

Contracts:
  - get_dataset(dataset_id, detail_level) → full metadata, resources, or data preview
  - get_resource_data(resource_id) → parsed data (list of dicts)
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastmcp.exceptions import ToolError

from .. import mcp
from ..api.models import Dataset
from . import _helpers as h


def _dataset_summary(ds: Dataset) -> dict[str, Any]:
    """Build a comparison-friendly summary from a Dataset."""
    org_name = ds.organization.name if ds.organization else "N/A"
    formats = sorted({r.format for r in ds.resources if r.format})
    quality = getattr(ds, "quality", None) or {}
    return {
        "id": ds.id,
        "title": ds.title,
        "organization": org_name,
        "resource_count": len(ds.resources),
        "formats": formats,
        "tags": ds.tags[:10],
        "temporal_coverage": ds.temporal_coverage,
        "frequency": ds.frequency,
        "modified_at": ds.modified_at.isoformat() if ds.modified_at else None,
        "quality_score": quality.get("score") if isinstance(quality, dict) else None,
    }


@mcp.tool()
async def get_dataset(
    dataset_id: str,
    detail_level: str = "metadata",
) -> dict[str, Any]:
    """Get dataset details. detail_level controls response size.

    Levels:
      - "metadata" (default): Full details + resource list with IDs, formats, URLs.
        Use this to find resource_id for get_resource_data().
      - "resources": Just the resource list (id, title, format, size). Fastest.
      - "preview": Metadata + first 10 rows of data from first resource. Best for exploration.
      - "summary": Lightweight summary (title, org, format count, tags, modified date).

    Returns dataset dict. Resource IDs inside → use with get_resource_data(resource_id).

    Args:
        dataset_id: Dataset identifier from search_datasets()
        detail_level: One of: metadata, resources, preview, summary
    """
    client = await h.get_client()
    try:
        dataset = await client.get_dataset(dataset_id)
    except Exception as e:
        raise ToolError(f"Dataset '{dataset_id}' not found. Use search_datasets() to find valid IDs.") from e

    if dataset is None:
        raise ToolError(f"Dataset '{dataset_id}' not found. Use search_datasets() to find valid IDs.")

    if detail_level == "resources":
        return {
            "dataset_id": dataset.id,
            "dataset_title": dataset.title,
            "resources": [h.resource_to_dict(r) for r in dataset.resources],
            "count": len(dataset.resources),
        }

    if detail_level == "summary":
        return _dataset_summary(dataset)

    if detail_level == "preview":
        result: dict[str, Any] = h.dataset_to_dict(dataset)
        if dataset.resources:
            try:
                data = await client.get_resource_data(dataset.resources[0].id)
                if isinstance(data, pd.DataFrame):
                    preview_df = data.head(10)
                    result["preview_data"] = preview_df.to_dict(orient="records")
                    result["preview_columns"] = list(preview_df.columns)
                    result["preview_rows"] = len(data)
            except Exception as e:
                result["preview_error"] = str(e)[:200]
        else:
            result["preview_error"] = "No downloadable resources"
        return result

    # Default: full metadata
    return h.dataset_to_dict(dataset)


@mcp.tool()
async def get_resource_data(resource_id: str) -> dict[str, Any]:
    """Download and parse a data file from data.gov.rs.

    Parses JSON, CSV, XLSX, XLS, and XML automatically.
    Resource IDs come from get_dataset(detail_level="metadata").

    Returns: {data: [row_dicts], columns: [...], rows: N} for tabular data.
             Or {data: <parsed_content>} for JSON/XML.

    Next: use data_profile() to understand columns, then transform or visualize.

    Args:
        resource_id: Resource identifier from get_dataset() resources list
    """
    client = await h.get_client()
    try:
        data = await client.get_resource_data(resource_id)
        if isinstance(data, pd.DataFrame):
            return h.dataframe_to_dict(data)
        if isinstance(data, (dict, list)):
            return {"data": data}
        return {"data": str(data)}
    except Exception as e:
        raise ToolError(f"Failed to download resource '{resource_id}': {e}") from e


@mcp.tool()
async def compare_datasets(dataset_id_1: str, dataset_id_2: str) -> dict[str, Any]:
    """Compare two datasets side by side. Helps choose the best dataset for analysis.

    Shows differences in publisher, tags, resource count, formats, quality.

    Args:
        dataset_id_1: First dataset ID (from search_datasets)
        dataset_id_2: Second dataset ID (from search_datasets)
    """
    client = await h.get_client()
    try:
        ds1 = await client.get_dataset(dataset_id_1)
    except Exception:
        raise ToolError(f"Dataset '{dataset_id_1}' not found")
    try:
        ds2 = await client.get_dataset(dataset_id_2)
    except Exception:
        raise ToolError(f"Dataset '{dataset_id_2}' not found")
    if ds1 is None:
        raise ToolError(f"Dataset '{dataset_id_1}' not found")
    if ds2 is None:
        raise ToolError(f"Dataset '{dataset_id_2}' not found")

    s1, s2 = _dataset_summary(ds1), _dataset_summary(ds2)
    return {
        "dataset_1": s1,
        "dataset_2": s2,
        "comparison": {
            "same_organization": s1["organization"] == s2["organization"],
            "resource_count_diff": s1["resource_count"] - s2["resource_count"],
            "shared_formats": list(set(s1["formats"]) & set(s2["formats"])),
            "unique_formats_1": list(set(s1["formats"]) - set(s2["formats"])),
            "unique_formats_2": list(set(s2["formats"]) - set(s1["formats"])),
            "shared_tags": list(set(s1["tags"]) & set(s2["tags"])),
        },
    }


@mcp.tool()
async def browse_recent_datasets(days: int = 7, page_size: int = 20) -> dict[str, Any]:
    """Discover newly added/updated datasets. Returns most recently modified first.

    Args:
        days: Look-back window (1-365, default 7)
        page_size: Results to return (1-100, default 20)
    """
    from datetime import datetime, UTC

    client = await h.get_client()
    days = min(max(days, 1), 365)
    page_size = min(max(page_size, 1), 100)
    result = await client.search_datasets(query="", page_size=page_size, page=1)
    now = datetime.now(UTC)
    cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)

    recent = [
        ds
        for ds in result.datasets
        if (ds.modified_at and ds.modified_at >= cutoff) or (ds.created_at and ds.created_at >= cutoff)
    ]
    return {
        "datasets": [h.dataset_to_dict(ds) for ds in recent],
        "total_returned": len(recent),
        "days_back": days,
        "queried_at": now.isoformat(),
    }


@mcp.tool()
async def get_dataset_resources(dataset_id: str) -> dict[str, Any]:
    """List the data files (resources) available for a specific dataset.

    Use this before get_resource_data() to discover:
      - Resource IDs (required by get_resource_data)
      - Available formats (json, csv, xlsx, xls, xml)
      - File descriptions and sizes
      - Direct download URLs

    Equivalent to get_dataset(detail_level="resources"), exposed as its own
    tool for callers that only need the file listing.

    Args:
        dataset_id: Dataset identifier from search_datasets()
    """
    client = await h.get_client()
    try:
        dataset = await client.get_dataset(dataset_id)
    except Exception as e:
        raise ToolError(f"Dataset '{dataset_id}' not found. Use search_datasets() to find valid IDs.") from e
    if dataset is None:
        raise ToolError(f"Dataset '{dataset_id}' not found. Use search_datasets() to find valid IDs.")
    return {
        "dataset_id": dataset.id,
        "dataset_title": dataset.title,
        "resources": [h.resource_to_dict(r) for r in dataset.resources],
        "count": len(dataset.resources),
    }


@mcp.tool()
async def get_data_summary(resource_id: str) -> dict[str, Any]:
    """Quick schema summary of a resource's data without downloading the full file.

    Returns column names, dtypes, row count, and sample values for the first
    few rows. Much faster than get_resource_data() for large XLSX/CSV files
    where you only need to know the schema.

    Workflow:
        1. get_dataset_resources(dataset_id) → find resource_id
        2. get_data_summary(resource_id) → understand structure
        3. get_resource_data(resource_id) → download full data if useful
        4. data_profile(data) → detailed stats after download

    Args:
        resource_id: Resource identifier from a dataset's resources list

    Returns: Dict with 'columns' (list of {name, dtype, sample_values}),
             'estimated_rows', 'format', 'resource_id'.
    """
    client = await h.get_client()
    try:
        data = await client.get_resource_data(resource_id)
    except Exception as e:
        raise ToolError(f"Failed to summarize resource '{resource_id}': {e}") from e

    if isinstance(data, pd.DataFrame):
        df = data.head(20)
        columns = [
            {
                "name": col,
                "dtype": str(df[col].dtype),
                "sample_values": df[col].dropna().head(5).tolist(),
            }
            for col in df.columns
        ]
        return {
            "columns": columns,
            "estimated_rows": len(data),
            "format": "tabular",
            "resource_id": resource_id,
        }

    if isinstance(data, dict):
        top_keys = list(data.keys())[:20]
        sample: dict[str, Any] = {}
        for k in top_keys:
            val = data[k]
            if isinstance(val, list):
                sample[k] = {"type": "list", "length": len(val), "first_items": val[:3]}
            elif isinstance(val, dict):
                sample[k] = {"type": "dict", "keys": list(val.keys())[:10]}
            else:
                sample[k] = val
        return {
            "columns": [{"name": k, "dtype": "key", "sample_values": None} for k in top_keys],
            "estimated_rows": "N/A (dict structure)",
            "format": "json-dict",
            "sample": sample,
            "resource_id": resource_id,
        }

    if isinstance(data, list) and data:
        sample_items = data[:5]
        if isinstance(sample_items[0], dict):
            columns = [
                {
                    "name": col,
                    "dtype": type(sample_items[0][col]).__name__,
                    "sample_values": [item.get(col) for item in sample_items if col in item][:5],
                }
                for col in sample_items[0]
            ]
            return {
                "columns": columns,
                "estimated_rows": len(data),
                "format": "json-list",
                "resource_id": resource_id,
            }
        return {
            "columns": [],
            "estimated_rows": len(data),
            "format": "json-list-scalar",
            "sample": sample_items[:3],
            "resource_id": resource_id,
        }

    raise ToolError(f"Unexpected data type for resource '{resource_id}': {type(data).__name__}")

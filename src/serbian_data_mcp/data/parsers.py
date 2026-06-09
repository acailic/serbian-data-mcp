"""Parse data from various formats."""

from typing import Any, Union
import json
import io

import pandas as pd
import httpx


async def parse_resource(response: httpx.Response, format: str) -> Union[pd.DataFrame, dict, list]:
    """Parse resource data based on format.

    Args:
        response: HTTP response with data
        format: File format (json, csv, xlsx, xml)

    Returns:
        Parsed data as DataFrame, dict, or list
    """
    content = response.content

    if format == "json":
        return await parse_json(content)
    elif format == "csv":
        return await parse_csv(content)
    elif format in ("xlsx", "xls", "excel"):
        return await parse_excel(content)
    elif format == "xml":
        # Return as text for XML (would need lxml for full parsing)
        return content.decode("utf-8")
    else:
        # Try to parse as JSON by default
        try:
            return await parse_json(content)
        except:
            return content.decode("utf-8", errors="replace")


async def parse_csv(content: bytes) -> pd.DataFrame:
    """Parse CSV data.

    Args:
        content: CSV file content as bytes

    Returns:
        DataFrame with parsed data
    """
    # Handle UTF-8 BOM and different encodings
    try:
        return pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            return pd.read_csv(io.BytesIO(content), encoding="latin1")
        except:
            return pd.read_csv(io.BytesIO(content), encoding="utf-8", errors="replace")


async def parse_json(content: bytes) -> Union[dict, list]:
    """Parse JSON data.

    Args:
        content: JSON file content as bytes

    Returns:
        Parsed JSON as dict or list
    """
    text = content.decode("utf-8")
    return json.loads(text)


async def parse_excel(content: bytes) -> pd.DataFrame:
    """Parse Excel data.

    Args:
        content: Excel file content as bytes

    Returns:
        DataFrame with parsed data
    """
    return pd.read_excel(io.BytesIO(content))

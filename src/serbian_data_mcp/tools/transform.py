"""Data transformation tools.

Contracts:
  - transform_data(data, operation, ...) → transformed data dict
"""

from __future__ import annotations

from typing import Any

from fastmcp.exceptions import ToolError

from .. import mcp
from ..data.transformers import aggregate_data, filter_data, group_data, select_columns, sort_data
from . import _helpers as h


@mcp.tool()
async def transform_data(
    data: list[dict[str, Any]],
    operation: str,
    column: str = "",
    columns: list[str] | None = None,
    group_by: str | list[str] | None = None,
    aggregations: dict[str, str] | None = None,
    function: str = "sum",
    ascending: bool = True,
) -> dict[str, Any]:
    """Transform data: filter, group, aggregate, sort, or select columns.

    Operations:
      - "filter": Keep rows matching criteria. Requires 'column' + value in 'filters' param.
        Example: operation="filter", column="godina", filters={"godina": "2023"}
        Comparison operators: {"column": {"$gt": 100}}, supports: $gt, $gte, $lt, $lte, $eq, $ne, $in, $not_in
      - "group": Group by column(s) with optional aggregations.
        Example: operation="group", group_by="category", aggregations={"value": "sum"}
        Aggregation functions: sum, mean, median, min, max, count, std, var
      - "aggregate": Single column aggregate.
        Example: operation="aggregate", column="population", function="mean"
      - "sort": Sort rows by column(s).
        Example: operation="sort", column="population", ascending=False
      - "select": Keep only specified columns.
        Example: operation="select", columns=["godina", "stanovnistvo"]

    Args:
        data: Row dicts from get_resource_data()
        operation: One of: filter, group, aggregate, sort, select
        column: Primary column for filter/sort/aggregate
        columns: Column list for select
        group_by: Column(s) for group
        aggregations: {column: agg_func} for group
        function: Aggregation function for aggregate (sum, mean, median, min, max, count, std, var)
        ascending: Sort direction
    """
    try:
        if operation == "filter":
            result = filter_data(data, {column: True})
            return h.dataframe_to_dict(result)

        if operation == "group":
            if not group_by:
                raise ToolError("Group operation requires 'group_by' parameter")
            result = group_data(data, group_by, aggregations)
            return h.dataframe_to_dict(result)

        if operation == "aggregate":
            if not column:
                raise ToolError("Aggregate operation requires 'column' parameter")
            value = aggregate_data(data, column, function)
            if value is not None:
                import numpy as np

                if isinstance(value, (np.integer,)):
                    value = int(value)
                elif isinstance(value, (np.floating,)):
                    value = float(value)
            return {"value": value, "column": column, "function": function}

        if operation == "sort":
            if not column:
                raise ToolError("Sort operation requires 'column' parameter")
            result = sort_data(data, column, ascending)
            return h.dataframe_to_dict(result)

        if operation == "select":
            if not columns:
                raise ToolError("Select operation requires 'columns' parameter")
            result = select_columns(data, columns)
            return h.dataframe_to_dict(result)

        raise ToolError(f"Unknown operation '{operation}'. Use: filter, group, aggregate, sort, select")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Transform failed ({operation}): {e}") from e


@mcp.tool()
async def filter_data_tool(
    data: list[dict[str, Any]],
    filters: dict[str, Any],
) -> dict[str, Any]:
    """Filter rows by criteria. Shorthand for transform_data(operation='filter').

    Patterns:
      - Exact match: {"column": "value"}
      - Comparison: {"column": {"$gt": 100}}
      - Operators: $gt, $gte, $lt, $lte, $eq, $ne, $in, $not_in

    Args:
        data: Row dicts from get_resource_data()
        filters: Column → value or column → {operator: value}
    """
    try:
        result = filter_data(data, filters)
        return h.dataframe_to_dict(result)
    except Exception as e:
        raise ToolError(f"Filter failed: {e}") from e

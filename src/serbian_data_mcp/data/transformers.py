"""Data transformation utilities."""

import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


def filter_data(data: Union[pd.DataFrame, List[Dict[str, Any]]], filters: Dict[str, Any]) -> pd.DataFrame:
    """Filter data based on criteria.

    Args:
        data: DataFrame or list of dictionaries
        filters: Dictionary of column: value pairs for filtering

    Returns:
        Filtered DataFrame
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    for column, value in filters.items():
        if column in df.columns:
            if isinstance(value, (list, tuple)):
                df = df[df[column].isin(value)]
            elif isinstance(value, dict):
                # Handle operators like {'>=': 10, '<=': 20}
                for op, val in value.items():
                    if op == ">=":
                        df = df[df[column] >= val]
                    elif op == "<=":
                        df = df[df[column] <= val]
                    elif op == ">":
                        df = df[df[column] > val]
                    elif op == "<":
                        df = df[df[column] < val]
                    elif op == "==":
                        df = df[df[column] == val]
                    elif op == "!=":
                        df = df[df[column] != val]
                    elif op == "in":
                        df = df[df[column].isin(val)]
                    elif op == "not_in":
                        df = df[~df[column].isin(val)]
            else:
                df = df[df[column] == value]

    return df


def group_data(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
    group_by: Union[str, List[str]],
    aggregations: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """Group data by columns.

    Args:
        data: DataFrame or list of dictionaries
        group_by: Column name(s) to group by
        aggregations: Optional dict of {column: aggregation_function}

    Returns:
        Grouped DataFrame
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    if isinstance(group_by, str):
        group_by = [group_by]

    if aggregations:
        agg_dict = {col: func for col, func in aggregations.items() if col in df.columns}
        grouped = df.groupby(group_by).agg(agg_dict)
    else:
        grouped = df.groupby(group_by).size().reset_index(name="count")

    return grouped.reset_index()


def aggregate_data(data: Union[pd.DataFrame, List[Dict[str, Any]]], column: str, function: str = "sum") -> Any:
    """Aggregate a column.

    Args:
        data: DataFrame or list of dictionaries
        column: Column name to aggregate
        function: Aggregation function (sum, mean, median, min, max, count)

    Returns:
        Aggregated value
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data

    if column not in df.columns:
        return None

    if function == "sum":
        return df[column].sum()
    elif function == "mean":
        return df[column].mean()
    elif function == "median":
        return df[column].median()
    elif function == "min":
        return df[column].min()
    elif function == "max":
        return df[column].max()
    elif function == "count":
        return df[column].count()
    elif function == "std":
        return df[column].std()
    elif function == "var":
        return df[column].var()
    else:
        return df[column].sum()


def sort_data(
    data: Union[pd.DataFrame, List[Dict[str, Any]]], by: Union[str, List[str]], ascending: bool = True
) -> pd.DataFrame:
    """Sort data.

    Args:
        data: DataFrame or list of dictionaries
        by: Column name(s) to sort by
        ascending: Sort order

    Returns:
        Sorted DataFrame
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    if isinstance(by, str):
        by = [by]

    return df.sort_values(by=by, ascending=ascending)


def select_columns(data: Union[pd.DataFrame, List[Dict[str, Any]]], columns: List[str]) -> pd.DataFrame:
    """Select specific columns.

    Args:
        data: DataFrame or list of dictionaries
        columns: Column names to select

    Returns:
        DataFrame with selected columns
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    available_cols = [col for col in columns if col in df.columns]
    return df[available_cols]


def pivot_table(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
    index: Union[str, List[str]],
    columns: str,
    values: str,
    aggfunc: str = "mean",
) -> pd.DataFrame:
    """Create a pivot table from data.

    Args:
        data: DataFrame or list of dictionaries
        index: Column name(s) to use as index
        columns: Column name to use as columns
        values: Column name to aggregate
        aggfunc: Aggregation function ('mean', 'sum', 'count', 'min', 'max')

    Returns:
        Pivot table as DataFrame
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    valid_funcs = {"mean", "sum", "count", "min", "max", "median", "std", "var"}
    if aggfunc not in valid_funcs:
        aggfunc = "mean"
        logger.warning("Unknown aggfunc, defaulting to 'mean'")

    try:
        result = df.pivot_table(index=index, columns=columns, values=values, aggfunc=aggfunc)
        return result.reset_index()
    except Exception as e:
        logger.error(f"Failed to create pivot table: {e}")
        raise


def rename_columns(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
    mapping: Dict[str, str],
) -> pd.DataFrame:
    """Rename columns using a mapping dict.

    Args:
        data: DataFrame or list of dictionaries
        mapping: Dictionary mapping old names to new names

    Returns:
        DataFrame with renamed columns
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    existing = {k: v for k, v in mapping.items() if k in df.columns}
    df = df.rename(columns=existing)
    logger.debug(f"Renamed {len(existing)} columns")
    return df


def drop_columns(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
    columns: List[str],
) -> pd.DataFrame:
    """Drop specified columns from data.

    Args:
        data: DataFrame or list of dictionaries
        columns: Column names to drop

    Returns:
        DataFrame with specified columns removed
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    cols_to_drop = [col for col in columns if col in df.columns]
    df = df.drop(columns=cols_to_drop)
    logger.debug(f"Dropped {len(cols_to_drop)} columns")
    return df


def head(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
    n: int = 5,
) -> pd.DataFrame:
    """Return first n rows.

    Args:
        data: DataFrame or list of dictionaries
        n: Number of rows to return

    Returns:
        DataFrame with first n rows
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data

    return df.head(n)


def tail(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
    n: int = 5,
) -> pd.DataFrame:
    """Return last n rows.

    Args:
        data: DataFrame or list of dictionaries
        n: Number of rows to return

    Returns:
        DataFrame with last n rows
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data

    return df.tail(n)


def describe_data(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
) -> pd.DataFrame:
    """Generate statistical summary of numeric columns.

    Args:
        data: DataFrame or list of dictionaries

    Returns:
        DataFrame with statistical summary (count, mean, std, min, 25%, 50%, 75%, max)
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data

    return df.describe()


def count_unique(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
    column: str,
) -> pd.DataFrame:
    """Count unique values in a column.

    Args:
        data: DataFrame or list of dictionaries
        column: Column name to count unique values for

    Returns:
        DataFrame with columns: the specified column name and 'count', sorted by count descending
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    if column not in df.columns:
        logger.warning(f"Column '{column}' not found in data")
        return pd.DataFrame(columns=[column, "count"])

    result = df[column].value_counts().reset_index()
    result.columns = [column, "count"]
    return result

"""Data transformation utilities."""

from typing import Any, Dict, List, Optional, Callable, Union
import pandas as pd


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

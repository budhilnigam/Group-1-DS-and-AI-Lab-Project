"""
pivot_operations.py

This module provides functions for performing pivot table operations
using pandas, including creating pivot tables, cross tabulations, and
pivoting with fill options and margin support.
"""

import pandas as pd
from pandas import DataFrame, PivotTable


def createPivot(data: DataFrame, index: list, columns: list, values: str, aggfunc: str = 'mean', margins: bool = False) -> PivotTable:
    """
    Create a pivot table from the given DataFrame.

    Parameters:
    data (DataFrame): The input data for pivoting.
    index (list): Column(s) to use as the index for the pivot table.
    columns (list): Column(s) to use as the columns for the pivot table.
    values (str): Column to aggregate.
    aggfunc (str): The aggregation function to apply (default is 'mean').
    margins (bool): Whether to add row/column margins (default is False).

    Returns:
    PivotTable: A pivot table as a DataFrame.
    """
    return pd.pivot_table(data, index=index, columns=columns, values=values, aggfunc=aggfunc, margins=margins)


def crossTabulation(data: DataFrame, rowVar: str, colVar: str, values: list = [], aggfunc: str = 'count', margins: bool = False) -> DataFrame:
    """
    Perform a cross tabulation of two variables.

    Parameters:
    data (DataFrame): The input data for cross tabulation.
    rowVar (str): The variable for rows.
    colVar (str): The variable for columns.
    values (list): Column to aggregate (optional).
    aggfunc (str): The aggregation function to apply (default is 'count').
    margins (bool): Whether to add row/column margins (default is False).

    Returns:
    DataFrame: A cross-tabulated DataFrame.
    """
    return pd.crosstab(data[rowVar], data[colVar], values=data[values] if values else None,
                       aggfunc=aggfunc, margins=margins)


def pivotAndFill(data: DataFrame, index: list, columns: list, values: str, fillValue: dict = {}, aggfunc: str = 'mean', margins: bool = False) -> DataFrame:
    """
    Create a pivot table and fill missing values.

    Parameters:
    data (DataFrame): The input data for pivoting.
    index (list): Column(s) to use as the index for the pivot table.
    columns (list): Column(s) to use as the columns for the pivot table.
    values (str): Column to aggregate.
    fillValue (dict): Value to fill missing data with (default is {}).
    aggfunc (str): The aggregation function to apply (default is 'mean').
    margins (bool): Whether to add row/column margins (default is False).

    Returns:
    DataFrame: A pivot table with filled missing values.
    """
    pivot_table = createPivot(data, index, columns, values, aggfunc, margins)
    return pivot_table.fillna(fillValue) if fillValue is not None else pivot_table
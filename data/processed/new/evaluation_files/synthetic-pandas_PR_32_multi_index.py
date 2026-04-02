"""
multi_index.py

This module provides functions to perform various operations on pandas MultiIndex objects.
The functions include creating a MultiIndex, extracting cross sections, performing level operations,
and resetting and setting indices.
"""

import pandas as pd
from pandas import MultiIndex
from typing import List, Tuple, Union

def createMultiIndex(levels: List[List[Union[str, int]]], labels: List[List[int]]) -> MultiIndex:
    """
    Create a MultiIndex from the provided levels and labels.

    Parameters:
    levels (List[List[Union[str, int]]]): A list of lists containing the unique values for each level.
    labels (List[List[int]]): A list of lists containing the corresponding labels for each level.

    Returns:
    MultiIndex: A MultiIndex object constructed from the given levels and labels.
    """
    return MultiIndex(levels=levels, labels=labels)


def crossSection(multi_index: MultiIndex, level: int, value: Union[str, int]) -> pd.DataFrame:
    """
    Extract a cross section from a MultiIndex DataFrame.

    Parameters:
    multi_index (MultiIndex): The MultiIndex to extract the cross section from.
    level (int): The level at which to extract the cross section.
    value (Union[str, int]): The value at the specified level to filter by.

    Returns:
    pd.DataFrame: A DataFrame containing the cross-section data.
    """
    return pd.DataFrame(index=multi_index).xs(value, level=level)


def level_operations(multiIndex: MultiIndex, level: int) -> Tuple[List[Union[str, int]], List[int]]:
    """
    Perform operations on a specific level of a MultiIndex.

    Parameters:
    multiIndex (MultiIndex): The MultiIndex to operate on.
    level (int): The level on which to perform operations.

    Returns:
    Tuple[List[Union[str, int]], List[int]]: A tuple containing unique values and their corresponding counts at the specified level.
    """
    unique_values = multiIndex.levels[level].tolist()
    counts = multiIndex.get_level_values(level).value_counts().reindex(unique_values, fill_value=0).tolist()
    return unique_values, counts


def reset_and_set_index(df: pd.DataFrame, new_index: List[str]) -> pd.DataFrame:
    """
    Reset the index of a DataFrame and set a new MultiIndex.

    Parameters:
    df (pd.DataFrame): The DataFrame to modify.
    new_index (List[str]): A list of column names to set as the new MultiIndex.

    Returns:
    pd.DataFrame: A DataFrame with the new MultiIndex set.
    """
    df_reset = df.reset_index(drop=True)
    return df_reset.set_index(new_index)
"""
categorical_data.py

This module provides functions for handling categorical data in pandas.
It includes operations for encoding categories, defining ordered categories,
and optimizing memory usage of categorical types.
"""

import pandas as pd
from typing import List, Union


def encodeCategories(data_frame: pd.DataFrame, column: str, categories: List[str]) -> pd.DataFrame:
    """
    Encodes a specified column in the DataFrame to a categorical type with given categories.

    Parameters:
        data_frame (pd.DataFrame): The DataFrame containing the data.
        column (str): The name of the column to be encoded.
        categories (List[str]): The list of categories to encode.

    Returns:
        pd.DataFrame: A DataFrame with the specified column encoded as a categorical type.
    """
    if column not in data_frame.columns:
        raise ValueError(f"Column '{column}' does not exist in the DataFrame.")

    data_frame[column] = pd.Categorical(data_frame[column], categories=categories)
    return data_frame


def orderedCategories(data_frame: pd.DataFrame, column: str, categories: List[str]) -> pd.DataFrame:
    """
    Converts a specified column in the DataFrame to an ordered categorical type.

    Parameters:
        data_frame (pd.DataFrame): The DataFrame containing the data.
        column (str): The name of the column to be converted.
        categories (List[str]): The list of categories to define the order.

    Returns:
        pd.DataFrame: A DataFrame with the specified column converted to an ordered categorical type.
    """
    if column not in data_frame.columns:
        raise ValueError(f"Column '{column}' does not exist in the DataFrame.")

    data_frame[column] = pd.Categorical(data_frame[column], categories=categories, ordered=True)
    return data_frame


def memoryOptimizeCategories(data_frame: pd.DataFrame) -> pd.DataFrame:
    """
    Optimizes the memory usage of all categorical columns in the DataFrame.

    Parameters:
        data_frame (pd.DataFrame): The DataFrame containing the data.

    Returns:
        pd.DataFrame: A DataFrame with optimized memory usage for categorical columns.
    """
    for column in data_frame.select_dtypes(include=['object']).columns:
        unique_values = data_frame[column].unique()
        data_frame[column] = pd.Categorical(data_frame[column], categories=unique_values)

    return data_frame


def main() -> None:
    """
    Example usage of the functions in the categorical_data module.
    """
    # Example DataFrame
    df = pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'gender': ['female', 'male', 'male', 'male', 'female'],
        'status': ['single', 'married', 'single', 'married', 'single']
    })

    # Encoding categories
    encoded_df = encodeCategories(df, 'gender', ['female', 'male'])
    print(encoded_df)

    # Ordered categories
    ordered_df = orderedCategories(df, 'status', ['single', 'married'])
    print(ordered_df)

    # Memory optimization
    optimized_df = memoryOptimizeCategories(df)
    print(optimized_df.info())


if __name__ == "__main__":
    main()
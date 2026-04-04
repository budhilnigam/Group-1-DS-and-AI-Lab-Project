"""Performance utilities for optimizing data processing in pandas DataFrames.

This module provides functions to optimize data types, process data in chunks,
report memory usage, and perform vectorized operations efficiently.
"""

import os
import sys
import re
import pandas as pd
import numpy as np
from typing import Callable, Dict, Tuple, Union


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
  """Optimize DataFrame dtypes to reduce memory usage.

  Args:
      df (pd.DataFrame): The DataFrame to optimize.

  Returns:
      pd.DataFrame: A DataFrame with optimized dtypes.
  """
  df_optimized = df.copy()
  for col in df_optimized.columns:
        if pd.api.types.is_integer_dtype(df_optimized[col]):
            df_optimized[col] = pd.to_numeric(df_optimized[col], downcast='integer')
        elif pd.api.types.is_float_dtype(df_optimized[col]):
            df_optimized[col] = pd.to_numeric(df_optimized[col], downcast='float')
        elif pd.api.types.is_object_dtype(df_optimized[col]):
            df_optimized[col] = df_optimized[col].astype('category')
  return df_optimized


def chunked_processing(
        df: pd.DataFrame,
        chunk_size: int,
        process_func: Callable[[pd.DataFrame], pd.DataFrame]
) -> pd.DataFrame:
      """Process DataFrame in chunks to manage memory usage.

      Args:
          df (pd.DataFrame): The DataFrame to process.
          chunk_size (int): Number of rows per chunk.
          process_func (Callable): Function to apply to each chunk.

      Returns:
          pd.DataFrame: A DataFrame resulting from processing all chunks.
      """
      chunks = [df[i:i + chunk_size] for i in range(0, df.shape[0], chunk_size)]
      processed_chunks = [process_func(chunk) for chunk in chunks]
      return pd.concat(processed_chunks, ignore_index=True)


def memory_usage_report(df: pd.DataFrame) -> Dict[str, Union[str, int]]:
    """Generate a report of memory usage for the DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame to analyze.

    Returns:
        Dict[str, Union[str, int]]: A dictionary with memory usage report.
    """
      memory_info = df.memory_usage(deep=True)
      total_memory = memory_info.sum()
      report = {
          'total_memory': total_memory,
          'memory_per_column': memory_info.to_dict(),
          'memory_usage_percentage': (total_memory / df.memory_usage(deep=True).sum()) * 100
      }
      return report


def vectorized_ops(df: pd.DataFrame, operations: Dict[str, Callable[[pd.Series], pd.Series]]) -> pd.DataFrame:
    """Apply a series of vectorized operations to DataFrame columns.

    Args:
        df (pd.DataFrame): The DataFrame to modify.
        operations (Dict[str, Callable]): A dictionary mapping column names to functions.

    Returns:
        pd.DataFrame: The DataFrame after applying operations.
    """
      for col, func in operations.items():
          if col in df.columns:
              df[col] = func(df[col])
      return df
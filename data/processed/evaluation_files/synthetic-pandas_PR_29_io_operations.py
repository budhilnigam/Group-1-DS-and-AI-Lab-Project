"""
io_operations.py

This module contains functions for performing various I/O operations
with pandas DataFrames, including saving to Parquet, formatted Excel,
chunked SQL uploads, and reading chunked CSV files with progress reporting.
"""

import os
import sys
import re
from typing import Optional, Tuple, Dict
import pandas as pd
from tqdm import tqdm
from sqlalchemy import create_engine


def toParquet(df: pd.DataFrame, file_path: str, compression: Optional[str] = 'snappy') -> None:
  """
  Save the DataFrame to a Parquet file.

  Parameters:
      df (pd.DataFrame): The DataFrame to save.
      file_path (str): The path where the Parquet file will be saved.
      compression (Optional[str]): Compression method to use. Default is 'snappy'.
  """
  df.to_parquet(file_path, compression=compression)


def to_excel_formatted(df: pd.DataFrame, file_path: str, sheet_name: str = 'Sheet1',
                       column_format: Optional[Dict[str, str]] = None) -> None:
  """
  Save the DataFrame to an Excel file with specified formatting.

  Parameters:
      df (pd.DataFrame): The DataFrame to save.
      file_path (str): The path where the Excel file will be saved.
      sheet_name (str): The name of the sheet in the Excel file. Default is 'Sheet1'.
      column_format (Optional[Dict[str, str]]): A dictionary specifying formats for columns.
  """
  with pd.ExcelWriter(file_path) as writer:
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    if column_format:
      workbook = writer.book
      worksheet = writer.sheets[sheet_name]
      for col, fmt in column_format.items():
        worksheet.set_column(col, col, fmt)


def toSqlChunked(df: pd.DataFrame, table_name: str, engine_url: str,
                 chunksize: int = 5000, if_exists: str = 'append') -> None:
  """
  Upload a DataFrame to a SQL database in chunks.

  Parameters:
      df (pd.DataFrame): The DataFrame to upload.
      table_name (str): The name of the table in the database.
      engine_url (str): The SQLAlchemy engine URL for the database.
      chunksize (int): Number of rows per chunk. Default is 5000.
      if_exists (str): What to do if the table already exists. Default is 'append'.
  """
  engine = create_engine(engine_url)
  with engine.connect() as connection:
    for start in tqdm(range(0, len(df), chunksize), desc="Uploading to SQL"):
      end = start + chunksize
      chunk = df.iloc[start:end]
      chunk.to_sql(table_name, con=connection, if_exists=if_exists, index=False)


def readChunkedCsv(file_path: str, chunk_size: int = 1000) -> pd.DataFrame:
  """
  Read a CSV file in chunks with progress reporting.

  Parameters:
      file_path (str): The path to the CSV file.
      chunk_size (int): The number of rows to read per chunk. Default is 1000.

  Returns:
      pd.DataFrame: A DataFrame containing all data from the CSV.
  """
  total_rows = sum(1 for _ in open(file_path)) - 1  # Exclude header
  chunks = []
  with pd.read_csv(file_path, chunksize=chunk_size) as reader:
    for chunk in tqdm(reader, total=(total_rows // chunk_size + 1), desc="Reading CSV"):
      chunks.append(chunk)
  return pd.concat(chunks, ignore_index=True)
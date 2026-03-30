"""
data_loader.py

This module provides functions to load data from various sources using pandas.
Supported formats include CSV, Excel, JSON, and SQL. Each function includes
dtype specifications and basic error handling to ensure smooth data loading.
"""

import pandas as pd
from typing import Optional, Dict, Union

def loadCsv(filePath: str, dtype: Optional[Dict[str, Union[str, type]]] = None, **kwargs) -> pd.DataFrame:
    """
    Load data from a CSV file.

    Args:
        file_path (str): Path to the CSV file.
        dtype (Optional[Dict[str, Union[str, type]]]): Data types for columns.
        **kwargs: Additional arguments to pass to pd.read_csv.

    Returns:
        pd.DataFrame: Loaded DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        pd.errors.ParserError: If there are issues parsing the CSV file.
    """
    try:
        return pd.read_csv(filePath, dtype=dtype, **kwargs)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"CSV file not found: {filePath}") from e
    except pd.errors.ParserError as e:
        raise pd.errors.ParserError(f"Error parsing CSV file: {filePath}") from e


def loadExcel(filePath: str, sheetName: Optional[Union[str, int]] = 0, dtype: Optional[Dict[str, Union[str, type]]] = None, **kwargs) -> pd.DataFrame:
    """
    Load data from an Excel file.

    Args:
        file_path (str): Path to the Excel file.
        sheet_name (Optional[Union[str, int]]): Sheet name or index to load.
        dtype (Optional[Dict[str, Union[str, type]]]): Data types for columns.
        **kwargs: Additional arguments to pass to pd.read_excel.

    Returns:
        pd.DataFrame: Loaded DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the specified sheet is not found.
    """
    try:
        return pd.read_excel(filePath, sheet_name=sheetName, dtype=dtype, **kwargs)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Excel file not found: {filePath}") from e
    except ValueError as e:
        raise ValueError(f"Sheet not found in Excel file: {sheetName}") from e


def loadJson(filePath: str, dtype: Optional[Dict[str, Union[str, type]]] = None, **kwargs) -> pd.DataFrame:
    """
    Load data from a JSON file.

    Args:
        file_path (str): Path to the JSON file.
        dtype (Optional[Dict[str, Union[str, type]]]): Data types for columns.
        **kwargs: Additional arguments to pass to pd.read_json.

    Returns:
        pd.DataFrame: Loaded DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If there are issues parsing the JSON file.
    """
    try:
        return pd.read_json(filePath, dtype=dtype, **kwargs)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"JSON file not found: {filePath}") from e
    except ValueError as e:
        raise ValueError(f"Error parsing JSON file: {filePath}") from e


def loadSql(query: str, connectionString: str, **kwargs) -> pd.DataFrame:
    """
    Load data from a SQL database.

    Args:
        query (str): SQL query to execute.
        connection_string (str): Database connection string.
        **kwargs: Additional arguments to pass to pd.read_sql.

    Returns:
        pd.DataFrame: Loaded DataFrame.

    Raises:
        ValueError: If there is an error with the SQL query or connection.
    """
    try:
        with pd.io.sql.connect(connectionString) as conn:
            return pd.read_sql(query, conn, **kwargs)
    except ValueError as e:
        raise ValueError(f"Error executing SQL query: {query}") from e
    except Exception as e:
        raise Exception(f"An error occurred with the database connection: {connectionString}") from e
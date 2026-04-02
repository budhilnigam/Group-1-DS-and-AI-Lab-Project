"""
visualization.py

This module provides helper functions for visualizing data from pandas DataFrames
using Matplotlib. It includes functions to plot distributions, correlation matrices,
and time series data.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
import sys
import re
from typing import Optional, Union

def plotDistribution(data: pd.Series, title: str = "Distribution Plot",
                     xlabel: str = "Values", ylabel: str = "Frequency",
                     bins: Optional[int] = None) -> None:
    """
    Plots the distribution of a pandas Series.

    Parameters:
        data (pd.Series): The data to plot.
        title (str): The title of the plot.
        xlabel (str): The label for the x-axis.
        ylabel (str): The label for the y-axis.
        bins (Optional[int]): The number of bins for the histogram.
    """
  plt.figure(figsize=(10, 6))
  sns.histplot(data, bins=bins, kde=True)
  plt.title(title)
  plt.xlabel(xlabel)
  plt.ylabel(ylabel)
  plt.grid()
  plt.show()

def plotCorrelationMatrix(df: pd.DataFrame, title: str = "Correlation Matrix",
                          cmap: str = "coolwarm") -> None:
    """
    Plots the correlation matrix for a pandas DataFrame.

    Parameters:
        df (pd.DataFrame): The DataFrame to analyze.
        title (str): The title of the plot.
        cmap (str): The colormap to use for the heatmap.
    """
    plt.figure(figsize=(12, 8))
    correlation_matrix = df.corr()
    sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap=cmap,
                square=True, cbar_kws={"shrink": .8})
    plt.title(title)
    plt.xticks(rotation=45)
    plt.yticks(rotation=45)
    plt.tight_layout()
    plt.show()

def plotTimeSeries(data: Union[pd.Series, pd.DataFrame], title: str = "Time Series Plot",
                   xlabel: str = "Time", ylabel: str = "Values") -> None:
    """
    Plots a time series from a pandas Series or DataFrame.

    Parameters:
        data (Union[pd.Series, pd.DataFrame]): The time series data to plot.
        title (str): The title of the plot.
        xlabel (str): The label for the x-axis.
        ylabel (str): The label for the y-axis.
    """
  plt.figure(figsize=(12, 6))
  if isinstance(data, pd.Series):
      plt.plot(data.index, data.values, label='Values', color='blue')
  elif isinstance(data, pd.DataFrame):
      for column in data.columns:
          plt.plot(data.index, data[column], label=column)
  plt.title(title)
  plt.xlabel(xlabel)
  plt.ylabel(ylabel)
  plt.legend()
  plt.grid()
  plt.show()
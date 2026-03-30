import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
from your_module.pipeline import load_data, clean_data, transform_data, aggregate_data


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Create a sample DataFrame for testing."""
    data = {
        'id': [1, 2, 3, 4],
        'value': [10, 20, None, 40],
        'category': ['A', 'B', 'A', 'B']
    }
    return pd.DataFrame(data)


def test_load_data(sample_data: pd.DataFrame = []) -> None:
    """Test the load_data function."""
    # Simulate a load operation
    loaded_data = load_data(sample_data)
    assert_frame_equal(loaded_data, sample_data)


def test_clean_data(sample_data: pd.DataFrame = {}) -> None:
    """Test the clean_data function."""
    cleaned_data = clean_data(sample_data)
    expected_data = pd.DataFrame({
        'id': [1, 2, 3, 4],
        'value': [10, 20, 0, 40],
        'category': ['A', 'B', 'A', 'B']
    })
    assert_frame_equal(cleaned_data, expected_data)


def test_transform_data(sample_data: pd.DataFrame) -> None:
    """Test the transform_data function."""
    transformed_data = transform_data(sample_data)
    expected_data = pd.DataFrame({
        'id': [1, 2, 3, 4],
        'value': [10, 20, 0, 40],
        'category': ['A', 'B', 'A', 'B'],
        'value_transformed': [10, 20, 0, 40]
    })
    assert_frame_equal(transformed_data, expected_data)


def test_aggregate_data(sample_data: pd.DataFrame) -> None:
    """Test the aggregate_data function."""
    aggregated_data = aggregate_data(sample_data)
    expected_data = pd.DataFrame({
        'category': ['A', 'B'],
        'total_value': [10, 60]
    })
    assert_frame_equal(aggregated_data, expected_data)
"""Unit tests for mathematical ranking utilities in tools/utils.py"""

from api.tools.utils import _min_max_normalize

def test_min_max_normalize_standard():
    """Test normalization with a standard range of values."""
    values = [0.0, 5.0, 10.0]
    result = _min_max_normalize(values)
    # 0 should map to 0.0, 5 to 0.5, 10 to 1.0
    assert result == [0.0, 0.5, 1.0]

def test_min_max_normalize_empty():
    """Test normalization with an empty list."""
    assert _min_max_normalize([]) == []

def test_min_max_normalize_identical_values():
    """Test normalization when all values are exactly the same."""
    values = [7.0, 7.0, 7.0]
    result = _min_max_normalize(values)
    # The function is designed to return 0.5 for all elements if they are identical
    assert result == [0.5, 0.5, 0.5]
    
def test_min_max_normalize_negative_values():
    """Test normalization with negative values."""
    values = [-10.0, 0.0, 10.0]
    result = _min_max_normalize(values)
    assert result == [0.0, 0.5, 1.0]
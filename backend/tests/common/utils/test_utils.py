"""Unit tests for common utilities."""

from datetime import datetime

from common.utils.time import get_timestamp
from common.utils.utils import extract_nested_json, string_to_numeric_hash


class TestTimeUtils:
    """Tests for time utility functions."""

    def test_get_timestamp_returns_int(self) -> None:
        result = get_timestamp()
        assert isinstance(result, int)

    def test_get_timestamp_is_milliseconds(self) -> None:
        result = get_timestamp()
        assert 10**12 <= result <= 10**13

    def test_get_timestamp_is_recent(self) -> None:
        result = get_timestamp()
        now_ms = int(datetime.now().timestamp() * 1000)
        assert abs(result - now_ms) < 1000


class TestStringUtils:
    """Tests for string utility functions."""

    def test_string_to_numeric_hash_returns_int(self) -> None:
        result = string_to_numeric_hash("test string")
        assert isinstance(result, int)

    def test_string_to_numeric_hash_consistent(self) -> None:
        text = "consistent input"
        result1 = string_to_numeric_hash(text)
        result2 = string_to_numeric_hash(text)
        assert result1 == result2

    def test_string_to_numeric_hash_different_inputs(self) -> None:
        result1 = string_to_numeric_hash("input1")
        result2 = string_to_numeric_hash("input2")
        assert result1 != result2

    def test_string_to_numeric_hash_positive(self) -> None:
        result = string_to_numeric_hash("any string")
        assert 0 <= result < 2**63


class TestJsonExtraction:
    """Tests for JSON extraction from text."""

    def test_extract_json_simple_object(self) -> None:
        text = 'Some text {"key": "value"} more text'
        result = extract_nested_json(text)
        assert result == '{"key": "value"}'

    def test_extract_json_nested_object(self) -> None:
        text = '{"outer": {"inner": "value"}}'
        result = extract_nested_json(text)
        assert result == '{"outer": {"inner": "value"}}'

    def test_extract_json_array(self) -> None:
        text = "prefix [1, 2, 3] suffix"
        result = extract_nested_json(text)
        assert result == "[1, 2, 3]"

    def test_extract_json_no_json(self) -> None:
        text = "This is just plain text with no JSON"
        result = extract_nested_json(text)
        assert result is None

    def test_extract_json_invalid_json(self) -> None:
        text = "This has {broken json"
        result = extract_nested_json(text)
        assert result is None

    def test_extract_json_with_numbers(self) -> None:
        text = '{"count": 42, "price": 19.99}'
        result = extract_nested_json(text)
        assert result == '{"count": 42, "price": 19.99}'

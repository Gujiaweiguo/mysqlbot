import string

from common.utils.random import get_random_string


class TestGetRandomString:
    def test_returns_requested_length(self) -> None:
        assert len(get_random_string(24)) == 24

    def test_uses_only_letters_and_digits(self) -> None:
        result = get_random_string(64)

        assert set(result) <= set(string.ascii_letters + string.digits)

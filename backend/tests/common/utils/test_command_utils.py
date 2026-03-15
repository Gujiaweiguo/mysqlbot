from apps.chat.models.chat_model import QuickCommand
from common.utils.command_utils import parse_quick_command


class TestParseQuickCommand:
    def test_returns_original_when_no_command_found(self) -> None:
        result = parse_quick_command("hello world")
        assert result == (None, "hello world", None, None)

    def test_returns_error_when_multiple_commands_found(self) -> None:
        command, text, record_id, warning = parse_quick_command(
            "hello /analysis /predict"
        )

        assert command is None
        assert text == "hello /analysis /predict"
        assert record_id is None
        assert warning is not None
        assert "/analysis" in warning
        assert "/predict" in warning

    def test_parses_command_with_record_id(self) -> None:
        command, text, record_id, warning = parse_quick_command("hello /analysis 42")

        assert command == QuickCommand.ANALYSIS
        assert text == "hello"
        assert record_id == 42
        assert warning is None

    def test_returns_error_when_command_not_at_end(self) -> None:
        command, text, record_id, warning = parse_quick_command("hello /analysis extra")

        assert command is None
        assert text == "hello /analysis extra"
        assert record_id is None
        assert warning is not None
        assert "命令不在字符串末尾" in warning

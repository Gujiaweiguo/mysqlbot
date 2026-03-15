import pytest

from common.utils.snowflake import SnowflakeGenerator


class TestSnowflakeGenerator:
    def test_rejects_invalid_worker_id(self) -> None:
        with pytest.raises(ValueError):
            SnowflakeGenerator(worker_id=32)

    def test_rejects_invalid_datacenter_id(self) -> None:
        with pytest.raises(ValueError):
            SnowflakeGenerator(datacenter_id=32)

    def test_wait_next_millis_waits_until_timestamp_advances(self, monkeypatch) -> None:
        generator = SnowflakeGenerator()
        timestamps = iter([5, 5, 6])
        monkeypatch.setattr(generator, "_current_time", lambda: next(timestamps))

        assert generator._wait_next_millis(5) == 6

    def test_generate_id_increments_sequence_on_same_millisecond(
        self, monkeypatch
    ) -> None:
        generator = SnowflakeGenerator(worker_id=1, datacenter_id=1)
        monkeypatch.setattr(generator, "_current_time", lambda: 1000)

        first = generator.generate_id()
        second = generator.generate_id()

        assert second > first
        assert generator.sequence == 1

    def test_generate_id_waits_when_sequence_overflows(self, monkeypatch) -> None:
        generator = SnowflakeGenerator()
        generator.last_timestamp = 100
        generator.sequence = generator.sequence_mask
        monkeypatch.setattr(generator, "_current_time", lambda: 100)
        monkeypatch.setattr(generator, "_wait_next_millis", lambda _last: 101)

        generated = generator.generate_id()

        assert generator.last_timestamp == 101
        assert generator.sequence == 0
        assert generated > 0

    def test_generate_id_rejects_clock_moving_backwards(self, monkeypatch) -> None:
        generator = SnowflakeGenerator()
        generator.last_timestamp = 10
        monkeypatch.setattr(generator, "_current_time", lambda: 9)

        with pytest.raises(ValueError, match="Clock moved backwards"):
            generator.generate_id()

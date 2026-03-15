import pandas as pd

from apps.chat.models.chat_model import AxisObj
from common.utils.data_format import DataFormat


class TestDataFormat:
    def test_safe_convert_to_string_preserves_shape_and_handles_nulls(self) -> None:
        original = pd.DataFrame({"id": [1, None], "name": ["alice", "bob"]})

        converted = DataFormat.safe_convert_to_string(original)

        assert converted.iloc[0, 0] == "\u200b1.0"
        assert converted.iloc[1, 0] == ""
        assert converted.iloc[0, 1] == "\u200balice"
        assert pd.isna(original.iloc[1, 0])

    def test_convert_large_numbers_in_object_array_handles_nested_values(self) -> None:
        data = [
            {
                "big_int": 10**16,
                "small_int": 7,
                "big_float": 123456789012.5,
                "tiny_float": 0.00000012,
                "nested": {"value": 10**16},
                "items": [{"metric": 123456789012.5}, "keep"],
            }
        ]

        result = DataFormat.convert_large_numbers_in_object_array(data)

        assert result[0]["big_int"] == str(10**16)
        assert result[0]["small_int"] == 7
        assert result[0]["big_float"] == "123456789012.5"
        assert result[0]["tiny_float"] == "0.00000012"
        assert result[0]["nested"]["value"] == str(10**16)
        assert result[0]["items"][0]["metric"] == "123456789012.5"

    def test_convert_object_array_for_pandas_keeps_column_order(self) -> None:
        columns = [AxisObj(name="Name", value="name"), AxisObj(name="Age", value="age")]
        rows = [{"name": "alice", "age": 18}, {"name": "bob", "age": 20}]

        data, fields = DataFormat.convert_object_array_for_pandas(columns, rows)

        assert fields == ["Name", "Age"]
        assert data == [["alice", 18], ["bob", 20]]

    def test_convert_data_fields_for_pandas_uses_chart_mappings(self) -> None:
        chart = {
            "columns": [{"value": "city", "name": "City"}],
            "axis": {
                "x": {"value": "date", "name": "Date"},
                "y": [
                    {"value": "sales", "name": "Sales"},
                    {"value": "profit", "name": "Profit"},
                ],
                "series": {"value": "region", "name": "Region"},
            },
        }
        fields = ["date", "sales", "profit", "region", "city", "raw"]
        rows = [
            {
                "date": "2025-01-01",
                "sales": 100,
                "profit": 30,
                "region": "east",
                "city": "shanghai",
                "raw": "value",
            }
        ]

        data, mapped_fields = DataFormat.convert_data_fields_for_pandas(
            chart, fields, rows
        )

        assert mapped_fields == ["Date", "Sales", "Profit", "Region", "City", "raw"]
        assert data == [["2025-01-01", 100, 30, "east", "shanghai", "value"]]

    def test_format_pd_data_marks_large_numbers_as_text(self) -> None:
        columns = [
            AxisObj(name="BigInt", value="big_int"),
            AxisObj(name="BigFloat", value="big_float"),
            AxisObj(name="Normal", value="normal"),
        ]
        rows = [
            {
                "big_int": 1234567890123456,
                "big_float": 0.12345678901234567,
                "normal": 12,
            }
        ]

        data, fields, formats = DataFormat.format_pd_data(columns, rows)

        assert fields == ["BigInt", "BigFloat", "Normal"]
        assert data[0][0] == "1234567890123456"
        assert isinstance(data[0][1], str)
        assert data[0][2] == 12
        assert formats == {0: "text", 1: "text", 2: "number"}

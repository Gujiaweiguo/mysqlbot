from typing import Any

import pandas as pd

from apps.chat.models.chat_model import AxisObj


class DataFormat:
    @staticmethod
    def safe_convert_to_string(df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()

        for col in df_copy.columns:
            # 使用map避免ambiguous truth value问题
            df_copy[col] = df_copy[col].map(
                # 关键：在数字字符串前添加零宽空格，阻止pandas的自动格式化
                lambda x: "" if pd.isna(x) else "\u200b" + str(x)
            )

        return df_copy

    @staticmethod
    def convert_large_numbers_in_object_array(
        obj_array: list[Any],
        int_threshold: float = 1e15,
        float_threshold: float = 1e10,
    ) -> list[Any]:
        """处理对象数组，将每个对象中的大数字转换为字符串"""

        def format_float_without_scientific(value: float) -> str:
            """格式化浮点数，避免科学记数法"""
            if value == 0:
                return "0"
            formatted = f"{value:.15f}"
            if "." in formatted:
                formatted = formatted.rstrip("0").rstrip(".")
            return formatted

        def process_object(obj: dict[str, Any]) -> dict[str, Any]:
            """处理单个对象"""
            processed_obj: dict[str, Any] = {}
            for key, value in obj.items():
                if isinstance(value, (int, float)):
                    # 只转换大数字
                    if isinstance(value, int) and abs(value) >= int_threshold:
                        processed_obj[key] = str(value)
                    elif isinstance(value, float) and (
                        abs(value) >= float_threshold or abs(value) < 1e-6
                    ):
                        processed_obj[key] = format_float_without_scientific(value)
                    else:
                        processed_obj[key] = value
                elif isinstance(value, dict):
                    # 处理嵌套对象
                    processed_obj[key] = process_object(value)
                elif isinstance(value, list):
                    # 处理对象中的数组
                    processed_obj[key] = [process_item(item) for item in value]
                else:
                    processed_obj[key] = value
            return processed_obj

        def process_item(item: Any) -> Any:
            """处理数组中的项目"""
            if isinstance(item, dict):
                return process_object(item)
            return item

        return [process_item(obj) for obj in obj_array]

    @staticmethod
    def convert_object_array_for_pandas(
        column_list: list[AxisObj],
        data_list: list[dict[str, Any]],
    ) -> tuple[list[list[Any]], list[str]]:
        _fields_list: list[str] = []
        for field in column_list:
            _fields_list.append(field.name)

        md_data: list[list[Any]] = []
        for inner_data in data_list:
            _row: list[Any] = []
            for field in column_list:
                value = inner_data.get(field.value)
                _row.append(value)
            md_data.append(_row)
        return md_data, _fields_list

    @staticmethod
    def convert_data_fields_for_pandas(
        chart: dict[str, Any],
        fields: list[str],
        data: list[dict[str, Any]],
    ) -> tuple[list[list[Any]], list[str]]:
        _fields: dict[str, str] = {}
        if chart.get("columns"):
            columns = chart.get("columns")
            if isinstance(columns, list):
                for _column in columns:
                    if isinstance(_column, dict):
                        value = _column.get("value")
                        name = _column.get("name")
                        if isinstance(value, str) and isinstance(name, str):
                            _fields[value] = name
        if chart.get("axis"):
            axis_obj = chart.get("axis")
            if isinstance(axis_obj, dict) and axis_obj.get("x"):
                x_axis = axis_obj.get("x")
                if isinstance(x_axis, dict):
                    x_value = x_axis.get("value")
                    x_name = x_axis.get("name")
                    if isinstance(x_value, str) and isinstance(x_name, str):
                        _fields[x_value] = x_name
            if isinstance(axis_obj, dict) and axis_obj.get("y"):
                # _fields[chart.get('axis').get('y').get('value')] = chart.get('axis').get('y').get('name')
                y_axis = axis_obj.get("y")
                if isinstance(y_axis, list):
                    # y轴是数组的情况（多指标字段）
                    for y_item in y_axis:
                        if (
                            isinstance(y_item, dict)
                            and "value" in y_item
                            and "name" in y_item
                        ):
                            y_value = y_item.get("value")
                            y_name = y_item.get("name")
                            if isinstance(y_value, str) and isinstance(y_name, str):
                                _fields[y_value] = y_name
                elif isinstance(y_axis, dict):
                    # y轴是对象的情况（单指标字段）
                    if "value" in y_axis and "name" in y_axis:
                        y_value = y_axis.get("value")
                        y_name = y_axis.get("name")
                        if isinstance(y_value, str) and isinstance(y_name, str):
                            _fields[y_value] = y_name
            if isinstance(axis_obj, dict) and axis_obj.get("series"):
                series_axis = axis_obj.get("series")
                if isinstance(series_axis, dict):
                    series_value = series_axis.get("value")
                    series_name = series_axis.get("name")
                    if isinstance(series_value, str) and isinstance(series_name, str):
                        _fields[series_value] = series_name
        _column_list: list[AxisObj] = []
        for field in fields:
            mapped_name = _fields.get(field)
            _column_list.append(
                AxisObj(name=field if mapped_name is None else mapped_name, value=field)
            )

        md_data, _fields_list = DataFormat.convert_object_array_for_pandas(
            _column_list, data
        )

        return md_data, _fields_list

    @staticmethod
    def format_pd_data(
        column_list: list[AxisObj],
        data_list: list[dict[str, Any]],
        col_formats: dict[int, str] | None = None,
    ) -> tuple[list[list[Any]], list[str], dict[int, str]]:
        # 预处理数据并记录每列的格式类型
        # 格式类型：'text'（文本）、'number'（数字）、'default'（默认）
        _fields_list: list[str] = []

        if col_formats is None:
            col_formats = {}
        for field_idx, field in enumerate(column_list):
            _fields_list.append(field.name)
            col_formats[field_idx] = "default"  # 默认不特殊处理

        data: list[list[Any]] = []

        for _data in data_list:
            _row: list[Any] = []
            for field_idx, field in enumerate(column_list):
                value = _data.get(field.value)
                if value is not None:
                    # 检查是否为数字且需要特殊处理
                    if isinstance(value, (int, float)):
                        # 整数且超过15位 → 转字符串并标记为文本列
                        if isinstance(value, int) and len(str(abs(value))) > 15:
                            value = str(value)
                            col_formats[field_idx] = "text"
                        # 小数且超过15位有效数字 → 转字符串并标记为文本列
                        elif isinstance(value, float):
                            decimal_str = format(value, ".16f").rstrip("0").rstrip(".")
                            if len(decimal_str) > 15:
                                value = str(value)
                                col_formats[field_idx] = "text"
                        # 其他数字列标记为数字格式（避免科学记数法）
                        elif col_formats[field_idx] != "text":
                            col_formats[field_idx] = "number"
                _row.append(value)
            data.append(_row)

        return data, _fields_list, col_formats

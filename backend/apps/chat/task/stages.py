from collections.abc import Callable

import orjson

from common.error import SingleMessageError
from common.utils.utils import extract_nested_json

ObjectDict = dict[str, object]


class SQLAnswerStage:
    def __init__(
        self,
        extract_payload: Callable[[str], tuple[str | None, ObjectDict | None]],
        is_successful_payload: Callable[[ObjectDict], bool],
        get_str: Callable[[ObjectDict, str], str | None],
    ) -> None:
        self._extract_payload = extract_payload
        self._is_successful_payload = is_successful_payload
        self._get_str = get_str

    def chart_type_from_answer(self, res: str) -> str | None:
        _, data = self._extract_payload(res)
        if data is None:
            return None
        try:
            if self._is_successful_payload(data):
                return self._get_str(data, "chart-type")
            return None
        except Exception:
            return None

    def brief_from_answer(self, res: str) -> str | None:
        _, data = self._extract_payload(res)
        if data is None:
            return None
        try:
            if self._is_successful_payload(data):
                return self._get_str(data, "brief")
            return None
        except Exception:
            return None


class ChartResultStage:
    def __init__(
        self,
        *,
        parse_json_object: Callable[[str], ObjectDict | None],
        as_object_dict: Callable[[object], ObjectDict | None],
        as_object_dict_list: Callable[[object], list[ObjectDict]],
        as_object_list: Callable[[object], list[object]],
        get_str: Callable[[ObjectDict, str], str | None],
        lowercase_mapping_value: Callable[[ObjectDict, str], None],
    ) -> None:
        self._parse_json_object = parse_json_object
        self._as_object_dict = as_object_dict
        self._as_object_dict_list = as_object_dict_list
        self._as_object_list = as_object_list
        self._get_str = get_str
        self._lowercase_mapping_value = lowercase_mapping_value

    def parse_chart(self, res: str) -> ObjectDict:
        json_str = extract_nested_json(res)
        if json_str is None:
            raise SingleMessageError(
                orjson.dumps(
                    {
                        "message": "Cannot parse chart config from answer",
                        "traceback": "Cannot parse chart config from answer:\n" + res,
                    }
                ).decode()
            )

        chart: ObjectDict = {}
        message = ""
        error = False
        try:
            data = self._parse_json_object(json_str)
            if data is None:
                raise ValueError("Chart payload is not a valid object")

            chart_type = self._get_str(data, "type")
            if chart_type and chart_type != "error":
                chart = data
                for column in self._as_object_dict_list(chart.get("columns")):
                    self._lowercase_mapping_value(column, "value")

                axis_data = self._as_object_dict(chart.get("axis"))
                if axis_data is not None:
                    x_axis = self._as_object_dict(axis_data.get("x"))
                    if x_axis is not None:
                        self._lowercase_mapping_value(x_axis, "value")

                    y_axis = axis_data.get("y")
                    if y_axis:
                        if isinstance(y_axis, list):
                            for item in self._as_object_dict_list(y_axis):
                                self._lowercase_mapping_value(item, "value")
                        else:
                            y_axis_mapping = self._as_object_dict(y_axis)
                            if y_axis_mapping is not None:
                                self._lowercase_mapping_value(y_axis_mapping, "value")

                    series = self._as_object_dict(axis_data.get("series"))
                    if series is not None:
                        self._lowercase_mapping_value(series, "value")

                    multi_quota = self._as_object_dict(axis_data.get("multi-quota"))
                    if multi_quota is not None:
                        multi_quota_value = multi_quota.get("value")
                        if isinstance(multi_quota_value, list):
                            multi_quota["value"] = [
                                value.lower() if isinstance(value, str) else value
                                for value in self._as_object_list(multi_quota_value)
                            ]
                        elif isinstance(multi_quota_value, str):
                            multi_quota["value"] = multi_quota_value.lower()
            elif chart_type == "error":
                message = self._get_str(data, "reason") or "Chart is empty"
                error = True
            else:
                raise Exception("Chart is empty")
        except Exception:
            error = True
            message = orjson.dumps(
                {
                    "message": "Cannot parse chart config from answer",
                    "traceback": "Cannot parse chart config from answer:\n" + res,
                }
            ).decode()

        if error:
            raise SingleMessageError(message)
        return chart


class PredictResultStage:
    def extract_predict_payload(self, res: str) -> str:
        json_str = extract_nested_json(res)
        return json_str or ""

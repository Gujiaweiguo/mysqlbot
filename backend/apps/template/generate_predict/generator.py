from typing import Any

from apps.template.template import get_base_template


def get_predict_template() -> Any:
    template = get_base_template()
    return template["template"]["predict"]

from typing import Any

from apps.template.template import get_base_template


def get_guess_question_template() -> Any:
    template = get_base_template()
    return template["template"]["guess"]

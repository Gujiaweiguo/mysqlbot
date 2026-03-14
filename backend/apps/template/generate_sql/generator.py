from typing import Any

from apps.db.constant import DB
from apps.template.template import (
    get_base_template,
)
from apps.template.template import (
    get_sql_template as get_base_sql_template,
)


def get_sql_template() -> Any:
    template = get_base_template()
    return template["template"]["sql"]


def get_sql_example_template(db_type: str | DB) -> Any:
    template = get_base_sql_template(db_type)
    return template["template"]

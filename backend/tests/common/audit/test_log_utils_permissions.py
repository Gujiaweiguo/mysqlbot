from typing import Any, cast

from sqlalchemy.dialects import postgresql

from common.audit.schemas.log_utils import build_resource_union_query


def test_build_resource_union_query_includes_local_permission_models() -> None:
    compiled = build_resource_union_query().compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
    )
    sql = str(cast(object, compiled))

    assert "ds_permission" in sql
    assert "ds_rules" in sql
    assert "custom_prompt" in sql
    assert "permission" in sql
    assert "prompt_words" in sql
    assert "rules" in sql

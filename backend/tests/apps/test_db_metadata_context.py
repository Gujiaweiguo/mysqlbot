from apps.db.db import build_metadata_context
from apps.system.schemas.system_schema import AssistantOutDsSchema


def test_build_metadata_context_populates_assistant_configuration() -> None:
    ds = AssistantOutDsSchema(
        id=10001,
        name="mock-demo-sales",
        type="pg",
        host="localhost",
        port=5432,
        user="root",
        password="Password123@pg",
        dataBase="sqlbot",
        db_schema="demo_sales",
        mode="read",
        configuration=None,
    )

    context = build_metadata_context(ds)

    assert ds.configuration is not None
    assert context.conf.database == "sqlbot"
    assert context.conf.dbSchema == "demo_sales"

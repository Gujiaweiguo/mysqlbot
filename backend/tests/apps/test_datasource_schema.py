from _pytest.monkeypatch import MonkeyPatch
from sqlmodel import Session

from apps.datasource.crud.datasource import get_table_schema
from apps.datasource.models.datasource import (
    CoreDatasource,
    CoreField,
    CoreTable,
    TableAndFields,
)
from apps.system.schemas.system_schema import UserInfoDTO


def _fake_table_objs(
    session: Session, current_user: UserInfoDTO, ds: CoreDatasource
) -> list[TableAndFields]:
    _ = session
    _ = current_user
    _ = ds
    return []


class TestDatasourceSchemaFormatting:
    def test_get_table_schema_quotes_pg_identifiers(
        self, monkeypatch: MonkeyPatch, auth_user: UserInfoDTO
    ) -> None:
        ds = CoreDatasource(
            id=1,
            name="mallcre",
            description="",
            type="pg",
            type_name="PostgreSQL",
            configuration="",
            create_by=1,
            status="Success",
            num="1/1",
            oid=1,
            table_relation=[],
            recommended_config=1,
        )
        table = CoreTable(
            id=1,
            ds_id=1,
            checked=True,
            table_name="bi_r_store_month",
            table_comment="项目每月汇总",
            custom_comment="",
        )
        field = CoreField(
            id=1,
            ds_id=1,
            table_id=1,
            checked=True,
            field_name="STORE_NAME",
            field_type="varchar",
            field_comment="项目名称",
            custom_comment="项目名称",
            field_index=1,
        )

        def fake_get_table_obj_by_ds(
            session: Session, current_user: UserInfoDTO, ds: CoreDatasource
        ) -> list[TableAndFields]:
            _ = _fake_table_objs(session, current_user, ds)
            return [TableAndFields(schema="mallcre", table=table, fields=[field])]

        monkeypatch.setattr(
            "apps.datasource.crud.datasource.get_table_obj_by_ds",
            fake_get_table_obj_by_ds,
        )
        monkeypatch.setattr(
            "apps.datasource.crud.datasource.settings.TABLE_EMBEDDING_ENABLED", False
        )

        schema = get_table_schema(
            session=Session(),
            current_user=auth_user,
            ds=ds,
            question="统计项目应收金额",
        )

        assert '# Table: "mallcre"."bi_r_store_month"' in schema
        assert '("STORE_NAME":varchar, 项目名称)' in schema

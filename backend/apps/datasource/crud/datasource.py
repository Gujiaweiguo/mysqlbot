import datetime
import json
from importlib import import_module
from typing import ClassVar, Protocol, cast

from fastapi import HTTPException
from sqlalchemy import and_, delete, text
from sqlmodel import col, select

from apps.datasource.crud.permission import (
    DsRulesRecordProtocol,
    get_column_permission_fields,
    get_row_permission_filters,
    is_normal_user,
)
from apps.datasource.embedding.table_embedding import calc_table_embedding
from apps.datasource.utils.utils import aes_decrypt, aes_encrypt
from apps.db.constant import DB
from apps.db.db import check_connection, exec_sql, get_fields, get_tables
from apps.db.engine import get_engine_config, get_engine_conn
from apps.system.schemas.auth import CacheName, CacheNamespace
from common.core.config import settings
from common.core.deps import CurrentUser, SessionDep, Trans
from common.core.sqlbot_cache import cache, clear_cache
from common.utils.embedding_threads import (
    run_save_ds_embeddings,
    run_save_table_embeddings,
)
from common.utils.utils import SQLBotLogUtil, deepcopy_ignore_extra

from ..crud.field import delete_field_by_ds_id, update_field
from ..crud.table import delete_table_by_ds_id, update_table
from ..models.datasource import (
    ColumnSchema,
    CoreDatasource,
    CoreField,
    CoreTable,
    CreateDatasource,
    DatasourceConf,
    TableAndFields,
    TableObj,
    TableSchema,
)
from .table import get_tables_by_ds_id

DEFAULT_INTERNAL_DS_NAME = "mySQLBot Internal PostgreSQL"
DEFAULT_INTERNAL_DS_DESCRIPTION = (
    "Auto-created datasource for mySQLBot internal PostgreSQL database"
)

ObjectDict = dict[str, object]
SchemaTableDict = dict[str, object]


class DsRulesModelProtocol(Protocol):
    id: ClassVar[object]


def _parse_json_object(raw_json: str) -> dict[str, object]:
    parsed = cast(object, json.loads(raw_json))
    return cast(dict[str, object], parsed) if isinstance(parsed, dict) else {}


def _as_object_list(value: object) -> list[object]:
    if not isinstance(value, list):
        return []
    return cast(list[object], value)


def _as_object_dict(value: object) -> ObjectDict | None:
    return cast(ObjectDict, value) if isinstance(value, dict) else None


def _as_object_dict_list(value: object) -> list[ObjectDict]:
    return [
        cast(ObjectDict, item)
        for item in _as_object_list(value)
        if isinstance(item, dict)
    ]


def _get_str(mapping: ObjectDict, key: str) -> str | None:
    value = mapping.get(key)
    return value if isinstance(value, str) else None


def _get_int(mapping: ObjectDict, key: str) -> int | None:
    value = mapping.get(key)
    return value if isinstance(value, int) else None


def _get_sheet_table_names(conf: DatasourceConf) -> list[str]:
    table_names: list[str] = []
    for sheet in _as_object_dict_list(conf.sheets):
        table_name = sheet.get("tableName")
        if isinstance(table_name, str):
            table_names.append(table_name)
    return table_names


def _get_ds_rules_model() -> type[DsRulesModelProtocol]:
    module = import_module("sqlbot_xpack.permissions.models.ds_rules")
    return cast(type[DsRulesModelProtocol], module.DsRules)


def _decrypt_configuration(config: str | bytes | None) -> str:
    if config is None:
        raise Exception("Datasource configuration is missing")
    if isinstance(config, bytes):
        return aes_decrypt(config)
    return aes_decrypt(config.encode("utf-8"))


def _get_datasource_conf(ds: CoreDatasource) -> DatasourceConf:
    raw_conf = _parse_json_object(_decrypt_configuration(ds.configuration))
    return DatasourceConf.model_validate(raw_conf)


def _is_internal_pg_conf(conf: DatasourceConf) -> bool:
    return (
        conf.host == settings.POSTGRES_SERVER
        and int(conf.port) == int(settings.POSTGRES_PORT)
        and conf.username == settings.POSTGRES_USER
        and conf.password == settings.POSTGRES_PASSWORD
        and conf.database == settings.POSTGRES_DB
        and (conf.dbSchema or "public") == "public"
    )


def ensure_internal_pg_datasource(
    session: SessionDep, oid: int, create_by: int = 1, commit: bool = True
) -> CoreDatasource | None:
    ds_list = session.exec(
        select(CoreDatasource).where(
            and_(col(CoreDatasource.oid) == oid, col(CoreDatasource.type) == "pg")
        )
    ).all()
    for ds in ds_list:
        try:
            raw_conf = _parse_json_object(_decrypt_configuration(ds.configuration))
            conf = DatasourceConf.model_validate(raw_conf)
            if raw_conf.get("sheets") in ("", None):
                ds.configuration = aes_encrypt(json.dumps(conf.to_dict())).decode(
                    "utf-8"
                )
                session.add(ds)
                if commit:
                    session.commit()
            if ds.name == DEFAULT_INTERNAL_DS_NAME or _is_internal_pg_conf(conf):
                return None
        except Exception:
            continue

    conf = get_engine_config()
    conf.extraJdbc = ""
    conf.driver = ""
    conf.sheets = []
    datasource = CoreDatasource(
        id=None,
        name=DEFAULT_INTERNAL_DS_NAME,
        description=DEFAULT_INTERNAL_DS_DESCRIPTION,
        type="pg",
        type_name=DB.get_db("pg").db_name,
        configuration=aes_encrypt(json.dumps(conf.to_dict())).decode("utf-8"),
        create_time=datetime.datetime.now(),
        create_by=create_by,
        status="Success",
        num="0/0",
        oid=oid,
        table_relation=[],
        embedding="",
        recommended_config=1,
    )
    session.add(datasource)
    session.flush()
    session.refresh(datasource)
    try:
        all_tables = get_tables(datasource) or []
        datasource.num = f"0/{len(all_tables)}"
    except Exception as ex:
        SQLBotLogUtil.warning(
            f"Failed to load tables for internal datasource in workspace [{oid}]: {ex}"
        )
    session.add(datasource)
    if commit:
        session.commit()
    return datasource


def get_datasource_list(
    session: SessionDep, user: CurrentUser, oid: int | None = None
) -> list[CoreDatasource]:
    current_oid = user.oid
    if user.isAdmin and oid:
        current_oid = oid
    return list(
        session.exec(
            select(CoreDatasource)
            .where(col(CoreDatasource.oid) == current_oid)
            .order_by(col(CoreDatasource.name))
        ).all()
    )


def get_ds(session: SessionDep, id: int) -> CoreDatasource | None:
    statement = select(CoreDatasource).where(col(CoreDatasource.id) == id)
    return session.exec(statement).first()


def check_status_by_id(
    session: SessionDep, trans: Trans, ds_id: int, is_raise: bool = False
) -> bool:
    ds = session.get(CoreDatasource, ds_id)
    if ds is None:
        if is_raise:
            raise HTTPException(status_code=500, detail=trans("i18n_ds_invalid"))
        return False
    return check_status(session, trans, ds, is_raise)


def check_status(
    _session: SessionDep, trans: Trans, ds: CoreDatasource, is_raise: bool = False
) -> bool:
    return check_connection(trans, ds, is_raise)


def check_name(
    session: SessionDep, trans: Trans, user: CurrentUser, ds: CoreDatasource
) -> None:
    ds_id = cast(object, getattr(ds, "id", None))
    if isinstance(ds_id, int):
        ds_list = list(
            session.exec(
                select(CoreDatasource).where(
                    and_(
                        col(CoreDatasource.name) == ds.name,
                        col(CoreDatasource.id) != ds_id,
                        col(CoreDatasource.oid) == user.oid,
                    )
                )
            )
        )
        if ds_list:
            raise HTTPException(status_code=500, detail=trans("i18n_ds_name_exist"))
    else:
        ds_list = list(
            session.exec(
                select(CoreDatasource).where(
                    and_(
                        col(CoreDatasource.name) == ds.name,
                        col(CoreDatasource.oid) == user.oid,
                    )
                )
            )
        )
        if ds_list:
            raise HTTPException(status_code=500, detail=trans("i18n_ds_name_exist"))


@clear_cache(
    namespace=str(CacheNamespace.AUTH_INFO),
    cacheName=str(CacheName.DS_ID_LIST),
    keyExpression="user.oid",
)
async def create_ds(
    session: SessionDep, trans: Trans, user: CurrentUser, create_ds: CreateDatasource
) -> CoreDatasource:
    ds = CoreDatasource.model_construct(
        name=create_ds.name,
        description=create_ds.description,
        type=create_ds.type,
        type_name="",
        configuration=create_ds.configuration,
        create_time=datetime.datetime.now(),
        create_by=user.id,
        status="Success",
        num="0/0",
        oid=user.oid,
        table_relation=[],
        embedding="",
        recommended_config=create_ds.recommended_config,
    )
    deepcopy_ignore_extra(create_ds, ds)
    check_name(session, trans, user, ds)
    # status = check_status(session, ds)
    ds.type_name = DB.get_db(ds.type).db_name
    record = CoreDatasource.model_validate(ds.model_dump())
    session.add(record)
    session.flush()
    session.refresh(record)
    ds.id = record.id
    session.commit()

    # save tables and fields
    sync_table(session, ds, create_ds.tables)
    updateNum(session, ds)
    return ds


def chooseTables(
    session: SessionDep, trans: Trans, id: int, tables: list[CoreTable]
) -> None:
    ds = session.exec(
        select(CoreDatasource).where(col(CoreDatasource.id) == id)
    ).first()
    if ds is None:
        raise HTTPException(status_code=500, detail=trans("i18n_ds_invalid"))
    _ = check_status(session, trans, ds, True)
    sync_table(session, ds, tables)
    updateNum(session, ds)


def update_ds(
    session: SessionDep, trans: Trans, user: CurrentUser, ds: CoreDatasource
) -> CoreDatasource:
    ds_id = cast(object, ds.id)
    if not isinstance(ds_id, int):
        raise HTTPException(status_code=500, detail=trans("i18n_ds_invalid"))
    ds.id = ds_id
    check_name(session, trans, user, ds)
    # status = check_status(session, trans, ds)
    ds.status = "Success"
    record = session.exec(
        select(CoreDatasource).where(col(CoreDatasource.id) == ds.id)
    ).first()
    if record is None:
        raise HTTPException(status_code=500, detail=trans("i18n_ds_invalid"))
    update_data = cast(dict[str, object], ds.model_dump(exclude_unset=True))
    for field, value in update_data.items():
        setattr(record, field, value)
    session.add(record)
    session.commit()

    run_save_ds_embeddings([ds.id])
    return ds


def update_ds_recommended_config(
    session: SessionDep, datasource_id: int, recommended_config: int
) -> None:
    record = session.exec(
        select(CoreDatasource).where(col(CoreDatasource.id) == datasource_id)
    ).first()
    if record is None:
        raise HTTPException(status_code=500, detail="datasource not found")
    record.recommended_config = recommended_config
    session.add(record)
    session.commit()


async def delete_ds(session: SessionDep, id: int) -> dict[str, str]:
    term = session.exec(
        select(CoreDatasource).where(col(CoreDatasource.id) == id)
    ).first()
    if term is None:
        return {"message": f"Datasource with ID {id} not found."}
    if term.type == "excel":
        # drop all tables for current datasource
        engine = get_engine_conn()
        conf = _get_datasource_conf(term)
        with engine.connect() as conn:
            for table_name in _get_sheet_table_names(conf):
                _ = conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
            conn.commit()

    session.delete(term)
    session.commit()
    delete_table_by_ds_id(session, id)
    delete_field_by_ds_id(session, id)
    if term:
        await clear_ws_ds_cache(term.oid)
    return {"message": f"Datasource with ID {id} deleted successfully."}


def getTables(session: SessionDep, id: int) -> list[TableSchema]:
    ds = session.exec(
        select(CoreDatasource).where(col(CoreDatasource.id) == id)
    ).first()
    if ds is None:
        raise HTTPException(status_code=500, detail="datasource not found")
    return list(get_tables(ds) or [])


def getTablesByDs(_session: SessionDep, ds: CoreDatasource) -> list[TableSchema]:
    # check_status(session, ds, True)
    return list(get_tables(ds) or [])


def getFields(session: SessionDep, id: int, table_name: str) -> list[ColumnSchema]:
    ds = session.exec(
        select(CoreDatasource).where(col(CoreDatasource.id) == id)
    ).first()
    if ds is None:
        raise HTTPException(status_code=500, detail="datasource not found")
    return list(get_fields(ds, table_name) or [])


def getFieldsByDs(
    _session: SessionDep, ds: CoreDatasource, table_name: str
) -> list[ColumnSchema]:
    return list(get_fields(ds, table_name) or [])


def execSql(session: SessionDep, id: int, sql: str) -> ObjectDict:
    ds = session.exec(
        select(CoreDatasource).where(col(CoreDatasource.id) == id)
    ).first()
    if ds is None:
        raise HTTPException(status_code=500, detail="datasource not found")
    return cast(ObjectDict, exec_sql(ds, sql, True))


def sync_single_fields(session: SessionDep, trans: Trans, id: int) -> None:
    table = session.get(CoreTable, id)
    if table is None:
        raise HTTPException(status_code=500, detail=trans("i18n_table_not_exist"))
    ds = session.get(CoreDatasource, table.ds_id)
    if ds is None:
        raise HTTPException(status_code=500, detail=trans("i18n_ds_invalid"))

    tables = getTablesByDs(session, ds)
    t_name = [table_schema.tableName for table_schema in tables]

    if table.table_name not in t_name:
        raise HTTPException(status_code=500, detail=trans("i18n_table_not_exist"))

    # sync field
    fields = getFieldsByDs(session, ds, table.table_name)
    sync_fields(session, ds, table, fields)

    # do table embedding
    run_save_table_embeddings([table.id])
    if ds.id is not None:
        run_save_ds_embeddings([ds.id])


def sync_table(
    session: SessionDep, ds: CoreDatasource, tables: list[CoreTable]
) -> None:
    id_list: list[int] = []
    for item in tables:
        statement = select(CoreTable).where(
            and_(
                col(CoreTable.ds_id) == ds.id,
                col(CoreTable.table_name) == item.table_name,
            )
        )
        record = session.exec(statement).first()
        # update exist table, only update table_comment
        if record is not None:
            item.id = record.id
            id_list.append(record.id)

            record.table_comment = item.table_comment
            session.add(record)
            session.commit()
        else:
            # save new table
            table = CoreTable.model_construct(
                ds_id=ds.id,
                checked=True,
                table_name=item.table_name,
                table_comment=item.table_comment,
                custom_comment=item.table_comment,
                embedding="",
            )
            session.add(table)
            session.flush()
            session.refresh(table)
            table_id = cast(object, getattr(table, "id", None))
            if not isinstance(table_id, int):
                raise HTTPException(status_code=500, detail="table create failed")
            item.id = table_id
            id_list.append(table_id)
            session.commit()

        # sync field
        fields = getFieldsByDs(session, ds, item.table_name)
        sync_fields(session, ds, item, fields)

    if len(id_list) > 0:
        _ = session.exec(
            delete(CoreTable).where(
                and_(col(CoreTable.ds_id) == ds.id, col(CoreTable.id).not_in(id_list))
            )
        )
        _ = session.exec(
            delete(CoreField).where(
                and_(
                    col(CoreField.ds_id) == ds.id,
                    col(CoreField.table_id).not_in(id_list),
                )
            )
        )
        session.commit()
    else:  # delete all tables and fields in this ds
        _ = session.exec(delete(CoreTable).where(col(CoreTable.ds_id) == ds.id))
        _ = session.exec(delete(CoreField).where(col(CoreField.ds_id) == ds.id))
        session.commit()

    # do table embedding
    run_save_table_embeddings(id_list)
    if ds.id is not None:
        run_save_ds_embeddings([ds.id])


def sync_fields(
    session: SessionDep,
    ds: CoreDatasource,
    table: CoreTable,
    fields: list[ColumnSchema],
) -> None:
    table_id = cast(object, getattr(table, "id", None))
    if not isinstance(table_id, int):
        return
    id_list: list[int] = []
    for index, item in enumerate(fields):
        statement = select(CoreField).where(
            and_(
                col(CoreField.table_id) == table_id,
                col(CoreField.field_name) == item.fieldName,
            )
        )
        record = session.exec(statement).first()
        if record is not None:
            id_list.append(record.id)

            record.field_comment = item.fieldComment or ""
            record.field_index = index
            record.field_type = item.fieldType
            session.add(record)
            session.commit()
        else:
            field = CoreField.model_construct(
                ds_id=ds.id,
                table_id=table_id,
                checked=True,
                field_name=item.fieldName,
                field_type=item.fieldType,
                field_comment=item.fieldComment or "",
                custom_comment=item.fieldComment or "",
                field_index=index,
            )
            session.add(field)
            session.flush()
            session.refresh(field)
            id_list.append(field.id)
            session.commit()

    if len(id_list) > 0:
        _ = session.exec(
            delete(CoreField).where(
                and_(
                    col(CoreField.table_id) == table_id,
                    col(CoreField.id).not_in(id_list),
                )
            )
        )
        session.commit()


def update_table_and_fields(session: SessionDep, data: TableObj) -> None:
    if data.table is None:
        return
    update_table(session, data.table)
    for field in data.fields:
        update_field(session, field)

    # do table embedding
    table_id = cast(object, getattr(data.table, "id", None))
    if not isinstance(table_id, int):
        return
    run_save_table_embeddings([table_id])
    run_save_ds_embeddings([data.table.ds_id])


def updateTable(session: SessionDep, table: CoreTable) -> None:
    update_table(session, table)

    # do table embedding
    run_save_table_embeddings([table.id])
    run_save_ds_embeddings([table.ds_id])


def updateField(session: SessionDep, field: CoreField) -> None:
    update_field(session, field)

    # do table embedding
    run_save_table_embeddings([field.table_id])
    run_save_ds_embeddings([field.ds_id])


def preview(
    session: SessionDep, current_user: CurrentUser, id: int, data: TableObj
) -> ObjectDict:
    ds = session.exec(
        select(CoreDatasource).where(col(CoreDatasource.id) == id)
    ).first()
    if ds is None:
        return {"fields": [], "data": [], "sql": ""}
    # check_status(session, ds, True)

    # ignore data's fields param, query fields from database
    if data.table is None:
        return {"fields": [], "data": [], "sql": ""}

    table = data.table

    fields = list(
        session.exec(
            select(CoreField)
            .where(col(CoreField.table_id) == table.id)
            .order_by(col(CoreField.field_index).asc())
        ).all()
    )

    if not fields:
        return {"fields": [], "data": [], "sql": ""}

    where = ""
    f_list: list[CoreField] = [field for field in fields if field.checked]
    if is_normal_user(current_user):
        # column is checked, and, column permission for data.fields
        ds_rules_model = _get_ds_rules_model()
        contain_rules = cast(
            list[DsRulesRecordProtocol],
            list(session.exec(select(ds_rules_model)).all()),
        )
        f_list = get_column_permission_fields(
            session=session,
            current_user=current_user,
            table=table,
            fields=f_list,
            contain_rules=contain_rules,
        )

        # row permission tree
        where_str = ""
        filter_mapping = get_row_permission_filters(
            session=session,
            current_user=current_user,
            ds=ds,
            tables=None,
            single_table=table,
        )
        if filter_mapping:
            mapping_dict = filter_mapping[0]
            where_str = mapping_dict.get("filter") or ""
        where = (" where " + where_str) if where_str else ""

    field_names = [field.field_name for field in f_list]
    if not field_names:
        return {"fields": [], "data": [], "sql": ""}

    conf = _get_datasource_conf(ds) if ds.type != "excel" else get_engine_config()
    sql: str = ""
    if ds.type == "mysql" or ds.type == "doris" or ds.type == "starrocks":
        sql = f"""SELECT `{"`, `".join(field_names)}` FROM `{table.table_name}`
            {where}
            LIMIT 100"""
    elif ds.type == "sqlServer":
        sql = f"""SELECT TOP 100 [{"], [".join(field_names)}] FROM [{conf.dbSchema}].[{table.table_name}]
            {where}
            """
    elif (
        ds.type == "pg"
        or ds.type == "excel"
        or ds.type == "redshift"
        or ds.type == "kingbase"
    ):
        sql = f"""SELECT "{'", "'.join(field_names)}" FROM "{conf.dbSchema}"."{table.table_name}"
            {where}
            LIMIT 100"""
    elif ds.type == "oracle":
        # sql = f"""SELECT "{'", "'.join(fields)}" FROM "{conf.dbSchema}"."{data.table.table_name}"
        #     {where}
        #     ORDER BY "{fields[0]}"
        #     OFFSET 0 ROWS FETCH NEXT 100 ROWS ONLY"""
        sql = f"""SELECT * FROM
                    (SELECT "{'", "'.join(field_names)}" FROM "{conf.dbSchema}"."{table.table_name}"
                    {where}
                    ORDER BY "{field_names[0]}")
                    WHERE ROWNUM <= 100
                    """
    elif ds.type == "ck":
        sql = f"""SELECT "{'", "'.join(field_names)}" FROM "{table.table_name}"
            {where}
            LIMIT 100"""
    elif ds.type == "dm":
        sql = f"""SELECT "{'", "'.join(field_names)}" FROM "{conf.dbSchema}"."{table.table_name}"
            {where}
            LIMIT 100"""
    elif ds.type == "es":
        sql = f"""SELECT "{'", "'.join(field_names)}" FROM "{table.table_name}"
            {where}
            LIMIT 100"""
    return exec_sql(ds, sql, True)


def fieldEnum(session: SessionDep, id: int) -> list[object]:
    field = session.get(CoreField, id)
    if field is None:
        return []
    table = session.get(CoreTable, field.table_id)
    if table is None:
        return []
    ds = session.get(CoreDatasource, table.ds_id)
    if ds is None:
        return []

    db = DB.get_db(ds.type)
    sql = f"""SELECT DISTINCT {db.prefix}{field.field_name}{db.suffix} FROM {db.prefix}{table.table_name}{db.suffix}"""
    res = cast(ObjectDict, exec_sql(ds, sql, True))
    fields = _as_object_list(res.get("fields"))
    data = _as_object_dict_list(res.get("data"))
    if not fields:
        return []
    key = fields[0]
    if not isinstance(key, str):
        return []
    return [item.get(key) for item in data]


def updateNum(session: SessionDep, ds: CoreDatasource) -> None:
    all_tables = (
        get_tables(ds) if ds.type != "excel" else _get_datasource_conf(ds).sheets
    )
    all_tables_list = all_tables or []
    ds_id = cast(object, ds.id)
    if not isinstance(ds_id, int):
        return
    selected_tables = get_tables_by_ds_id(session, ds_id)
    num = f"{len(selected_tables)}/{len(all_tables_list)}"

    record = session.exec(
        select(CoreDatasource).where(col(CoreDatasource.id) == ds_id)
    ).first()
    if record is None:
        return
    update_data = cast(dict[str, object], ds.model_dump(exclude_unset=True))
    for field, value in update_data.items():
        setattr(record, field, value)
    record.num = num
    session.add(record)
    session.commit()


def get_table_obj_by_ds(
    session: SessionDep, current_user: CurrentUser, ds: CoreDatasource
) -> list[TableAndFields]:
    _list: list[TableAndFields] = []
    tables = list(
        session.exec(select(CoreTable).where(col(CoreTable.ds_id) == ds.id)).all()
    )
    conf = _get_datasource_conf(ds) if ds.type != "excel" else get_engine_config()
    schema = conf.dbSchema if conf.dbSchema != "" else conf.database

    # get all field
    table_ids = [table.id for table in tables]
    all_fields = list(
        session.exec(
            select(CoreField).where(
                and_(
                    col(CoreField.table_id).in_(table_ids),
                    col(CoreField.checked).is_(True),
                )
            )
        )
    )
    # build dict
    fields_dict: dict[int, list[CoreField]] = {}
    for field in all_fields:
        fields_dict.setdefault(field.table_id, []).append(field)

    ds_rules_model = _get_ds_rules_model()
    contain_rules = cast(
        list[DsRulesRecordProtocol],
        list(session.exec(select(ds_rules_model)).all()),
    )
    for table in tables:
        fields = fields_dict.get(table.id, [])

        # do column permissions, filter fields
        fields = get_column_permission_fields(
            session=session,
            current_user=current_user,
            table=table,
            fields=fields,
            contain_rules=contain_rules,
        )
        _list.append(TableAndFields(schema=schema, table=table, fields=fields))
    return _list


def get_table_schema(
    session: SessionDep,
    current_user: CurrentUser,
    ds: CoreDatasource,
    question: str,
    embedding: bool = True,
    table_list: list[str] | None = None,
) -> str:
    schema_str = ""
    table_objs = get_table_obj_by_ds(session=session, current_user=current_user, ds=ds)
    if len(table_objs) == 0:
        return schema_str
    db_name = table_objs[0].schema
    schema_str += f"【DB_ID】 {db_name}\n【Schema】\n"
    tables: list[SchemaTableDict] = []
    all_tables: list[SchemaTableDict] = []  # temp save all tables
    for obj in table_objs:
        # 如果传入了table_list，则只处理在列表中的表
        if table_list is not None and obj.table.table_name not in table_list:
            continue

        schema_table = ""
        schema_table += (
            f"# Table: {db_name}.{obj.table.table_name}"
            if ds.type != "mysql" and ds.type != "es"
            else f"# Table: {obj.table.table_name}"
        )
        table_comment = ""
        if obj.table.custom_comment:
            table_comment = obj.table.custom_comment.strip()
        if table_comment == "":
            schema_table += "\n[\n"
        else:
            schema_table += f", {table_comment}\n[\n"

        if obj.fields:
            field_list: list[str] = []
            for field in obj.fields:
                field_comment = ""
                if field.custom_comment:
                    field_comment = field.custom_comment.strip()
                if field_comment == "":
                    field_list.append(f"({field.field_name}:{field.field_type})")
                else:
                    field_list.append(
                        f"({field.field_name}:{field.field_type}, {field_comment})"
                    )
            schema_table += ",\n".join(field_list)
        schema_table += "\n]\n"

        t_obj: SchemaTableDict = {
            "id": obj.table.id,
            "schema_table": schema_table,
            "embedding": obj.table.embedding,
        }
        tables.append(t_obj)
        all_tables.append(t_obj)

    # 如果没有符合过滤条件的表，直接返回
    if not tables:
        return schema_str

    # do table embedding
    if embedding and tables and settings.TABLE_EMBEDDING_ENABLED:
        tables = cast(list[SchemaTableDict], calc_table_embedding(tables, question))
    # splice schema
    if tables:
        for s in tables:
            schema_str += str(s.get("schema_table") or "")

    # field relation
    relation_source = _as_object_dict_list(ds.table_relation or [])
    if tables and relation_source:
        relations = [rel for rel in relation_source if _get_str(rel, "shape") == "edge"]
        if relations:
            # Complete the missing table
            # get tables in relation, remove irrelevant relation
            embedding_table_ids: list[int] = []
            for table_info in tables:
                table_id = table_info.get("id")
                if isinstance(table_id, int):
                    embedding_table_ids.append(table_id)
            all_relations = list(
                filter(
                    lambda relation: (
                        _get_int(_as_object_dict(relation.get("source")) or {}, "cell")
                        in embedding_table_ids
                        or _get_int(
                            _as_object_dict(relation.get("target")) or {}, "cell"
                        )
                        in embedding_table_ids
                    ),
                    relations,
                )
            )

            # get relation table ids, sub embedding table ids
            relation_table_ids: list[int] = []
            for r in all_relations:
                source = _as_object_dict(r.get("source")) or {}
                target = _as_object_dict(r.get("target")) or {}
                source_cell = _get_int(source, "cell")
                target_cell = _get_int(target, "cell")
                if isinstance(source_cell, int):
                    relation_table_ids.append(source_cell)
                if isinstance(target_cell, int):
                    relation_table_ids.append(target_cell)
            relation_table_ids = list(set(relation_table_ids))
            table_records = list(
                session.exec(
                    select(CoreTable).where(col(CoreTable.id).in_(relation_table_ids))
                ).all()
            )
            table_dict: dict[int, str] = {}
            for ele in table_records:
                table_dict[ele.id] = ele.table_name

            # get lost table ids
            lost_table_ids = list(set(relation_table_ids) - set(embedding_table_ids))
            # get lost table schema and splice it
            lost_tables = list(
                filter(
                    lambda table_info: table_info.get("id") in lost_table_ids,
                    all_tables,
                )
            )
            if lost_tables:
                for s in lost_tables:
                    schema_str += str(s.get("schema_table") or "")

            # get field dict
            relation_field_ids: list[int] = []
            for relation in all_relations:
                source = _as_object_dict(relation.get("source")) or {}
                target = _as_object_dict(relation.get("target")) or {}
                source_port = _get_int(source, "port")
                target_port = _get_int(target, "port")
                if isinstance(source_port, int):
                    relation_field_ids.append(source_port)
                if isinstance(target_port, int):
                    relation_field_ids.append(target_port)
            relation_field_ids = list(set(relation_field_ids))
            field_records = list(
                session.exec(
                    select(CoreField).where(col(CoreField.id).in_(relation_field_ids))
                ).all()
            )
            field_dict: dict[int, str] = {}
            for field_record in field_records:
                field_dict[field_record.id] = field_record.field_name

            if all_relations:
                schema_str += "【Foreign keys】\n"
                for relation_item in all_relations:
                    source = _as_object_dict(relation_item.get("source")) or {}
                    target = _as_object_dict(relation_item.get("target")) or {}
                    source_cell = _get_int(source, "cell")
                    target_cell = _get_int(target, "cell")
                    source_port = _get_int(source, "port")
                    target_port = _get_int(target, "port")
                    left_table = (
                        table_dict.get(source_cell, "")
                        if isinstance(source_cell, int)
                        else ""
                    )
                    right_table = (
                        table_dict.get(target_cell, "")
                        if isinstance(target_cell, int)
                        else ""
                    )
                    left_field = (
                        field_dict.get(source_port, "")
                        if isinstance(source_port, int)
                        else ""
                    )
                    right_field = (
                        field_dict.get(target_port, "")
                        if isinstance(target_port, int)
                        else ""
                    )
                    schema_str += (
                        f"{left_table}.{left_field}={right_table}.{right_field}\n"
                    )

    return schema_str


@cache(
    namespace=str(CacheNamespace.AUTH_INFO),
    cacheName=str(CacheName.DS_ID_LIST),
    keyExpression="oid",
)
async def get_ws_ds(session: SessionDep, oid: int) -> list[int]:
    stmt = (
        select(col(CoreDatasource.id)).distinct().where(col(CoreDatasource.oid) == oid)
    )
    db_list = session.exec(stmt).all()
    return [db_id for db_id in db_list if isinstance(db_id, int)]


@clear_cache(
    namespace=str(CacheNamespace.AUTH_INFO),
    cacheName=str(CacheName.DS_ID_LIST),
    keyExpression="oid",
)
async def clear_ws_ds_cache(oid: int) -> None:
    SQLBotLogUtil.info(f"ds cache for ws [{oid}] has been cleaned")

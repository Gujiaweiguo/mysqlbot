import base64
import importlib
import json
import os
import platform
import urllib.parse
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, cast

import oracledb
import sqlglot
from fastapi import HTTPException
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlglot import expressions as exp

from apps.datasource.models.datasource import (
    ColumnSchema,
    CoreDatasource,
    DatasourceConf,
    TableSchema,
)
from apps.datasource.utils.utils import aes_decrypt
from apps.db.constant import DB, ConnectType
from apps.db.db_sql import get_field_sql, get_table_sql, get_version_sql
from apps.db.engine import get_engine_config
from apps.db.es_engine import (
    get_es_connect,
    get_es_data_by_http,
    get_es_fields,
    get_es_index,
)
from apps.system.crud.assistant import get_out_ds_conf
from apps.system.schemas.system_schema import AssistantOutDsSchema
from common.core.config import settings
from common.core.deps import Trans
from common.error import ParseSQLResultError
from common.utils.utils import SQLBotLogUtil, equals_ignore_case

dmPython: Any | None = None
if platform.system() != "Darwin":
    dmPython = cast(Any, importlib.import_module("dmPython"))

pymssql = cast(Any, importlib.import_module("pymssql"))
psycopg2 = cast(Any, importlib.import_module("psycopg2"))
pymysql = cast(Any, importlib.import_module("pymysql"))
redshift_connector = cast(Any, importlib.import_module("redshift_connector"))

try:
    if os.path.exists(settings.ORACLE_CLIENT_PATH):
        oracledb.init_oracle_client(lib_dir=settings.ORACLE_CLIENT_PATH)
        SQLBotLogUtil.info("init oracle client success, use thick mode")
    else:
        SQLBotLogUtil.info(
            "init oracle client failed, because not found oracle client, use thin mode"
        )
except Exception:
    SQLBotLogUtil.error(
        "init oracle client failed, check your client is installed, use thin mode"
    )


def _decrypt_configuration(config: str | bytes | None) -> str:
    if config is None:
        raise Exception("Datasource configuration is missing")
    if isinstance(config, bytes):
        return aes_decrypt(config)
    return aes_decrypt(config.encode("utf-8"))


def _get_ds_type(ds: CoreDatasource | AssistantOutDsSchema) -> str:
    return cast(str, ds.type)


def _require_dm_python() -> Any:
    if dmPython is None:
        raise Exception("dmPython is not available")
    return dmPython


def _normalize_out_configuration(config: str | bytes | None) -> str:
    if config is None:
        raise Exception("Datasource configuration is missing")
    if isinstance(config, bytes):
        return config.decode("utf-8")
    return config


def get_uri(ds: CoreDatasource | AssistantOutDsSchema) -> str:
    ds_type = _get_ds_type(ds)
    conf = (
        DatasourceConf(**json.loads(_decrypt_configuration(ds.configuration)))
        if not equals_ignore_case(ds_type, "excel")
        else get_engine_config()
    )
    return get_uri_from_config(ds_type, conf)


def get_uri_from_config(type: str, conf: DatasourceConf) -> str:
    db_url: str
    if equals_ignore_case(type, "mysql"):
        if conf.extraJdbc is not None and conf.extraJdbc != "":
            db_url = f"mysql+pymysql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"mysql+pymysql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "sqlServer"):
        if conf.extraJdbc is not None and conf.extraJdbc != "":
            db_url = f"mssql+pymssql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"mssql+pymssql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "pg", "excel"):
        if conf.extraJdbc is not None and conf.extraJdbc != "":
            db_url = f"postgresql+psycopg2://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"postgresql+psycopg2://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "oracle"):
        if equals_ignore_case(conf.mode, "service_name", "serviceName"):
            if conf.extraJdbc is not None and conf.extraJdbc != "":
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}?service_name={conf.database}&{conf.extraJdbc}"
            else:
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}?service_name={conf.database}"
        else:
            if conf.extraJdbc is not None and conf.extraJdbc != "":
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
            else:
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "ck"):
        if conf.extraJdbc is not None and conf.extraJdbc != "":
            db_url = f"clickhouse+http://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"clickhouse+http://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    else:
        raise Exception("The datasource type not support.")
    return db_url


def get_extra_config(conf: DatasourceConf) -> dict[str, str]:
    config_dict: dict[str, str] = {}
    if conf.extraJdbc:
        config_arr = conf.extraJdbc.split("&")
        for config in config_arr:
            kv = config.split("=")
            if len(kv) == 2 and kv[0] and kv[1]:
                config_dict[kv[0]] = kv[1]
            else:
                raise Exception(f"param: {config} is error")
    return config_dict


def get_origin_connect(type: str, conf: DatasourceConf) -> Any:
    extra_config_dict = get_extra_config(conf)
    if equals_ignore_case(type, "sqlServer"):
        # none or true, set tds_version = 7.0
        if conf.lowVersion is None or conf.lowVersion:
            return pymssql.connect(
                server=conf.host,
                port=str(conf.port),
                user=conf.username,
                password=conf.password,
                database=conf.database,
                timeout=conf.timeout,
                tds_version="7.0",  # options: '4.2', '7.0', '8.0' ...,
                **extra_config_dict,
            )
        else:
            return pymssql.connect(
                server=conf.host,
                port=str(conf.port),
                user=conf.username,
                password=conf.password,
                database=conf.database,
                timeout=conf.timeout,
                **extra_config_dict,
            )


def get_engine(ds: CoreDatasource | AssistantOutDsSchema, timeout: int = 0) -> Engine:
    ds_type = _get_ds_type(ds)
    conf = (
        DatasourceConf(**json.loads(_decrypt_configuration(ds.configuration)))
        if not equals_ignore_case(ds_type, "excel")
        else get_engine_config()
    )
    if conf.timeout is None:
        conf.timeout = timeout
    if timeout > 0:
        conf.timeout = timeout

    if equals_ignore_case(ds_type, "pg"):
        if conf.dbSchema is not None and conf.dbSchema != "":
            engine = create_engine(
                get_uri(ds),
                connect_args={
                    "options": f"-c search_path={urllib.parse.quote(conf.dbSchema)}",
                    "connect_timeout": conf.timeout,
                },
                poolclass=NullPool,
            )
        else:
            engine = create_engine(
                get_uri(ds),
                connect_args={"connect_timeout": conf.timeout},
                poolclass=NullPool,
            )
    elif equals_ignore_case(ds_type, "sqlServer"):
        engine = create_engine(
            "mssql+pymssql://",
            creator=lambda: get_origin_connect(ds_type, conf),
            poolclass=NullPool,
        )
    elif equals_ignore_case(ds_type, "oracle"):
        engine = create_engine(get_uri(ds), poolclass=NullPool)
    else:  # mysql, ck
        engine = create_engine(
            get_uri(ds),
            connect_args={"connect_timeout": conf.timeout},
            poolclass=NullPool,
        )
    return engine


def get_session(ds: CoreDatasource | AssistantOutDsSchema) -> Session:
    # engine = get_engine(ds) if isinstance(ds, CoreDatasource) else get_ds_engine(ds)
    if isinstance(ds, AssistantOutDsSchema):
        out_conf = _normalize_out_configuration(get_out_ds_conf(ds, 30))
        ds.configuration = out_conf

    engine = get_engine(ds)
    session_maker = sessionmaker(bind=engine)
    session = session_maker()
    return session


def check_connection(
    trans: Trans | None,
    ds: CoreDatasource | AssistantOutDsSchema,
    is_raise: bool = False,
) -> bool:
    if isinstance(ds, AssistantOutDsSchema):
        out_conf = _normalize_out_configuration(get_out_ds_conf(ds, 10))
        ds.configuration = out_conf

    trans_func = trans if trans is not None else (lambda message: message)

    ds_type = _get_ds_type(ds)
    db = DB.get_db(ds_type)
    if db.connect_type == ConnectType.sqlalchemy:
        conn = get_engine(ds, 10)
        try:
            with conn.connect():
                SQLBotLogUtil.info("success")
                return True
        except Exception as e:
            SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
            if is_raise:
                raise HTTPException(
                    status_code=500,
                    detail=trans_func("i18n_ds_invalid") + f": {e.args}",
                )
            return False
    else:
        conf = DatasourceConf(**json.loads(_decrypt_configuration(ds.configuration)))
        extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds_type, "dm"):
            with (
                _require_dm_python().connect(
                    user=conf.username,
                    password=conf.password,
                    server=conf.host,
                    port=conf.port,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                try:
                    cursor.execute("select 1", timeout=10).fetchall()
                    SQLBotLogUtil.info("success")
                    return True
                except Exception as e:
                    SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                    if is_raise:
                        raise HTTPException(
                            status_code=500,
                            detail=trans_func("i18n_ds_invalid") + f": {e.args}",
                        )
                    return False
        elif equals_ignore_case(ds_type, "doris", "starrocks"):
            with (
                pymysql.connect(
                    user=conf.username,
                    passwd=conf.password,
                    host=conf.host,
                    port=conf.port,
                    db=conf.database,
                    connect_timeout=10,
                    read_timeout=10,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                try:
                    cursor.execute("select 1")
                    SQLBotLogUtil.info("success")
                    return True
                except Exception as e:
                    SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                    if is_raise:
                        raise HTTPException(
                            status_code=500,
                            detail=trans_func("i18n_ds_invalid") + f": {e.args}",
                        )
                    return False
        elif equals_ignore_case(ds_type, "redshift"):
            with (
                redshift_connector.connect(
                    host=conf.host,
                    port=conf.port,
                    database=conf.database,
                    user=conf.username,
                    password=conf.password,
                    timeout=10,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                try:
                    cursor.execute("select 1")
                    SQLBotLogUtil.info("success")
                    return True
                except Exception as e:
                    SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                    if is_raise:
                        raise HTTPException(
                            status_code=500,
                            detail=trans_func("i18n_ds_invalid") + f": {e.args}",
                        )
                    return False
        elif equals_ignore_case(ds_type, "kingbase"):
            with (
                psycopg2.connect(
                    host=conf.host,
                    port=conf.port,
                    database=conf.database,
                    user=conf.username,
                    password=conf.password,
                    connect_timeout=10,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                try:
                    cursor.execute("select 1")
                    SQLBotLogUtil.info("success")
                    return True
                except Exception as e:
                    SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                    if is_raise:
                        raise HTTPException(
                            status_code=500,
                            detail=trans_func("i18n_ds_invalid") + f": {e.args}",
                        )
                    return False
        elif equals_ignore_case(ds_type, "es"):
            es_conn = get_es_connect(conf)
            if es_conn.ping():
                SQLBotLogUtil.info("success")
                return True
            else:
                SQLBotLogUtil.info("failed")
                return False
    # else:
    #     conn = get_ds_engine(ds)
    #     try:
    #         with conn.connect() as connection:
    #             SQLBotLogUtil.info("success")
    #             return True
    #     except Exception as e:
    #         SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
    #         if is_raise:
    #             raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
    #         return False

    return False


def get_version(ds: CoreDatasource | AssistantOutDsSchema) -> str:
    version = ""
    ds_type = _get_ds_type(ds)
    if isinstance(ds, CoreDatasource):
        conf = (
            DatasourceConf(**json.loads(_decrypt_configuration(ds.configuration)))
            if not equals_ignore_case(ds_type, "excel")
            else get_engine_config()
        )
    else:
        conf = DatasourceConf(
            **json.loads(_decrypt_configuration(get_out_ds_conf(ds, 10)))
        )
    # if isinstance(ds, AssistantOutDsSchema):
    #     conf = DatasourceConf()
    #     conf.host = ds.host
    #     conf.port = ds.port
    #     conf.username = ds.user
    #     conf.password = ds.password
    #     conf.database = ds.dataBase
    #     conf.dbSchema = ds.db_schema
    #     conf.timeout = 10
    db = DB.get_db(ds_type)
    core_ds = cast(CoreDatasource, ds)
    sql = get_version_sql(core_ds, conf)
    try:
        if db.connect_type == ConnectType.sqlalchemy:
            with get_session(ds) as session:
                with session.execute(text(sql)) as result:
                    res = result.fetchall()
                    version = res[0][0]
        else:
            extra_config_dict = get_extra_config(conf)
            if equals_ignore_case(ds_type, "dm"):
                with (
                    _require_dm_python().connect(
                        user=conf.username,
                        password=conf.password,
                        server=conf.host,
                        port=conf.port,
                    ) as conn,
                    conn.cursor() as cursor,
                ):
                    cursor.execute(sql, timeout=10, **extra_config_dict)
                    res = cursor.fetchall()
                    version = res[0][0]
            elif equals_ignore_case(ds_type, "doris", "starrocks"):
                with (
                    pymysql.connect(
                        user=conf.username,
                        passwd=conf.password,
                        host=conf.host,
                        port=conf.port,
                        db=conf.database,
                        connect_timeout=10,
                        read_timeout=10,
                        **extra_config_dict,
                    ) as conn,
                    conn.cursor() as cursor,
                ):
                    cursor.execute(sql)
                    res = cursor.fetchall()
                    version = res[0][0]
            elif equals_ignore_case(ds_type, "redshift", "es"):
                version = ""
    except Exception as e:
        print(e)
        version = ""
    return version.decode() if isinstance(version, bytes) else version


def get_schema(ds: CoreDatasource) -> list[str] | None:
    ds_type = ds.type
    conf = (
        DatasourceConf(**json.loads(_decrypt_configuration(ds.configuration)))
        if ds_type != "excel"
        else get_engine_config()
    )
    db = DB.get_db(ds_type)
    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            sql: str = ""
            if equals_ignore_case(ds_type, "sqlServer"):
                sql = """select name
                         from sys.schemas"""
            elif equals_ignore_case(ds_type, "pg", "excel"):
                sql = """SELECT nspname
                         FROM pg_namespace"""
            elif equals_ignore_case(ds_type, "oracle"):
                sql = """select *
                         from all_users"""
            with session.execute(text(sql)) as result:
                res = result.fetchall()
                res_list = [item[0] for item in res]
                return res_list
    else:
        extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds_type, "dm"):
            with (
                _require_dm_python().connect(
                    user=conf.username,
                    password=conf.password,
                    server=conf.host,
                    port=conf.port,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                cursor.execute(
                    """select OBJECT_NAME
                                  from dba_objects
                                  where object_type = 'SCH'""",
                    timeout=conf.timeout,
                )
                res = cursor.fetchall()
                res_list = [item[0] for item in res]
                return res_list
        elif equals_ignore_case(ds_type, "redshift"):
            with (
                redshift_connector.connect(
                    host=conf.host,
                    port=conf.port,
                    database=conf.database,
                    user=conf.username,
                    password=conf.password,
                    timeout=conf.timeout,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                cursor.execute("""SELECT nspname
                                  FROM pg_namespace""")
                res = cursor.fetchall()
                res_list = [item[0] for item in res]
                return res_list
        elif equals_ignore_case(ds_type, "kingbase"):
            with (
                psycopg2.connect(
                    host=conf.host,
                    port=conf.port,
                    database=conf.database,
                    user=conf.username,
                    password=conf.password,
                    options=f"-c statement_timeout={conf.timeout * 1000}",
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                cursor.execute("""SELECT nspname
                                  FROM pg_namespace""")
                res = cursor.fetchall()
                res_list = [item[0] for item in res]
                return res_list

    return None


def get_tables(ds: CoreDatasource) -> list[TableSchema] | None:
    ds_type = ds.type
    conf = (
        DatasourceConf(**json.loads(_decrypt_configuration(ds.configuration)))
        if not equals_ignore_case(ds_type, "excel")
        else get_engine_config()
    )
    db = DB.get_db(ds_type)
    sql, sql_param = get_table_sql(ds, conf, get_version(ds))
    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            with session.execute(text(sql), {"param": sql_param}) as result:
                res = result.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
    else:
        extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds_type, "dm"):
            with (
                _require_dm_python().connect(
                    user=conf.username,
                    password=conf.password,
                    server=conf.host,
                    port=conf.port,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                cursor.execute(sql, {"param": sql_param}, timeout=conf.timeout)
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds_type, "doris", "starrocks"):
            with (
                pymysql.connect(
                    user=conf.username,
                    passwd=conf.password,
                    host=conf.host,
                    port=conf.port,
                    db=conf.database,
                    connect_timeout=conf.timeout,
                    read_timeout=conf.timeout,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                cursor.execute(sql, (sql_param,))
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds_type, "redshift"):
            with (
                redshift_connector.connect(
                    host=conf.host,
                    port=conf.port,
                    database=conf.database,
                    user=conf.username,
                    password=conf.password,
                    timeout=conf.timeout,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                cursor.execute(sql, (sql_param,))
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds_type, "kingbase"):
            with (
                psycopg2.connect(
                    host=conf.host,
                    port=conf.port,
                    database=conf.database,
                    user=conf.username,
                    password=conf.password,
                    options=f"-c statement_timeout={conf.timeout * 1000}",
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                cursor.execute(sql.format(sql_param))
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds_type, "es"):
            es_indexes = get_es_index(conf)
            res_list = [TableSchema(*item) for item in es_indexes]
            return res_list

    return None


def get_fields(
    ds: CoreDatasource, table_name: str | None = None
) -> list[ColumnSchema] | None:
    ds_type = ds.type
    conf = (
        DatasourceConf(**json.loads(_decrypt_configuration(ds.configuration)))
        if not equals_ignore_case(ds_type, "excel")
        else get_engine_config()
    )
    db = DB.get_db(ds_type)
    sql, p1, p2 = get_field_sql(ds, conf, table_name)
    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            with session.execute(text(sql), {"param1": p1, "param2": p2}) as result:
                res = result.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
    else:
        extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds_type, "dm"):
            with (
                _require_dm_python().connect(
                    user=conf.username,
                    password=conf.password,
                    server=conf.host,
                    port=conf.port,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                cursor.execute(sql, {"param1": p1, "param2": p2}, timeout=conf.timeout)
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds_type, "doris", "starrocks"):
            with (
                pymysql.connect(
                    user=conf.username,
                    passwd=conf.password,
                    host=conf.host,
                    port=conf.port,
                    db=conf.database,
                    connect_timeout=conf.timeout,
                    read_timeout=conf.timeout,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                cursor.execute(sql, (p1, p2))
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds_type, "redshift"):
            with (
                redshift_connector.connect(
                    host=conf.host,
                    port=conf.port,
                    database=conf.database,
                    user=conf.username,
                    password=conf.password,
                    timeout=conf.timeout,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                cursor.execute(sql, (p1, p2))
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds_type, "kingbase"):
            with (
                psycopg2.connect(
                    host=conf.host,
                    port=conf.port,
                    database=conf.database,
                    user=conf.username,
                    password=conf.password,
                    options=f"-c statement_timeout={conf.timeout * 1000}",
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                cursor.execute(sql.format(p1, p2))
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds_type, "es"):
            table_name_value = table_name or ""
            es_fields = get_es_fields(conf, table_name_value)
            res_list = [ColumnSchema(*item) for item in es_fields]
            return res_list

    return None


def convert_value(value: Any, datetime_format: str = "space") -> Any:
    """
    将Python值转换为JSON可序列化的类型

    :param value: 要转换的值
    :param datetime_format: 日期时间格式
        'iso' - 2024-01-15T14:30:45 (ISO标准，带T)
        'space' - 2024-01-15 14:30:45 (空格分隔，更常见)
        'auto' - 自动选择
    """
    if value is None:
        return None
        # 处理 bytes 类型（包括 BIT 字段）
    if isinstance(value, bytes):
        # 1. 尝试判断是否是 BIT 类型
        if len(value) <= 8:  # BIT 类型通常不会很长
            try:
                # 转换为整数
                int_val = int.from_bytes(value, "big")

                # 如果是 0 或 1，返回布尔值更直观
                if int_val in (0, 1):
                    return bool(int_val)
                else:
                    return int_val
            except Exception:
                # 如果转换失败，尝试解码为字符串
                pass

        # 2. 尝试解码为 UTF-8 字符串
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            # 3. 如果包含非打印字符，返回十六进制
            if any(b < 32 and b not in (9, 10, 13) for b in value):  # 非打印字符
                return f"0x{value.hex()}"
            else:
                # 4. 尝试 Latin-1 解码（不会失败）
                return value.decode("latin-1")

    elif isinstance(value, bytearray):
        # 处理 bytearray
        return convert_value(bytes(value))

    if isinstance(value, timedelta):
        # 将 timedelta 转换为秒数（整数）或字符串
        return str(value)  # 或 value.total_seconds()
    elif isinstance(value, Decimal):
        return float(value)
    # 4. 处理 datetime
    elif isinstance(value, datetime):
        if datetime_format == "iso":
            return value.isoformat()
        elif datetime_format == "space":
            return value.strftime("%Y-%m-%d %H:%M:%S")
        else:  # 'auto' 或其他
            # 自动判断：没有时间部分只显示日期
            if (
                value.hour == 0
                and value.minute == 0
                and value.second == 0
                and value.microsecond == 0
            ):
                return value.strftime("%Y-%m-%d")
            else:
                return value.strftime("%Y-%m-%d %H:%M:%S")

    # 5. 处理 date
    elif isinstance(value, date):
        return value.isoformat()  # 总是 YYYY-MM-DD

    # 6. 处理 time
    elif isinstance(value, time):
        return str(value)
    else:
        return value


def exec_sql(
    ds: CoreDatasource | AssistantOutDsSchema,
    sql: str,
    origin_column: bool = False,
) -> dict[str, Any]:
    while sql.endswith(";"):
        sql = sql[:-1]
    # check execute sql only contain read operations
    if not check_sql_read(sql, ds):
        raise ValueError("SQL can only contain read operations")

    ds_type = _get_ds_type(ds)
    db = DB.get_db(ds_type)
    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            with session.execute(text(sql)) as result:
                try:
                    columns = (
                        result.keys()._keys
                        if origin_column
                        else [item.lower() for item in result.keys()._keys]
                    )
                    res = result.fetchall()
                    result_list = [
                        {
                            str(columns[i]): convert_value(value)
                            for i, value in enumerate(tuple_item)
                        }
                        for tuple_item in res
                    ]
                    return {
                        "fields": columns,
                        "data": result_list,
                        "sql": bytes.decode(base64.b64encode(bytes(sql, "utf-8"))),
                    }
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
    else:
        conf = DatasourceConf(**json.loads(_decrypt_configuration(ds.configuration)))
        extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds_type, "dm"):
            with (
                _require_dm_python().connect(
                    user=conf.username,
                    password=conf.password,
                    server=conf.host,
                    port=conf.port,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                try:
                    cursor.execute(sql, timeout=conf.timeout)
                    res = cursor.fetchall()
                    columns = (
                        [str(field[0]) for field in cursor.description]
                        if origin_column
                        else [str(field[0]).lower() for field in cursor.description]
                    )
                    result_list = [
                        {
                            str(columns[i]): convert_value(value)
                            for i, value in enumerate(tuple_item)
                        }
                        for tuple_item in res
                    ]
                    return {
                        "fields": columns,
                        "data": result_list,
                        "sql": bytes.decode(base64.b64encode(bytes(sql, "utf-8"))),
                    }
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
        elif equals_ignore_case(ds_type, "doris", "starrocks"):
            with (
                pymysql.connect(
                    user=conf.username,
                    passwd=conf.password,
                    host=conf.host,
                    port=conf.port,
                    db=conf.database,
                    connect_timeout=conf.timeout,
                    read_timeout=conf.timeout,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                try:
                    cursor.execute(sql)
                    res = cursor.fetchall()
                    columns = (
                        [str(field[0]) for field in cursor.description]
                        if origin_column
                        else [str(field[0]).lower() for field in cursor.description]
                    )
                    result_list = [
                        {
                            str(columns[i]): convert_value(value)
                            for i, value in enumerate(tuple_item)
                        }
                        for tuple_item in res
                    ]
                    return {
                        "fields": columns,
                        "data": result_list,
                        "sql": bytes.decode(base64.b64encode(bytes(sql, "utf-8"))),
                    }
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
        elif equals_ignore_case(ds_type, "redshift"):
            with (
                redshift_connector.connect(
                    host=conf.host,
                    port=conf.port,
                    database=conf.database,
                    user=conf.username,
                    password=conf.password,
                    timeout=conf.timeout,
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                try:
                    cursor.execute(sql)
                    res = cursor.fetchall()
                    columns = (
                        [str(field[0]) for field in cursor.description]
                        if origin_column
                        else [str(field[0]).lower() for field in cursor.description]
                    )
                    result_list = [
                        {
                            str(columns[i]): convert_value(value)
                            for i, value in enumerate(tuple_item)
                        }
                        for tuple_item in res
                    ]
                    return {
                        "fields": columns,
                        "data": result_list,
                        "sql": bytes.decode(base64.b64encode(bytes(sql, "utf-8"))),
                    }
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
        elif equals_ignore_case(ds_type, "kingbase"):
            with (
                psycopg2.connect(
                    host=conf.host,
                    port=conf.port,
                    database=conf.database,
                    user=conf.username,
                    password=conf.password,
                    options=f"-c statement_timeout={conf.timeout * 1000}",
                    **extra_config_dict,
                ) as conn,
                conn.cursor() as cursor,
            ):
                try:
                    cursor.execute(sql)
                    res = cursor.fetchall()
                    columns = (
                        [str(field[0]) for field in cursor.description]
                        if origin_column
                        else [str(field[0]).lower() for field in cursor.description]
                    )
                    result_list = [
                        {
                            str(columns[i]): convert_value(value)
                            for i, value in enumerate(tuple_item)
                        }
                        for tuple_item in res
                    ]
                    return {
                        "fields": columns,
                        "data": result_list,
                        "sql": bytes.decode(base64.b64encode(bytes(sql, "utf-8"))),
                    }
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
        elif equals_ignore_case(ds_type, "es"):
            try:
                es_rows, es_columns = get_es_data_by_http(conf, sql)
                columns = (
                    [str(field.get("name") or "") for field in es_columns]
                    if origin_column
                    else [str(field.get("name") or "").lower() for field in es_columns]
                )
                result_list = [
                    {
                        str(columns[i]): convert_value(value)
                        for i, value in enumerate(tuple_item)
                    }
                    for tuple_item in es_rows
                ]
                return {
                    "fields": columns,
                    "data": result_list,
                    "sql": bytes.decode(base64.b64encode(bytes(sql, "utf-8"))),
                }
            except Exception as ex:
                raise Exception(str(ex))

    raise ParseSQLResultError("SQL execution returned no result")


def check_sql_read(sql: str, ds: CoreDatasource | AssistantOutDsSchema) -> bool:
    try:
        dialect = None
        ds_type = _get_ds_type(ds)
        if equals_ignore_case(ds_type, "mysql", "doris", "starrocks"):
            dialect = "mysql"
        elif equals_ignore_case(ds_type, "sqlServer"):
            dialect = "tsql"

        statements = sqlglot.parse(sql, dialect=dialect)

        if not statements:
            raise ValueError("Parse SQL Error")

        write_types = (
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Create,
            exp.Drop,
            exp.Alter,
            exp.Merge,
            exp.Command,
        )

        for stmt in statements:
            if stmt is None:
                continue
            if isinstance(stmt, write_types):
                return False

        return True

    except Exception as e:
        raise ValueError(f"Parse SQL Error: {e}")

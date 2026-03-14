# Author: Junjun
# Date: 2025/5/19
import urllib.parse
from typing import Any

from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from apps.datasource.models.datasource import DatasourceConf
from common.core.config import settings


def get_engine_config() -> DatasourceConf:
    return DatasourceConf(
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        dbSchema="public",
        timeout=30,
    )


def get_engine_uri(conf: DatasourceConf) -> str:
    return (
        f"postgresql+psycopg2://{urllib.parse.quote(conf.username)}:"
        f"{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/"
        f"{urllib.parse.quote(conf.database)}"
    )


def get_engine_conn() -> Engine:
    conf = get_engine_config()
    db_url = get_engine_uri(conf)
    engine = create_engine(
        db_url,
        connect_args={
            "options": f"-c search_path={conf.dbSchema}",
            "connect_timeout": conf.timeout,
        },
        pool_timeout=conf.timeout,
    )
    return engine


def get_data_engine() -> Session:
    engine = get_engine_conn()
    session_maker = sessionmaker(bind=engine)
    session = session_maker()
    return session


def create_table(
    session: Session, table_name: str, fields: list[dict[str, str]]
) -> None:
    relation_fields: list[str] = []
    for f in fields:
        field_type = f.get("type", "")
        if "object" in field_type:
            f["relType"] = "text"
        elif "int" in field_type:
            f["relType"] = "bigint"
        elif "float" in field_type:
            f["relType"] = "numeric"
        elif "datetime" in field_type:
            f["relType"] = "timestamp"
        else:
            f["relType"] = "text"
        relation_fields.append(f'"{f["name"]}" {f["relType"]}')

    sql = f"""
            CREATE TABLE "{table_name}" (
                {", ".join(relation_fields)}
            );
            """
    session.execute(text(sql))
    session.commit()


def insert_data(
    _session: Session,
    table_name: str,
    _fields: list[dict[str, str]],
    data: list[dict[str, Any]],
) -> None:
    engine = get_engine_conn()
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    with engine.connect() as conn:
        stmt = table.insert().values(data)
        conn.execute(stmt)
        conn.commit()

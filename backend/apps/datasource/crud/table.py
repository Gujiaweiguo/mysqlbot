import json
import time
import traceback
from typing import Any

from sqlalchemy import or_
from sqlmodel import col, select, update

from apps.ai_model.embedding import EmbeddingModelCache
from apps.system.crud.embedding_admin import embedding_runtime_enabled
from common.core.config import settings
from common.core.deps import SessionDep
from common.utils.utils import SQLBotLogUtil

from ..models.datasource import CoreDatasource, CoreField, CoreTable


MAX_EMBEDDING_INPUT_CHARS = 2000


def _truncate_embedding_input(text: str) -> str:
    if len(text) <= MAX_EMBEDDING_INPUT_CHARS:
        return text

    SQLBotLogUtil.warning(
        f"Embedding input exceeded safe limit ({len(text)} chars), "
        f"truncating to {MAX_EMBEDDING_INPUT_CHARS} chars"
    )
    truncated = text[:MAX_EMBEDDING_INPUT_CHARS]
    last_paren = truncated.rfind(")")
    if last_paren > 0:
        return truncated[: last_paren + 1] + "\n]\n"
    return truncated + "\n]\n"


def delete_table_by_ds_id(session: SessionDep, id: int) -> None:
    session.query(CoreTable).filter(col(CoreTable.ds_id) == id).delete(
        synchronize_session=False
    )
    session.commit()


def get_tables_by_ds_id(session: SessionDep, id: int) -> list[CoreTable]:
    return (
        session.query(CoreTable)
        .filter(col(CoreTable.ds_id) == id)
        .order_by(col(CoreTable.table_name).asc())
        .all()
    )


def update_table(session: SessionDep, item: CoreTable) -> None:
    record = session.query(CoreTable).filter(col(CoreTable.id) == item.id).first()
    if record is None:
        return
    record.checked = item.checked
    record.custom_comment = item.custom_comment
    session.add(record)
    session.commit()


def run_fill_empty_table_and_ds_embedding(session_maker: Any) -> None:
    if not settings.TABLE_EMBEDDING_ENABLED or not embedding_runtime_enabled():
        return

    try:
        session = session_maker()

        SQLBotLogUtil.info("get tables")
        stmt = select(col(CoreTable.id)).where(
            or_(col(CoreTable.embedding).is_(None), col(CoreTable.embedding) == "")
        )
        results = list(session.execute(stmt).scalars().all())
        SQLBotLogUtil.info("table result: " + str(len(results)))
        save_table_embedding(session_maker, results)

        SQLBotLogUtil.info("get datasource")
        ds_stmt = select(col(CoreDatasource.id)).where(
            or_(
                col(CoreDatasource.embedding).is_(None),
                col(CoreDatasource.embedding) == "",
            )
        )
        ds_results = list(session.execute(ds_stmt).scalars().all())
        SQLBotLogUtil.info("datasource result: " + str(len(ds_results)))
        save_ds_embedding(session_maker, ds_results)
    except Exception:
        traceback.print_exc()
    finally:
        session_maker.remove()


def save_table_embedding(session_maker: Any, ids: list[int]) -> None:
    if not settings.TABLE_EMBEDDING_ENABLED or not embedding_runtime_enabled():
        return

    if not ids:
        return

    try:
        SQLBotLogUtil.info("start table embedding")
        start_time = time.time()
        model: Any = EmbeddingModelCache.get_model()
        session = session_maker()

        for _id in ids:
            try:
                table = (
                    session.query(CoreTable).filter(col(CoreTable.id) == _id).first()
                )
                if table is None:
                    continue

                fields = (
                    session.query(CoreField)
                    .filter(col(CoreField.table_id) == table.id)
                    .all()
                )

                schema_table = f"# Table: {table.table_name}"
                table_comment = (
                    table.custom_comment.strip() if table.custom_comment else ""
                )
                if table_comment == "":
                    schema_table += "\n[\n"
                else:
                    schema_table += f", {table_comment}\n[\n"

                if fields:
                    field_list: list[str] = []
                    for field in fields:
                        field_comment = (
                            field.custom_comment.strip() if field.custom_comment else ""
                        )
                        if field_comment == "":
                            field_list.append(
                                f"({field.field_name}:{field.field_type})"
                            )
                        else:
                            field_list.append(
                                f"({field.field_name}:{field.field_type}, {field_comment})"
                            )
                    schema_table += ",\n".join(field_list)
                schema_table += "\n]\n"
                schema_table = _truncate_embedding_input(schema_table)

                emb = json.dumps(model.embed_query(schema_table))
                stmt = (
                    update(CoreTable)
                    .where(col(CoreTable.id) == _id)
                    .values(embedding=emb)
                )
                session.execute(stmt)
                session.commit()
            except Exception as exc:
                session.rollback()
                SQLBotLogUtil.warning(
                    f"Failed to generate embedding for table [{_id}]: {exc}"
                )

        end_time = time.time()
        SQLBotLogUtil.info(
            "table embedding finished in: " + str(end_time - start_time) + " seconds"
        )
    except Exception:
        traceback.print_exc()
    finally:
        session_maker.remove()


def save_ds_embedding(session_maker: Any, ids: list[int]) -> None:
    if not settings.TABLE_EMBEDDING_ENABLED or not embedding_runtime_enabled():
        return

    if not ids:
        return

    try:
        SQLBotLogUtil.info("start datasource embedding")
        start_time = time.time()
        model: Any = EmbeddingModelCache.get_model()
        session = session_maker()

        for _id in ids:
            try:
                ds = (
                    session.query(CoreDatasource)
                    .filter(col(CoreDatasource.id) == _id)
                    .first()
                )
                if ds is None:
                    continue

                schema_table = f"{ds.name}, {ds.description}\n"
                tables = (
                    session.query(CoreTable).filter(col(CoreTable.ds_id) == ds.id).all()
                )
                for table in tables:
                    fields = (
                        session.query(CoreField)
                        .filter(col(CoreField.table_id) == table.id)
                        .all()
                    )

                    schema_table += f"# Table: {table.table_name}"
                    table_comment = (
                        table.custom_comment.strip() if table.custom_comment else ""
                    )
                    if table_comment == "":
                        schema_table += "\n[\n"
                    else:
                        schema_table += f", {table_comment}\n[\n"

                    if fields:
                        field_list: list[str] = []
                        for field in fields:
                            field_comment = (
                                field.custom_comment.strip()
                                if field.custom_comment
                                else ""
                            )
                            if field_comment == "":
                                field_list.append(
                                    f"({field.field_name}:{field.field_type})"
                                )
                            else:
                                field_list.append(
                                    f"({field.field_name}:{field.field_type}, {field_comment})"
                                )
                        schema_table += ",\n".join(field_list)
                    schema_table += "\n]\n"

                schema_table = _truncate_embedding_input(schema_table)

                emb = json.dumps(model.embed_query(schema_table))
                stmt = (
                    update(CoreDatasource)
                    .where(col(CoreDatasource.id) == _id)
                    .values(embedding=emb)
                )
                session.execute(stmt)
                session.commit()
            except Exception as exc:
                session.rollback()
                SQLBotLogUtil.warning(
                    f"Failed to generate embedding for datasource [{_id}]: {exc}"
                )

        end_time = time.time()
        SQLBotLogUtil.info(
            "datasource embedding finished in: "
            + str(end_time - start_time)
            + " seconds"
        )
    except Exception:
        traceback.print_exc()
    finally:
        session_maker.remove()

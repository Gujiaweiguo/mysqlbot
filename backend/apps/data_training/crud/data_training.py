import datetime
import traceback
from collections.abc import Mapping, Sequence
from typing import Protocol, cast
from xml.dom.minidom import Document, Element

from sqlalchemy import and_, delete, func, or_, select, text, update
from sqlalchemy.orm import Session as SASession
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import Label
from sqlmodel import col

from apps.ai_model.embedding import EmbeddingModelCache
from apps.data_training.models.data_training_model import (
    DataTraining,
    DataTrainingInfo,
    DataTrainingInfoResult,
)
from apps.datasource.models.datasource import CoreDatasource
from apps.system.models.system_model import AssistantModel
from apps.system.crud.embedding_admin import embedding_runtime_enabled
from apps.template.generate_chart.generator import get_base_data_training_template
from common.core.config import settings
from common.core.deps import SessionDep, Trans
from common.utils.embedding_runtime import embedding_executor, embedding_session_maker

ObjectDict = dict[str, object]
DataTrainingTemplateItem = dict[str, object]
DataTrainingBaseQuery = Select[tuple[int | None]]
DataTrainingBuiltQuery = Select[
    tuple[
        int | None,
        int | None,
        int | None,
        str | None,
        str | None,
        datetime.datetime | None,
        str | None,
        bool | None,
        int | None,
        str | None,
    ]
]


class DataTrainingSearchRow(Protocol):
    id: int | None
    question: str | None


class DataTrainingMapRow(Protocol):
    id: int | None
    question: str | None
    description: str | None


class DataTrainingQueryRow(Protocol):
    id: int | None
    oid: int | None
    datasource: int | None
    name: str | None
    question: str | None
    create_time: datetime.datetime | None
    description: str | None
    enabled: bool | None
    advanced_application: int | None
    advanced_application_name: str | None


class SessionMakerProtocol(Protocol):
    def __call__(self, **kw: object) -> SASession: ...

    def remove(self) -> None: ...


def _as_object_dict(value: object) -> ObjectDict | None:
    return cast(ObjectDict, value) if isinstance(value, dict) else None


def _as_object_list(value: object) -> list[object]:
    if not isinstance(value, list):
        return []
    return cast(list[object], value)


def _run_save_data_training_embeddings(ids: list[int]) -> None:
    _ = embedding_executor.submit(save_embeddings, embedding_session_maker, ids)


def get_data_training_base_query(
    oid: int, name: str | None = None
) -> DataTrainingBaseQuery:
    """
    获取数据训练查询的基础查询结构
    """
    if name and name.strip() != "":
        keyword_pattern = f"%{name.strip()}%"
        parent_ids_subquery = select(col(DataTraining.id)).where(
            and_(
                col(DataTraining.question).ilike(keyword_pattern),
                col(DataTraining.oid) == oid,
            )
        )
    else:
        parent_ids_subquery = select(col(DataTraining.id)).where(
            col(DataTraining.oid) == oid
        )

    return parent_ids_subquery


def build_data_training_query(
    session: SessionDep,
    oid: int,
    name: str | None = None,
    paginate: bool = True,
    current_page: int = 1,
    page_size: int = 10,
) -> tuple[DataTrainingBuiltQuery, int, int, int, int]:
    """
    构建数据训练查询的通用方法
    """
    parent_ids_subquery = get_data_training_base_query(oid, name)

    # 计算总数
    count_stmt = select(func.count()).select_from(parent_ids_subquery.subquery())
    total_count = int(session.scalar(count_stmt) or 0)

    if paginate:
        # 分页处理
        page_size = max(10, page_size)
        total_pages = (total_count + page_size - 1) // page_size
        current_page = max(1, min(current_page, total_pages)) if total_pages > 0 else 1

        paginated_parent_ids = (
            parent_ids_subquery.order_by(col(DataTraining.create_time).desc())
            .offset((current_page - 1) * page_size)
            .limit(page_size)
            .subquery()
        )
    else:
        # 不分页，获取所有数据
        total_pages = 1
        current_page = 1
        page_size = total_count if total_count > 0 else 1

        paginated_parent_ids = parent_ids_subquery.order_by(
            col(DataTraining.create_time).desc()
        ).subquery()

    # 构建主查询
    advanced_application_name_label = cast(
        Label[object],
        col(AssistantModel.name).label("advanced_application_name"),
    )

    stmt = cast(
        DataTrainingBuiltQuery,
        select(
            col(DataTraining.id),
            col(DataTraining.oid),
            col(DataTraining.datasource),
            col(CoreDatasource.name),
            col(DataTraining.question),
            col(DataTraining.create_time),
            col(DataTraining.description),
            col(DataTraining.enabled),
            col(DataTraining.advanced_application),
            advanced_application_name_label,
        )
        .outerjoin(
            CoreDatasource, and_(col(DataTraining.datasource) == col(CoreDatasource.id))
        )
        .outerjoin(
            AssistantModel,
            and_(
                col(DataTraining.advanced_application) == col(AssistantModel.id),
                col(AssistantModel.type) == 1,
            ),
        )
        .where(col(DataTraining.id).in_(select(paginated_parent_ids.c.id)))
        .order_by(col(DataTraining.create_time).desc()),
    )

    return stmt, total_count, total_pages, current_page, page_size


def execute_data_training_query(
    session: SessionDep, stmt: DataTrainingBuiltQuery
) -> list[DataTrainingInfoResult]:
    """
    执行查询并返回数据训练信息列表
    """
    _list: list[DataTrainingInfoResult] = []
    result = cast(list[DataTrainingQueryRow], session.execute(stmt).all())

    for row in result:
        _list.append(
            DataTrainingInfoResult(
                id=str(row.id),
                oid=str(row.oid),
                datasource=row.datasource,
                datasource_name=row.name,
                question=row.question,
                create_time=row.create_time,
                description=row.description,
                enabled=row.enabled,
                advanced_application=str(row.advanced_application)
                if row.advanced_application
                else None,
                advanced_application_name=row.advanced_application_name,
            )
        )

    return _list


def page_data_training(
    session: SessionDep,
    current_page: int = 1,
    page_size: int = 10,
    name: str | None = None,
    oid: int | None = 1,
) -> tuple[int, int, int, int, list[DataTrainingInfoResult]]:
    """
    分页查询数据训练（原方法保持不变）
    """
    effective_oid = oid or 1
    stmt, total_count, total_pages, current_page, page_size = build_data_training_query(
        session, effective_oid, name, True, current_page, page_size
    )
    _list = execute_data_training_query(session, stmt)

    return current_page, page_size, total_count, total_pages, _list


def get_all_data_training(
    session: SessionDep, name: str | None = None, oid: int | None = 1
) -> list[DataTrainingInfoResult]:
    """
    获取所有数据训练（不分页）
    """
    effective_oid = oid or 1
    stmt, _, _, _, _ = build_data_training_query(session, effective_oid, name, False)
    _list = execute_data_training_query(session, stmt)

    return _list


def create_training(
    session: SessionDep,
    info: DataTrainingInfo,
    oid: int,
    trans: Trans,
    skip_embedding: bool = False,
) -> int:
    """
    创建单个数据训练记录
    Args:
        skip_embedding: 是否跳过embedding处理（用于批量插入）
    """
    # 基本验证
    if not info.question or not info.question.strip():
        raise Exception(trans("i18n_data_training.question_cannot_be_empty"))

    if not info.description or not info.description.strip():
        raise Exception(trans("i18n_data_training.description_cannot_be_empty"))

    create_time = datetime.datetime.now()

    # 检查数据源和高级应用不能同时为空
    if info.datasource is None and info.advanced_application is None:
        raise Exception(trans("i18n_data_training.datasource_assistant_cannot_be_none"))

    # 检查重复记录
    select_stmt = select(col(DataTraining.id)).where(
        and_(
            col(DataTraining.question) == info.question.strip(),
            col(DataTraining.oid) == oid,
        )
    )

    if info.datasource is not None and info.advanced_application is not None:
        select_stmt = select_stmt.where(
            or_(
                col(DataTraining.datasource) == info.datasource,
                col(DataTraining.advanced_application) == info.advanced_application,
            )
        )
    elif info.datasource is not None and info.advanced_application is None:
        select_stmt = select_stmt.where(col(DataTraining.datasource) == info.datasource)
    elif info.datasource is None and info.advanced_application is not None:
        select_stmt = select_stmt.where(
            col(DataTraining.advanced_application) == info.advanced_application
        )

    exists = bool(session.scalar(select(select_stmt.exists())))

    if exists:
        raise Exception(trans("i18n_data_training.exists_in_db"))

    # 创建记录
    data_training = DataTraining.model_construct(
        question=info.question.strip(),
        description=info.description.strip(),
        oid=oid,
        datasource=info.datasource,
        advanced_application=info.advanced_application,
        create_time=create_time,
        embedding=None,
        enabled=info.enabled if info.enabled is not None else True,
    )

    session.add(data_training)
    session.flush()
    session.refresh(data_training)
    session.commit()

    # 处理embedding（批量插入时跳过）
    if not skip_embedding:
        if data_training.id is None:
            raise Exception(trans("i18n_data_training.data_training_not_exists"))
        _run_save_data_training_embeddings([data_training.id])

    if data_training.id is None:
        raise Exception(trans("i18n_data_training.data_training_not_exists"))
    return data_training.id


def update_training(
    session: SessionDep, info: DataTrainingInfo, oid: int, trans: Trans
) -> int:
    # 基本验证
    if not info.question or not info.question.strip():
        raise Exception(trans("i18n_data_training.question_cannot_be_empty"))

    if not info.description or not info.description.strip():
        raise Exception(trans("i18n_data_training.description_cannot_be_empty"))

    if info.datasource is None and info.advanced_application is None:
        raise Exception(trans("i18n_data_training.datasource_assistant_cannot_be_none"))

    if info.id is None:
        raise Exception(trans("i18n_data_training.data_training_not_exists"))

    count_stmt = select(func.count()).where(col(DataTraining.id) == info.id)
    count = int(session.scalar(count_stmt) or 0)
    if count == 0:
        raise Exception(trans("i18n_data_training.data_training_not_exists"))

    stmt = select(col(DataTraining.id)).where(
        and_(
            col(DataTraining.question) == info.question,
            col(DataTraining.oid) == oid,
            col(DataTraining.id) != info.id,
        )
    )

    if info.datasource is not None and info.advanced_application is not None:
        stmt = stmt.where(
            or_(
                col(DataTraining.datasource) == info.datasource,
                col(DataTraining.advanced_application) == info.advanced_application,
            )
        )
    elif info.datasource is not None and info.advanced_application is None:
        stmt = stmt.where(col(DataTraining.datasource) == info.datasource)
    elif info.datasource is None and info.advanced_application is not None:
        stmt = stmt.where(
            col(DataTraining.advanced_application) == info.advanced_application
        )

    exists = bool(session.scalar(select(stmt.exists())))

    if exists:
        raise Exception(trans("i18n_data_training.exists_in_db"))

    update_stmt = (
        update(DataTraining)
        .where(and_(col(DataTraining.id) == info.id))
        .values(
            question=info.question.strip(),
            description=info.description.strip(),
            datasource=info.datasource,
            advanced_application=info.advanced_application,
            enabled=info.enabled if info.enabled is not None else True,
        )
    )
    _ = session.exec(update_stmt)
    session.commit()

    # embedding
    _run_save_data_training_embeddings([info.id])

    return info.id


def batch_create_training(
    session: SessionDep, info_list: list[DataTrainingInfo], oid: int, trans: Trans
) -> ObjectDict:
    """
    批量创建数据训练记录（复用单条插入逻辑）
    """
    if not info_list:
        return cast(
            ObjectDict,
            {
                "success_count": 0,
                "failed_records": [],
                "duplicate_count": 0,
                "original_count": 0,
                "deduplicated_count": 0,
            },
        )

    failed_records: list[dict[str, object]] = []
    success_count: int = 0
    inserted_ids: list[int] = []

    # 第一步：数据去重
    unique_records: dict[tuple[str, str, str], DataTrainingInfo] = {}
    duplicate_records: list[DataTrainingInfo] = []

    for info in info_list:
        # 创建唯一标识
        unique_key = (
            info.question.strip().lower() if info.question else "",
            info.datasource_name.strip().lower() if info.datasource_name else "",
            info.advanced_application_name.strip().lower()
            if info.advanced_application_name
            else "",
        )

        if unique_key in unique_records:
            duplicate_records.append(info)
        else:
            unique_records[unique_key] = info

    # 将去重后的数据转换为列表
    deduplicated_list: list[DataTrainingInfo] = list(unique_records.values())

    # 预加载数据源和高级应用名称到ID的映射
    datasource_name_to_id: dict[str, int] = {}
    datasource_stmt = select(col(CoreDatasource.id), col(CoreDatasource.name)).where(
        col(CoreDatasource.oid) == oid
    )
    datasource_result = cast(
        list[tuple[int, str]], session.execute(datasource_stmt).all()
    )
    for ds_id, ds_name in datasource_result:
        datasource_name_to_id[ds_name.strip()] = ds_id

    assistant_name_to_id: dict[str, int] = {}

    assistant_stmt = select(col(AssistantModel.id), col(AssistantModel.name)).where(
        and_(col(AssistantModel.type) == 1, col(AssistantModel.oid) == oid)
    )
    assistant_result = cast(
        list[tuple[int, str]], session.execute(assistant_stmt).all()
    )
    for assistant_id, assistant_name in assistant_result:
        assistant_name_to_id[assistant_name.strip()] = assistant_id

    # 验证和转换数据
    valid_records: list[DataTrainingInfo] = []
    for info in deduplicated_list:
        error_messages: list[str] = []

        # 基本验证
        if not info.question or not info.question.strip():
            error_messages.append(trans("i18n_data_training.question_cannot_be_empty"))

        if not info.description or not info.description.strip():
            error_messages.append(
                trans("i18n_data_training.description_cannot_be_empty")
            )

        # 数据源验证和转换
        datasource_id: int | None = None
        if info.datasource_name and info.datasource_name.strip():
            if info.datasource_name.strip() in datasource_name_to_id:
                datasource_id = datasource_name_to_id[info.datasource_name.strip()]
            else:
                error_messages.append(
                    trans("i18n_data_training.datasource_not_found").format(
                        info.datasource_name
                    )
                )

        # 高级应用验证和转换
        advanced_application_id: int | None = None
        if info.advanced_application_name and info.advanced_application_name.strip():
            if info.advanced_application_name.strip() in assistant_name_to_id:
                advanced_application_id = assistant_name_to_id[
                    info.advanced_application_name.strip()
                ]
            else:
                error_messages.append(
                    trans("i18n_data_training.advanced_application_not_found").format(
                        info.advanced_application_name
                    )
                )

        # 检查数据源和高级应用不能同时为空
        if not datasource_id and not advanced_application_id:
            error_messages.append(
                trans("i18n_data_training.datasource_assistant_cannot_be_none")
            )

        if error_messages:
            failed_records.append({"data": info, "errors": error_messages})
            continue

        # 创建处理后的DataTrainingInfo对象
        question_text = info.question or ""
        description_text = info.description or ""
        processed_info = DataTrainingInfo(
            question=question_text.strip(),
            description=description_text.strip(),
            datasource=datasource_id,
            datasource_name=info.datasource_name,
            advanced_application=advanced_application_id,
            advanced_application_name=info.advanced_application_name,
            enabled=info.enabled if info.enabled is not None else True,
        )

        valid_records.append(processed_info)

    # 使用事务处理有效记录
    if valid_records:
        for info in valid_records:
            try:
                # 直接复用create_training方法，跳过embedding处理
                training_id = create_training(
                    session, info, oid, trans, skip_embedding=True
                )
                inserted_ids.append(training_id)
                success_count += 1

            except Exception as e:
                # 如果单条插入失败，回滚当前记录
                session.rollback()
                failed_records.append({"data": info, "errors": [str(e)]})

        # 批量处理embedding（只在最后执行一次）
        if success_count > 0 and inserted_ids:
            try:
                _run_save_data_training_embeddings(inserted_ids)
            except Exception as e:
                # 如果embedding处理失败，记录错误但不回滚数据
                print(f"Embedding processing failed: {str(e)}")
                # 可以选择将embedding失败的信息记录到日志或返回给调用方

    return cast(
        ObjectDict,
        {
            "success_count": success_count,
            "failed_records": failed_records,
            "duplicate_count": len(duplicate_records),
            "original_count": len(info_list),
            "deduplicated_count": len(deduplicated_list),
        },
    )


def delete_training(session: SessionDep, ids: list[int]) -> None:
    stmt = delete(DataTraining).where(and_(col(DataTraining.id).in_(ids)))
    _ = session.exec(stmt)
    session.commit()


def enable_training(session: SessionDep, id: int, enabled: bool, trans: Trans) -> None:
    count_stmt = select(func.count()).where(col(DataTraining.id) == id)
    count = int(session.scalar(count_stmt) or 0)
    if count == 0:
        raise Exception(trans("i18n_data_training.data_training_not_exists"))

    stmt = (
        update(DataTraining)
        .where(and_(col(DataTraining.id) == id))
        .values(
            enabled=enabled,
        )
    )
    _ = session.exec(stmt)
    session.commit()


# def run_save_embeddings(ids: List[int]):
#     executor.submit(save_embeddings, ids)
#
#
# def fill_empty_embeddings():
#     executor.submit(run_fill_empty_embeddings)


def run_fill_empty_embeddings(session_maker: SessionMakerProtocol) -> None:
    try:
        if not settings.EMBEDDING_ENABLED or not embedding_runtime_enabled():
            return

        session = session_maker()
        stmt = select(col(DataTraining.id)).where(col(DataTraining.embedding).is_(None))
        results = cast(list[int], session.execute(stmt).scalars().all())

        save_embeddings(session_maker, results)
    except Exception:
        traceback.print_exc()
    finally:
        session_maker.remove()


def save_embeddings(session_maker: SessionMakerProtocol, ids: list[int]) -> None:
    if not settings.EMBEDDING_ENABLED or not embedding_runtime_enabled():
        return

    if not ids or len(ids) == 0:
        return
    try:
        session = session_maker()
        _list = cast(
            list[DataTraining],
            session.execute(
                select(DataTraining).where(and_(col(DataTraining.id).in_(ids)))
            )
            .scalars()
            .all(),
        )

        _question_list = [item.question for item in _list if item.question]

        model = EmbeddingModelCache.get_model()

        results = model.embed_documents(_question_list)

        for index in range(len(results)):
            item = results[index]
            stmt = (
                update(DataTraining)
                .where(and_(col(DataTraining.id) == _list[index].id))
                .values(embedding=item)
            )
            _ = session.execute(stmt)
            session.commit()

    except Exception:
        traceback.print_exc()
    finally:
        session_maker.remove()


embedding_sql = f"""
SELECT id, datasource, question, similarity
FROM
(SELECT id, datasource, question, oid, enabled,
( 1 - (embedding <=> :embedding_array) ) AS similarity
FROM data_training AS child
) TEMP
WHERE similarity > {settings.EMBEDDING_DATA_TRAINING_SIMILARITY} and oid = :oid and datasource = :datasource and enabled = true
ORDER BY similarity DESC
LIMIT {settings.EMBEDDING_DATA_TRAINING_TOP_COUNT}
"""
embedding_sql_in_advanced_application = f"""
SELECT id, advanced_application, question, similarity
FROM
(SELECT id, advanced_application, question, oid, enabled,
( 1 - (embedding <=> :embedding_array) ) AS similarity
FROM data_training AS child
) TEMP
WHERE similarity > {settings.EMBEDDING_DATA_TRAINING_SIMILARITY} and oid = :oid and advanced_application = :advanced_application and enabled = true
ORDER BY similarity DESC
LIMIT {settings.EMBEDDING_DATA_TRAINING_TOP_COUNT}
"""


def select_training_by_question(
    session: SessionDep,
    question: str,
    oid: int,
    datasource: int | None = None,
    advanced_application_id: int | None = None,
) -> list[DataTrainingTemplateItem]:
    if question.strip() == "":
        return []

    _list: list[DataTraining] = []

    # maybe use label later?
    stmt = select(
        col(DataTraining.id),
        col(DataTraining.question),
    ).where(
        and_(
            or_(
                text(":sentence ILIKE '%' || question || '%'"),
                text("question ILIKE '%' || :sentence || '%'"),
            ),
            col(DataTraining.oid) == oid,
            col(DataTraining.enabled).is_(True),
        )
    )
    if advanced_application_id is not None:
        stmt = stmt.where(
            col(DataTraining.advanced_application) == advanced_application_id
        )
    else:
        stmt = stmt.where(col(DataTraining.datasource) == datasource)

    results = cast(
        list[DataTrainingSearchRow],
        session.execute(stmt, {"sentence": question}).fetchall(),
    )

    for row in results:
        _list.append(
            DataTraining.model_construct(
                id=row.id,
                oid=oid,
                datasource=datasource,
                create_time=None,
                question=row.question,
                description=None,
                embedding=None,
                enabled=True,
                advanced_application=advanced_application_id,
            )
        )

    if settings.EMBEDDING_ENABLED and embedding_runtime_enabled():
        with session.begin_nested():
            try:
                model = EmbeddingModelCache.get_model()

                embedding = model.embed_query(question)

                if advanced_application_id is not None:
                    results = cast(
                        list[DataTrainingSearchRow],
                        session.execute(
                            text(embedding_sql_in_advanced_application),
                            {
                                "embedding_array": str(embedding),
                                "oid": oid,
                                "advanced_application": advanced_application_id,
                            },
                        ).fetchall(),
                    )
                else:
                    results = cast(
                        list[DataTrainingSearchRow],
                        session.execute(
                            text(embedding_sql),
                            {
                                "embedding_array": str(embedding),
                                "oid": oid,
                                "datasource": datasource,
                            },
                        ).fetchall(),
                    )

                for row in results:
                    _list.append(
                        DataTraining.model_construct(
                            id=row.id,
                            oid=oid,
                            datasource=datasource,
                            create_time=None,
                            question=row.question,
                            description=None,
                            embedding=None,
                            enabled=True,
                            advanced_application=advanced_application_id,
                        )
                    )

            except Exception:
                traceback.print_exc()
                session.rollback()

    _map: dict[int, DataTrainingTemplateItem] = {}
    _ids: list[int] = []
    for record in _list:
        if record.id is None:
            continue
        if record.id in _ids:
            continue
        else:
            _ids.append(record.id)

    if len(_ids) == 0:
        return []

    t_list = cast(
        list[DataTrainingMapRow],
        session.execute(
            select(
                col(DataTraining.id),
                col(DataTraining.question),
                col(DataTraining.description),
            ).where(and_(col(DataTraining.id).in_(_ids)))
        ).all(),
    )

    for row in t_list:
        if row.id is None:
            continue
        _map[row.id] = {
            "question": row.question,
            "suggestion-answer": row.description,
        }

    _results: list[DataTrainingTemplateItem] = []
    for key in _map.keys():
        item = _map.get(key)
        if item is not None:
            _results.append(item)

    return _results


def to_xml_string(
    _dict: Sequence[Mapping[str, object]] | Mapping[str, object],
    root: str = "sql-examples",
) -> str:
    def item_name_func(name: str) -> str:
        return "sql-example" if name == "sql-examples" else "item"

    cdata_fields = {"question", "suggestion-answer"}

    def append_scalar(doc: Document, parent: Element, name: str, value: object) -> None:
        element = doc.createElement(name)
        _ = parent.appendChild(element)
        text = "" if value is None else str(value)
        if name in cdata_fields:
            _ = element.appendChild(doc.createCDATASection(text))
        else:
            _ = element.appendChild(doc.createTextNode(text))

    def append_item(
        doc: Document, parent: Element, item_name: str, value: object
    ) -> None:
        value_dict = _as_object_dict(value)
        if value_dict is not None:
            item_element = doc.createElement(item_name)
            _ = parent.appendChild(item_element)
            for child_key, child_value in value_dict.items():
                append_named(doc, item_element, str(child_key), child_value)
            return
        if isinstance(value, list):
            for nested_value in _as_object_list(cast(object, value)):
                append_item(doc, parent, item_name, nested_value)
            return
        append_scalar(doc, parent, item_name, value)

    def append_named(doc: Document, parent: Element, name: str, value: object) -> None:
        value_dict = _as_object_dict(value)
        if value_dict is not None:
            container = doc.createElement(name)
            _ = parent.appendChild(container)
            for child_key, child_value in value_dict.items():
                append_named(doc, container, str(child_key), child_value)
            return
        if isinstance(value, list):
            container = doc.createElement(name)
            _ = parent.appendChild(container)
            item_name = item_name_func(name)
            for item in _as_object_list(cast(object, value)):
                append_item(doc, container, item_name, item)
            return
        append_scalar(doc, parent, name, value)

    doc = Document()
    root_element = doc.createElement(root)
    _ = doc.appendChild(root_element)

    if isinstance(_dict, dict):
        for key, value in _dict.items():
            append_named(doc, root_element, str(key), value)
    else:
        list_item_name = item_name_func(root)
        for item in _dict:
            append_item(doc, root_element, list_item_name, item)

    pretty_xml = doc.toprettyxml()

    if pretty_xml.startswith("<?xml"):
        end_index = pretty_xml.find(">") + 1
        pretty_xml = pretty_xml[end_index:].lstrip()

    # 替换所有 XML 转义字符
    escape_map = {"&lt;": "<", "&gt;": ">", "&amp;": "&", "&quot;": '"', "&apos;": "'"}
    for escaped, original in escape_map.items():
        pretty_xml = pretty_xml.replace(escaped, original)

    return pretty_xml


def get_training_template(
    session: SessionDep,
    question: str,
    oid: int | None = 1,
    datasource: int | None = None,
    advanced_application_id: int | None = None,
) -> tuple[str, list[DataTrainingTemplateItem]]:
    if not oid:
        oid = 1
    if not datasource and not advanced_application_id:
        return "", []
    _results = select_training_by_question(
        session, question, oid, datasource, advanced_application_id
    )
    if _results and len(_results) > 0:
        data_training = to_xml_string(_results)
        template_source = cast(object, get_base_data_training_template())
        template = str(template_source).format(data_training=data_training)
        return template, _results
    else:
        return "", []

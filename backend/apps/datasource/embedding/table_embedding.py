# Author: Junjun
# Date: 2025/9/23
import json
import time
import traceback
from typing import Any, TypedDict

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.embedding.utils import cosine_similarity
from common.core.config import settings
from common.utils.utils import SQLBotLogUtil


class TableScoreItem(TypedDict):
    id: int | None
    schema_table: str
    cosine_similarity: float


class TableEmbeddingItem(TableScoreItem):
    embedding: str | None


def _to_int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def get_table_embedding(
    tables: list[dict[str, Any]], question: str
) -> list[TableScoreItem]:
    _list: list[TableScoreItem] = []
    for table in tables:
        table_id = table.get("id")
        _list.append(
            {
                "id": _to_int_or_none(table_id),
                "schema_table": str(table.get("schema_table") or ""),
                "cosine_similarity": 0.0,
            }
        )

    if _list:
        try:
            text: list[str] = [s["schema_table"] for s in _list]

            model = EmbeddingModelCache.get_model()
            start_time = time.time()
            results = model.embed_documents(text)
            end_time = time.time()
            SQLBotLogUtil.info(str(end_time - start_time))

            q_embedding = model.embed_query(question)
            for index in range(len(results)):
                item = results[index]
                _list[index]["cosine_similarity"] = float(
                    cosine_similarity(q_embedding, item)
                )

            _list.sort(key=lambda x: float(x["cosine_similarity"]), reverse=True)
            _list = _list[: settings.TABLE_EMBEDDING_COUNT]
            # print(len(_list))
            SQLBotLogUtil.info(json.dumps(_list))
            return _list
        except Exception:
            traceback.print_exc()
    return _list


def calc_table_embedding(
    tables: list[dict[str, Any]], question: str
) -> list[TableEmbeddingItem]:
    _list: list[TableEmbeddingItem] = []
    for table in tables:
        table_id = table.get("id")
        _list.append(
            {
                "id": _to_int_or_none(table_id),
                "schema_table": str(table.get("schema_table") or ""),
                "embedding": (
                    str(table.get("embedding"))
                    if table.get("embedding") is not None
                    else None
                ),
                "cosine_similarity": 0.0,
            }
        )

    if _list:
        try:
            # text = [s.get('schema_table') for s in _list]
            #
            model = EmbeddingModelCache.get_model()
            start_time = time.time()
            # results = model.embed_documents(text)
            # end_time = time.time()
            # SQLBotLogUtil.info(str(end_time - start_time))
            results: list[str | None] = [item.get("embedding") for item in _list]

            q_embedding = model.embed_query(question)
            for index in range(len(results)):
                item = results[index]
                if isinstance(item, str):
                    _list[index]["cosine_similarity"] = float(
                        cosine_similarity(q_embedding, json.loads(item))
                    )

            _list.sort(key=lambda x: float(x["cosine_similarity"]), reverse=True)
            _list = _list[: settings.TABLE_EMBEDDING_COUNT]
            # print(len(_list))
            end_time = time.time()
            SQLBotLogUtil.info(str(end_time - start_time))
            SQLBotLogUtil.info(
                json.dumps(
                    [
                        {
                            "id": ele.get("id"),
                            "schema_table": ele.get("schema_table"),
                            "cosine_similarity": ele.get("cosine_similarity"),
                        }
                        for ele in _list
                    ]
                )
            )
            return _list
        except Exception:
            traceback.print_exc()
    return _list

# Author: Junjun
# Date: 2025/9/18
import json
import time
import traceback
from typing import Any

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.embedding.utils import cosine_similarity
from apps.datasource.models.datasource import CoreDatasource
from apps.system.crud.assistant import AssistantOutDs
from common.core.config import settings
from common.core.deps import CurrentAssistant, CurrentUser, SessionDep
from common.utils.utils import SQLBotLogUtil


def get_ds_embedding(
    session: SessionDep,
    current_user: CurrentUser,
    _ds_list: list[dict[str, Any]],
    out_ds: AssistantOutDs,
    question: str,
    current_assistant: CurrentAssistant | None = None,
) -> list[dict[str, Any]]:
    _ = current_user
    _list: list[dict[str, Any]] = []
    if current_assistant and current_assistant.type == 1:
        if out_ds.ds_list:
            for _ds in out_ds.ds_list:
                if _ds.id is None:
                    continue
                ds_id = int(_ds.id)
                ds = out_ds.get_ds(ds_id)
                table_schema = out_ds.get_db_schema(ds_id, question, embedding=False)
                ds_info = f"{ds.name}, {ds.description}\n"
                ds_schema = ds_info + table_schema
                _list.append(
                    {
                        "id": ds_id,
                        "name": ds.name,
                        "description": ds.description,
                        "ds_schema": ds_schema,
                        "cosine_similarity": 0.0,
                    }
                )

        if _list:
            try:
                text: list[str] = [str(s["ds_schema"]) for s in _list]

                model = EmbeddingModelCache.get_model()
                results = model.embed_documents(text)

                q_embedding = model.embed_query(question)
                for index in range(len(results)):
                    item = results[index]
                    _list[index]["cosine_similarity"] = float(
                        cosine_similarity(q_embedding, item)
                    )

                _list.sort(key=lambda x: float(x["cosine_similarity"]), reverse=True)
                # print(len(_list))
                _list = _list[: settings.DS_EMBEDDING_COUNT]
                SQLBotLogUtil.info(
                    json.dumps(
                        [
                            {
                                "id": ele.get("id"),
                                "name": ele.get("name"),
                                "cosine_similarity": ele.get("cosine_similarity"),
                            }
                            for ele in _list
                        ]
                    )
                )
                return [
                    {
                        "id": obj.get("id"),
                        "name": obj.get("name"),
                        "description": obj.get("description"),
                    }
                    for obj in _list
                ]
            except Exception:
                traceback.print_exc()
    else:
        for ds_item in _ds_list:
            ds_id_raw = ds_item.get("id")
            ds_id_value: int | None = None
            if isinstance(ds_id_raw, int):
                ds_id_value = ds_id_raw
            elif isinstance(ds_id_raw, str):
                try:
                    ds_id_value = int(ds_id_raw)
                except ValueError:
                    ds_id_value = None
            if ds_id_value is not None:
                db_ds = session.get(CoreDatasource, ds_id_value)
                if db_ds is None:
                    continue
                _list.append(
                    {
                        "id": db_ds.id,
                        "name": db_ds.name,
                        "description": db_ds.description,
                        "cosine_similarity": 0.0,
                        "embedding": db_ds.embedding,
                    }
                )

        if _list:
            try:
                # text = [s.get('ds_schema') for s in _list]

                model = EmbeddingModelCache.get_model()
                start_time = time.time()
                # results = model.embed_documents(text)
                embeddings_raw: list[str | None] = [
                    item.get("embedding")
                    if isinstance(item.get("embedding"), str)
                    else None
                    for item in _list
                ]

                q_embedding = model.embed_query(question)
                for index in range(len(embeddings_raw)):
                    emb_str = embeddings_raw[index]
                    if isinstance(emb_str, str):
                        _list[index]["cosine_similarity"] = float(
                            cosine_similarity(q_embedding, json.loads(emb_str))
                        )

                _list.sort(key=lambda x: float(x["cosine_similarity"]), reverse=True)
                # print(len(_list))
                end_time = time.time()
                SQLBotLogUtil.info(str(end_time - start_time))
                _list = _list[: settings.DS_EMBEDDING_COUNT]
                SQLBotLogUtil.info(
                    json.dumps(
                        [
                            {
                                "id": ele.get("id"),
                                "name": ele.get("name"),
                                "cosine_similarity": ele.get("cosine_similarity"),
                            }
                            for ele in _list
                        ]
                    )
                )
                return [
                    {
                        "id": obj.get("id"),
                        "name": obj.get("name"),
                        "description": obj.get("description"),
                    }
                    for obj in _list
                ]
            except Exception:
                traceback.print_exc()
    return _list

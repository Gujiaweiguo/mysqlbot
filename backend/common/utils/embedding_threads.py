from importlib import import_module
from typing import Protocol, cast

from common.utils.embedding_runtime import embedding_executor, embedding_session_maker


class EmbeddingSaveCallable(Protocol):
    def __call__(self, session_maker: object, ids: list[int]) -> object: ...


class EmbeddingFillCallable(Protocol):
    def __call__(self, session_maker: object) -> object: ...


def _load_attr(module_path: str, attr_name: str) -> object:
    module = import_module(module_path)
    return cast(object, getattr(module, attr_name))


def _load_save_callable(module_path: str, attr_name: str) -> EmbeddingSaveCallable:
    return cast(EmbeddingSaveCallable, _load_attr(module_path, attr_name))


def _load_fill_callable(module_path: str, attr_name: str) -> EmbeddingFillCallable:
    return cast(EmbeddingFillCallable, _load_attr(module_path, attr_name))


def run_save_terminology_embeddings(ids: list[int]) -> None:
    save_embeddings = _load_save_callable(
        "apps.terminology.crud.terminology", "save_embeddings"
    )

    _ = embedding_executor.submit(save_embeddings, embedding_session_maker, ids)


def fill_empty_terminology_embeddings() -> None:
    run_fill_empty_embeddings = _load_fill_callable(
        "apps.terminology.crud.terminology", "run_fill_empty_embeddings"
    )

    _ = embedding_executor.submit(run_fill_empty_embeddings, embedding_session_maker)


def run_save_data_training_embeddings(ids: list[int]) -> None:
    save_embeddings = _load_save_callable(
        "apps.data_training.crud.data_training", "save_embeddings"
    )

    _ = embedding_executor.submit(save_embeddings, embedding_session_maker, ids)


def fill_empty_data_training_embeddings() -> None:
    run_fill_empty_embeddings = _load_fill_callable(
        "apps.data_training.crud.data_training", "run_fill_empty_embeddings"
    )

    _ = embedding_executor.submit(run_fill_empty_embeddings, embedding_session_maker)


def run_save_table_embeddings(ids: list[int]) -> None:
    save_table_embedding = _load_save_callable(
        "apps.datasource.crud.table", "save_table_embedding"
    )

    _ = embedding_executor.submit(save_table_embedding, embedding_session_maker, ids)


def run_save_ds_embeddings(ids: list[int]) -> None:
    save_ds_embedding = _load_save_callable(
        "apps.datasource.crud.table", "save_ds_embedding"
    )

    _ = embedding_executor.submit(save_ds_embedding, embedding_session_maker, ids)


def fill_empty_table_and_ds_embeddings() -> None:
    run_fill_empty_table_and_ds_embedding = _load_fill_callable(
        "apps.datasource.crud.table", "run_fill_empty_table_and_ds_embedding"
    )

    _ = embedding_executor.submit(
        run_fill_empty_table_and_ds_embedding, embedding_session_maker
    )

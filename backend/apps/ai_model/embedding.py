import os.path
import threading

from langchain_core.embeddings import Embeddings
from pydantic import BaseModel

from common.core.config import settings

os.environ["TOKENIZERS_PARALLELISM"] = "false"


class EmbeddingModelInfo(BaseModel):
    folder: str
    name: str
    device: str = "cpu"


local_embedding_model = EmbeddingModelInfo(
    folder=settings.LOCAL_MODEL_PATH,
    name=os.path.join(
        settings.LOCAL_MODEL_PATH, "embedding", "shibing624_text2vec-base-chinese"
    ),
)

_lock = threading.Lock()
locks: dict[str, threading.Lock] = {}

_embedding_model: dict[str, Embeddings | None] = {}


class EmbeddingModelCache:
    @staticmethod
    def _new_instance(config: EmbeddingModelInfo = local_embedding_model) -> Embeddings:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=config.name,
            cache_folder=config.folder,
            model_kwargs={"device": config.device},
            encode_kwargs={"normalize_embeddings": True},
        )

    @staticmethod
    def _get_lock(key: str = settings.DEFAULT_EMBEDDING_MODEL) -> threading.Lock:
        lock = locks.get(key)
        if lock is None:
            with _lock:
                lock = locks.get(key)
                if lock is None:
                    lock = threading.Lock()
                    locks[key] = lock

        return lock

    @staticmethod
    def get_model(
        key: str = settings.DEFAULT_EMBEDDING_MODEL,
        config: EmbeddingModelInfo = local_embedding_model,
    ) -> Embeddings:
        model_instance = _embedding_model.get(key)
        if model_instance is None:
            lock = EmbeddingModelCache._get_lock(key)
            with lock:
                model_instance = _embedding_model.get(key)
                if model_instance is None:
                    model_instance = EmbeddingModelCache._new_instance(config)
                    _embedding_model[key] = model_instance

        return model_instance

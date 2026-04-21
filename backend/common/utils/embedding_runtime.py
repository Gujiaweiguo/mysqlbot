from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import scoped_session, sessionmaker

from common.core.config import settings
from common.core.db import engine

embedding_executor = ThreadPoolExecutor(max_workers=settings.DATASOURCE_SYNC_EMBEDDING_MAX_WORKERS)
embedding_session_maker = scoped_session(sessionmaker(bind=engine))

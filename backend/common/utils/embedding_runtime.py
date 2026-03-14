from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import scoped_session, sessionmaker

from common.core.db import engine

embedding_executor = ThreadPoolExecutor(max_workers=200)
embedding_session_maker = scoped_session(sessionmaker(bind=engine))

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from common.core.config import settings

engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_size=settings.PG_POOL_SIZE,
    max_overflow=settings.PG_MAX_OVERFLOW,
    pool_recycle=settings.PG_POOL_RECYCLE,
    pool_pre_ping=settings.PG_POOL_PRE_PING,
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)

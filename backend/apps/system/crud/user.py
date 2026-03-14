from sqlmodel import Session, col, func, select
from sqlmodel import delete as sqlmodel_delete

from apps.system.models.system_model import UserWsModel, WorkspaceModel
from apps.system.schemas.auth import CacheName, CacheNamespace
from apps.system.schemas.system_schema import (
    EMAIL_REGEX,
    PWD_REGEX,
    BaseUserDTO,
    UserInfoDTO,
    UserWs,
)
from common.core.deps import SessionDep
from common.core.security import verify_md5pwd
from common.core.sqlbot_cache import cache, clear_cache
from common.utils.locale import I18nHelper
from common.utils.utils import SQLBotLogUtil

from ..models.user import UserModel, UserPlatformModel


def get_db_user(*, session: Session, user_id: int) -> UserModel | None:
    db_user = session.get(UserModel, user_id)
    return db_user


def get_user_by_account(*, session: Session, account: str) -> BaseUserDTO | None:
    statement = select(UserModel).where(UserModel.account == account)
    db_user = session.exec(statement).first()
    if not db_user:
        return None
    return BaseUserDTO.model_validate(db_user.model_dump())


@cache(
    namespace=CacheNamespace.AUTH_INFO.value,
    cacheName=CacheName.USER_INFO.value,
    keyExpression="user_id",
)
async def get_user_info(*, session: Session, user_id: int) -> UserInfoDTO | None:
    db_user = get_db_user(session=session, user_id=user_id)
    if not db_user:
        return None
    user_info = UserInfoDTO.model_validate(db_user.model_dump())
    user_info.isAdmin = user_info.id == 1 and user_info.account == "admin"
    if user_info.isAdmin:
        return user_info
    ws_model = session.exec(
        select(UserWsModel).where(
            col(UserWsModel.uid) == user_info.id,
            col(UserWsModel.oid) == user_info.oid,
        )
    ).first()
    user_info.weight = ws_model.weight if ws_model else -1
    return user_info


def authenticate(
    *, session: Session, account: str, password: str
) -> BaseUserDTO | None:
    db_user = get_user_by_account(session=session, account=account)
    if not db_user:
        return None
    if not verify_md5pwd(password, db_user.password):
        return None
    return db_user


async def user_ws_options(
    session: Session,
    uid: int,
    trans: I18nHelper | None = None,
) -> list[UserWs]:
    if uid == 1:
        stmt = select(WorkspaceModel.id, WorkspaceModel.name).order_by(
            col(WorkspaceModel.name), col(WorkspaceModel.create_time)
        )
    else:
        stmt = (
            select(WorkspaceModel.id, WorkspaceModel.name)
            .join(UserWsModel, col(UserWsModel.oid) == col(WorkspaceModel.id))
            .where(col(UserWsModel.uid) == uid)
            .order_by(col(WorkspaceModel.name), col(WorkspaceModel.create_time))
        )
    result_rows = session.exec(stmt).all()
    if not trans:
        return [
            UserWs(id=ws_id, name=ws_name)
            for ws_id, ws_name in result_rows
            if isinstance(ws_id, int)
        ]
    list_result = [
        UserWs(id=ws_id, name=trans(ws_name) if ws_name.startswith("i18n") else ws_name)
        for ws_id, ws_name in result_rows
        if isinstance(ws_id, int) and isinstance(ws_name, str)
    ]
    if list_result:
        list_result.sort(key=lambda x: x.name)
    return list_result


@clear_cache(
    namespace=CacheNamespace.AUTH_INFO.value,
    cacheName=CacheName.USER_INFO.value,
    keyExpression="id",
)
async def single_delete(session: SessionDep, id: int) -> None:
    user_model = get_db_user(session=session, user_id=id)
    if user_model is None:
        return
    del_stmt = sqlmodel_delete(UserWsModel).where(col(UserWsModel.uid) == id)
    session.exec(del_stmt)
    if user_model and user_model.origin and user_model.origin != 0:
        platform_del_stmt = sqlmodel_delete(UserPlatformModel).where(
            col(UserPlatformModel.uid) == id
        )
        session.exec(platform_del_stmt)
    session.delete(user_model)
    session.commit()


@clear_cache(
    namespace=CacheNamespace.AUTH_INFO.value,
    cacheName=CacheName.USER_INFO.value,
    keyExpression="id",
)
async def clean_user_cache(id: int) -> None:
    SQLBotLogUtil.info(f"User cache for [{id}] has been cleaned")


def check_account_exists(*, session: Session, account: str) -> bool:
    return (
        session.exec(
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.account == account)
        ).one()
        > 0
    )


def check_email_exists(*, session: Session, email: str) -> bool:
    return (
        session.exec(
            select(func.count()).select_from(UserModel).where(UserModel.email == email)
        ).one()
        > 0
    )


def check_email_format(email: str) -> bool:
    return bool(EMAIL_REGEX.fullmatch(email))


def check_pwd_format(pwd: str) -> bool:
    return bool(PWD_REGEX.fullmatch(pwd))

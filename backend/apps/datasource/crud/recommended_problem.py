import datetime

import orjson
from sqlmodel import col, select

from common.core.deps import CurrentUser, SessionDep

from ..models.datasource import (
    CoreDatasource,
    DsRecommendedProblem,
    RecommendedProblemBase,
    RecommendedProblemResponse,
)


def get_datasource_recommended(
    session: SessionDep,
    ds_id: int,
) -> list[DsRecommendedProblem]:
    statement = select(DsRecommendedProblem).where(
        col(DsRecommendedProblem.datasource_id) == ds_id
    )
    ds_recommended_problem = list(session.exec(statement).all())
    return ds_recommended_problem


def get_datasource_recommended_chart(session: SessionDep, ds_id: int) -> list[str]:
    statement = select(col(DsRecommendedProblem.question)).where(
        col(DsRecommendedProblem.datasource_id) == ds_id
    )
    ds_recommended_problems = list(session.exec(statement).all())
    return ds_recommended_problems


def get_datasource_recommended_base(
    session: SessionDep,
    ds_id: int,
) -> RecommendedProblemResponse:
    statement = select(
        col(CoreDatasource.id),
        col(CoreDatasource.recommended_config),
    ).where(col(CoreDatasource.id) == ds_id)
    datasource_base = session.exec(statement).first()
    if datasource_base is None:
        return RecommendedProblemResponse(ds_id, 0, None)

    datasource_id, recommended_config = datasource_base
    if recommended_config == 1:
        return RecommendedProblemResponse(datasource_id, 1, None)

    ds_recommended_problems = session.exec(
        select(col(DsRecommendedProblem.question)).where(
            col(DsRecommendedProblem.datasource_id) == ds_id
        )
    ).all()
    return RecommendedProblemResponse(
        datasource_id,
        recommended_config,
        orjson.dumps(ds_recommended_problems).decode(),
    )


def save_recommended_problem(
    session: SessionDep,
    user: CurrentUser,
    data_info: RecommendedProblemBase,
) -> None:
    session.query(DsRecommendedProblem).filter(
        col(DsRecommendedProblem.datasource_id) == data_info.datasource_id
    ).delete(synchronize_session=False)

    problem_info = data_info.problemInfo
    if problem_info is not None:
        for problem_item in problem_info:
            problem_data = problem_item.model_dump()
            problem_data["id"] = None
            problem_data["create_time"] = datetime.datetime.now()
            problem_data["create_by"] = user.id
            record = DsRecommendedProblem(**problem_data)
            session.add(record)
            session.flush()
            session.refresh(record)
    session.commit()

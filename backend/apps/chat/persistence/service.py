from sqlmodel import Session

from apps.chat.curd.chat import (
    finish_record,
    save_analysis_predict_record,
    save_chart,
    save_error_message,
    save_predict_data,
    save_question,
    save_sql,
    save_sql_exec_data,
)
from apps.chat.models.chat_model import ChatQuestion, ChatRecord
from apps.system.schemas.system_schema import UserInfoDTO


class ChatPersistenceService:
    def init_record(
        self, session: Session, current_user: UserInfoDTO, question: ChatQuestion
    ) -> ChatRecord:
        return save_question(
            session=session, current_user=current_user, question=question
        )

    def create_analysis_or_predict_record(
        self, session: Session, base_record: ChatRecord, action_type: str
    ) -> ChatRecord:
        return save_analysis_predict_record(session, base_record, action_type)

    def save_sql(self, session: Session, record_id: int, sql: str) -> ChatRecord:
        return save_sql(session=session, record_id=record_id, sql=sql)

    def save_chart(self, session: Session, record_id: int, chart: str) -> ChatRecord:
        return save_chart(session=session, record_id=record_id, chart=chart)

    def save_predict_data(
        self, session: Session, record_id: int, data: str
    ) -> ChatRecord:
        return save_predict_data(session=session, record_id=record_id, data=data)

    def save_error(self, session: Session, record_id: int, message: str) -> ChatRecord:
        return save_error_message(session=session, record_id=record_id, message=message)

    def save_sql_exec_data(
        self, session: Session, record_id: int, data: str
    ) -> ChatRecord:
        return save_sql_exec_data(session=session, record_id=record_id, data=data)

    def finish(self, session: Session, record_id: int) -> ChatRecord:
        return finish_record(session=session, record_id=record_id)

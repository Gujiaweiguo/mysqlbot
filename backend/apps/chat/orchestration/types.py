from dataclasses import dataclass

from sqlmodel import Session

from apps.chat.models.chat_model import ChatFinishStep, ChatQuestion, ChatRecord
from common.core.deps import CurrentAssistant, CurrentUser


@dataclass(slots=True)
class ChatExecutionRequest:
    session: Session
    current_user: CurrentUser
    request_question: ChatQuestion
    current_assistant: CurrentAssistant | None = None
    in_chat: bool = True
    stream: bool = True
    finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART
    embedding: bool = False


@dataclass(slots=True)
class QuestionAnswerRequest:
    session: Session
    current_user: CurrentUser
    request_question: ChatQuestion
    current_assistant: CurrentAssistant | None = None
    in_chat: bool = True
    stream: bool = True
    finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART
    embedding: bool = False


@dataclass(slots=True)
class AnalysisRequest:
    session: Session
    current_user: CurrentUser
    request_question: ChatQuestion
    chat_record: ChatRecord
    action_type: str
    current_assistant: CurrentAssistant
    in_chat: bool = True
    stream: bool = True


@dataclass(slots=True)
class AnalysisRecordRequest:
    session: Session
    current_user: CurrentUser
    chat_record_id: int
    action_type: str
    current_assistant: CurrentAssistant | None = None
    in_chat: bool = True
    stream: bool = True


@dataclass(slots=True)
class RecommendQuestionsRequest:
    session: Session
    current_user: CurrentUser
    request_question: ChatQuestion
    record: ChatRecord
    current_assistant: CurrentAssistant
    articles_number: int = 4

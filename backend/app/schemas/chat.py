from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    source_type: str
    title: str
    snippet: str
    url: str | None = None
    document_id: int | None = None
    document_name: str | None = None
    page_number: int | None = None


class ChatQueryRequest(BaseModel):
    question: str = Field(min_length=3)
    conversation_id: int | None = None
    document_ids: list[int] | None = None


class ChatResponse(BaseModel):
    conversation_id: int
    user_message_id: int
    assistant_message_id: int
    answer: str
    decision: str
    citations: list[Citation]
    debug: dict | None = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    decision: str | None = None
    citations: list[Citation] | None = None
    created_at: datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class ConversationDetail(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: list[MessageRead]

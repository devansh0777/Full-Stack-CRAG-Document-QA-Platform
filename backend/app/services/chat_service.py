from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.graph.crag_graph import crag_graph
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ChatQueryRequest, ChatResponse, ConversationDetail
from app.services.document_qa_service import (
    answer_marks_question,
    answer_subject_list_question,
    is_marks_question,
    is_subject_list_question,
)
from app.services.search_service import retrieve_document_chunks


def _get_or_create_conversation(db: Session, user_id: int, conversation_id: int | None, question: str) -> Conversation:
    if conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )
        if conversation:
            return conversation
    conversation = Conversation(user_id=user_id, title=question[:80])
    db.add(conversation)
    db.flush()
    return conversation


def process_chat_query(db: Session, user: User, payload: ChatQueryRequest) -> ChatResponse:
    conversation = _get_or_create_conversation(db, user.id, payload.conversation_id, payload.question)
    user_message = Message(conversation_id=conversation.id, role="user", content=payload.question)
    db.add(user_message)
    db.flush()

    retrieved_chunks = retrieve_document_chunks(
        db=db,
        user_id=user.id,
        question=payload.question,
        document_ids=payload.document_ids,
    )

    deterministic_result = None
    if is_subject_list_question(payload.question):
        deterministic_result = answer_subject_list_question(retrieved_chunks)
    elif is_marks_question(payload.question):
        deterministic_result = answer_marks_question(payload.question, retrieved_chunks)

    if deterministic_result:
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=deterministic_result["answer"],
            decision=deterministic_result["decision"],
            citations=deterministic_result["citations"],
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        db.refresh(user_message)
        return ChatResponse(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            answer=deterministic_result["answer"],
            decision=deterministic_result["decision"],
            citations=deterministic_result["citations"],
            debug={"mode": "deterministic_document_qa"} if settings.enable_debug_metadata else None,
        )

    result = crag_graph.invoke(
        {
            "db": db,
            "user_id": user.id,
            "question": payload.question,
            "document_ids": payload.document_ids,
            "debug": {"pre_retrieved_chunk_count": len(retrieved_chunks)},
        }
    )

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result["answer"],
        decision=result.get("retrieval_grade"),
        citations=result.get("citations", []),
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    db.refresh(user_message)

    debug = result.get("debug") if settings.enable_debug_metadata else None
    return ChatResponse(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        answer=result["answer"],
        decision=result.get("retrieval_grade", "incorrect"),
        citations=result.get("citations", []),
        debug=debug,
    )


def list_conversations(db: Session, user_id: int) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .all()
    )


def get_conversation_detail(db: Session, user_id: int, conversation_id: int) -> ConversationDetail | None:
    conversation = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(Conversation.user_id == user_id, Conversation.id == conversation_id)
        .first()
    )
    if not conversation:
        return None

    ordered_messages = sorted(conversation.messages, key=lambda message: message.created_at)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=ordered_messages,
    )

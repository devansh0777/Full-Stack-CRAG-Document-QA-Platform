from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.chat import ConversationDetail, ConversationRead
from app.services.chat_service import get_conversation_detail, list_conversations

router = APIRouter()


@router.get("", response_model=list[ConversationRead])
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Conversation]:
    return list_conversations(db, current_user.id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    detail = get_conversation_detail(db, current_user.id, conversation_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import ChatQueryRequest, ChatResponse
from app.services.chat_service import process_chat_query

router = APIRouter()


@router.post("/query", response_model=ChatResponse)
def query_chat(
    payload: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    return process_chat_query(db=db, user=current_user, payload=payload)


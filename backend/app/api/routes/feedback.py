from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackRead
from app.services.feedback_service import create_feedback

router = APIRouter()


@router.post("", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackRead:
    feedback = create_feedback(db, current_user.id, payload)
    if not feedback:
        raise HTTPException(status_code=404, detail="Assistant message not found")
    return feedback


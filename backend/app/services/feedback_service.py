from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.feedback import Feedback
from app.models.message import Message
from app.schemas.feedback import FeedbackCreate


def create_feedback(db: Session, user_id: int, payload: FeedbackCreate) -> Feedback | None:
    message = db.get(Message, payload.message_id)
    if not message or message.role != "assistant":
        return None
    conversation = db.get(Conversation, message.conversation_id)
    if not conversation or conversation.user_id != user_id:
        return None

    feedback = Feedback(
        message_id=payload.message_id,
        user_id=user_id,
        is_positive=payload.is_positive,
        comment=payload.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback

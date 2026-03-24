from app.schemas.feedback import FeedbackCreate
from app.services.feedback_service import create_feedback


class DummyMessage:
    def __init__(self, role: str):
        self.role = role


class DummyDB:
    def __init__(self):
        self.saved = []

    def get(self, model, _id):
        if model.__name__ == "Message":
            message = DummyMessage("assistant")
            message.conversation_id = 7
            return message
        conversation = type("ConversationObj", (), {"user_id": 1})()
        return conversation

    def add(self, item):
        self.saved.append(item)

    def commit(self):
        pass

    def refresh(self, _item):
        pass


def test_feedback_creation_for_assistant_message():
    db = DummyDB()
    payload = FeedbackCreate(message_id=1, is_positive=True, comment="helpful")
    feedback = create_feedback(db, 1, payload)
    assert feedback is not None
    assert feedback.comment == "helpful"

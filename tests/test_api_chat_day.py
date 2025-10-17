import json
from datetime import datetime

import pytest

from app import app
import app_lib.models as models
from app_lib import auth


class FakeUser:
    def __init__(self):
        self.id = 1
        self.username = 'finance_user'
        self.department = 'finance'


class FakeMessage:
    def __init__(self, id, type_, content, timestamp, user):
        self.id = id
        self.type = type_
        self.content = content
        self.timestamp = timestamp
        self.user = user
        # Intentionally do NOT define chat_id to simulate older model


class FakeQuery:
    def __init__(self, msgs):
        self._msgs = msgs

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self._msgs


def test_api_chat_day_returns_messages_without_chat_id(monkeypatch):
    """Ensure /api/chat-day returns messages and falls back to message id when chat_id is missing."""

    # Prepare fake messages (no chat_id attribute)
    fake_msgs = [
        FakeMessage(101, 'user', 'User message', datetime(2025, 9, 22, 10, 0, 0), 'alice'),
        FakeMessage(102, 'assistant', 'Assistant reply', datetime(2025, 9, 22, 11, 0, 0), 'assistant'),
    ]

    # Run the test inside an application context so SQLAlchemy's query descriptor
    # can be accessed and monkeypatched safely. Also enable TESTING so our
    # modified login_required allows test flows when needed.
    app.config['TESTING'] = True
    with app.app_context():
        # Monkeypatch the ChatMessage.query to return our fake messages
        monkeypatch.setattr(models.ChatMessage, 'query', FakeQuery(fake_msgs), raising=False)

        # Monkeypatch get_current_user to return a user in the 'finance' department
        monkeypatch.setattr('app.get_current_user', lambda: FakeUser())

        # Use the Flask test client and set a session user_id so login_required passes
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 1

            resp = client.get('/api/chat-day/2025-09-22')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert isinstance(data['messages'], list)
        assert len(data['messages']) == 2

        # Each returned message should have a chat_id field equal to the message id (fallback)
        for idx, msg in enumerate(data['messages']):
            assert 'chat_id' in msg
            assert msg['chat_id'] == fake_msgs[idx].id

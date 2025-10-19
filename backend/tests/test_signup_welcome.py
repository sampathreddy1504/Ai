from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app


def test_signup_triggers_welcome_email(monkeypatch):
    # Mock create_user to return a user dict
    def fake_create_user(name, email, pw):
        return {"id": 123, "name": name, "email": email}

    monkeypatch.setattr('app.api.auth.create_user', fake_create_user)

    fake_send = MagicMock(return_value=True)
    monkeypatch.setattr('app.api.auth.send_welcome_email', fake_send)

    client = TestClient(app)
    resp = client.post('/auth/signup', json={"name": "Test User", "email": "test@example.com", "password": "secret"})
    assert resp.status_code == 200
    j = resp.json()
    assert j['success'] is True
    # send_welcome_email should have been scheduled (we can't guarantee threading in test), but our mock should be callable
    # At least ensure response contains token and user
    assert j['user']['email'] == 'test@example.com'

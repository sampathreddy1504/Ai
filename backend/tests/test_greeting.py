import asyncio
import pytest
from unittest.mock import patch, MagicMock

from app.main import app


@pytest.mark.asyncio
async def test_greet_when_not_greeted(monkeypatch):
    # Mock get_current_user_id -> 1, get_user_by_id returns a name
    async def fake_get_user_by_id(uid):
        return {"id": uid, "name": "Sampath"}

    # Mock Redis client
    fake_redis = MagicMock()
    fake_redis.get.return_value = None

    monkeypatch.setattr('app.main.get_user_by_id', fake_get_user_by_id)
    monkeypatch.setattr('app.main.get_redis_client', lambda: fake_redis)

    # Call greet endpoint via TestClient
    from fastapi.testclient import TestClient
    client = TestClient(app)
    # Use a dummy token value that get_current_user_id will decode, but we patch get_user_by_id only
    resp = client.get('/chat/greet', params={'token': 'dummy'})
    assert resp.status_code == 200
    j = resp.json()
    assert j['greeted'] is False
    assert 'Sampath' in j['message']


@pytest.mark.asyncio
async def test_greet_when_already_greeted(monkeypatch):
    async def fake_get_user_by_id(uid):
        return {"id": uid, "name": "Sampath"}

    fake_redis = MagicMock()
    fake_redis.get.return_value = '1'

    monkeypatch.setattr('app.main.get_user_by_id', fake_get_user_by_id)
    monkeypatch.setattr('app.main.get_redis_client', lambda: fake_redis)

    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get('/chat/greet', params={'token': 'dummy'})
    assert resp.status_code == 200
    j = resp.json()
    assert j['greeted'] is True
    assert j['message'] is None

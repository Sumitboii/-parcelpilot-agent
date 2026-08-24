"""
test_key_manager.py — Unit tests for Groq Key Pool Manager & Health Step Function.
"""
import asyncio
import os
import time
from unittest.mock import AsyncMock, patch

import pytest
from groq import RateLimitError, APIStatusError

from backend.key_manager import GroqKeyPoolManager, KeyHealthInfo, DEFAULT_RATE_LIMIT_COOLDOWN


@pytest.fixture
def mock_keys(monkeypatch):
    test_keys = [
        "gsk_testkey111111111111111111111111111111111",
        "gsk_testkey222222222222222222222222222222222",
        "gsk_testkey333333333333333333333333333333333",
        "gsk_testkey444444444444444444444444444444444",
        "gsk_testkey555555555555555555555555555555555",
    ]
    monkeypatch.setenv("GROQ_API_KEYS", ",".join(test_keys))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("BACKUP_GROQ_API_KEYS", raising=False)
    monkeypatch.setattr("backend.key_manager.dotenv_values", lambda *args, **kwargs: {})
    monkeypatch.setattr("backend.key_manager.load_dotenv", lambda *args, **kwargs: None)
    return test_keys



def test_key_discovery_and_masking(mock_keys):
    manager = GroqKeyPoolManager(explicit_keys=mock_keys)
    assert manager.total_keys == 5
    assert len(manager._keys) == 5
    assert manager._keys[0].masked_key.startswith("gsk_tes")
    assert manager._keys[0].masked_key.endswith("1111")
    assert manager._keys[0].status == "HEALTHY"


def test_zero_latency_selection_lru(mock_keys):
    manager = GroqKeyPoolManager(explicit_keys=mock_keys)
    
    # 1st call -> key 1
    c1, info1 = manager.get_healthy_client()
    assert info1.key_index == 1
    assert info1.total_requests == 1

    # 2nd call -> key 2 (because key 1 was just used)
    c2, info2 = manager.get_healthy_client()
    assert info2.key_index == 2
    assert info2.total_requests == 1

    # 3rd call -> key 3
    c3, info3 = manager.get_healthy_client()
    assert info3.key_index == 3


def test_rate_limit_failover_step_function(mock_keys):
    manager = GroqKeyPoolManager(explicit_keys=mock_keys)

    # Mark key 1 as rate-limited
    key1 = manager._keys[0].api_key
    manager.mark_rate_limited(key1, cooldown_seconds=60.0, error_msg="Rate limit 429")

    assert manager._keys[0].status == "RATE_LIMITED"
    assert not manager._keys[0].is_available

    # get_healthy_client should skip key 1 and pick key 2
    client, selected = manager.get_healthy_client()
    assert selected.api_key != key1
    assert selected.status == "HEALTHY"


def test_rate_limit_cooldown_auto_recovery(mock_keys):
    manager = GroqKeyPoolManager(explicit_keys=mock_keys)
    key1 = manager._keys[0].api_key

    # Mark with very short cooldown (0.01s)
    manager.mark_rate_limited(key1, cooldown_seconds=0.01)
    time.sleep(0.02)

    # Calling get_healthy_client should auto-restore key1 to HEALTHY
    client, selected = manager.get_healthy_client()
    assert manager._keys[0].status == "HEALTHY"
    assert manager._keys[0].is_available


@pytest.mark.asyncio
async def test_concurrent_health_probe(mock_keys):
    manager = GroqKeyPoolManager(explicit_keys=mock_keys)

    # Mock AsyncGroq models.list
    for k in manager._keys:
        k.client.models.list = AsyncMock(return_value={"data": []})

    results = await manager.check_all_keys_health()
    assert len(results) == 5
    for res in results:
        assert res["status"] == "HEALTHY"
        assert "latency_ms" in res


def test_status_report(mock_keys):
    manager = GroqKeyPoolManager(explicit_keys=mock_keys)
    manager.mark_rate_limited(manager._keys[1].api_key, cooldown_seconds=30.0)

    report = manager.get_status_report()
    assert report["total_keys"] == 5
    assert report["healthy_keys"] == 4
    assert report["rate_limited_keys"] == 1
    assert report["error_keys"] == 0
    assert len(report["keys"]) == 5


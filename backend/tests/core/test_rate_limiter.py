import time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.core.rate_limiter import RateLimiter


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    redis.ttl = AsyncMock(return_value=60)
    return redis


@pytest.fixture
def limiter(mock_redis):
    return RateLimiter(redis=mock_redis, max_requests=5, window_seconds=60)


@pytest.mark.asyncio
async def test_allows_under_limit(limiter, mock_redis):
    mock_redis.incr.return_value = 1
    allowed, remaining, _ = await limiter.check(uuid4())
    assert allowed is True
    assert remaining == 4


@pytest.mark.asyncio
async def test_allows_at_limit(limiter, mock_redis):
    mock_redis.incr.return_value = 5
    allowed, remaining, _ = await limiter.check(uuid4())
    assert allowed is True
    assert remaining == 0


@pytest.mark.asyncio
async def test_rejects_over_limit(limiter, mock_redis):
    mock_redis.incr.return_value = 6
    allowed, remaining, _ = await limiter.check(uuid4())
    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_sets_expiry_on_first_request(limiter, mock_redis):
    mock_redis.incr.return_value = 1
    await limiter.check(uuid4())
    mock_redis.expire.assert_called_once()


@pytest.mark.asyncio
async def test_skips_expiry_on_subsequent_requests(limiter, mock_redis):
    mock_redis.incr.return_value = 3
    await limiter.check(uuid4())
    mock_redis.expire.assert_not_called()


@pytest.mark.asyncio
async def test_key_includes_device_id_and_window(limiter, mock_redis):
    device_id = uuid4()
    with patch("src.core.rate_limiter.time") as mock_time:
        mock_time.time.return_value = 1000.0
        await limiter.check(device_id)
    key = mock_redis.incr.call_args[0][0]
    assert str(device_id) in key
    assert key.endswith(":16")  # 1000 // 60 = 16


@pytest.mark.asyncio
async def test_returns_ttl_as_reset(limiter, mock_redis):
    mock_redis.incr.return_value = 1
    mock_redis.ttl.return_value = 42
    _, _, reset = await limiter.check(uuid4())
    assert reset == 42


from src.metrics.instruments import RATE_LIMIT_REJECTIONS


def _rejection_counter_value():
    return RATE_LIMIT_REJECTIONS._value.get()


@pytest.mark.asyncio
async def test_increments_rejection_counter_on_deny(limiter, mock_redis):
    mock_redis.incr.return_value = 6  # over limit of 5
    before = _rejection_counter_value()
    await limiter.check(uuid4())
    after = _rejection_counter_value()
    assert after - before == 1


@pytest.mark.asyncio
async def test_no_rejection_counter_on_allow(limiter, mock_redis):
    mock_redis.incr.return_value = 1  # under limit
    before = _rejection_counter_value()
    await limiter.check(uuid4())
    after = _rejection_counter_value()
    assert after - before == 0

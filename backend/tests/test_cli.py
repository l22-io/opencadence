import json as json_mod  # noqa: F401
from datetime import UTC, datetime  # noqa: F401
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401
from uuid import uuid4  # noqa: F401

from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()


def test_app_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "OpenCadence" in result.stdout


def test_json_flag_accepted():
    result = runner.invoke(app, ["--json", "--help"])
    assert result.exit_code == 0


def _mock_session():
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


def _mock_factory(session=None):
    if session is None:
        session = _mock_session()
    factory = MagicMock(return_value=session)
    return factory, session


@patch("src.cli._get_session_factory")
def test_keys_generate(mock_factory_fn):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory

    result = runner.invoke(app, ["keys", "generate", "my-watch"])
    assert result.exit_code == 0
    assert "Device ID:" in result.stdout
    assert "API Key:" in result.stdout
    assert "oc_" in result.stdout
    session.execute.assert_called_once()
    session.commit.assert_called_once()


@patch("src.cli._get_session_factory")
def test_keys_generate_json(mock_factory_fn):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory

    result = runner.invoke(app, ["--json", "keys", "generate", "my-watch"])
    assert result.exit_code == 0
    data = json_mod.loads(result.stdout)
    assert "device_id" in data
    assert "api_key" in data
    assert data["name"] == "my-watch"
    assert data["source_type"] == "healthkit"


@patch("src.cli._get_session_factory")
def test_keys_generate_custom_source(mock_factory_fn):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory

    result = runner.invoke(
        app, ["keys", "generate", "pixel-watch", "--source-type", "health-connect"]
    )
    assert result.exit_code == 0
    assert "health-connect" in result.stdout


def _mock_device_row(device_id, revoked=False):
    row = MagicMock()
    row._mapping = {
        "id": device_id,
        "name": "test-device",
        "revoked_at": datetime(2026, 1, 1, tzinfo=UTC) if revoked else None,
    }
    return row


def _mock_result(rows):
    result = MagicMock()
    result.first.return_value = rows[0] if rows else None
    result.__iter__ = MagicMock(return_value=iter(rows))
    return result


@patch("src.cli._get_session_factory")
def test_keys_rotate(mock_factory_fn):
    device_id = uuid4()
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    session.execute.return_value = _mock_result([_mock_device_row(device_id)])

    result = runner.invoke(app, ["keys", "rotate", str(device_id)])
    assert result.exit_code == 0
    assert "New API Key:" in result.stdout
    assert "oc_" in result.stdout
    assert session.commit.called


@patch("src.cli._get_session_factory")
def test_keys_rotate_not_found(mock_factory_fn):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    session.execute.return_value = _mock_result([])

    result = runner.invoke(app, ["keys", "rotate", str(uuid4())])
    assert result.exit_code == 1
    assert "not found" in result.stdout


@patch("src.cli._get_session_factory")
def test_keys_rotate_revoked(mock_factory_fn):
    device_id = uuid4()
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    session.execute.return_value = _mock_result([_mock_device_row(device_id, revoked=True)])

    result = runner.invoke(app, ["keys", "rotate", str(device_id)])
    assert result.exit_code == 1
    assert "revoked" in result.stdout


@patch("src.cli._get_session_factory")
def test_keys_revoke(mock_factory_fn):
    device_id = uuid4()
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    session.execute.return_value = _mock_result([_mock_device_row(device_id)])

    result = runner.invoke(app, ["keys", "revoke", str(device_id)])
    assert result.exit_code == 0
    assert "revoked" in result.stdout.lower()
    assert session.commit.called


@patch("src.cli._get_session_factory")
def test_keys_revoke_not_found(mock_factory_fn):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    session.execute.return_value = _mock_result([])

    result = runner.invoke(app, ["keys", "revoke", str(uuid4())])
    assert result.exit_code == 1
    assert "not found" in result.stdout


@patch("src.cli._get_session_factory")
def test_keys_revoke_already_revoked(mock_factory_fn):
    device_id = uuid4()
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    session.execute.return_value = _mock_result([_mock_device_row(device_id, revoked=True)])

    result = runner.invoke(app, ["keys", "revoke", str(device_id)])
    assert result.exit_code == 1
    assert "already revoked" in result.stdout


@patch("src.cli.SampleRepository")
@patch("src.cli._get_session_factory")
def test_export_csv(mock_factory_fn, mock_repo):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    repo_instance = mock_repo.return_value
    repo_instance.query_raw = AsyncMock(return_value=[
        {"time": datetime(2026, 3, 1, tzinfo=UTC), "value": 72.0, "unit": "bpm",
         "source": "healthkit"},
        {"time": datetime(2026, 3, 1, 0, 1, tzinfo=UTC), "value": 75.0, "unit": "bpm",
         "source": "healthkit"},
    ])

    result = runner.invoke(app, [
        "export", str(uuid4()), "--metric", "heart_rate",
        "--start", "2026-03-01", "--end", "2026-03-14",
    ])
    assert result.exit_code == 0
    assert "time,value,unit,source" in result.stdout
    assert "72.0" in result.stdout
    assert "75.0" in result.stdout


@patch("src.cli.SampleRepository")
@patch("src.cli._get_session_factory")
def test_export_json(mock_factory_fn, mock_repo):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    repo_instance = mock_repo.return_value
    repo_instance.query_raw = AsyncMock(return_value=[
        {"time": datetime(2026, 3, 1, tzinfo=UTC), "value": 72.0, "unit": "bpm",
         "source": "healthkit"},
    ])

    result = runner.invoke(app, [
        "export", str(uuid4()), "--metric", "heart_rate",
        "--start", "2026-03-01", "--end", "2026-03-14", "--format", "json",
    ])
    assert result.exit_code == 0
    data = json_mod.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["value"] == 72.0


@patch("src.cli.SampleRepository")
@patch("src.cli._get_session_factory")
def test_export_json_global_flag(mock_factory_fn, mock_repo):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    repo_instance = mock_repo.return_value
    repo_instance.query_raw = AsyncMock(return_value=[
        {"time": datetime(2026, 3, 1, tzinfo=UTC), "value": 72.0, "unit": "bpm",
         "source": "healthkit"},
    ])

    result = runner.invoke(app, [
        "--json", "export", str(uuid4()), "--metric", "heart_rate",
        "--start", "2026-03-01", "--end", "2026-03-14",
    ])
    assert result.exit_code == 0
    data = json_mod.loads(result.stdout)
    assert len(data) == 1


@patch("src.cli.SampleRepository")
@patch("src.cli._get_session_factory")
def test_export_empty(mock_factory_fn, mock_repo):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    repo_instance = mock_repo.return_value
    repo_instance.query_raw = AsyncMock(return_value=[])

    result = runner.invoke(app, [
        "export", str(uuid4()), "--metric", "heart_rate",
        "--start", "2026-03-01", "--end", "2026-03-14",
    ])
    assert result.exit_code == 0


@patch("src.cli.Redis")
@patch("src.cli._get_settings")
@patch("src.cli._get_session_factory")
def test_health_all_ok(mock_factory_fn, mock_settings_fn, mock_redis_cls):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory

    mock_settings = MagicMock()
    mock_settings.redis_url = "redis://localhost"
    mock_settings_fn.return_value = mock_settings

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()
    mock_redis_cls.from_url.return_value = mock_redis

    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "ok" in result.stdout.lower()


@patch("src.cli.Redis")
@patch("src.cli._get_settings")
@patch("src.cli._get_session_factory")
def test_health_db_down(mock_factory_fn, mock_settings_fn, mock_redis_cls):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    session.execute.side_effect = Exception("connection refused")

    mock_settings = MagicMock()
    mock_settings.redis_url = "redis://localhost"
    mock_settings_fn.return_value = mock_settings

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()
    mock_redis_cls.from_url.return_value = mock_redis

    result = runner.invoke(app, ["health"])
    assert result.exit_code == 1
    assert "connection refused" in result.stdout.lower()


@patch("src.cli.Redis")
@patch("src.cli._get_settings")
@patch("src.cli._get_session_factory")
def test_health_redis_down(mock_factory_fn, mock_settings_fn, mock_redis_cls):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory

    mock_settings = MagicMock()
    mock_settings.redis_url = "redis://localhost"
    mock_settings_fn.return_value = mock_settings

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(side_effect=ConnectionError("connection refused"))
    mock_redis.aclose = AsyncMock()
    mock_redis_cls.from_url.return_value = mock_redis

    result = runner.invoke(app, ["health"])
    assert result.exit_code == 1
    assert "ok" in result.stdout.lower()  # DB is ok
    assert "connection refused" in result.stdout.lower()  # Redis is down


@patch("src.cli.Redis")
@patch("src.cli._get_settings")
@patch("src.cli._get_session_factory")
def test_health_json(mock_factory_fn, mock_settings_fn, mock_redis_cls):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory

    mock_settings = MagicMock()
    mock_settings.redis_url = "redis://localhost"
    mock_settings_fn.return_value = mock_settings

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()
    mock_redis_cls.from_url.return_value = mock_redis

    result = runner.invoke(app, ["--json", "health"])
    assert result.exit_code == 0
    data = json_mod.loads(result.stdout)
    assert data["db"] == "ok"
    assert data["redis"] == "ok"


def _mock_dl_row(id_=1, replayed=False):
    now = datetime(2026, 3, 14, 10, 0, tzinfo=UTC)
    row = MagicMock()
    row._mapping = {
        "id": id_,
        "event_type": "DataReceived",
        "error": "ValueError: bad data",
        "module": "storage",
        "created_at": now,
        "replayed_at": now if replayed else None,
    }
    return row


@patch("src.cli._get_session_factory")
def test_dead_letters_list(mock_factory_fn):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    rows = [_mock_dl_row(id_=1), _mock_dl_row(id_=2)]
    result_mock = MagicMock()
    result_mock.__iter__ = MagicMock(return_value=iter(rows))
    session.execute.return_value = result_mock

    result = runner.invoke(app, ["dead-letters", "list"])
    assert result.exit_code == 0
    assert "DataReceived" in result.stdout
    assert "pending" in result.stdout.lower()


@patch("src.cli._get_session_factory")
def test_dead_letters_list_json(mock_factory_fn):
    factory, session = _mock_factory()
    mock_factory_fn.return_value = factory
    rows = [_mock_dl_row(id_=1)]
    result_mock = MagicMock()
    result_mock.__iter__ = MagicMock(return_value=iter(rows))
    session.execute.return_value = result_mock

    result = runner.invoke(app, ["--json", "dead-letters", "list"])
    assert result.exit_code == 0
    data = json_mod.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["event_type"] == "DataReceived"

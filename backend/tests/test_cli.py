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

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

"""Tests for the eumpa_studio command line interface."""

import tomllib

from typer.testing import CliRunner

from eumpa_studio.cli import app_cli


def test_cli_help_lists_start_command():
    runner = CliRunner()

    result = runner.invoke(app_cli, ["--help"])

    assert result.exit_code == 0
    assert "Commands" in result.stdout
    assert "start" in result.stdout
    assert "Start the eumpa_studio backend" in result.stdout


def test_pyproject_declares_eumpa_studio_script():
    with open("pyproject.toml", "rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    assert (
        pyproject["project"]["scripts"]["eumpa_studio"]
        == "eumpa_studio.cli:main"
    )

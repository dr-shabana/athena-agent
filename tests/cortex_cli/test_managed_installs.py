from types import SimpleNamespace
from unittest.mock import patch

from cortex_cli.config import (
    format_managed_message,
    get_managed_system,
    recommended_update_command,
)
from cortex_cli.main import cmd_update
from tools.skills_hub import OptionalSkillSource


def test_get_managed_system_homebrew(monkeypatch):
    monkeypatch.setenv("HERMES_MANAGED", "homebrew")

    assert get_managed_system() == "Homebrew"
    assert recommended_update_command() == "brew upgrade athena-agent"


def test_format_managed_message_homebrew(monkeypatch):
    monkeypatch.setenv("HERMES_MANAGED", "homebrew")

    message = format_managed_message("update Athena Agent")

    assert "managed by Homebrew" in message
    assert "brew upgrade athena-agent" in message


def test_recommended_update_command_defaults_to_hermes_update(monkeypatch):
    monkeypatch.delenv("HERMES_MANAGED", raising=False)

    # Also short-circuit the .managed marker path — CI runners may have an
    # ambient ~/.cortex/.managed if a prior test left CORTEX_HOME pointing
    # somewhere with that marker, which would make get_managed_update_command()
    # return "Update your Nix flake input ..." instead of falling through to
    # detect_install_method().
    with patch("cortex_cli.config.get_managed_update_command", return_value=None), \
         patch("cortex_cli.config.detect_install_method", return_value="git"):
        assert recommended_update_command() == "hermes update"


def test_cmd_update_blocks_managed_homebrew(monkeypatch, capsys):
    monkeypatch.setenv("HERMES_MANAGED", "homebrew")

    with patch("cortex_cli.main.subprocess.run") as mock_run:
        cmd_update(SimpleNamespace())

    assert not mock_run.called
    captured = capsys.readouterr()
    assert "managed by Homebrew" in captured.err
    assert "brew upgrade athena-agent" in captured.err


def test_optional_skill_source_honors_env_override(monkeypatch, tmp_path):
    optional_dir = tmp_path / "optional-skills"
    optional_dir.mkdir()
    monkeypatch.setenv("HERMES_OPTIONAL_SKILLS", str(optional_dir))

    source = OptionalSkillSource()

    assert source._optional_dir == optional_dir

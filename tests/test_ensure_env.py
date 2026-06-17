"""Tests for environment bootstrap."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("ensure_env", ROOT / "scripts" / "ensure_env.py")
assert _spec and _spec.loader
env = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(env)


def test_is_ready_false_without_venv(tmp_path, monkeypatch):
    monkeypatch.setattr(env, "ROOT", tmp_path)
    monkeypatch.setattr(env, "VENV_DIR", tmp_path / ".venv")
    monkeypatch.setattr(env, "VENV_PYTHON", tmp_path / ".venv" / "Scripts" / "python.exe")
    monkeypatch.setattr(env, "VENV_CLI", tmp_path / ".venv" / "Scripts" / "skyblock-agent.exe")
    monkeypatch.setattr(env, "STAMP", tmp_path / ".venv" / ".install-stamp")
    monkeypatch.setattr(env, "PYPROJECT", tmp_path / "pyproject.toml")
    assert env.is_ready(None) is False

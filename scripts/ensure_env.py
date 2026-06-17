"""Create venv and install dependencies only when needed."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"
PYPROJECT = ROOT / "pyproject.toml"
STAMP = VENV_DIR / ".install-stamp"

if sys.platform == "win32":
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
    VENV_PIP = VENV_DIR / "Scripts" / "pip.exe"
    VENV_CLI = VENV_DIR / "Scripts" / "skyblock-agent.exe"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"
    VENV_PIP = VENV_DIR / "bin" / "pip"
    VENV_CLI = VENV_DIR / "bin" / "skyblock-agent"


def _run(cmd: list[str], *, quiet: bool = False) -> None:
    kwargs: dict = {"cwd": ROOT, "check": True}
    if quiet:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    subprocess.run(cmd, **kwargs)


def _import_check(extra: str | None) -> bool:
    if not VENV_PYTHON.is_file() or not VENV_CLI.is_file():
        return False
    snippet = "import skyblock_agent"
    if extra == "gui":
        snippet += "; import fastapi, uvicorn"
    result = subprocess.run(
        [str(VENV_PYTHON), "-c", snippet],
        cwd=ROOT,
        capture_output=True,
    )
    return result.returncode == 0


def _pyproject_changed() -> bool:
    if not PYPROJECT.is_file() or not STAMP.is_file():
        return True
    return PYPROJECT.stat().st_mtime > STAMP.stat().st_mtime


def is_ready(extra: str | None) -> bool:
    return _import_check(extra) and not _pyproject_changed()


def ensure(extra: str | None) -> None:
    if is_ready(extra):
        return

    if not VENV_PYTHON.is_file():
        print("[skyblock-agent] Creating virtual environment...")
        _run([sys.executable, "-m", "venv", str(VENV_DIR)])

    print("[skyblock-agent] Installing dependencies...")
    _run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"], quiet=True)
    install_target = ".[gui]" if extra == "gui" else "."
    _run([str(VENV_PIP), "install", "-e", install_target, "-q"], quiet=True)
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.write_text("ok\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure skyblock-agent venv is ready")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Require GUI extras (fastapi, uvicorn)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed status",
    )
    args = parser.parse_args()
    extra = "gui" if args.gui else None
    if args.verbose:
        print(f"[ensure_env] ROOT={ROOT}")
        print(f"[ensure_env] VENV_PYTHON={VENV_PYTHON} exists={VENV_PYTHON.is_file()}")
        print(f"[ensure_env] VENV_CLI={VENV_CLI} exists={VENV_CLI.is_file()}")
        print(f"[ensure_env] ready={is_ready(extra)} pyproject_changed={_pyproject_changed()}")
    try:
        if is_ready(extra):
            if args.verbose:
                print("[ensure_env] Environment already ready - skipping install.")
            return 0
        ensure(extra)
        if args.verbose:
            print("[ensure_env] Environment prepared successfully.")
    except subprocess.CalledProcessError:
        print("[skyblock-agent] Failed to prepare environment.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

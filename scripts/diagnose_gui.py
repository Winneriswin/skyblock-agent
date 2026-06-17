"""Pre-flight checks for the local GUI (run from start.bat)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "skyblock_agent" / "web" / "static"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
VENV_CLI = ROOT / ".venv" / "Scripts" / "skyblock-agent.exe"


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def check_file(path: Path, *, must_contain: list[str] | None = None) -> bool:
    if not path.is_file():
        fail(f"Missing file: {path}")
        return False
    ok(f"Found: {path.relative_to(ROOT)}")
    if must_contain:
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in must_contain:
            if needle not in text:
                fail(f"{path.name} missing expected snippet: {needle!r}")
                return False
        ok(f"{path.name} content checks passed ({len(must_contain)} markers)")
    return True


def main() -> int:
    host = "127.0.0.1"
    port = 8765
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    print("[diagnose] Project root:", ROOT)
    print("[diagnose] Working directory:", Path.cwd())

    errors = 0

    print("[diagnose] Virtual environment")
    if VENV_PY.is_file():
        ok(f"Python: {VENV_PY}")
    else:
        fail(f"Python not found: {VENV_PY}")
        errors += 1

    if VENV_CLI.is_file():
        ok(f"CLI: {VENV_CLI}")
    else:
        fail(f"CLI not found: {VENV_CLI}")
        errors += 1

    print("[diagnose] Installed package")
    if VENV_PY.is_file():
        import subprocess

        result = subprocess.run(
            [str(VENV_PY), "-c", "import skyblock_agent; print(skyblock_agent.__file__)"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            ok(f"skyblock_agent -> {result.stdout.strip()}")
        else:
            fail("Cannot import skyblock_agent")
            if result.stderr.strip():
                print("         ", result.stderr.strip())
            errors += 1

        result = subprocess.run(
            [str(VENV_PY), "-c", "import fastapi, uvicorn; print('gui deps ok')"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            ok("GUI dependencies (fastapi, uvicorn)")
        else:
            fail("GUI dependencies missing")
            errors += 1

    print("[diagnose] Static UI files (source)")
    for name, needles in [
        ("index.html", ['data-view="market"', "onsubmit=\"return false\"", "app.js"]),
        ("app.js", ["function initApp", "switchView", "MarketBrowser.open"]),
        ("market-browser.js", ["window.MarketBrowser", "initMarketBrowser"]),
    ]:
        if not check_file(STATIC / name, must_contain=needles):
            errors += 1

    print("[diagnose] JavaScript syntax (node --check)")
    import shutil
    import subprocess

    node = shutil.which("node")
    if node:
        for name in ("minetip.js", "item-tooltips.js", "market-browser.js", "app.js"):
            path = STATIC / name
            if not path.is_file():
                continue
            result = subprocess.run(
                [node, "--check", str(path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                ok(f"{name} syntax valid")
            else:
                fail(f"{name} syntax error: {result.stderr.strip().splitlines()[-1] if result.stderr else 'unknown'}")
                errors += 1
    else:
        warn("Node.js not found — skipping JS syntax check")

    print("[diagnose] Served package static path")
    if VENV_PY.is_file():
        import subprocess

        script = (
            "from skyblock_agent.web.app import STATIC_DIR, _asset_version, _render_index_html; "
            "html = _render_index_html(); "
            "print(STATIC_DIR); "
            "print('asset_version=' + _asset_version()); "
            "print('market_nav=' + str('data-view=\"market\"' in html)); "
            "print('init_guard=' + str('onsubmit=\"return false\"' in html))"
        )
        result = subprocess.run(
            [str(VENV_PY), "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                ok(line)
        else:
            fail("Could not load web.app from installed package")
            if result.stderr.strip():
                print("         ", result.stderr.strip())
            errors += 1

    print(f"[diagnose] Port {port} on {host}")
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    in_use = sock.connect_ex((host, port)) == 0
    sock.close()
    if in_use:
        warn(f"Port {port} is already in use (old server may still be running)")
        url = f"http://{host}:{port}/"
        health_url = f"http://{host}:{port}/api/health"
        try:
            with urllib.request.urlopen(health_url, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            ok(f"Existing server health: {data.get('status', '?')}")
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            warn(f"Port busy but health check failed: {exc}")

        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            ok(f"GET / -> HTTP {resp.status}")
            for label, needle in [
                ("Resources nav", 'data-view="market"'),
                ("form guard", 'onsubmit="return false"'),
                ("app.js", "app.js"),
            ]:
                if needle in html:
                    ok(f"Live HTML has {label}")
                else:
                    fail(f"Live HTML missing {label}")
                    errors += 1
        except (urllib.error.URLError, OSError) as exc:
            warn(f"Could not fetch live HTML: {exc}")
    else:
        ok(f"Port {port} is free")

    print("[diagnose] Summary")
    if errors:
        print(f"  {errors} check(s) failed — fix the items above before using the GUI.")
        return 1

    print("  All checks passed.")
    print("  If the browser still has no response, press Ctrl+Shift+R on the GUI page")
    print("  or close all tabs for http://127.0.0.1:8765 and restart start.bat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

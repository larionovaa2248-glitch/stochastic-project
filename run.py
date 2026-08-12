"""One-command runner for the whole project — Windows, macOS, and Linux.

    python run.py                 set up + run tests + launch the dashboard
    python run.py --experiments   also regenerate all CSVs and figures first
    python run.py --slides        serve the presentation instead (slides +
                                  one-click dashboard button)
    python run.py --skip-tests    skip the test suite
    python run.py --no-dashboard  stop after setup/tests (CI-style check)

What it does, in order:
  1. creates a local virtual environment in .venv (first run only)
  2. installs requirements.txt into it
  3. runs the 37-test validation suite
  4. launches the Streamlit dashboard at http://localhost:8601
Ctrl-C stops the dashboard. Needs Python 3.11+ on PATH; nothing else.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def run(cmd: list, **kwargs) -> None:
    print("\n$ " + " ".join(str(c) for c in cmd), flush=True)
    subprocess.check_call([str(c) for c in cmd], cwd=str(ROOT), **kwargs)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--experiments", action="store_true",
                    help="regenerate results/ CSVs and report figures (a few minutes)")
    ap.add_argument("--slides", action="store_true",
                    help="serve the slide deck (with one-click dashboard) instead")
    ap.add_argument("--skip-tests", action="store_true", help="skip the test suite")
    ap.add_argument("--no-dashboard", action="store_true",
                    help="stop after setup and tests")
    args = ap.parse_args()

    if sys.version_info < (3, 11):
        print(f"WARNING: Python 3.11+ recommended; you have {sys.version.split()[0]}.")

    py = venv_python()
    if not py.exists():
        print(f"[run] creating virtual environment in {VENV} …")
        venv.create(VENV, with_pip=True)
    print("[run] installing dependencies (fast if already installed) …")
    run([py, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
         "-r", "requirements.txt"])

    if not args.skip_tests:
        print("[run] running the validation suite …")
        run([py, "-m", "pytest", "tests/", "-q"])

    if args.experiments:
        print("[run] regenerating all experiments and figures (seed 20260812) …")
        run([py, "-m", "src.experiments"])

    if args.slides:
        print("[run] serving slides at http://localhost:8700 "
              "(demo button boots the dashboard) — Ctrl-C to stop")
        run([py, str(ROOT / "slides" / "present.py")])
    elif not args.no_dashboard:
        # headless=true suppresses Streamlit's first-run email prompt; we open
        # the browser ourselves as soon as the server answers.
        import socket
        import time
        import webbrowser

        url = "http://localhost:8601"
        print(f"[run] launching the dashboard at {url} — Ctrl-C to stop")
        proc = subprocess.Popen(
            [str(py), "-m", "streamlit", "run", str(ROOT / "dashboard" / "app.py"),
             "--server.port", "8601", "--server.headless", "true",
             "--browser.gatherUsageStats", "false"],
            cwd=str(ROOT),
        )
        for _ in range(120):
            if proc.poll() is not None:
                return proc.returncode or 1
            try:
                with socket.create_connection(("127.0.0.1", 8601), timeout=0.5):
                    break
            except OSError:
                time.sleep(0.5)
        webbrowser.open(url)
        proc.wait()
    else:
        print("[run] done — environment ready, tests green.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        print(f"\n[run] step failed with exit code {exc.returncode}.")
        sys.exit(exc.returncode)
    except KeyboardInterrupt:
        print("\n[run] stopped.")
        sys.exit(0)

"""Presentation server: serves the slide deck AND powers the demo button.

Run from the repo root (or anywhere):

    python slides/present.py

- Serves the slides at http://localhost:8700 (and opens them in your browser).
- The "Open the dashboard" button on the demo slide calls this server's tiny
  API, which starts `streamlit run dashboard/app.py` on port 8601 if it is
  not already running, waits until it answers, and only then opens it.

Stdlib only — no extra dependencies. Streamlit itself is launched from the
project's .venv when present, else from the current interpreter.

Flags:  --no-open   don't auto-open the slides in a browser
        --slides-port / --dashboard-port to override the defaults
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SLIDES_DIR = Path(__file__).resolve().parent
REPO_ROOT = SLIDES_DIR.parent
DASHBOARD_APP = REPO_ROOT / "dashboard" / "app.py"

_streamlit_proc: subprocess.Popen | None = None


def dashboard_python() -> str:
    """Prefer the project venv's interpreter; fall back to this one."""
    venv_py = REPO_ROOT / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def start_dashboard(port: int) -> dict:
    """Spawn streamlit if nothing is listening on the dashboard port yet."""
    global _streamlit_proc
    if port_open(port):
        return {"running": True, "started": False}
    if _streamlit_proc is not None and _streamlit_proc.poll() is None:
        return {"running": False, "started": True}  # still booting
    log = open(SLIDES_DIR / ".dashboard.log", "ab")
    _streamlit_proc = subprocess.Popen(
        [
            dashboard_python(), "-m", "streamlit", "run", str(DASHBOARD_APP),
            "--server.headless", "true",
            "--server.port", str(port),
            "--browser.gatherUsageStats", "false",
        ],
        cwd=str(REPO_ROOT),
        stdout=log,
        stderr=log,
        start_new_session=True,  # keep running even if this server stops
    )
    return {"running": False, "started": True}


class PresentHandler(SimpleHTTPRequestHandler):
    """Static slides + a two-endpoint JSON API for the demo button."""

    dashboard_port = 8601

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 — http.server naming
        path = self.path.split("?")[0]
        if path == "/api/dashboard/status":
            self._json({"running": port_open(self.dashboard_port),
                        "port": self.dashboard_port})
        elif path == "/api/dashboard/start":
            self._json(start_dashboard(self.dashboard_port))
        else:
            super().do_GET()

    def log_message(self, fmt: str, *args) -> None:
        if "/api/" not in (args[0] if args else ""):
            super().log_message(fmt, *args)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slides-port", type=int, default=8700)
    ap.add_argument("--dashboard-port", type=int, default=8601)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    PresentHandler.dashboard_port = args.dashboard_port
    handler = partial(PresentHandler, directory=str(SLIDES_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", args.slides_port), handler)
    url = f"http://localhost:{args.slides_port}"
    print(f"[present] slides at {url}  ·  demo button will boot the dashboard "
          f"on port {args.dashboard_port}  ·  Ctrl-C to stop")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[present] stopped (the dashboard, if started, keeps running)")


if __name__ == "__main__":
    main()

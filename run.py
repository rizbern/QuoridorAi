#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py — One-shot launcher for Quoridor.

Serves the FastAPI backend (api.py) and the static frontend
(index.html / style.css / game.js) from a single process.

Usage:
    python run.py [--host HOST] [--port PORT] [--no-browser]

Dependencies (install once):
    pip install fastapi uvicorn[standard]

Expected project layout:
    run.py
    backend/
        ai.py       ← contains both BFS helpers and MCTS; aliased as 'mcts'
        api.py
        board.py
        game.py
    frontend/
        game.js
        index.html
        style.css
"""

import argparse
import sys
import threading
import time
import webbrowser
from pathlib import Path

# ── Resolve directories ────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent.resolve()
BACKEND  = ROOT / "backend"
FRONTEND = ROOT / "frontend"

for d, label in [(BACKEND, "backend/"), (FRONTEND, "frontend/")]:
    if not d.is_dir():
        sys.exit(
            f"[run.py] Expected a '{label}' folder next to run.py but didn't find one.\n"
            f"         Looked in: {ROOT}"
        )

# ── Put backend/ on sys.path so all relative imports inside it work ────────────
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# ── Register ai.py as 'mcts' so api.py's `from mcts import …` succeeds ────────
import importlib.util

def _register_alias(real_name: str, alias: str, search_dir: Path) -> None:
    """Load *real_name*.py from *search_dir* and expose it as *alias* too."""
    if alias in sys.modules:
        return
    filepath = search_dir / f"{real_name}.py"
    if not filepath.exists():
        raise FileNotFoundError(
            f"[run.py] Cannot find '{real_name}.py' in {search_dir}."
        )
    spec   = importlib.util.spec_from_file_location(real_name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[real_name] = module
    sys.modules[alias]     = module   # the alias api.py expects
    spec.loader.exec_module(module)

_register_alias("ai", "mcts", BACKEND)

# ── Create bfs.py / mcts.py shims on disk if absent ─────────────────────────
# Some code paths check for these files by name even though all logic lives
# in ai.py. One-line re-export shims satisfy those checks without duplicating
# any code.
for _shim in ("bfs", "mcts"):
    _shim_path = BACKEND / f"{_shim}.py"
    if not _shim_path.exists():
        _shim_path.write_text(
            "# Auto-generated shim — all logic lives in ai.py\n"
            "from ai import *  # noqa: F401,F403\n"
        )
        print(f"[run.py] Created shim: backend/{_shim}.py -> ai.py")

# ── Import the FastAPI app from backend/api.py ─────────────────────────────────
try:
    from api import app as fastapi_app
except ImportError as exc:
    sys.exit(
        f"[run.py] Failed to import backend/api.py: {exc}\n"
        "         Make sure fastapi is installed:  pip install fastapi uvicorn[standard]"
    )

# ── Serve the frontend ─────────────────────────────────────────────────────────
from fastapi.responses import FileResponse

FRONTEND_FILES = {
    "index.html": "text/html",
    "style.css":  "text/css",
    "app.js":     "application/javascript",
}

missing = [f for f in FRONTEND_FILES if not (FRONTEND / f).exists()]
if missing:
    print(
        f"[run.py] WARNING: missing frontend file(s): {', '.join(missing)}\n"
        "         The game UI may not load correctly."
    )

@fastapi_app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(str(FRONTEND / "index.html"))

@fastapi_app.get("/style.css", include_in_schema=False)
def serve_css():
    return FileResponse(str(FRONTEND / "style.css"), media_type="text/css")

@fastapi_app.get("/game.js", include_in_schema=False)
def serve_js():
    return FileResponse(str(FRONTEND / "app.js"), media_type="application/javascript")


# ── CLI args ───────────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(description="Quoridor launcher")
    parser.add_argument("--host",       default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port",       default=8000, type=int, help="Bind port (default: 8000)")
    parser.add_argument("--no-browser", action="store_true",   help="Don't open browser automatically")
    return parser.parse_args()


# ── Browser opener ─────────────────────────────────────────────────────────────
def _open_browser(url: str, delay: float = 1.5) -> None:
    time.sleep(delay)
    webbrowser.open(url)


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    args = parse_args()

    url = f"http://{args.host}:{args.port}"

    print("=" * 52)
    print("  QUORIDOR")
    print("=" * 52)
    print(f"  Backend + frontend  →  {url}")
    print(f"  API docs            →  {url}/docs")
    print(f"  Press  Ctrl+C  to stop")
    print("=" * 52)

    if not args.no_browser:
        t = threading.Thread(target=_open_browser, args=(url,), daemon=True)
        t.start()

    try:
        import uvicorn
    except ImportError:
        sys.exit(
            "[run.py] uvicorn is not installed.\n"
            "Install it with:  pip install uvicorn[standard]"
        )

    uvicorn.run(
        fastapi_app,
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
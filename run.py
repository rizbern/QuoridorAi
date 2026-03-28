import uvicorn
import webbrowser
import threading
import time
import os
import sys

HOST = "localhost"
PORT = 8000
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")


def open_browser():
    """Wait briefly for the server to start, then open the browser."""
    time.sleep(1.5)
    webbrowser.open(f"http://{HOST}:{PORT}/app")
    print(f"\n  Browser opened → http://{HOST}:{PORT}/app")
    print("  Press CTRL+C to stop the server\n")


if __name__ == "__main__":

    print("""
  ╔═══════════════════════════════════╗
  ║          Q U O R I D O R          ║
  ║       AI powered by MCTS          ║
  ╚═══════════════════════════════════╝

  Starting server on http://{host}:{port}
    """.format(host=HOST, port=PORT))

    # Check that the backend files exist
    required = ["backend/api.py", "backend/board.py", "backend/bfs.py", "backend/mcts.py"]
    missing = [f for f in required if not os.path.exists(os.path.join(os.path.dirname(__file__), f))]
    if missing:
        print("  ✗ Missing files:")
        for f in missing:
            print(f"      {f}")
        sys.exit(1)

    # Open browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Add backend to path so uvicorn can find the modules
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

    # Serve the FastAPI app — also mounts the frontend as static files
    from fastapi.staticfiles import StaticFiles
    from api import app # type: ignore

    # Mount the frontend folder so index.html is served at /app
    if os.path.exists(FRONTEND_DIR):
        app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    else:
        print("  ⚠  frontend/ folder not found — API only mode")

    uvicorn.run(app, host=HOST, port=PORT)
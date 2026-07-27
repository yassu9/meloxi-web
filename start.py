#!/usr/bin/env python3
"""
Meloxi One-Click Launcher.
Runs the FastAPI Backend, built React Web App, and opens it in your default browser.
"""

import os
import sys
import socket
import subprocess
import time
import webbrowser
from pathlib import Path

# Ensure Homebrew path is accessible for Node/npm if needed
os.environ["PATH"] = f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"

def kill_stale_servers():
    """Kill lingering background servers to ensure fresh code is loaded."""
    try:
        subprocess.run("lsof -ti:8000 | xargs kill -9 2>/dev/null", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-9", "-f", "backend.main:app"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-9", "-f", "uvicorn"], stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    except Exception:
        pass

def find_available_port(start_port: int = 8000) -> int:
    """Find a free port starting from start_port after killing stale processes."""
    kill_stale_servers()
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port

def ensure_frontend_built():
    """Build React frontend bundle to guarantee latest code is served."""
    print("📦 Building Meloxi Web Frontend bundle...")
    try:
        subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True)
        print("✅ Frontend built successfully.")
    except Exception as e:
        print(f"⚠️ Warning during frontend build: {e}")

def open_browser(url: str, delay: float = 1.5):
    """Open default browser after server starts."""
    def _open():
        time.sleep(delay)
        print(f"🌐 Opening {url} in your browser...")
        webbrowser.open(url)
    
    import threading
    threading.Thread(target=_open, daemon=True).start()

def main():
    print("\n" + "="*60)
    print("🎵  MELOXI WEB APPLICATION - ONE-CLICK LAUNCHER  🎵")
    print("="*60 + "\n")

    port = find_available_port(8000)
    ensure_frontend_built()

    url = f"http://127.0.0.1:{port}"
    print(f"➜ 🌐 Web App:  {url}")
    print(f"➜ 📄 API Docs: {url}/docs\n")
    print("Press CTRL+C to stop the server.\n")

    open_browser(url)

    try:
        import uvicorn
        # reload=False is MANDATORY so file writes (SQLite DB, logs) don't restart server during playback
        uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=False)

    except KeyboardInterrupt:
        print("\n👋 Meloxi Web App stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()

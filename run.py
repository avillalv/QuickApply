#!/usr/bin/env python3
"""
QuickApply launcher — starts the FastAPI backend and Vite frontend,
then opens localhost:5173 in the browser.
"""
import os
import sys
import subprocess
import time
import signal
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

processes: list[subprocess.Popen] = []


def cleanup(sig=None, frame=None):
    print("\nShutting down QuickApply...")
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    for p in processes:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def check_requirements():
    env_file = ROOT / ".env"
    if not env_file.exists():
        example = ROOT / ".env.example"
        if example.exists():
            import shutil
            shutil.copy(example, env_file)
            print("Created .env from .env.example — fill in your API keys before continuing.")
            print(f"  Edit: {env_file}")
            sys.exit(1)


def start_backend():
    print("Starting FastAPI backend on http://localhost:8000 ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    p = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=BACKEND_DIR,
        env=env,
    )
    processes.append(p)
    return p


def start_frontend():
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print("Installing frontend dependencies (npm install)...")
        result = subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)
        if result.returncode != 0:
            print("npm install failed. Make sure Node.js is installed.")
            sys.exit(1)

    print("Starting Vite dev server on http://localhost:5173 ...")
    p = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
    )
    processes.append(p)
    return p


def wait_for_backend(timeout=30):
    import urllib.request
    import urllib.error

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen("http://localhost:8000/api/health", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def main():
    print("=" * 60)
    print("  QuickApply — Job Application Automation Tool")
    print("=" * 60)

    check_requirements()

    backend_proc = start_backend()
    frontend_proc = start_frontend()

    print("Waiting for backend to start...")
    if wait_for_backend(30):
        print("Backend ready.")
    else:
        print("Backend may not be ready yet — check for errors above.")

    time.sleep(3)
    print("\nOpening QuickApply in browser...")
    webbrowser.open("http://localhost:5173")

    print("\nQuickApply is running. Press Ctrl+C to stop.\n")

    try:
        while True:
            if backend_proc.poll() is not None:
                print("Backend process exited unexpectedly.")
                cleanup()
            if frontend_proc.poll() is not None:
                print("Frontend process exited unexpectedly.")
                cleanup()
            time.sleep(2)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()

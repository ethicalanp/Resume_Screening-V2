import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"


def find_python_executable() -> str:
    candidates = []
    if os.name == "nt":
        candidates.append(ROOT / "venv" / "Scripts" / "python.exe")
    else:
        candidates.append(ROOT / "venv" / "bin" / "python")
    candidates.append(sys.executable)

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return sys.executable


def find_free_port(start_port: int) -> int:
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1


if __name__ == "__main__":
    python_exe = find_python_executable()
    backend_port = find_free_port(8000)
    frontend_port = find_free_port(3000)
    backend_cmd = [python_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(backend_port)]
    frontend_cmd = ["npm.cmd", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(frontend_port)] if os.name == "nt" else ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(frontend_port)]

    print(f"Starting backend on http://127.0.0.1:{backend_port}")
    print(f"Starting frontend on http://127.0.0.1:{frontend_port}")

    processes = []
    try:
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=str(BACKEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append(("backend", backend_proc))

        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=str(FRONTEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append(("frontend", frontend_proc))

        while True:
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"[{name}] exited with code {proc.returncode}")
                    raise SystemExit(proc.returncode)
                line = proc.stdout.readline()
                if line:
                    print(f"[{name}] {line.rstrip()}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down services...")
    finally:
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

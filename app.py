import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"


def _candidate_python_paths():
    seen = set()

    def add(path):
        if not path:
            return
        path_obj = Path(path)
        if not path_obj:
            return
        candidate = str(path_obj)
        if candidate not in seen:
            seen.add(candidate)
            yield candidate

    for candidate in [
        ROOT / "venv" / "Scripts" / "python.exe",
        ROOT / "venv" / "Scripts" / "python",
        ROOT / "venv" / "bin" / "python",
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "Scripts" / "python",
        ROOT / ".venv" / "bin" / "python",
    ]:
        yield from add(candidate)

    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        for name in ("python.exe", "python", "python3.exe", "python3"):
            yield from add(Path(entry) / name)

    yield from add(sys.executable)
    yield from add(shutil.which("python"))
    yield from add(shutil.which("python3"))


def _python_can_run_backend(candidate: str) -> bool:
    if not candidate:
        return False
    candidate_path = Path(candidate)
    if not candidate_path.exists():
        return False
    try:
        result = subprocess.run(
            [str(candidate_path), "-c", "import fastapi, uvicorn"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except OSError:
        return False


def find_python_executable() -> str:
    for candidate in _candidate_python_paths():
        if _python_can_run_backend(candidate):
            return str(candidate)

    return str(sys.executable)


def find_free_port(start_port: int) -> int:
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                sock.listen(1)
                return port
            except OSError:
                port += 1


if __name__ == "__main__":
    python_exe = find_python_executable()
    backend_port = find_free_port(8000)
    frontend_port = find_free_port(3000)
    backend_cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(backend_port),
    ]
    frontend_cmd = ["npm.cmd", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(frontend_port)] if os.name == "nt" else ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(frontend_port)]

    print(f"Starting backend on http://127.0.0.1:{backend_port}")
    print(f"Starting frontend on http://127.0.0.1:{frontend_port}")

    processes = []
    try:
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=str(ROOT),
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

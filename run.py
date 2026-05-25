import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request


# Ensure UTF-8 output on Windows terminals for readable child-process logs.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def find_free_port(start_port: int = 8000, end_port: int = 8100) -> int:
    """Find a free localhost TCP port between start_port and end_port."""
    for port in range(start_port, end_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sys.platform == "win32":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No available port found between {start_port} and {end_port}.")


def stream_process_logs(name: str, proc: subprocess.Popen) -> None:
    """Print child process logs with a prefix so startup failures are visible."""
    if not proc.stdout:
        return

    for line in proc.stdout:
        print(f"[{name}] {line}", end="")


def wait_for_backend(url: str, timeout_seconds: int = 60) -> bool:
    """Wait until the backend responds to its root health endpoint."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 500:
                    return True
        except Exception:
            time.sleep(1)
    return False


def terminate_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


def main() -> None:
    print("==============================================================================")
    print("                     Starting GitReview AI Launcher                            ")
    print("==============================================================================")

    root_dir = os.path.dirname(os.path.abspath(__file__))
    env_file = os.path.join(root_dir, ".env")
    env_example = os.path.join(root_dir, ".env.example")

    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            print("Copying .env.example to .env ...")
            shutil.copy(env_example, env_file)
            print("Created .env with default configurations (running in demo/mock mode).")
        else:
            print("Warning: .env.example missing. Please create a .env file at root manually.")

    os.makedirs(os.path.join(root_dir, "temp_repos"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "chroma_db"), exist_ok=True)

    backend_port = find_free_port(8000, 8100)
    frontend_port = find_free_port(8501, 8600)
    backend_url = f"http://127.0.0.1:{backend_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"

    print(f"\nLaunching Backend (FastAPI on {backend_url})...")
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(backend_port),
    ]
    backend_env = os.environ.copy()
    backend_env["FRONTEND_URL"] = frontend_url
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=root_dir,
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    threading.Thread(target=stream_process_logs, args=("backend", backend_proc), daemon=True).start()

    print("Waiting for backend API to initialize database tables...")
    if not wait_for_backend(backend_url, timeout_seconds=60):
        print("Backend did not become ready within 60 seconds. Check the backend logs above.")
        terminate_process(backend_proc)
        return

    print(f"\nLaunching Frontend (Streamlit on {frontend_url})...")
    frontend_env = os.environ.copy()
    frontend_env["API_BASE_URL"] = f"{backend_url}/api/v1"
    frontend_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/app.py",
        "--server.port",
        str(frontend_port),
        "--server.address",
        "0.0.0.0",
    ]
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=root_dir,
        env=frontend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    threading.Thread(target=stream_process_logs, args=("frontend", frontend_proc), daemon=True).start()

    print("\n==============================================================================")
    print(f"System initialized successfully! Open {frontend_url} in your browser.")
    print("Press Ctrl+C to terminate both servers concurrently.")
    print("==============================================================================\n")

    try:
        while True:
            backend_exit = backend_proc.poll()
            frontend_exit = frontend_proc.poll()

            if backend_exit is not None:
                print(f"Backend exited unexpectedly with code: {backend_exit}")
                break
            if frontend_exit is not None:
                print(f"Frontend exited unexpectedly with code: {frontend_exit}")
                break

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nInterruption received. Terminating FastAPI and Streamlit servers...")
    finally:
        terminate_process(backend_proc)
        terminate_process(frontend_proc)
        print("Servers cleanly terminated. Thank you for using GitReview AI!")


if __name__ == "__main__":
    main()

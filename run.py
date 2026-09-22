#!/usr/bin/env python3
"""Cross-platform AIMPF local runner.

Works on Windows, macOS, and Linux with Python 3.11+.
Prerequisites: Docker Desktop (or Docker Engine + Compose), Python, Node.js/npm.

Usage:
    python run.py
    python run.py --no-install
    python run.py --research

The script intentionally avoids shell-specific commands and never requires
activating a virtual environment manually.
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = ROOT / ".venv"


def die(message: str, code: int = 1) -> None:
    print(f"\nAIMPF RUN ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def command(name: str, candidates: list[str]) -> str:
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    die(f"Required command not found: {name}. Install it and re-run.")
    return ""  # unreachable


def run(cmd: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print("\n> " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def wait_for_port(host: str, port: int, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    last_error = "unknown error"
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError as exc:
            last_error = str(exc)
            time.sleep(1)
    die(f"Timed out waiting for {host}:{port} ({last_error}).")


def python_executable() -> Path:
    exe = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not exe.exists():
        run([sys.executable, "-m", "venv", str(VENV)])
    return exe


def npm_command() -> str:
    return command("npm", ["npm.cmd", "npm"])


def ensure_local_env() -> None:
    backend_env = BACKEND / ".env"
    frontend_env = FRONTEND / ".env.local"
    if not backend_env.exists():
        backend_env.write_text(
            "DATABASE_URL=postgresql+psycopg://aimpf:aimpf@localhost:5432/aimpf\n"
            "SECRET_KEY=aimpf-local-development-only\n"
            "CORS_ORIGINS=http://localhost:3000\n"
            "AIMPF_ALGORITHM_VERSION=1.1.0\n",
            encoding="utf-8",
        )
        print(f"Created {backend_env.relative_to(ROOT)}")
    if not frontend_env.exists():
        frontend_env.write_text(
            "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000\n",
            encoding="utf-8",
        )
        print(f"Created {frontend_env.relative_to(ROOT)}")


def docker_command() -> str:
    return command("docker", ["docker"])


def docker_compose(docker: str, args: list[str]) -> None:
    result = subprocess.run([docker, "compose", *args], cwd=ROOT)
    if result.returncode != 0:
        die("Docker Compose command failed. Start Docker Desktop/Engine and try again.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AIMPF locally across Windows/macOS/Linux.")
    parser.add_argument("--no-install", action="store_true", help="skip pip/npm dependency installation")
    parser.add_argument("--research", action="store_true", help="run the deterministic research benchmark before starting")
    parser.add_argument("--no-seed", action="store_true", help="skip idempotent demo-data seeding")
    args = parser.parse_args()

    command("Python", ["python3", "python", "py"])
    docker = docker_command()
    npm = npm_command()
    py = python_executable()

    ensure_local_env()

    # Start only PostgreSQL; the Python runner owns API/frontend processes so
    # the same launcher behaves consistently on Windows, macOS, and Linux.
    docker_compose(docker, ["up", "-d", "postgres"])
    wait_for_port("127.0.0.1", 5432, timeout=90)

    if not args.no_install:
        run([str(py), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")])
        run([npm, "install"], cwd=FRONTEND)

    run([str(py), "-m", "alembic", "upgrade", "head"], cwd=BACKEND)
    if not args.no_seed:
        run([str(py), "seed.py"], cwd=BACKEND)
        run([str(py), "auth_seed.py"], cwd=BACKEND)

    if args.research:
        run([str(py), str(ROOT / "scripts" / "research_benchmark.py")])

    api_log = open(ROOT / "aimpf-api.log", "a", encoding="utf-8")
    web_log = open(ROOT / "aimpf-web.log", "a", encoding="utf-8")
    api = subprocess.Popen(
        [str(py), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND,
        stdout=api_log,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_for_port("127.0.0.1", 8000, timeout=60)
        web = subprocess.Popen(
            [npm, "run", "dev", "--", "--hostname", "127.0.0.1", "--port", "3000"],
            cwd=FRONTEND,
            stdout=web_log,
            stderr=subprocess.STDOUT,
        )
    except Exception:
        api.terminate()
        api_log.close()
        web_log.close()
        raise

    print("\nAIMPF is running")
    print("  Frontend: http://127.0.0.1:3000")
    print("  Backend:  http://127.0.0.1:8000")
    print("  Health:   http://127.0.0.1:8000/api/health")
    print("  Demo:     demo@aimpf.local / aimpf-demo-password")
    print("\nPress Ctrl+C to stop the API and frontend. PostgreSQL data remains in the Docker volume.")

    try:
        while True:
            time.sleep(1)
            if api.poll() is not None:
                die("Backend process exited. See aimpf-api.log for details.")
            if web.poll() is not None:
                die("Frontend process exited. See aimpf-web.log for details.")
    except KeyboardInterrupt:
        print("\nStopping AIMPF...")
    finally:
        for process in (web, api):
            if process.poll() is None:
                process.terminate()
        for process in (web, api):
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        api_log.close()
        web_log.close()
        print("AIMPF stopped. PostgreSQL was left running so the next start is fast and non-destructive.")


if __name__ == "__main__":
    main()

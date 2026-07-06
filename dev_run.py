from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
WATCHED_EXTENSIONS = {".py", ".json"}
IGNORED_DIRS = {".venv", "__pycache__", ".git"}


def iter_watched_files() -> list[Path]:
    files: list[Path] = []
    for path in PROJECT_DIR.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in WATCHED_EXTENSIONS:
            files.append(path)
    return files


def get_file_snapshot() -> dict[Path, int]:
    return {path: path.stat().st_mtime_ns for path in iter_watched_files()}


def start_app() -> subprocess.Popen[bytes]:
    return subprocess.Popen([sys.executable, "main.py"], cwd=PROJECT_DIR)


def stop_app(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> None:
    print("Albion Market Test - modo desarrollo")
    print("La app se reiniciara cuando cambie un archivo .py.")
    print("Cierra esta ventana para detener el modo desarrollo.")

    snapshot = get_file_snapshot()
    process = start_app()

    try:
        while True:
            time.sleep(1)
            current_snapshot = get_file_snapshot()

            if current_snapshot != snapshot:
                print("Cambio detectado. Reiniciando la app...")
                stop_app(process)
                snapshot = current_snapshot
                process = start_app()

            if process.poll() is not None:
                print("La app se cerro. Deteniendo modo desarrollo...")
                break
    except KeyboardInterrupt:
        print("Deteniendo modo desarrollo...")
    finally:
        stop_app(process)


if __name__ == "__main__":
    main()

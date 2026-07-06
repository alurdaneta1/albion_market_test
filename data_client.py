from __future__ import annotations

import os
import subprocess
from pathlib import Path


CLIENT_PROCESS_NAME = "albiondata-client.exe"


def find_data_client(candidate_paths: list[str]) -> Path | None:
    for candidate_path in candidate_paths:
        path = Path(candidate_path).expanduser()
        if path.exists() and path.is_file():
            return path
    return None


def is_data_client_running() -> bool:
    if os.name != "nt":
        return False

    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {CLIENT_PROCESS_NAME}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    return CLIENT_PROCESS_NAME.lower() in result.stdout.lower()


def start_data_client(candidate_paths: list[str], args: list[str] | None = None) -> str:
    if os.name != "nt":
        return "Albion Data Client solo se inicia automaticamente en Windows."

    if is_data_client_running():
        return "Albion Data Client ya esta en ejecucion."

    client_path = find_data_client(candidate_paths)
    if client_path is None:
        return (
            "No se encontro Albion Data Client. Instálalo o configura "
            "DATA_CLIENT_PATHS en config.py."
        )

    command = [str(client_path), *(args or [])]

    try:
        subprocess.Popen(
            command,
            cwd=str(client_path.parent),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    except OSError as exc:
        return f"No se pudo iniciar Albion Data Client: {exc}"

    return "Albion Data Client iniciado."

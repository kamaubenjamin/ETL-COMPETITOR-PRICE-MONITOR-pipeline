"""Validate the Vercel API manifest and side-effect-free startup import."""

from __future__ import annotations

import builtins
import io
import os
import socket
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "requirements-api.txt"
EXPECTED_DEPENDENCIES = (
    "fastapi==0.139.2",
    "httpx==0.28.1",
    "pyjwt[crypto]==2.10.1",
)
PROHIBITED_DEPENDENCIES = (
    "pandas",
    "numpy",
    "streamlit",
    "selenium",
    "playwright",
    "pytest",
    "reportlab",
    "rapidfuzz",
    "beautifulsoup",
    "lxml",
    "openpyxl",
    "uvicorn",
)
REQUIRED_ROUTES = frozenset({"/health", "/api/v1/health", "/api/v1/workflow-definitions"})


def _manifest_dependencies() -> tuple[str, ...]:
    lines = MANIFEST.read_text(encoding="utf-8").splitlines()
    return tuple(line.strip().lower() for line in lines if line.strip() and not line.startswith("#"))


def _guard_startup_io():
    real_builtin_open = builtins.open
    real_io_open = io.open
    real_os_open = os.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"api.index import attempted a filesystem write: {file}")
        return real_builtin_open(file, mode, *args, **kwargs)

    def guarded_io_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"api.index import attempted a filesystem write: {file}")
        return real_io_open(file, mode, *args, **kwargs)

    def guarded_os_open(path, flags, *args, **kwargs):
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
        if flags & write_flags:
            raise AssertionError(f"api.index import attempted a filesystem write: {path}")
        return real_os_open(path, flags, *args, **kwargs)

    def unexpected_network(*args, **kwargs):
        raise AssertionError("api.index import attempted network access")

    def unexpected_directory_write(*args, **kwargs):
        raise AssertionError("api.index import attempted a filesystem write")

    builtins.open = guarded_open
    io.open = guarded_io_open
    os.open = guarded_os_open
    os.mkdir = unexpected_directory_write
    os.makedirs = unexpected_directory_write
    socket.create_connection = unexpected_network
    socket.socket.connect = unexpected_network
    socket.socket.connect_ex = unexpected_network


def main() -> int:
    dependencies = _manifest_dependencies()
    if dependencies != EXPECTED_DEPENDENCIES:
        raise AssertionError(
            f"requirements-api.txt must contain the proven direct runtime closure: {EXPECTED_DEPENDENCIES}"
        )
    for prohibited in PROHIBITED_DEPENDENCIES:
        if any(line.startswith(prohibited) for line in dependencies):
            raise AssertionError(f"prohibited API runtime dependency: {prohibited}")
    sys.path.insert(0, str(ROOT))
    sys.dont_write_bytecode = True
    _guard_startup_io()

    from api.index import app
    from fastapi import FastAPI

    for prohibited_module in ("pandas", "numpy"):
        if prohibited_module in sys.modules:
            raise AssertionError(f"api.index eagerly imported {prohibited_module}")
    if not isinstance(app, FastAPI):
        raise AssertionError("api.index did not export a FastAPI application")
    paths = set(app.openapi()["paths"])
    missing_routes = REQUIRED_ROUTES - paths
    if missing_routes:
        raise AssertionError(f"api.index is missing required routes: {sorted(missing_routes)}")

    print("API runtime dependency validation passed")
    print(f"app_type={type(app).__name__}")
    print("tabular_modules_loaded=false")
    print(f"required_routes={','.join(sorted(REQUIRED_ROUTES))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

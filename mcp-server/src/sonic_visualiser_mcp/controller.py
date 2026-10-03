"""Process and OSC-script control for Sonic Visualiser."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any, Iterable, TextIO


class SonicVisualiserError(RuntimeError):
    """Raised when Sonic Visualiser cannot perform a requested operation."""


def _quote(value: str | int | float) -> str:
    """Encode one value for Sonic Visualiser's quoted OSC-script syntax."""
    if isinstance(value, bool):
        raise SonicVisualiserError("Boolean OSC arguments are not supported")
    if isinstance(value, (int, float)):
        return str(value)
    if "\n" in value or "\r" in value or "\x00" in value:
        raise SonicVisualiserError("OSC arguments must not contain newlines or NUL bytes")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class SonicVisualiserController:
    """Own a Sonic Visualiser process and write commands to its OSC script input."""

    def __init__(self, executable: str | None = None,
                 allowed_roots: Iterable[Path] | None = None,
                 process_factory: Any = subprocess.Popen) -> None:
        self.executable = executable or os.environ.get(
            "SONIC_VISUALISER_EXECUTABLE", "sonic-visualiser")
        configured_roots = allowed_roots or self._roots_from_environment()
        self.allowed_roots = tuple(Path(root).expanduser().resolve() for root in configured_roots)
        self._process_factory = process_factory
        self._process: subprocess.Popen[str] | None = None
        self._log: TextIO | None = None
        self._log_path: Path | None = None

    @staticmethod
    def _roots_from_environment() -> tuple[Path, ...]:
        configured = os.environ.get("SV_MCP_ALLOWED_ROOTS")
        if configured:
            return tuple(Path(item) for item in configured.split(os.pathsep) if item)
        return (Path.cwd(),)

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def status(self) -> dict[str, Any]:
        return {"running": self.running,
                "pid": self._process.pid if self.running and self._process else None,
                "executable": self.executable,
                "allowed_roots": [str(root) for root in self.allowed_roots],
                "log_path": str(self._log_path) if self._log_path else None}

    def validate_path(self, value: str, *, must_exist: bool) -> Path:
        path = Path(value).expanduser().resolve()
        if not any(path == root or path.is_relative_to(root) for root in self.allowed_roots):
            roots = ", ".join(str(root) for root in self.allowed_roots)
            raise SonicVisualiserError(f"Path {path} is outside the allowed roots: {roots}")
        if must_exist and not path.is_file():
            raise SonicVisualiserError(f"Input file does not exist: {path}")
        if not must_exist and not path.parent.is_dir():
            raise SonicVisualiserError(f"Output directory does not exist: {path.parent}")
        return path

    def launch(self, initial_file: str | None = None, *, no_audio: bool = False) -> dict[str, Any]:
        if self.running:
            raise SonicVisualiserError("Sonic Visualiser is already running")
        if self._process is not None:
            self._cleanup_process()
        command = [self.executable, "--no-splash", "--osc-script", "-"]
        if no_audio:
            command.insert(1, "--no-audio")
        if initial_file:
            command.append(str(self.validate_path(initial_file, must_exist=True)))
        log = tempfile.NamedTemporaryFile(
            mode="w+", prefix="sonic-visualiser-mcp-", suffix=".log", delete=False)
        self._log, self._log_path = log, Path(log.name)
        try:
            self._process = self._process_factory(
                command, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
                text=True, bufsize=1)
        except OSError as exc:
            self._cleanup_process()
            raise SonicVisualiserError(f"Could not start {self.executable!r}: {exc}") from exc
        time.sleep(0.1)
        if not self.running:
            details = self._read_log()
            self._cleanup_process()
            raise SonicVisualiserError(
                "Sonic Visualiser exited during startup" + (f": {details}" if details else ""))
        return self.status()

    def send(self, method: str, *arguments: str | int | float) -> dict[str, Any]:
        if not method or not method.replace("_", "").isalnum():
            raise SonicVisualiserError(f"Invalid OSC method: {method!r}")
        if not self.running or self._process is None or self._process.stdin is None:
            raise SonicVisualiserError("Sonic Visualiser is not running; call launch first")
        command = "/" + method
        if arguments:
            command += " " + " ".join(_quote(argument) for argument in arguments)
        try:
            self._process.stdin.write(command + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise SonicVisualiserError(f"Failed to send OSC command: {exc}") from exc
        return {"sent": command, "pid": self._process.pid}

    def export(self, method: str, output_file: str, timeout: float = 30.0) -> dict[str, Any]:
        path = self.validate_path(output_file, must_exist=False)
        if path.exists():
            raise SonicVisualiserError(f"Refusing to overwrite existing output: {path}")
        result = self.send(method, str(path))
        deadline, previous_size, stable_checks = time.monotonic() + timeout, -1, 0
        while time.monotonic() < deadline:
            if not self.running:
                raise SonicVisualiserError(
                    f"Sonic Visualiser exited while exporting; see {self._log_path}")
            if path.is_file():
                size = path.stat().st_size
                stable_checks = stable_checks + 1 if size == previous_size else 0
                if stable_checks >= 2:
                    return {**result, "path": str(path), "bytes": size}
                previous_size = size
            time.sleep(0.1)
        raise SonicVisualiserError(
            f"Timed out after {timeout:g}s waiting for export: {path}; see {self._log_path}")

    def close(self, *, timeout: float = 5.0) -> dict[str, Any]:
        if self._process is None:
            return {"closed": False, "reason": "not started"}
        process = self._process
        if process.poll() is None:
            try:
                self.send("quit")
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=timeout)
        return_code = process.returncode
        log_path = str(self._log_path) if self._log_path else None
        self._cleanup_process()
        return {"closed": True, "return_code": return_code, "log_path": log_path}

    def _read_log(self) -> str:
        if self._log is None:
            return ""
        self._log.flush()
        self._log.seek(0)
        return self._log.read().strip()

    def _cleanup_process(self) -> None:
        if self._process is not None and self._process.stdin is not None:
            self._process.stdin.close()
        self._process = None
        if self._log is not None:
            self._log.close()
        self._log = None

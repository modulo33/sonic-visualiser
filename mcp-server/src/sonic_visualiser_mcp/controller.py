"""Process and OSC-script control for Sonic Visualiser."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
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
                 process_factory: Any = subprocess.Popen,
                 executable_resolver: Any = shutil.which) -> None:
        self.executable = executable or os.environ.get(
            "SONIC_VISUALISER_EXECUTABLE", "sonic-visualiser")
        configured_roots = allowed_roots or self._roots_from_environment()
        self.allowed_roots = tuple(Path(root).expanduser().resolve() for root in configured_roots)
        self._process_factory = process_factory
        self._executable_resolver = executable_resolver
        self._process: subprocess.Popen[str] | None = None
        self._log: TextIO | None = None
        self._log_path: Path | None = None
        self._last_return_code: int | None = None
        self._lock = threading.RLock()
        self._export_lock = threading.Lock()

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
        with self._lock:
            process = self._process
            running = process is not None and process.poll() is None
            return {"running": running,
                    "pid": process.pid if running else None,
                    "return_code": (None if running else
                                    process.returncode if process is not None else
                                    self._last_return_code),
                    "executable": self.executable,
                    "readiness": "unconfirmed" if running else "not_running",
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

    def launch(self, initial_file: str | None = None, *, no_audio: bool = False,
               startup_grace: float = 0.5) -> dict[str, Any]:
        if startup_grace < 0 or startup_grace > 30:
            raise SonicVisualiserError("startup_grace must be between 0 and 30 seconds")
        with self._lock:
            if self.running:
                raise SonicVisualiserError("Sonic Visualiser is already running")
            if self._process is not None:
                self._cleanup_process()
            self._remove_log()
            self._last_return_code = None
            resolved_executable = self._executable_resolver(self.executable)
            if resolved_executable is None:
                raise SonicVisualiserError(
                    f"Sonic Visualiser executable not found: {self.executable!r}. "
                    "Set SONIC_VISUALISER_EXECUTABLE to its path.")
            command = [resolved_executable, "--no-splash", "--osc-script", "-"]
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
            deadline = time.monotonic() + startup_grace
            while time.monotonic() < deadline and self.running:
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
            if not self.running:
                details = self.read_log_tail()
                self._cleanup_process()
                raise SonicVisualiserError(
                    "Sonic Visualiser exited during startup" + (f": {details}" if details else ""))
            return {**self.status(), "completion": "process_alive"}

    def send(self, method: str, *arguments: str | int | float) -> dict[str, Any]:
        if not method or not method.replace("_", "").isalnum():
            raise SonicVisualiserError(f"Invalid OSC method: {method!r}")
        command = "/" + method
        if arguments:
            command += " " + " ".join(_quote(argument) for argument in arguments)
        with self._lock:
            if not self.running or self._process is None or self._process.stdin is None:
                detail = self.read_log_tail()
                suffix = f" Last log output: {detail}" if detail else ""
                raise SonicVisualiserError(
                    "Sonic Visualiser is not running; call launch first." + suffix)
            try:
                self._process.stdin.write(command + "\n")
                self._process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise SonicVisualiserError(f"Failed to send OSC command: {exc}") from exc
            return {"sent": command, "pid": self._process.pid,
                    "delivery": "sent", "completion": "unconfirmed"}

    def export(self, method: str, output_file: str, timeout: float = 30.0,
               settle_time: float = 0.75) -> dict[str, Any]:
        if timeout <= 0 or settle_time < 0 or settle_time >= timeout:
            raise SonicVisualiserError(
                "timeout must be positive and settle_time must be non-negative and less than timeout")
        with self._export_lock:
            path = self.validate_path(output_file, must_exist=False)
            if path.exists():
                raise SonicVisualiserError(f"Refusing to overwrite existing output: {path}")
            result = self.send(method, str(path))
            deadline = time.monotonic() + timeout
            previous_signature: tuple[int, int] | None = None
            stable_since: float | None = None
            while time.monotonic() < deadline:
                if not self.running:
                    raise SonicVisualiserError(
                        f"Sonic Visualiser exited while exporting. {self.read_log_tail()}")
                if path.is_file():
                    stat = path.stat()
                    signature = (stat.st_size, stat.st_mtime_ns)
                    now = time.monotonic()
                    if signature != previous_signature:
                        previous_signature, stable_since = signature, now
                    elif stable_since is not None and now - stable_since >= settle_time:
                        return {**result, "path": str(path), "bytes": stat.st_size,
                                "completion": "inferred_from_stable_file"}
                time.sleep(min(0.1, max(0, deadline - time.monotonic())))
            details = self.read_log_tail()
            suffix = f" Last log output: {details}" if details else ""
            raise SonicVisualiserError(
                f"Timed out after {timeout:g}s waiting for export: {path}.{suffix}")

    def close(self, *, timeout: float = 5.0) -> dict[str, Any]:
        with self._lock:
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
                except (SonicVisualiserError, BrokenPipeError, OSError):
                    process.terminate()
                    try:
                        process.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=timeout)
            return_code = process.returncode
            log_path = str(self._log_path) if self._log_path else None
            self._cleanup_process()
            return {"closed": True, "return_code": return_code, "log_path": log_path,
                    "completion": "process_exited"}

    def shutdown(self) -> None:
        """Best-effort final cleanup for interpreter shutdown."""
        try:
            self.close(timeout=1.0)
        finally:
            self._remove_log()

    def read_log_tail(self, max_characters: int = 4000) -> str:
        """Return recent process diagnostics without exposing an unbounded log."""
        if max_characters < 1 or max_characters > 100_000:
            raise SonicVisualiserError("max_characters must be between 1 and 100000")
        with self._lock:
            if self._log is None or self._log_path is None:
                return ""
            self._log.flush()
            with self._log_path.open("rb") as stream:
                stream.seek(0, os.SEEK_END)
                length = stream.tell()
                stream.seek(max(0, length - max_characters))
                return stream.read().decode("utf-8", errors="replace").strip()

    def _cleanup_process(self) -> None:
        if self._process is not None:
            self._last_return_code = self._process.poll()
        if self._process is not None and self._process.stdin is not None:
            try:
                self._process.stdin.close()
            except (BrokenPipeError, OSError):
                pass
        self._process = None
        if self._log is not None:
            self._log.close()
        self._log = None

    def _remove_log(self) -> None:
        if self._log_path is None:
            return
        try:
            self._log_path.unlink(missing_ok=True)
        except OSError:
            return
        self._log_path = None

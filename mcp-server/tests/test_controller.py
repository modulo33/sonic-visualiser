from __future__ import annotations

import io
from pathlib import Path
import subprocess
import threading
import time

import pytest

from sonic_visualiser_mcp.controller import SonicVisualiserController, SonicVisualiserError


class FakeProcess:
    def __init__(self, command, **kwargs):
        self.command = command
        self.stdin = io.StringIO()
        self.pid = 4321
        self.returncode = None

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            raise subprocess.TimeoutExpired(self.command, timeout)
        return self.returncode

    def terminate(self):
        self.returncode = 0

    def kill(self):
        self.returncode = -9


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path.resolve()


def test_launch_and_send_quote_arguments(root: Path):
    controller = SonicVisualiserController(
        executable="sv", allowed_roots=[root], process_factory=FakeProcess,
        executable_resolver=lambda value: value)
    result = controller.launch(no_audio=True, startup_grace=0)
    assert result["pid"] == 4321
    assert controller._process.command == [
        "sv", "--no-audio", "--no-splash", "--osc-script", "-"]
    controller.send("set", "layer", "Scale Units", 2)
    assert controller._process.stdin.getvalue() == '/set "layer" "Scale Units" 2\n'


def test_path_validation_blocks_escape_and_missing_input(root: Path):
    controller = SonicVisualiserController(allowed_roots=[root])
    with pytest.raises(SonicVisualiserError, match="outside the allowed roots"):
        controller.validate_path(str(root.parent / "escape.wav"), must_exist=True)
    with pytest.raises(SonicVisualiserError, match="does not exist"):
        controller.validate_path(str(root / "missing.wav"), must_exist=True)


def test_open_path_with_spaces_is_quoted(root: Path):
    audio = root / "audio file.wav"
    audio.touch()
    controller = SonicVisualiserController(allowed_roots=[root], process_factory=FakeProcess, executable_resolver=lambda value: value)
    controller.launch(startup_grace=0)
    controller.send("open", str(controller.validate_path(str(audio), must_exist=True)))
    assert controller._process.stdin.getvalue() == f'/open "{audio}"\n'


def test_export_waits_for_stable_file(root: Path):
    controller = SonicVisualiserController(allowed_roots=[root], process_factory=FakeProcess, executable_resolver=lambda value: value)
    controller.launch(startup_grace=0)
    output = root / "layer.csv"

    def create_output():
        time.sleep(0.05)
        output.write_text("time,label\n", encoding="utf-8")

    thread = threading.Thread(target=create_output)
    thread.start()
    result = controller.export("exportlayer", str(output), timeout=1)
    thread.join()
    assert result["path"] == str(output)
    assert result["bytes"] == len("time,label\n")


def test_export_refuses_overwrite(root: Path):
    output = root / "existing.csv"
    output.touch()
    controller = SonicVisualiserController(allowed_roots=[root], process_factory=FakeProcess, executable_resolver=lambda value: value)
    controller.launch(startup_grace=0)
    with pytest.raises(SonicVisualiserError, match="Refusing to overwrite"):
        controller.export("exportlayer", str(output))


def test_send_requires_running_process(root: Path):
    controller = SonicVisualiserController(allowed_roots=[root])
    with pytest.raises(SonicVisualiserError, match="call launch first"):
        controller.send("play")


def test_rejects_multiline_argument(root: Path):
    controller = SonicVisualiserController(allowed_roots=[root], process_factory=FakeProcess, executable_resolver=lambda value: value)
    controller.launch(startup_grace=0)
    with pytest.raises(SonicVisualiserError, match="must not contain"):
        controller.send("open", "bad\n/quit")


def test_launch_reports_missing_executable(root: Path):
    controller = SonicVisualiserController(
        executable="missing-sv", allowed_roots=[root],
        executable_resolver=lambda value: None)
    with pytest.raises(SonicVisualiserError, match="executable not found"):
        controller.launch(startup_grace=0)


def test_export_waits_until_file_stops_changing(root: Path):
    controller = SonicVisualiserController(
        allowed_roots=[root], process_factory=FakeProcess,
        executable_resolver=lambda value: value)
    controller.launch(startup_grace=0)
    output = root / "growing.csv"

    def create_output():
        time.sleep(0.05)
        output.write_text("first\n", encoding="utf-8")
        time.sleep(0.15)
        with output.open("a", encoding="utf-8") as stream:
            stream.write("second\n")

    thread = threading.Thread(target=create_output)
    thread.start()
    result = controller.export(
        "exportlayer", str(output), timeout=1, settle_time=0.25)
    thread.join()
    assert result["bytes"] == len("first\nsecond\n")


def test_status_retains_exit_code_and_diagnostics(root: Path):
    controller = SonicVisualiserController(
        allowed_roots=[root], process_factory=FakeProcess,
        executable_resolver=lambda value: value)
    controller.launch(startup_grace=0)
    controller._log.write("useful diagnostic\n")
    controller._process.returncode = 17

    assert controller.status()["return_code"] == 17
    assert controller.read_log_tail() == "useful diagnostic"
    controller.close()
    assert controller.status()["return_code"] == 17


def test_concurrent_commands_are_not_interleaved(root: Path):
    controller = SonicVisualiserController(
        allowed_roots=[root], process_factory=FakeProcess,
        executable_resolver=lambda value: value)
    controller.launch(startup_grace=0)
    threads = [
        threading.Thread(target=controller.send, args=("jump", position))
        for position in range(20)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    lines = controller._process.stdin.getvalue().splitlines()
    assert sorted(lines) == sorted(f"/jump {position}" for position in range(20))

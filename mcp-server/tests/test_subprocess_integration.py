from __future__ import annotations

import os
from pathlib import Path
import time

import pytest

from sonic_visualiser_mcp.controller import SonicVisualiserController, SonicVisualiserError


pytestmark = pytest.mark.skipif(os.name == "nt", reason="fixture uses a POSIX shebang")


@pytest.fixture
def fake_executable() -> Path:
    path = Path(__file__).parent / "fixtures" / "fake_sonic_visualiser.py"
    path.chmod(0o755)
    return path.resolve()


def wait_for_log(controller: SonicVisualiserController, text: str) -> None:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if text in controller.read_log_tail():
            return
        time.sleep(0.02)
    raise AssertionError(f"Did not find {text!r} in process log")


def test_real_subprocess_launch_command_export_and_shutdown(
    tmp_path: Path, fake_executable: Path,
) -> None:
    controller = SonicVisualiserController(
        executable=str(fake_executable), allowed_roots=[tmp_path])
    launched = controller.launch(startup_grace=0.1)
    assert launched["completion"] == "process_alive"
    assert launched["readiness"] == "unconfirmed"

    sent = controller.send("play", 1.25)
    assert sent["delivery"] == "sent"
    assert sent["completion"] == "unconfirmed"
    wait_for_log(controller, "/play 1.25")

    output = tmp_path / "export.csv"
    exported = controller.export(
        "exportlayer", str(output), timeout=2, settle_time=0.25)
    assert exported["completion"] == "inferred_from_stable_file"
    assert output.read_bytes() == b"first chunk\nsecond chunk\n"

    log_path = Path(controller.status()["log_path"])
    closed = controller.close(timeout=1)
    assert closed["return_code"] == 0
    assert closed["completion"] == "process_exited"
    assert log_path.exists()
    controller.shutdown()
    assert not log_path.exists()


def test_real_subprocess_startup_failure_is_reported(
    tmp_path: Path, fake_executable: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FAKE_SV_EXIT_ON_START", "1")
    controller = SonicVisualiserController(
        executable=str(fake_executable), allowed_roots=[tmp_path])
    with pytest.raises(SonicVisualiserError, match="simulated startup failure"):
        controller.launch(startup_grace=0.5)
    controller.shutdown()

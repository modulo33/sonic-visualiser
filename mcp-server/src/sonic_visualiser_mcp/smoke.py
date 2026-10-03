"""Desktop smoke test for a real Sonic Visualiser installation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from .controller import SonicVisualiserController


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch Sonic Visualiser, open audio, and export a test image")
    parser.add_argument("audio", type=Path, help="audio file to open")
    parser.add_argument("--output", type=Path, default=Path("sv-mcp-smoke.png"))
    parser.add_argument("--load-wait", type=float, default=3.0,
                        help="seconds to allow asynchronous audio decoding")
    parser.add_argument("--executable", help="Sonic Visualiser executable path")
    args = parser.parse_args()

    audio = args.audio.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if args.load_wait < 0:
        parser.error("--load-wait must not be negative")
    controller = SonicVisualiserController(
        executable=args.executable, allowed_roots=[audio.parent, output.parent])
    try:
        launched = controller.launch(str(audio), startup_grace=1.0)
        time.sleep(args.load_wait)
        controller.send("add", "spectrogram")
        controller.send("zoom", "fit")
        exported = controller.export("exportimage", str(output), timeout=60)
        print(json.dumps({"launch": launched, "export": exported}, indent=2))
    finally:
        controller.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Small process fixture that emulates the OSC-script behavior used by tests."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import sys
import time


if os.environ.get("FAKE_SV_EXIT_ON_START"):
    print("simulated startup failure", flush=True)
    raise SystemExit(23)

print("Finished setting up internal-only OSC queue", flush=True)

for raw_line in sys.stdin:
    line = raw_line.strip()
    if not line:
        continue
    print(f"received: {line}", flush=True)
    parts = shlex.split(line)
    method = parts[0].lstrip("/")
    if method == "quit":
        raise SystemExit(0)
    if method in {"export", "exportlayer", "exportimage", "exportsvg", "save"}:
        output = Path(parts[1])
        output.write_bytes(b"first chunk\n")
        time.sleep(0.15)
        with output.open("ab") as stream:
            stream.write(b"second chunk\n")
        print(f"completed: {output}", flush=True)

# Sonic Visualiser MCP server

This directory contains an Option A integration: a standalone MCP server that launches and controls
Sonic Visualiser through its existing `--osc-script -` interface. It does not modify the desktop
application or add a network service to it.

## Requirements

- Python 3.10 or newer
- Sonic Visualiser built with OSC support and available as `sonic-visualiser`
- A graphical session in which Sonic Visualiser can run

## Install and run

From this directory, create an environment and install the package:

```bash
python -m venv .venv
.venv/bin/pip install -e .
```

Configure an MCP client to start the server over stdio. For example:

```json
{
  "mcpServers": {
    "sonic-visualiser": {
      "command": "/absolute/path/to/mcp-server/.venv/bin/sonic-visualiser-mcp",
      "env": {
        "SV_MCP_ALLOWED_ROOTS": "/absolute/path/to/audio:/absolute/path/to/exports"
      }
    }
  }
}
```

On Windows, separate allowed roots with `;` instead of `:`. If `SV_MCP_ALLOWED_ROOTS` is omitted,
only the MCP server's current working directory is accessible. Set `SONIC_VISUALISER_EXECUTABLE` to
an absolute executable path when Sonic Visualiser is not on `PATH`.

## Tools

The server exposes tools to:

- inspect status and launch or close the managed application;
- read bounded recent process diagnostics when startup or a command fails;
- open audio, session, and layer files;
- add visualisation panes and choose the current pane/layer;
- select a time region and control playback;
- run a Vamp transform with its default parameters; and
- export audio, layers, images, SVG, and sessions.

All file inputs and outputs are restricted to configured allowed roots. Exports refuse to overwrite
existing files and wait for the output file's size and modification time to remain stable before
returning. Commands are serialized so concurrent MCP calls cannot interleave data on the OSC-script
input stream.

The `launch` tool accepts a `startup_grace` value (0–30 seconds, default 0.5) used to detect an
application that exits immediately. `status` retains the last child-process return code, while
`diagnostics` returns a bounded tail of Sonic Visualiser's combined standard output and error log.
Logs remain available after `close` for troubleshooting and are removed on the next launch or when
the MCP server exits normally.

Tool results state what the bridge can actually confirm:

- `launch` reports `completion: process_alive`; this is a liveness check, not application readiness.
- ordinary OSC commands report `delivery: sent` and `completion: unconfirmed`.
- exports report `completion: inferred_from_stable_file` after the output settles.

## Current limitations

- This server manages one Sonic Visualiser child process; it does not attach to an existing process.
- OSC script commands do not return structured application state. A successful tool result means the
  command was accepted for delivery. Export tools additionally verify that an output file appeared.
- Export completion is inferred from the output file remaining unchanged for a short settling period;
  the OSC interface itself does not send an export-complete response.
- The underlying Sonic Visualiser interface runs transforms only on the main model and uses plugin
  defaults; it cannot set transform parameters, block size, step size, or channel selection.
- Sonic Visualiser remains a GUI application and may require a display even when `no_audio` is used.

## Development

```bash
python -m pip install -e '.[test]'
pytest
```

The test suite includes controller unit tests, a real-subprocess fake Sonic Visualiser test, and MCP
protocol/schema tests. The MCP tests run when the pinned SDK dependency is installed. CI exercises
the package on Python 3.10 and 3.14 on Linux and Windows. Runtime and build dependencies are pinned in
`pyproject.toml`; update those pins deliberately and rerun the full suite when upgrading.

## Real desktop smoke test

After installing the package on a graphical desktop with Sonic Visualiser, run:

```bash
sonic-visualiser-mcp-smoke /absolute/path/to/audio.wav \
  --output /absolute/path/to/sv-mcp-smoke.png
```

The smoke test launches Sonic Visualiser, waits for asynchronous audio decoding, adds a spectrogram,
fits it to the window, exports a PNG, and closes the managed process. Use `--load-wait` for files or
systems that need more than the default three seconds, and `--executable` when Sonic Visualiser is not
on `PATH`. The output path must not already exist.

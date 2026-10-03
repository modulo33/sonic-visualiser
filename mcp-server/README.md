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
- open audio, session, and layer files;
- add visualisation panes and choose the current pane/layer;
- select a time region and control playback;
- run a Vamp transform with its default parameters; and
- export audio, layers, images, SVG, and sessions.

All file inputs and outputs are restricted to configured allowed roots. Exports refuse to overwrite
existing files and wait for the output file to finish writing before returning.

## Current limitations

- This server manages one Sonic Visualiser child process; it does not attach to an existing process.
- OSC script commands do not return structured application state. A successful tool result means the
  command was accepted for delivery. Export tools additionally verify that an output file appeared.
- The underlying Sonic Visualiser interface runs transforms only on the main model and uses plugin
  defaults; it cannot set transform parameters, block size, step size, or channel selection.
- Sonic Visualiser remains a GUI application and may require a display even when `no_audio` is used.

## Development

```bash
python -m pip install -e '.[test]'
pytest
```

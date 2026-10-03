"""MCP tool definitions for Sonic Visualiser."""

from __future__ import annotations

import atexit
from typing import Literal

from mcp.server import MCPServer

from .controller import SonicVisualiserController


mcp = MCPServer("Sonic Visualiser")
controller = SonicVisualiserController()
atexit.register(controller.close)


@mcp.tool()
def status() -> dict:
    """Report whether the managed Sonic Visualiser process is running."""
    return controller.status()


@mcp.tool()
def launch(initial_file: str | None = None, no_audio: bool = False) -> dict:
    """Launch Sonic Visualiser in OSC-script mode, optionally opening an audio or session file."""
    return controller.launch(initial_file, no_audio=no_audio)


@mcp.tool()
def open_file(path: str, additional: bool = False) -> dict:
    """Open an audio, session, or layer file; optionally keep the current main audio."""
    validated = controller.validate_path(path, must_exist=True)
    return controller.send("openadditional" if additional else "open", str(validated))


@mcp.tool()
def add_visualisation(
    layer_type: Literal[
        "waveform", "spectrogram", "melodicrange", "peakfrequency", "spectrum",
        "timeruler", "timeinstants", "timevalues", "notes", "text", "colour3dplot",
    ],
    channel: int | None = None,
) -> dict:
    """Add a pane with a visualisation layer, optionally for a zero-based audio channel."""
    if channel is not None and channel < 0:
        raise ValueError("channel must be zero or greater")
    return controller.send("add", layer_type, *(() if channel is None else (channel,)))


@mcp.tool()
def select_region(start: float | None = None, end: float | None = None,
                  clear: bool = False) -> dict:
    """Select a time range in seconds, select all when no range is supplied, or clear it."""
    if clear:
        return controller.send("select", "none")
    if start is None and end is None:
        return controller.send("select", "all")
    if start is None or end is None or start < 0 or end <= start:
        raise ValueError("start and end must define an increasing, non-negative range")
    return controller.send("select", start, end)


@mcp.tool()
def set_current(pane: int, layer: int | None = None) -> dict:
    """Choose the one-based current pane and optionally its one-based current layer."""
    if pane < 1 or (layer is not None and layer < 1):
        raise ValueError("pane and layer numbers start at 1")
    return controller.send("setcurrent", pane, *(() if layer is None else (layer,)))


@mcp.tool()
def run_transform(transform_id: str) -> dict:
    """Run a Vamp transform with its default parameters on the main audio model."""
    if not transform_id.strip():
        raise ValueError("transform_id must not be empty")
    return controller.send("transform", transform_id)


@mcp.tool()
def playback(
    action: Literal["play", "stop", "jump"],
    position: float | Literal["selection", "end"] | None = None,
) -> dict:
    """Play, stop, or jump, optionally using seconds, selection, or end as appropriate."""
    if action == "stop":
        if position is not None:
            raise ValueError("stop does not accept a position")
        return controller.send("stop")
    if position is None:
        if action == "jump":
            raise ValueError("jump requires a position")
        return controller.send("play")
    if isinstance(position, float) and position < 0:
        raise ValueError("position must not be negative")
    return controller.send(action, position)


@mcp.tool()
def export_artifact(
    kind: Literal["audio", "layer", "image", "svg", "session"],
    output_file: str,
    timeout: float = 30.0,
) -> dict:
    """Export an artifact and wait until its output file has been written."""
    if timeout <= 0 or timeout > 600:
        raise ValueError("timeout must be greater than zero and no more than 600 seconds")
    methods = {
        "audio": "export", "layer": "exportlayer", "image": "exportimage",
        "svg": "exportsvg", "session": "save",
    }
    return controller.export(methods[kind], output_file, timeout)


@mcp.tool()
def close() -> dict:
    """Quit the managed Sonic Visualiser process."""
    return controller.close()


def main() -> None:
    """Run the MCP server over standard input and output."""
    mcp.run()


if __name__ == "__main__":
    main()

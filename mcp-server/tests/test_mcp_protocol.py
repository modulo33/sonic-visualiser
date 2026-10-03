from __future__ import annotations

import pytest


pytest.importorskip("mcp", reason="MCP SDK is not installed")

from mcp import Client  # noqa: E402

from sonic_visualiser_mcp.server import mcp  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_mcp_lists_expected_tools_and_schemas() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        tools = (await client.list_tools()).tools

    by_name = {tool.name: tool for tool in tools}
    assert {
        "status", "launch", "diagnostics", "open_file", "add_visualisation",
        "select_region", "set_current", "run_transform", "playback",
        "export_artifact", "close",
    } <= by_name.keys()
    layer_schema = by_name["add_visualisation"].input_schema
    assert "spectrogram" in layer_schema["properties"]["layer_type"]["enum"]
    export_schema = by_name["export_artifact"].input_schema
    assert set(export_schema["properties"]["kind"]["enum"]) == {
        "audio", "layer", "image", "svg", "session",
    }


@pytest.mark.anyio
async def test_mcp_status_tool_returns_structured_state() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool("status", {})

    assert not result.is_error
    assert result.structured_content is not None
    assert result.structured_content["running"] is False
    assert result.structured_content["readiness"] == "not_running"


@pytest.mark.anyio
async def test_mcp_rejects_invalid_tool_arguments() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "add_visualisation", {"layer_type": "not-a-layer"})

    assert result.is_error

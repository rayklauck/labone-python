"""Simplifying the creation of a mock server."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from labone.mock.mock_server import MockServer
from labone.mock.session_mock_template import SessionMockTemplate

if TYPE_CHECKING:
    from labone.mock.session_mock_functionality import SessionMockFunctionality


async def spawn_hpk_mock(functionality: SessionMockFunctionality) -> MockServer:
    """Shortcut for creating a mock server.

    Args:
        functionality: Functionality to be mocked.

    Returns:
        Mock server.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read.
        capnp.lib.capnp.KjException: If the schema is invalid. Or the id
            of the concrete server is not in the schema.

    Example:
        >>> mock_server = await spawn_hpk_mock(AutomaticSessionFunctionality(paths_to_info))

    """
    test_reflection_server = await functionality.create_reflection_server()
    return MockServer(
        capability_bytes=Path(__file__).parent.parent / "resources" / "session.bin",
        concrete_server=SessionMockTemplate(
            functionality,
        ),
    )



import asyncio
from pathlib import Path

from labone.mock.automatic_hpk_functionality import AutomaticHpkFunctionality
from labone.mock.hpk_functionality import HpkMockFunctionality
from labone.mock.mock_server import MockServer
from labone.mock.session_mock_template import SessionMockTemplate


async def spawn_hpk_mock(functionality: HpkMockFunctionality):
    return MockServer(
        capability_bytes=Path(__file__).parent.parent / 'resources' / 'session.bin',
        concrete_server=SessionMockTemplate(
            functionality
        ),
    )
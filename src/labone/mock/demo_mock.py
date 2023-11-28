import asyncio
from pathlib import Path
from typing import Any, Coroutine
from labone.core import ListNodesFlags
from labone.core.helper import LabOneNodePath

from labone.core.reflection import ReflectionServer
from labone.core.session import Session
from labone.core.subscription import StreamingHandle
from labone.core.value import AnnotatedValue
from labone.mock.automatic_hpk_functionality import AutomaticHpkFunctionality
from labone.mock.entry_point import spawn_hpk_mock
from labone.mock.session_mock_template import SessionMockTemplate
from labone.mock.hpk_functionality import HpkMockFunctionality
from labone.mock.mock_server import MockServer


class TestHPK(AutomaticHpkFunctionality):

    
    def set_with_expression(self, value: AnnotatedValue) -> Coroutine[Any, Any, list[AnnotatedValue]]:
        raise ValueError("(test) e.g. tried to set invalid path")

    def get_with_expression(self, path_expression: LabOneNodePath, flags: ListNodesFlags | int = ListNodesFlags.ABSOLUTE | ListNodesFlags.RECURSIVE | ListNodesFlags.LEAVES_ONLY | ListNodesFlags.EXCLUDE_STREAMING | ListNodesFlags.GET_ONLY) -> Coroutine[Any, Any, list[AnnotatedValue]]:
        raise ValueError("(test) e.g. tried to set invalid path")
    pass

async def main():

    paths_to_info={
                    "/a/b/c": {"Description": "some path"},
                    "/a/x/y": {"Properties": "Read, Write"},
                    "/a/x/z/q": {},
                }

    mock_server = await spawn_hpk_mock(AutomaticHpkFunctionality(paths_to_info))

    client_connection = await mock_server.start()
    reflection_client = await ReflectionServer.create_from_connection(client_connection)
    session = Session(reflection_client.session, reflection_server=reflection_client)

    q = await session.subscribe("/a/b/c")

    # print(await session.get("/a/b/c"))
    print(await session.set(AnnotatedValue(path="/a/b/c", value=123, timestamp=0)))
    print(await session.get("/a/b/c"))
    print(await session.set(AnnotatedValue(path="/a/b/c", value=445, timestamp=0)))
    print(await session.set(AnnotatedValue(path="/a/b/c", value=678, timestamp=0)))
    print(await session.set_with_expression(AnnotatedValue(path="/a/*", value=7)))
    print(await session.get_with_expression('/a/x'))

    print("Queue:")
    while not q.empty():
        print(await q.get())

    print(await session.list_nodes("/a/x"))
    print(await session.list_nodes_info("/a/x"))


if __name__ == "__main__":
    asyncio.run(main())

"""Demo on how to use a (custom) mock server."""


from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Coroutine

from labone.core import ListNodesFlags
from labone.core.reflection import ReflectionServer
from labone.core.session import Session
from labone.core.value import AnnotatedValue
from labone.mock.automatic_hpk_functionality import AutomaticHpkFunctionality
from labone.mock.entry_point import spawn_hpk_mock

if TYPE_CHECKING:
    from labone.core.helper import LabOneNodePath


class TestHPK(AutomaticHpkFunctionality):
    def set_with_expression(
        self,
        value: AnnotatedValue,
    ) -> Coroutine[Any, Any, list[AnnotatedValue]]:
        msg = "(test) e.g. tried to set invalid path"
        raise ValueError(msg)

    def get_with_expression(
        self,
        path_expression: LabOneNodePath,
        flags: ListNodesFlags
        | int = ListNodesFlags.ABSOLUTE
        | ListNodesFlags.RECURSIVE
        | ListNodesFlags.LEAVES_ONLY
        | ListNodesFlags.EXCLUDE_STREAMING
        | ListNodesFlags.GET_ONLY,
    ) -> Coroutine[Any, Any, list[AnnotatedValue]]:
        msg = "(test) e.g. tried to set invalid path"
        raise ValueError(msg)


async def main():

    paths_to_info = {
        "/a/b/c": {"Description": "some path"},
        "/a/x/y": {"Properties": "Read, Write"},
        "/a/x/z/q": {},
    }

    mock_server = await spawn_hpk_mock(AutomaticHpkFunctionality(paths_to_info))

    client_connection = await mock_server.start()
    reflection_client = await ReflectionServer.create_from_connection(client_connection)
    session = Session(reflection_client.session, reflection_server=reflection_client)

    q = await session.subscribe("/a/b/c")

    print(await session.set(AnnotatedValue(path="/a/b/c", value=123, timestamp=0)))
    print(await session.get("/a/b/t"))
    print(await session.set(AnnotatedValue(path="/a/b/c", value=445, timestamp=0)))
    print(await session.set(AnnotatedValue(path="/a/b/c", value=678, timestamp=0)))
    print(await session.set_with_expression(AnnotatedValue(path="/a/*", value=7)))
    print(await session.get_with_expression("/a/x"))

    print("Queue:")
    while not q.empty():
        print(await q.get())

    print(await session.list_nodes("/a/x"))
    print(await session.list_nodes_info("/a/x"))

    print(mock_server._concrete_server._functionality._memory)


if __name__ == "__main__":
    asyncio.run(main())

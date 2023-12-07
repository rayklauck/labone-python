"""Demo on how to use a (custom) mock server."""


from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Coroutine

import numpy as np

from labone.core import ListNodesFlags
from labone.core.reflection import ReflectionServer
from labone.core.session import Session
from labone.core.shf_vector_data import SHFDemodSample, ShfDemodulatorVectorExtraHeader, ShfResultLoggerVectorExtraHeader, ShfScopeVectorExtraHeader
from labone.core.value import AnnotatedValue
from labone.mock.automatic_session_functionality import AutomaticSessionFunctionality
from labone.mock.entry_point import spawn_hpk_mock

if TYPE_CHECKING:
    from labone.core.helper import LabOneNodePath


async def main():

    paths_to_info = {
        "/a/b/c": {"Description": "some path"},
        "/a/x/y": {"Properties": "Read, Write"},
        "/a/x/z/q": {},
    }
    functionality = AutomaticSessionFunctionality(paths_to_info)

    mock_server = await spawn_hpk_mock(functionality)

    client_connection = await mock_server.start()
    reflection_client = await ReflectionServer.create_from_connection(client_connection)
    session = Session(reflection_client.session, reflection_server=reflection_client)

    q = await session.subscribe("/a/b/c")

    # print(await session.set(AnnotatedValue(path="/a/b/c", value=123, timestamp=0)))
    # print(await session.get("/a/b/t"))
    # print(await session.set(AnnotatedValue(path="/a/b/c", value=445, timestamp=0)))
    # print(await session.set(AnnotatedValue(path="/a/b/c", value=678, timestamp=0)))
    # print(await session.set_with_expression(AnnotatedValue(path="/a/*", value=7)))
    # print(await session.get_with_expression("/a/x"))

    await session.set(
        AnnotatedValue(
            path="/a/b/c",
            value=np.array([6 + 6j, 5 + 3j], dtype=np.complex64),
            timestamp=0,
            extra_header=ShfScopeVectorExtraHeader(
                0, 0, False, 3.0, 7, 0, 0, 1, 1, 1, 1, 0
            ),
        ),
    )

    # await session.set(
    #     AnnotatedValue(
    #         path="/a/b/c",
    #         value=SHFDemodSample(np.array([6, 3], dtype=np.int64), np.array([7, 2], dtype=np.int64)),
    #         timestamp=0,
    #         extra_header=ShfDemodulatorVectorExtraHeader(0,0,False,0,0,0,0,0,0.5,-3, 0,0),
    #     ),
    # )

    # await session.set(
    #     AnnotatedValue(
    #         path="/a/b/c",
    #         value=np.array([50 + 100j, 100 + 150j], dtype=np.complex64) ,
    #         timestamp=0,
    #         extra_header=ShfResultLoggerVectorExtraHeader(0,0,50,0),
           
    #             ),
    # )
    
    print("Queue:")
    while not q.empty():
        print(await q.get())

    # print(await session.list_nodes("/a/x"))
    # print(await session.list_nodes_info("/a/x"))

    # print(mock_server._concrete_server._functionality._memory)


if __name__ == "__main__":
    asyncio.run(main())

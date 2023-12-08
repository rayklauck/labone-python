"""Demo on how to use a (custom) mock server."""


from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, Coroutine

import numpy as np

from labone.core import ListNodesFlags
from labone.core.reflection import ReflectionServer
from labone.core.reflection.parsed_wire_schema import ParsedWireSchema
from labone.core.session import Session
from labone.core.shf_vector_data import (
    SHFDemodSample,
    ShfDemodulatorVectorExtraHeader,
    ShfResultLoggerVectorExtraHeader,
    ShfScopeVectorExtraHeader,
)
from labone.core.value import AnnotatedValue
from labone.mock.automatic_session_functionality import AutomaticSessionFunctionality
from labone.mock.entry_point import spawn_hpk_mock
from labone.core.reflection.server import reflection_capnp

if TYPE_CHECKING:
    from labone.core.helper import LabOneNodePath


async def main():

    paths_to_info = {
        "/a/b/c": {"Description": "some path"},
        "/a/x/y": {"Properties": "Read, Write"},
        "/a/x/z/q": {},
    }
    # capability_bytes=Path(__file__).parent.parent / "resources" / "session.bin"
    # with capability_bytes.open("rb") as f:
    #         schema_bytes = f.read()
    # with reflection_capnp.CapSchema.from_bytes(schema_bytes) as schema:
    #     _schema_parsed_dict = schema.to_dict()
    #     _schema = ParsedWireSchema(schema.theSchema)
    #     full_schema = _schema.full_schema

    functionality = AutomaticSessionFunctionality(paths_to_info)

    session = await spawn_hpk_mock(functionality)

    # client_connection = await mock_server.start()
    # reflection_client = await ReflectionServer.create_from_connection(client_connection)
    # session = Session(reflection_client.session, reflection_server=reflection_client)

    q = await session.subscribe("/a/b/c")

    print(await session.set(AnnotatedValue(path="/a/b/c", value=123, timestamp=0)))
    # print(await session.get("/a/b/t"))
    print(await session.set(AnnotatedValue(path="/a/b/c", value=445, timestamp=0)))
    print(await session.set(AnnotatedValue(path="/a/b/c", value=678, timestamp=0)))
    print(await session.set_with_expression(AnnotatedValue(path="/a/*", value=7)))
    print(await session.get_with_expression("/a/x"))

    # In some cases, directly modifying the mock server state is useful.
    # This can be by manipulating the functionality object.
    # All side effects like subscriptions are bypassed this way.

    # changing values directly in memory.
    # functionality.memory["/a/b/c"] = AnnotatedValue(
    #    path="/a/b/c", value=123, timestamp=0
    # )

    # adding a new node to the tree structure. The info dictionary is not stricly required
    # here, and will only affect the output of list_nodes_info.
    # functionality.paths_to_info["/new/path/to/node"] = {"Description": "New Node"}

    # If, on the other hand, you still want the side effects (like updating subscriptions),
    # but need to bypass the capnp interface, you can do so by calling the methods on
    # the functionality object directly, instead of calling them via the session object.

    # This way, shf vector nodes can be set, which is not possible via the capnp interface.
    await functionality.set(
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

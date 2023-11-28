import asyncio
import socket
from abc import ABC
from pathlib import Path

import capnp
from labone.core.helper import ensure_capnp_event_loop
from labone.core.reflection.parsed_wire_schema import ParsedWireSchema
from labone.core.reflection.server import reflection_capnp


class ServerTemplate(ABC):
    id: int


def capnp_server_factory(interface, mock, schema_parsed_dict):
    class MockServerImpl(interface.Server):
        def __init__(self) -> None:
            self._mock = mock

        def __getattr__(self, name):
            if hasattr(self._mock, name):
                return getattr(self._mock, name)
            return getattr(super(), name)
        
        async def getTheSchema(self, _context, **kwargs):
        # Use `from_dict` to benefit from pycapnp lifetime management
        # Otherwise the underlying capnp object need to be copied manually to avoid
        # segfaults
            _context.results.theSchema.from_dict(schema_parsed_dict)
    return MockServerImpl


class MockServer:
    def __init__(
        self,
        *,
        capability_bytes: Path,
        concrete_server: ServerTemplate,
    ):
        self._functionality = concrete_server
        with capability_bytes.open("rb") as f:
            schema_bytes = f.read()
        with reflection_capnp.CapSchema.from_bytes(schema_bytes) as schema:
            self._schema_parsed_dict = schema.to_dict()
            self._schema = ParsedWireSchema(schema.theSchema)
        self._capnp_interface = capnp.lib.capnp._InterfaceModule(
            self._schema.full_schema[concrete_server.id].schema.as_interface(),
            self._schema.full_schema[concrete_server.id].name,
        )
        self._server = None

    async def start(self):
        if self._server is not None:
            msg = "Server already started."
            raise RuntimeError(msg)
        await ensure_capnp_event_loop()
        # create local socket pair
        # Since there is only a single client there is no need to use a asyncio server
        read, write = socket.socketpair()
        reader = await capnp.AsyncIoStream.create_connection(sock=read)
        writer = await capnp.AsyncIoStream.create_connection(sock=write)
        # create server for the local socket pair
        self._server = capnp.TwoPartyServer(
            writer,
            bootstrap=capnp_server_factory(
                self._capnp_interface,
                self._functionality,
                self._schema_parsed_dict,
            )(),
        )
        return reader

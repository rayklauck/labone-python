"""Hpk Mock Server method definitions.

This module contains the method definitions for the Hpk Mock Server,
including setting and getting values, listing nodes, and subscribing to
nodes. This specific capnp server methods define the specific
Hpk behavior.
The logic of the capnp methods is deligated to the HpkMockFunctionality class,
which offers a blueprint meant to be overriden by the user.
"""


from __future__ import annotations

import json
import typing as t
from typing import TYPE_CHECKING

import numpy as np

from labone.core.helper import VectorElementType, VectorValueType
from labone.core.value import AnnotatedValue, _capnp_value_to_python_value, _value_from_python_types_dict
from labone.mock.mock_server import ServerTemplate

if TYPE_CHECKING:
    from capnp.lib.capnp import (
        _CallContext,
        _DynamicEnum,
        _DynamicStructBuilder,
        _DynamicStructReader,
    )

    from labone.core.session import ListNodesFlags
    from labone.mock.session_mock_functionality import SessionMockFunctionality

HPK_SCHEMA_ID = 11970870220622790664
SERVER_ERROR = "SERVER_ERROR"


def build_capnp_error(error: Exception) -> _DynamicStructBuilder:
    """Helper function to build a capnp error message.

    Args:
        error: Caught python exception to be converted.

    Returns:
        Capnp Type dictionary for Result(Error).
    """
    return {
        "err": {
            "code": 2,
            "message": f"{error}",
            "category": SERVER_ERROR,
            "source": __name__,
        },
    }


class SessionMockTemplate(ServerTemplate):
    """Hpk Mock Server.

    The logic for answering capnp requests is outsourced and taken as an argument.
    This allows for custom mock server definition while keeping this classes
    code static.

    Note:
        Methods within serve for capnp to answer requests. They should not be
        called directly. They should not be overritten in order to define
        custom behavior. Instead, override the methods of HpkMockFunctionality.

    Args:
        functionality: The implementation of the mock server behavior.
    """

    # unique capnp id of the Hpk schema
    id_ = HPK_SCHEMA_ID

    def __init__(self, functionality: SessionMockFunctionality) -> None:
        self._functionality = functionality

    async def listNodes(  # noqa: N802
        self,
        pathExpression: str,  # noqa: N803
        flags: ListNodesFlags,
        client: bytes,  # noqa: ARG002
        _context: _CallContext,
        **kwargs,  # noqa: ARG002
    ) -> list[str]:
        """Capnp server method to list nodes.

        Args:
            pathExpression: Path to narrow down which nodes should be listed.
                Omitting the path will list all nodes by default.
            flags: Flags to control the behaviour of the list_nodes method.
            client: Capnp specific argument.
            _context: Capnp specific argument.
            **kwargs: Capnp specific arguments.

        Returns:
            List of paths.
        """
        return await self._functionality.list_nodes(pathExpression, flags=flags)

    async def listNodesJson(  # noqa: N802
        self,
        pathExpression: str,  # noqa: N803
        flags: ListNodesFlags,
        client: bytes,  # noqa: ARG002
        _context: _CallContext,
        **kwargs,  # noqa: ARG002
    ) -> str:
        """Capnp server method to list nodes plus additional informtion as json.

        Args:
            pathExpression: Path to narrow down which nodes should be listed.
                Omitting the path will list all nodes by default.
            flags: Flags to control the behaviour of the list_nodes_info method.
            client: Capnp specific argument.
            _context: Capnp specific argument.
            **kwargs: Capnp specific arguments.

        Returns:
            Json encoded dictionary of paths and node info.
        """
        return json.dumps(
            await self._functionality.list_nodes_info(
                path=pathExpression,
                flags=flags,
            ),
        )

    async def getValue(  # noqa: N802
        self,
        pathExpression: str,  # noqa: N803
        lookupMode: _DynamicEnum,  # noqa: N803
        flags: int,
        client: bytes,  # noqa: ARG002
        _context: _CallContext,
        **kwargs,  # noqa: ARG002
    ) -> list[_DynamicStructBuilder]:
        """Capnp server method to get values.

        Args:
            pathExpression: Path for which the value should be retrieved.
            lookupMode: Defining whether a single path should be retrieved
                or potentially multiple ones specified by a wildcard path.
            flags: Flags to control the behaviour of wildcard path requests.
            client: Capnp specific argument.
            _context: Capnp specific argument.
            **kwargs: Capnp specific arguments.

        Returns:
            List of read values.
        """
        try:
            if lookupMode == 0:  # direct lookup
                responses = [await self._functionality.get(pathExpression)]
            else:
                responses = await self._functionality.get_with_expression(
                    pathExpression,
                    flags=flags,
                )
        except Exception as e:  # noqa: BLE001
            return [build_capnp_error(e)]

        return [
            {
                "ok": {
                    "value": _value_from_python_types_dict(response.value),
                    "metadata": {
                        "path": response.path,
                        "timestamp": response.timestamp,
                    },
                },
            }
            for response in responses
        ]

    async def setValue(  # noqa: PLR0913, N802
        self,
        pathExpression: str,  # noqa: N803
        value: _DynamicStructReader,
        lookupMode: _DynamicEnum,  # noqa: N803
        completeWhen: _DynamicEnum,  # noqa: N803, ARG002
        client: bytes,  # noqa: ARG002
        _context: _CallContext,
        **kwargs,  # noqa: ARG002
    ) -> list[_DynamicStructBuilder]:
        """Capnp server method to set values.

        Args:
            pathExpression: Path for which the value should be set.
            value: Value to be set.
            lookupMode: Defining whether a single path should be set
                or potentially multiple ones specified by a wildcard path.
            completeWhen: Capnp specific argument.
            client: Capnp specific argument.
            _context: Capnp specific argument.
            **kwargs: Capnp specific arguments.

        Returns:
            List of acknowledged values.
        """
        value, _ = _capnp_value_to_python_value(value)
        try:
            if lookupMode == 0:  # direct lookup
                responses = [
                    await self._functionality.set(
                        AnnotatedValue(value=value, path=pathExpression),
                    ),
                ]
            else:
                responses = await self._functionality.set_with_expression(
                    AnnotatedValue(value=value, path=pathExpression),
                )
        except Exception as e:  # noqa: BLE001
            return [build_capnp_error(e)]

        return [
            {
                "ok": {
                    "value": _value_from_python_types_dict(response.value),
                    "metadata": {
                        "path": response.path,
                        "timestamp": response.timestamp,
                    },
                },
            }
            for response in responses
        ]

    async def subscribe(
        self,
        subscription: _DynamicStructReader,
        _context: _CallContext,
        **kwargs,  # noqa: ARG002
    ) -> _DynamicStructBuilder:
        """Capnp server method to subscribe to nodes.

        Do not override this method. Instead, override 'subscribe_logic'
        of HpkMockFunctionality (or subclass).

        Args:
            subscription: Capnp object containing information on
                where to distribute updates to.
            _context: Capnp specific argument.
            **kwargs: Capnp specific arguments.

        Returns:
            Capnp acknowledgement.
        """
        try:
            await self._functionality.subscribe_logic(
                path=subscription.path,
                streaming_handle=subscription.streamingHandle,
                subscriber_id=subscription.subscriberId,
            )
        except Exception as e:  # noqa: BLE001
            return build_capnp_error(e)
        return {"ok": {}}

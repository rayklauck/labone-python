from abc import ABC
from contextlib import contextmanager
import json

from labone.core import ListNodesFlags, ListNodesInfoFlags
from labone.core.helper import LabOneNodePath
from labone.core.session import NodeInfo
from labone.core.subscription import StreamingHandle
from labone.core.value import AnnotatedValue, _value_from_python_types
from labone.mock.mock_server import ServerTemplate
from labone.mock.hpk_functionality import HpkMockFunctionality


HPK_SCHEMA_ID = 11970870220622790664
SERVER_ERROR = "SERVER_ERROR"



def build_capnp_error(error: Exception):
    """
    Returns:
        Capnp Type dictionary for: Result(Error)
    """
    return {
        "err": {
            "code": 2,
            "message": f"{error}",
            "category": SERVER_ERROR,
            "source": __name__,
        }
    }


class SessionMockTemplate(ServerTemplate):
    id = HPK_SCHEMA_ID

    def __init__(self, functionality: HpkMockFunctionality) -> None:
        self._functionality = functionality

    async def listNodes(self, pathExpression, flags, client, _context, **kwargs):
        return await self._functionality.list_nodes(pathExpression, flags=flags)

    async def listNodesJson(self, pathExpression, flags, client, _context, **kwargs):
        return json.dumps(
            await self._functionality.list_nodes_info(
                path=pathExpression,
                flags=flags,
            )
        )

    async def getValue(
        self,
        pathExpression,
        lookupMode,
        flags,
        client,
        _context,
        **kwargs,
    ):
        try:
            if lookupMode == 0:  # direct lookup
                responses = [await self._functionality.get(pathExpression)]
            else:
                responses = await self._functionality.get_with_expression(
                    pathExpression, flags=flags
                )
        except BaseException as e:
            return [build_capnp_error(e)]

        return [
            {
                "ok": {
                    "value":{"int64": response.value},# _value_from_python_types(response.value),#
                    "metadata": {
                        "path": response.path,
                        "timestamp": response.timestamp,
                    },
                },
            }
            for response in responses
        ]

    async def setValue(
        self,
        pathExpression,
        value,
        lookupMode,
        completeWhen,
        client,
        _context,
        **kwargs,
    ):
        value = value.int64
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
        except BaseException as e:
            return [build_capnp_error(e)]

        return [
            {
                "ok": {
                    "value": {"int64": response.value},
                    "metadata": {
                        "path": response.path,
                        "timestamp": response.timestamp,
                    },
                },
            }
            for response in responses
        ]

    async def subscribe(self, subscription, _context, **kwargs):
        """This is a capnp protocol method. Do not override it, but override 'subscribe_logic' instead."""
        try:
            await self._functionality.subscribe_logic(
                path=subscription.path,
                streaming_handle=subscription.streamingHandle,
                subscriber_ID=subscription.subscriberId,
            )
        except BaseException as e:
            return build_capnp_error(e)
        return {"ok": {}}

"""Partially predifined behaviour for HPK mock.

This class provides basic Hpk mock functionality by taking over some usually
desired tasks. With that in place, the user may inherit from this class
in order to further specify behavior, without having to start from scratch.
Even if some of the predefined behaviour is not desired, the implementation
can give some reference on how an individual mock server can be implemented.


Already predefined behaviour:

    * Simulating state for get/set:
        A dictionary is used to store the state of the mock server.
        Get and set will access this dictionary.
    * Answering list_nodes(_info) via knowledge of the tree structure:
        Given a dictionary of paths to node info passed in the constructor,
        the list_nodes(_info) methods will be able to answer accordingly.
    * Reducing get_with_expression/set_with_expression to multiple get/set:
        As the tree structure is known, the get_with_expression/set_with_expression
        methods can be implemented by calling the get/set methods multiple times.
    * Managing subscriptions and passing all changes into the queues:
        The subscriptions are stored and on every change, the new value is passed
        into the queues.
    * Adding chronological timestamps to responses:
        The server answers need timestamps to the responsis in any case.
        By using the monotonic clock, the timestamps are added automatically.

"""

from __future__ import annotations

import asyncio
import fnmatch
import re
import time
import typing as t

import numpy as np

from labone.core import ListNodesFlags, ListNodesInfoFlags
from labone.core.shf_vector_data import SHFDemodSample, encode_shf_vector_data_struct
from labone.core.value import (
    AnnotatedValue,
    CntSample,
    TriggerSample,
    Value,
    _value_from_python_types_dict,
)
from labone.mock.session_mock_functionality import SessionMockFunctionality

if t.TYPE_CHECKING:
    from labone.core.helper import LabOneNodePath
    from labone.core.session import NodeInfo
    from labone.core.subscription import StreamingHandle


class AutomaticSessionFunctionality(SessionMockFunctionality):
    """Predefined behaviour for HPK mock.

    Args:
        paths_to_info: Dictionary of paths to node info. (tree structure)
    """

    def __init__(
        self,
        paths_to_info: dict[LabOneNodePath, NodeInfo] | None = None,
    ) -> None:
        if paths_to_info is None:
            paths_to_info = {}

        # remembering tree structure
        self._paths_to_info = paths_to_info
        # storing state
        self._memory: dict[LabOneNodePath, Value] = {}
        # storing subscriptions
        self._path_to_streaming_handles: dict[
            LabOneNodePath,
            list[StreamingHandle],
        ] = {}

    def _get_timestamp(self) -> int:
        return time.clock_gettime_ns(time.CLOCK_MONOTONIC)

    async def list_nodes_info(
        self,
        path: LabOneNodePath = "",
        *,
        flags: ListNodesInfoFlags | int = ListNodesInfoFlags.ALL,  # noqa: ARG002
    ) -> dict[LabOneNodePath, NodeInfo]:
        """Predefined behaviour for list_nodes_info.

        Uses knowledge of the tree structure to answer.

        Warning:
            Flags will be ignored in this implementation. (TODO)

        Args:
            path: Path to narrow down which nodes should be listed. Omitting
                the path will list all nodes by default.
            flags: Flags to control the behaviour of the list_nodes_info method.

        Returns:
            Dictionary of paths to node info.
        """
        if path == "":
            return self._paths_to_info
        if path[-1] != "*":
            path = path + "/*"
        return {
            k: v for k, v in self._paths_to_info.items() if fnmatch.fnmatch(k, path)
        }

    async def list_nodes(
        self,
        path: LabOneNodePath = "",
        *,
        flags: ListNodesFlags | int = ListNodesFlags.ABSOLUTE,  # noqa: ARG002
    ) -> list[LabOneNodePath]:
        """Predefined behaviour for list_nodes.

        Uses knowledge of the tree structure to answer.

        Warning:
            Flags will be ignored in this implementation. (TODO)

        Args:
            path: Path to narrow down which nodes should be listed. Omitting
                the path will list all nodes by default.
            flags: Flags to control the behaviour of the list_nodes method.

        Returns:
            List of paths.
        """
        if path == "":
            return list(self._paths_to_info.keys())
        if path[-1] != "*":
            path = path + "/*"
        return fnmatch.filter(self._paths_to_info.keys(), path)

    async def get(self, path: LabOneNodePath) -> AnnotatedValue:
        """Predefined behaviour for get.

        Look up the path in the internal dictionary.

        Args:
            path: Path of the node to get.

        Returns:
            Corresponding value.
        """
        value = self._memory.get(
            path,
            "not found in mock memory",
        )
        response = AnnotatedValue(path=path, value=value)
        response.timestamp = self._get_timestamp()
        return response

    async def get_with_expression(
        self,
        path_expression: LabOneNodePath,
        flags: ListNodesFlags  # noqa: ARG002
        | int = ListNodesFlags.ABSOLUTE
        | ListNodesFlags.RECURSIVE
        | ListNodesFlags.LEAVES_ONLY
        | ListNodesFlags.EXCLUDE_STREAMING
        | ListNodesFlags.GET_ONLY,
    ) -> list[AnnotatedValue]:
        """Predefined behaviour for get_with_expression.

        Find all nodes associated with the path expression
        and call get for each of them.

        Args:
            path_expression: Path expression to get.
            flags: Flags to control the behaviour of the get_with_expression method.

        Returns:
            List of values, corresponding to nodes of the path expression.
        """
        return [
            await self.get(p)
            for p in resolve_wildcards_labone(
                path_expression,
                await self.list_nodes(path=path_expression),
            )
        ]

    async def set(self, value: AnnotatedValue) -> AnnotatedValue:  # noqa: A003
        """Predefined behaviour for set.

        Updates the internal dictionary. A set command is considered
        as an update and will be distributed to all registered subscription handlers.

        Args:
            value: Value to set.

        Returns:
            Acknowledged value.
        """
        self._memory[value.path] = value.value
        response = value
        response.timestamp = self._get_timestamp()

        capnp_response = {
            "value": _value_from_python_types_dict(response),
            "metadata": {
                "path": response.path,
                "timestamp": response.timestamp,
            },
        }
        # sending updated value to subscriptions
        await asyncio.gather(
            *[
                handle.sendValues([capnp_response])
                for handle in self._path_to_streaming_handles.get(value.path, [])
            ],
        )

        return response

    async def set_with_expression(self, value: AnnotatedValue) -> list[AnnotatedValue]:
        """Predefined behaviour for set_with_expression.

        Finds all nodes associated with the path expression
        and call set for each of them.

        Args:
            value: Value to set.

        Returns:
            List of acknowledged values, corresponding to nodes of the path expression.
        """
        return [
            await self.set(AnnotatedValue(value=value.value, path=p))
            for p in resolve_wildcards_labone(
                value.path,
                await self.list_nodes(value.path),
            )
        ]

    async def subscribe_logic(
        self,
        *,
        path: LabOneNodePath,
        streaming_handle: StreamingHandle,
        subscriber_id: int,  # noqa: ARG002
    ) -> None:
        """Predefined behaviour for subscribe_logic.

        Stores the subscription. Whenever an update event happens
        they are distributed to all registered handles,

        Args:
            path: Path to subscribe to.
            streaming_handle: Streaming handle of the subscriber.
            subscriber_id: Id of the subscriber.
        """
        if path not in self._path_to_streaming_handles:
            self._path_to_streaming_handles[path] = []
        self._path_to_streaming_handles[path].append(streaming_handle)


def resolve_wildcards_labone(path: str, nodes: list[str]) -> list[str]:
    """Resolves potential wildcards.

    In addition to the wildcard, this function also resolves partial nodes to
    its leaf nodes.

    Args:
        path: Path to resolve.
        nodes: List of nodes to resolve against.

    Returns:
        List of matched nodes in the raw path format
    """
    node_raw = re.escape(path)
    node_raw = node_raw.replace("/\\*/", "/[^/]*/").replace("/\\*", "/*") + "(/.*)?$"
    node_raw_regex = re.compile(node_raw)
    return list(filter(node_raw_regex.match, nodes))

import asyncio
import fnmatch
import re
import time
import typing as t
from typing import Any, Coroutine

from labone.core import ListNodesFlags, ListNodesInfoFlags
from labone.core.helper import LabOneNodePath
from labone.core.session import NodeInfo
from labone.core.subscription import StreamingHandle
from labone.core.value import AnnotatedValue
from labone.mock.hpk_functionality import HpkMockFunctionality


class AutomaticHpkFunctionality(HpkMockFunctionality):
    """Already predifined behaviour:
    - simulating state for get/set
    - adding chronological timestamps to responses
    - manages subscriptions and passes all changes into the queues.
    - answering list_nodes(_info) via knowledge of the tree structure
    - reducing get_with_expression/set_with_expression naturally to get/set
      (via knowledge of the tree structure)
    """

    def __init__(self, paths_to_info: dict[LabOneNodePath, NodeInfo] = {}) -> None:
        self._paths_to_info = paths_to_info
        self._memory = {}
        self._path_to_streaming_handles: dict[
            LabOneNodePath,
            list[StreamingHandle],
        ] = {}

    def get_timestamp(self) -> int:
        return time.clock_gettime_ns(time.CLOCK_MONOTONIC)

    async def list_nodes_info(
        self,
        path: LabOneNodePath = "",
        *,
        flags: ListNodesInfoFlags | int = ListNodesInfoFlags.ALL,
    ) -> Coroutine[Any, Any, dict[LabOneNodePath, NodeInfo]]:
        """
        Warning:
            Flags will be ignored in this implementation. TODO
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
        flags: ListNodesFlags | int = ListNodesFlags.ABSOLUTE,
    ) -> list[LabOneNodePath]:
        """
        Warning:
            Flags will be ignored in this implementation. TODO
        """
        if path == "":
            return list(self._paths_to_info.keys())
        if path[-1] != "*":
            path = path + "/*"
        return fnmatch.filter(self._paths_to_info.keys(), path)

    async def get(self, path: LabOneNodePath) -> AnnotatedValue:
        response = self._memory.get(path, AnnotatedValue(path=path, value=0))
        response.timestamp = self.get_timestamp()
        return response

    async def get_with_expression(
        self,
        path_expression: LabOneNodePath,
        flags: ListNodesFlags
        | int = ListNodesFlags.ABSOLUTE
        | ListNodesFlags.RECURSIVE
        | ListNodesFlags.LEAVES_ONLY
        | ListNodesFlags.EXCLUDE_STREAMING
        | ListNodesFlags.GET_ONLY,
    ) -> list[AnnotatedValue]:
        return [
            await self.get(p)
            for p in resolve_wildcards_labone(
                path_expression, await self.list_nodes(path=path_expression)
            )
        ]

    async def set(self, value: AnnotatedValue) -> AnnotatedValue:
        self._memory[value.path] = value
        response = value
        response.timestamp = self.get_timestamp()

        capnp_response = {
            "value": {"int64": response.value},
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
        return [
            await self.set(AnnotatedValue(value=value.value, path=p))
            for p in resolve_wildcards_labone(
                value.path, await self.list_nodes(value.path)
            )
        ]

    async def subscribe_logic(
        self,
        *,
        path: LabOneNodePath,
        streaming_handle: StreamingHandle,
        subscriber_ID: int,
    ) -> None:
        """Override this method for defining subscription behavior."""
        if path not in self._path_to_streaming_handles:
            self._path_to_streaming_handles[path] = []
        self._path_to_streaming_handles[path].append(streaming_handle)


def resolve_wildcards_labone(path: str, nodes: t.List[str]) -> t.List[str]:
    """Resolves potential wildcards.

    Also will resolve partial nodes to its leaf nodes.

    Returns:
        List of matched nodes in the raw path format
    """
    node_raw = re.escape(path)
    node_raw = node_raw.replace("/\\*/", "/[^/]*/").replace("/\\*", "/*") + "(/.*)?$"
    node_raw_regex = re.compile(node_raw)
    return list(filter(node_raw_regex.match, nodes))

from abc import ABC, abstractmethod
from contextlib import contextmanager
import json

from labone.core import ListNodesFlags, ListNodesInfoFlags
from labone.core.helper import LabOneNodePath
from labone.core.session import NodeInfo
from labone.core.subscription import StreamingHandle
from labone.core.value import AnnotatedValue
from labone.mock.mock_server import ServerTemplate


class HpkMockFunctionality(ABC):

    @abstractmethod
    async def get(self, path: LabOneNodePath) -> AnnotatedValue:
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def set(self, value: AnnotatedValue) -> AnnotatedValue:
        ...

    @abstractmethod
    async def set_with_expression(self, value: AnnotatedValue) -> list[AnnotatedValue]:
        ...

    @abstractmethod
    async def list_nodes(
        self,
        path: LabOneNodePath = "",
        *,
        flags: ListNodesFlags | int = ListNodesFlags.ABSOLUTE,
    ) -> list[LabOneNodePath]:
        ...

    @abstractmethod
    async def list_nodes_info(
        self,
        path: LabOneNodePath = "",
        *,
        flags: ListNodesInfoFlags | int = ListNodesInfoFlags.ALL,
    ) -> dict[LabOneNodePath, NodeInfo]:
        ...

    @abstractmethod
    async def subscribe_logic(
        self,
        *,
        path: LabOneNodePath,
        streaming_handle: StreamingHandle,
        subscriber_ID: int,
    ) -> None:
        """Override this method for defining subscription behavior."""
        ...
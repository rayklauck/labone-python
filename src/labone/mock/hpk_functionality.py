"""Hpk blueprint for defining mock server behavior.

The HpKMockFunctionality class offers a interface between
capnp server logic and the user. The user can override the methods
to define an individual mock server. The signature of the methods
is mostly identical to the session-interface on the caller side.
Thereby it feels as if the session-interface is overritten directly,
hiding the capnp server logic from the user.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from labone.core import ListNodesFlags, ListNodesInfoFlags

if TYPE_CHECKING:
    from labone.core.helper import LabOneNodePath
    from labone.core.session import NodeInfo
    from labone.core.subscription import StreamingHandle
    from labone.core.value import AnnotatedValue


class HpkMockFunctionality(ABC):
    """Hpk blueprint for defining mock server behavior.

    Inherit and override the methods to define an individual mock server.
    """

    @abstractmethod
    async def get(self, path: LabOneNodePath) -> AnnotatedValue:
        """Override this method for defining get behavior.

        Args:
            path: Path to a single the node.

        Returns:
            Retrieved value.
        """
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
        """Override this method for defining get_with_expression behavior.

        Args:
            path_expression: Path expression to get.
            flags: Flags to control the behaviour of the get_with_expression method.

        Returns:
            List of values, corresponding to nodes of the path expression.
        """
        ...

    @abstractmethod
    async def set(self, value: AnnotatedValue) -> AnnotatedValue:  # noqa: A003
        """Override this method for defining set behavior.

        Args:
            value: Value to set. Note that this is in the form of an AnnotatedValue.
                Therefore, value, path and timestamp are encapsulated within.

        Returns:
            Acknowledged value (also in annotated form).
        """
        ...

    @abstractmethod
    async def set_with_expression(self, value: AnnotatedValue) -> list[AnnotatedValue]:
        """Override this method for defining set_with_expression behavior.

        Args:
            value: Value to set. Note that this is in the form of an AnnotatedValue.
                Therefore, value, wildcard-path and timestamp are encapsulated within.
                All nodes matching the wildcard-path will be set to the value.

        Returns:
            Acknowledged values (also in annotated form).
        """
        ...

    @abstractmethod
    async def list_nodes(
        self,
        path: LabOneNodePath = "",
        *,
        flags: ListNodesFlags | int = ListNodesFlags.ABSOLUTE,
    ) -> list[LabOneNodePath]:
        """Override this method for defining list_nodes behavior.

        Args:
            path: Path to narrow down which nodes should be listed.
                Omitting the path will list all nodes by default.
            flags: Flags to control the behaviour of the list_nodes method.

        Returns:
            List of nodes, corresponding to the path and flags.
        """
        ...

    @abstractmethod
    async def list_nodes_info(
        self,
        path: LabOneNodePath = "",
        *,
        flags: ListNodesInfoFlags | int = ListNodesInfoFlags.ALL,
    ) -> dict[LabOneNodePath, NodeInfo]:
        """Override this method for defining list_nodes_info behavior.

        Args:
            path: Path to narrow down which nodes should be listed.
                Omitting the path will list all nodes by default.
            flags: Flags to control the behaviour of the list_nodes_info method.

        Returns:
            Dictionary of paths to node info.
        """
        ...

    @abstractmethod
    async def subscribe_logic(
        self,
        *,
        path: LabOneNodePath,
        streaming_handle: StreamingHandle,
        subscriber_id: int,
    ) -> None:
        """Override this method for defining subscription behavior.

        Args:
            path: Path to the node to subscribe to.
            streaming_handle: Handle to the stream.
            subscriber_id: Unique id of the subscriber.
        """
        ...

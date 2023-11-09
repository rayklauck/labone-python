"""High-level functionality for connecting to devices and zi servers."""
from __future__ import annotations

import typing as t
from functools import partial

from labone.core import (
    DeviceKernelInfo,
    KernelSession,
    ServerInfo,
    ZIKernelInfo,
    AnnotatedValue,
)
from labone.devices import Instrument
from labone.nodetree import construct_nodetree
from labone.nodetree.node import Node, NodeTreeManager, PartialNode


class DataServer(PartialNode):
    """High-level functionality for connecting to devices and zi servers."""

    def __init__(
        self,
        host: str,
        port: int = 8004,
        *,
        model_node: PartialNode,
    ):
        self.host = host
        self.port = port
        self.server_info = ServerInfo(host=host, port=port)

        super().__init__(
            tree_manager=model_node.tree_manager,
            path_segments=model_node.path_segments,
            path_aliases=model_node.path_aliases,
            subtree_paths=model_node.subtree_paths,
        )

    @classmethod
    async def build(
        cls,
        host: str,
        port: int = 8004,
        *,
        use_enum_parser: bool = True,
        custom_parser: t.Callable[[AnnotatedValue], AnnotatedValue] | None = None,
        hide_kernel_prefix: bool = True,
    ) -> DataServer:
        session = await KernelSession.create(
            kernel_info=ZIKernelInfo(),
            server_info=ServerInfo(host=host, port=port),
        )

        model_node = await construct_nodetree(
            session,
            hide_kernel_prefix=hide_kernel_prefix,
            use_enum_parser=use_enum_parser,
            custom_parser=custom_parser,
        )

        return DataServer(host, port, model_node=model_node)

    async def _connect_zi(
        self,
        *,
        use_enum_parser: bool = True,
        custom_parser: t.Callable[[AnnotatedValue], AnnotatedValue] | None = None,
        hide_kernel_prefix: bool = True,
    ) -> Node:
        """Connect to a zi server.

        Args:
            parser_builder: A custom parser builder for the nodetree.
                Default is `None`.
            hide_kernel_prefix: Hide the kernel prefix in the nodetree.
                Default is `True`.
        """


    async def connect_device(
        self,
        serial: str,
        *,
        interface: DeviceKernelInfo.DeviceInterface =
            DeviceKernelInfo.DeviceInterface.GbE,
        hide_kernel_prefix: bool = True,
        use_enum_parser: bool = True,
        custom_parser: t.Callable[[AnnotatedValue], AnnotatedValue] | None = None,
    ) -> Instrument:
        """Connect to a device.

        Args:
            serial: Serial number of the device, e.g. *'dev12000'*.
                The serial number can be found on the back panel of the instrument.
            interface: Interface of the device, e.g. *'1GbE'*.
                The interface can be found on the back panel of the instrument.
            hide_kernel_prefix: Hide the kernel prefix in the nodetree.
                Default is `True`.
            parser_builder: A custom parser builder for the nodetree.
                Default is `None`.

        Returns:
            The connected device.
        """
        session = await KernelSession.create(
            kernel_info=DeviceKernelInfo(device_id=serial, interface=interface),
            server_info=self.server_info,
        )

        model_node = await construct_nodetree(
            session,
            hide_kernel_prefix=hide_kernel_prefix,
            use_enum_parser=use_enum_parser,
            custom_parser=custom_parser,
        )

        return Instrument(
            serial=serial,
            device_type="instrument",
            data_server=self,
            model_node=model_node,
        )


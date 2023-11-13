"""High-level functionality for connecting to devices and zi servers."""
from __future__ import annotations

import typing as t

from labone.devices import Instrument
from labone.core import (
    AnnotatedValue,
    DeviceKernelInfo,
    KernelSession,
    ServerInfo,
    ZIKernelInfo,
)
from labone.errors import LabOneError
from labone.nodetree import construct_nodetree
from labone.nodetree.node import PartialNode


class DataServer(PartialNode):
    """High-level functionality for connecting to devices and zi servers."""

    def __init__(
        self,
        host: str,
        port: int = 8004,
        *,
        model_node: PartialNode,
    ):
        self._host = host
        self._port = port

        super().__init__(
            tree_manager=model_node.tree_manager,
            path_segments=model_node.path_segments,
            path_aliases=model_node.path_aliases,
            subtree_paths=model_node.subtree_paths,
        )

    @classmethod
    async def create(
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

        try:
            model_node = await construct_nodetree(
                session,
                hide_kernel_prefix=hide_kernel_prefix,
                use_enum_parser=use_enum_parser,
                custom_parser=custom_parser,
            )
        except LabOneError as e:
            raise LabOneError(
                f"Could not connect to Data Server at {host}:{port}.",
            ) from e

        return DataServer(host, port, model_node=model_node)

    async def connect_device(
        self,
        serial: str,
        *,
        interface: str = "",
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
            server_info=ServerInfo(host=self.host, port=self.port),
        )

        try:
            model_node = await construct_nodetree(
                session,
                hide_kernel_prefix=hide_kernel_prefix,
                use_enum_parser=use_enum_parser,
                custom_parser=custom_parser,
            )
        except LabOneError as e:
            raise LabOneError(
                f"Could not connect to device {serial} through {interface}.",
            ) from e

        return Instrument(
            serial=serial,
            data_server=self,
            model_node=model_node,
        )

    @property
    def host(self) -> str:
        """Host of the Data Server."""
        return self._host

    @property
    def port(self) -> int:
        """Port of the Data Server."""
        return self._port

"""High-level functionality for connecting to devices and zi servers."""
from __future__ import annotations

import typing as t
from functools import partial

from labone.core import DeviceKernelInfo, KernelSession, ServerInfo, ZIKernelInfo, \
    AnnotatedValue
from labone.devices import BaseInstrument
from labone.nodetree import construct_nodetree
from labone.nodetree.enum import get_default_enum_parser
from labone.nodetree.node import Node, NodeTreeManager


class Session:
    """High-level functionality for connecting to devices and zi servers."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server_info = ServerInfo(host=host, port=port)

    async def connect_zi(
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
        session = await KernelSession.create(
            kernel_info=ZIKernelInfo(),
            server_info=self.server_info,
        )

        return await construct_nodetree(session,
                                        hide_kernel_prefix=hide_kernel_prefix,
            use_enum_parser=use_enum_parser,
            custom_parser=custom_parser,)

    async def connect_device(
        self,
        serial: str,
        *,
        interface: DeviceKernelInfo.DeviceInterface =
            DeviceKernelInfo.DeviceInterface.GbE,
        hide_kernel_prefix: bool = True,
        use_enum_parser: bool = True,
        custom_parser: t.Callable[[AnnotatedValue], AnnotatedValue] | None = None,
    ) -> BaseInstrument:
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

        # construct_nodetree logic
        path_to_info = await session.list_nodes_info("*")

        if use_enum_parser:
            parser = get_default_enum_parser(path_to_info)
        else:

            def parser(x: AnnotatedValue) -> AnnotatedValue:
                return x  # pragma: no cover

        if custom_parser is not None:
            def parser(x: AnnotatedValue) -> AnnotatedValue:
                return custom_parser(parser(x))  # pragma: no cover

        nodetree_manager = NodeTreeManager(
            session=session,
            parser=parser,
            path_to_info=path_to_info,
        )


        zi_tree = await self.connect_zi(
                use_enum_parser=use_enum_parser,
                custom_parser=custom_parser,
                hide_kernel_prefix=True
            )
        # NodetreeManager.construct_nodetree logic

        has_common_prefix = (
                len(nodetree_manager._partially_explored_structure.keys()) == 1)



        if not hide_kernel_prefix or not has_common_prefix:
            return BaseInstrument(serial=serial,
            device_type="instrument",
            zi_tree=zi_tree,
            tree_manager=nodetree_manager,
            path_segments=(),
            subtree_paths=nodetree_manager.find_substructure(()),
            path_aliases=None,
            )

        common_prefix = (
            next(iter(nodetree_manager._partially_explored_structure.keys())))
        return BaseInstrument(
            serial=serial,
            device_type="instrument",
            zi_tree=zi_tree,
            tree_manager=nodetree_manager,
            path_segments=(common_prefix,),
            subtree_paths=nodetree_manager.find_substructure((common_prefix,)),
            path_aliases=None,
        )
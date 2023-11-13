"""Base Instrument Driver.

Natively works with all device types and provides the basic functionality like
the device specific nodetree.
"""
from __future__ import annotations

import logging

from labone.nodetree.node import Node, PartialNode

logger = logging.getLogger(__name__)

VERSION_LENGTH = 3


class Instrument(PartialNode):
    """Generic toolkit driver for a Zurich Instrument device.

    It exposes the nodetree and also implements common functions valid for all
    devices.

    It is implicitly assumed that the device is not a leaf node and does
    not contain wildcards.

    Args:
        serial: Serial number of the device, e.g. *'dev12000'*.
            The serial number can be found on the back panel of the instrument.
        session: Session to the Data Server
    """

    def __init__(
        self,
        *,
        serial: str,
        data_server: 'DataServer',
        model_node: Node,
    ):
        self._serial = serial
        self._data_server = data_server

        super().__init__(
            tree_manager=model_node.tree_manager,
            path_segments=model_node.path_segments,
            subtree_paths=model_node.subtree_paths,
            path_aliases=model_node.path_aliases,
        )

    def __repr__(self) -> str:
        return str(
            f"{self.__class__.__name__}({self.serial})",
        )

    @property
    def serial(self) -> str:
        """Instrument specific serial."""
        return self._serial

    @property
    def data_server(self) -> 'DataServer':
        """Data Server instance."""
        return self._data_server

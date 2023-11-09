"""Base Instrument Driver.

Natively works with all device types and provides the basic functionality like
the device specific nodetree.
"""
from __future__ import annotations

import contextlib
import json
import logging
import typing as t
import warnings
from functools import cached_property

from labone.errors import LabOneError

from labone.nodetree.node import Node, PartialNode

from labone.core.value import AnnotatedValue


logger = logging.getLogger(__name__)

VERSION_LENGTH = 3


class Instrument(PartialNode):
    """Generic toolkit driver for a Zurich Instrument device.

    All device specific class are derived from this class.
    It exposes the nodetree and also implements common functions valid for all
    devices.
    It also can be used directly, e.g. for instrument types that have no special
    class in toolkit.

    It is implicitly assumed that the device is not a leaf node and does
    not contain wildcards.

    Args:
        serial: Serial number of the device, e.g. *'dev12000'*.
            The serial number can be found on the back panel of the instrument.
        device_type: Type of the device.
        session: Session to the Data Server
    """

    def __init__(  # noqa: PLR0913
        self,
        *,
        serial: str,
        device_type: str,
        data_server: "DataServer",
        model_node: Node,
    ):
        self._serial = serial
        self._device_type = device_type
        try:
            self._options = self.features.options()  # retrieve options from dataserver
        except RuntimeError:
            self._options = ""

        self._streaming_nodes: list[Node] | None = None
        self.data_server = data_server

        super().__init__(
            tree_manager=model_node.tree_manager,
            path_segments=model_node.path_segments,
            subtree_paths=model_node.subtree_paths,
            path_aliases=model_node.path_aliases,
        )

    def __repr__(self) -> str:
        options = f"({self._options})" if self._options else ""
        options = options.replace("\n", ",")
        return str(
            f"{self.__class__.__name__}({self._device_type}{options},{self.serial})",
        )

    @staticmethod
    def _version_string_to_tuple(version: str) -> tuple[int, int, int]:
        """Converts a version string into a version tuple.

        Args:
            version: Version

        Returns:
            Version as a tuple of ints
        """
        result = [0, 0, 0]  # default 0, if a part of the version is not a number

        for i, value in enumerate(version.split(".")):
            with contextlib.suppress(ValueError):
                result[i] = int(value)

        if len(result) != VERSION_LENGTH:
            msg = (
                f"Version string must contain three parts separated by dots, "
                f"'{version}' is therefore not a valid version"
            )
            raise ValueError(msg)

        return result[0], result[1], result[2]

    @staticmethod
    def _check_labone_version(
        labone_python_version: tuple[int, int, int],
        labone_version: tuple[int, int, int],
    ) -> None:
        """Check that the LabOne version matches the labone-python version.

        Args:
            labone_python_version: Version of this package.
            labone_version: LabOne DataServer version.

        Raises:
            ToolkitError: If the zhinst.core version does not match the
                version of the connected LabOne DataServer.
        """
        if labone_version[:2] < labone_python_version[:2]:
            msg = (
                "The LabOne version is smaller than the labone-python version. "
                f"{labone_version} < {labone_python_version}. "
                "Please install the latest/matching LabOne version from "
                "https://www.zhinst.com/support/download-center."
            )
            raise LabOneError(msg)
        if labone_version[:2] > labone_python_version[:2]:
            msg = (
                "the labone-python version is smaller than the LabOne version "
                f"{labone_python_version} < {labone_version}. "
                "Please install the latest/matching version from pypi.org."
            )
            raise LabOneError(msg)
        if labone_version[-1] != labone_python_version[-1]:
            msg = (
                "The patch version of labone-python and the LabOne DataServer "
                f"mismatch {labone_version[-1]} ! {labone_python_version[-1]}."
            )
            warnings.warn(
                msg,
                RuntimeWarning,
                stacklevel=2,
            )

    async def _check_firmware_update_status(self) -> None:
        """Check if the firmware matches LabOne version.

        Raises:
            ConnectionError: If the device is currently updating
            ToolkitError: If the firmware revision does not match to the
                version of the connected LabOne DataServer.
        """
        devices: AnnotatedValue = await self._zi_tree.devices.connected()  # type: ignore
        device_info = json.loads(devices.value)[self.serial.upper()]  # type: ignore
        status_flag = device_info["STATUSFLAGS"]
        if status_flag & 1 << 8:
            raise ConnectionError(
                "The device is currently updating please try again after the update "
                "process is complete"
            )
        if status_flag & 1 << 4 or status_flag & 1 << 5:
            raise LabOneError(
                "The Firmware does not match the LabOne version. "
                "Please update the firmware (e.g. in the LabOne UI)"
            )
        if status_flag & 1 << 6 or status_flag & 1 << 7:
            raise LabOneError(
                "The Firmware does not match the LabOne version. "
                "Please update LabOne to the latest version from "
                "https://www.zhinst.com/support/download-center."
            )

    async def check_compatibility(self) -> None:
        """Check if the software stack is compatible.

        Only if all versions and revisions of the software stack match stability
        can be ensured. The following criteria are checked:

            * firmware revision matches the LabOne Data Server version

        Raises:
            ConnectionError: If the device is currently updating
            ToolkitError: If one of the above mentioned criterion is not
                fulfilled
        """

        await self._check_firmware_update_status()

    @property
    def serial(self) -> str:
        """Instrument specific serial."""
        return self._serial

    @property
    def device_type(self) -> str:
        """Type of the instrument (e.g. MFLI)."""
        return self._device_type

    @cached_property
    async def device_options(self) -> str:
        """Enabled options of the instrument."""
        return (await self.features.options()).value  # type: ignore

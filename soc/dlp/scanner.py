"""DLP scanner interface stub.

This module exists ONLY to give downstream pipeline stages a typed
handle to bind against until the real scanner from canonical spec
section 6 lands. See ``soc/dlp/__init__.py`` for the resolution path.

The Risk Engine already consumes a :class:`soc.risk.types.DLPResult`
(a frozen dataclass), so anything that satisfies the contract below
and ultimately produces a ``DLPResult`` will plug in without changes
to the Risk Engine.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from soc.risk.types import DLPResult


@runtime_checkable
class DLPScannerProtocol(Protocol):
    """Contract every DLP scanner implementation MUST satisfy.

    Mirrors the call signature used inside ``SOCPipeline.evaluate`` in
    canonical spec section 5.2:

        dlp_result = await self.dlp.scan(event.data, classification=event.classification)
    """

    async def scan(
        self,
        data: Any,
        *,
        classification: str,
    ) -> DLPResult:
        ...  # pragma: no cover --- protocol method


class NotImplementedDLPScanner:
    """Placeholder scanner that loudly refuses to run.

    Use this as the ``dlp`` dependency of ``SOCPipeline`` ONLY in
    tests where DLP is irrelevant. Any code path that actually needs
    DLP results will raise immediately, making the gap obvious.
    """

    async def scan(
        self,
        data: Any,
        *,
        classification: str,
    ) -> DLPResult:
        raise NotImplementedError(
            "DLP scanner is not implemented yet. See soc/dlp/__init__.py "
            "for the resolution path (Priority 1 in the SOC pipeline "
            "roadmap)."
        )


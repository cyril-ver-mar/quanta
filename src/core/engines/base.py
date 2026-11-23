"""XPS engine interface.

Gaussian 09 (molecules) and GPAW (periodic) implement this. An ORCA engine
can be added the same way: a core planner that returns :class:`DscfStep`
records, plus a service runner. Engines must not import their optional
binaries at import time.
"""

from __future__ import annotations

from typing import Protocol

ENGINE_GAUSSIAN = "gaussian"
ENGINE_GPAW = "gpaw"
ENGINES = (ENGINE_GAUSSIAN, ENGINE_GPAW)


class XpsEngine(Protocol):
    name: str

    def available(self) -> tuple[bool, str]:
        """Whether this engine can run a job on this machine, and why not."""

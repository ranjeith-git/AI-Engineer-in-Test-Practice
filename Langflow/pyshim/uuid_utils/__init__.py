"""Workspace-local pure-Python stand-in for the ``uuid-utils`` package.

Windows Smart App Control blocks the compiled ``_uuid_utils.pyd`` shipped in
``Langflow/venv``, which stops Langflow from starting. This directory is put on
``PYTHONPATH`` ahead of site-packages so ``import uuid_utils`` resolves to pure
Python instead. It implements only the surface Langflow's dependency stack
(``langchain_core`` and ``langsmith``) actually uses.

Nothing here is installed; delete ``Langflow/pyshim`` to undo.
"""

from __future__ import annotations

import os
import time
import uuid as _uuid
from uuid import (  # re-exported for API compatibility
    NAMESPACE_DNS,
    NAMESPACE_OID,
    NAMESPACE_URL,
    NAMESPACE_X500,
    RESERVED_FUTURE,
    RESERVED_MICROSOFT,
    RESERVED_NCS,
    RFC_4122,
    UUID,
    getnode,
)

__version__ = "0.19.0"

MAX = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
NIL = UUID("00000000-0000-0000-0000-000000000000")

_GREGORIAN_EPOCH_100NS = 0x01B21DD213814000
_VARIANT_BITS = 0x2 << 62


def _rand_bits(nbytes: int) -> int:
    return int.from_bytes(os.urandom(nbytes), "big")


def _uuid4_int() -> int:
    return _uuid.uuid4().int


def _uuid7_int(timestamp=None, nanos=None) -> int:
    if timestamp is None:
        ms = time.time_ns() // 1_000_000
    else:
        ms = int(timestamp)
    ms &= (1 << 48) - 1
    rand_a = _rand_bits(2) & 0x0FFF
    rand_b = _rand_bits(8) & ((1 << 62) - 1)
    return (ms << 80) | (0x7 << 76) | (rand_a << 64) | _VARIANT_BITS | rand_b


def uuid1(node=None, clock_seq=None) -> UUID:
    return _uuid.uuid1(node, clock_seq)


def uuid3(namespace, name) -> UUID:
    return _uuid.uuid3(namespace, name)


def uuid4() -> UUID:
    return _uuid.uuid4()


def uuid5(namespace, name) -> UUID:
    return _uuid.uuid5(namespace, name)


def uuid6(node=None, timestamp=None) -> UUID:
    if timestamp is None:
        ts = (time.time_ns() // 100) + _GREGORIAN_EPOCH_100NS
    else:
        ts = int(timestamp)
    ts &= (1 << 48) - 1
    rand_a = _rand_bits(2) & 0x0FFF
    rand_b = _rand_bits(8) & ((1 << 62) - 1)
    return UUID(int=(ts << 80) | (0x6 << 76) | (rand_a << 64) | _VARIANT_BITS | rand_b)


def uuid7(timestamp=None, nanos=None) -> UUID:
    return UUID(int=_uuid7_int(timestamp, nanos))


def uuid8(bytes_data) -> UUID:
    b = bytes(bytes_data)
    if len(b) != 16:
        raise ValueError("uuid8 requires exactly 16 bytes")
    value = int.from_bytes(b, "big")
    value &= ~(0xF << 76)
    value |= 0x8 << 76
    value &= ~(0x3 << 62)
    value |= _VARIANT_BITS
    return UUID(int=value)


def reseed() -> None:
    return None


__all__ = [
    "MAX",
    "NAMESPACE_DNS",
    "NAMESPACE_OID",
    "NAMESPACE_URL",
    "NAMESPACE_X500",
    "NIL",
    "RESERVED_FUTURE",
    "RESERVED_MICROSOFT",
    "RESERVED_NCS",
    "RFC_4122",
    "UUID",
    "__version__",
    "getnode",
    "uuid1",
    "uuid3",
    "uuid4",
    "uuid5",
    "uuid6",
    "uuid7",
    "uuid8",
]

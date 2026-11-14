"""Pure-Python subset of ``uuid_utils.compat``.

Mirrors the real module's behaviour of returning standard-library
``uuid.UUID`` objects.
"""

from __future__ import annotations

from uuid import (
    NAMESPACE_DNS,
    NAMESPACE_OID,
    NAMESPACE_URL,
    NAMESPACE_X500,
    RESERVED_FUTURE,
    RESERVED_MICROSOFT,
    RESERVED_NCS,
    RFC_4122,
    UUID,
    SafeUUID,
    getnode,
)

import uuid_utils

NIL = UUID("00000000-0000-0000-0000-000000000000")
MAX = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

__version__ = uuid_utils.__version__

uuid1 = uuid_utils.uuid1
uuid3 = uuid_utils.uuid3
uuid4 = uuid_utils.uuid4
uuid5 = uuid_utils.uuid5
uuid6 = uuid_utils.uuid6
uuid7 = uuid_utils.uuid7
uuid8 = uuid_utils.uuid8

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
    "SafeUUID",
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

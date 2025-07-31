# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from typing import TYPE_CHECKING, TypeVar

# Third-party imports
# Local imports
from openide.nodes._like_netbeans.entry_support import EntrySupport

if TYPE_CHECKING:
    from typing import Any

    from openide.nodes._like_netbeans.node import Node

PN = TypeVar('PN', bound='Node[Any, Any]')
N = TypeVar('N', bound='Node[Any, Any]')


class EntrySupportLazy(EntrySupport[PN, N]):  # Stub
    ...

# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from typing import Any, TypeVar

# Third-party imports
# Local imports
from openide.nodes._like_netbeans.node import Node

PN = TypeVar('PN', bound=Node[Any, Any])
CN = TypeVar('CN', bound=Node[Any, Any])


class FilterNode(Node[PN, CN]):  # Stub
    def __init__(self, node: Node[PN, CN]) -> None: ...

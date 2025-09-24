# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore
""""""

from __future__ import annotations

# System imports
import logging
from typing import TYPE_CHECKING

# Third-party imports
# Local imports
from .node import ChildNode, ParentNode, Node

if TYPE_CHECKING:
    from typing import Final

__all__: Final = ('FilterNode',)

_logger = logging.getLogger(__name__)


class FilterNode(Node[ParentNode, ChildNode]):  # Stub
    def __init__(self, node: Node[ParentNode, ChildNode]) -> None: ...

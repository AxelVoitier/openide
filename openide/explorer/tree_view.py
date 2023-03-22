# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from typing import TYPE_CHECKING

# Third-party imports
# from qtpy.QtCore import Signal
from qtpy.QtWidgets import QTreeView

# Local imports
from openide.utils.typing import override
# from openide.nodes import Node
from openide.explorer.model import _N
from openide.explorer.abstract_view import AbstractNodeView


if TYPE_CHECKING:
    from typing import Union
    from openide.explorer.model import ModelIndex


class NodeTreeView(AbstractNodeView[_N], QTreeView):

    @override  # QTreeView
    def collapse(self, index_or_node: Union[ModelIndex, _N]) -> None:
        return super().collapse(self._to_index(index_or_node))

    # TODO: watcher + connect to collapsed only if someone connect to this one
    # collapsed_node = Signal(Node, arguments=['node'])

    @override  # QTreeView
    def expand(self, index_or_node: Union[ModelIndex, _N]) -> None:
        return super().expand(self._to_index(index_or_node))

    @override  # QTreeView
    def expandRecursively(self, index_or_node: Union[ModelIndex, _N], depth: int = -1) -> None:
        return super().expandRecursively(self._to_index(index_or_node), depth)

    # TODO: watcher + connect to expanded only if someone connect to this one
    # expanded_node = Signal(Node, arguments=['node'])

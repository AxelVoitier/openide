# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from typing import TYPE_CHECKING

# Third-party imports
# from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTreeView
from typing_extensions import override

# Local imports
from openide.explorer.abstract_view import AbstractNodeView

# from openide.nodes import Node
from openide.explorer.model import _N

if TYPE_CHECKING:
    from PySide6.QtGui import QContextMenuEvent

    from openide.explorer.model import ModelIndex


class NodeTreeView(AbstractNodeView[_N], QTreeView):
    @override  # QTreeView
    def collapse(self, index_or_node: ModelIndex | _N) -> None:
        return super().collapse(self._to_index(index_or_node))

    # TODO: watcher + connect to collapsed only if someone connect to this one
    # collapsed_node = Signal(Node, arguments=['node'])

    @override  # QTreeView
    def expand(self, index_or_node: ModelIndex | _N) -> None:
        return super().expand(self._to_index(index_or_node))

    @override  # QTreeView
    def expandRecursively(self, index_or_node: ModelIndex | _N, depth: int = -1) -> None:
        return super().expandRecursively(self._to_index(index_or_node), depth)

    # TODO: watcher + connect to expanded only if someone connect to this one
    # expanded_node = Signal(Node, arguments=['node'])

    @override  # QWidget
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        node = self.model().node_for_index(self.indexAt(event.pos()))
        menu = node.context_menu
        if menu is None:
            event.accept()
            return

        menu.exec(self.viewport().mapToGlobal(event.pos()))

        # preferred_action = node.preferred_action
        # print(f'preferred action is {preferred_action}')
        # if preferred_action is not None:
        #     menu.popup(self.viewport().mapToGlobal(event.pos()), preferred_action)

        event.accept()

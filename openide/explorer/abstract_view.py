# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from typing import TYPE_CHECKING, Generic, cast

# Third-party imports
from PySide6.QtCore import QAbstractItemModel, QModelIndex, QPersistentModelIndex

# from PySide6.QtWidgets import QAbstractItemView
# Local imports
from openide.explorer.model import _N, NodeModel
from openide.utils.typing import override

if TYPE_CHECKING:
    from openide.explorer.model import ModelIndex


# For some reasons, if we subclass QAbstractItemView,
# it will segfault when we add a concrete class instance
# like a NodeTreeView in a QVBoxLayout with addWidget()?!...
class AbstractNodeView(Generic[_N]):
    def _to_index(self, index_or_node: ModelIndex | _N) -> ModelIndex:
        if isinstance(index_or_node, (QModelIndex, QPersistentModelIndex)):
            return index_or_node
        else:
            return self.model().index_for_node(index_or_node)

    @override  # QAbstractItemView
    def model(self) -> NodeModel[_N]:
        return cast('NodeModel[_N]', super().model())

    @override  # QAbstractItemView
    def setModel(self, model: QAbstractItemModel | NodeModel[_N]) -> None:
        assert isinstance(model, NodeModel), 'Model must be a subclass of NodeModel'

        super().setModel(model)

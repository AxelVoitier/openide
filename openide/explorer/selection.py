# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from collections.abc import Iterable
from typing import TYPE_CHECKING, Generic, cast

# Third-party imports
from qtpy.QtCore import (
    Slot, Signal, QAbstractItemModel,
    QItemSelectionModel, QItemSelection,
    QModelIndex, QPersistentModelIndex
)

# Local imports
from openide.explorer.model import NodeModel, _N
from openide.utils.typing import override
from openide.nodes._like_netbeans import Node


if TYPE_CHECKING:
    from collections.abc import Generator, Iterable
    from typing import Any, Optional, Union

    from openide.explorer.model import ModelIndex


class NodeSelection(QItemSelection, Generic[_N]):

    def __init__(self, *args: Any, node_model: NodeModel[_N], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        assert node_model is not None
        self.__node_model = node_model

    def __to_index(self, index_or_node: Union[ModelIndex, _N]) -> ModelIndex:
        if isinstance(index_or_node, (QModelIndex, QPersistentModelIndex)):
            return index_or_node
        else:
            return self.__node_model.index_for_node(index_or_node)

    @override  # QItemSelection
    def __add__(self, arg__1: Union[QItemSelection, Iterable[_N]]) -> QItemSelection:
        if isinstance(arg__1, QItemSelection):
            return super().__add__(arg__1)
        else:
            selection = NodeSelection[_N](node_model=self.__node_model)
            selection.nodes = arg__1
            return super().__add__(selection)

    # This list is unsure, because these are basically methods operating
    # at a lower level, that is a QList<QItemSelectionRange>.
    # What would be more important is to rather provide a pythonic
    # interface for node and iterable of nodes.
    # TODO: __iadd__
    # TODO: __lshift__? (seems very C++esque construct. Maybe __ilshift__ instead?)
    # TODO: append
    # TODO: fromList/fromVector (ie. @classmethod from_nodes)
    # TODO: insert
    # TODO: isSharedWith?
    # TODO: prepend
    # TODO: push_back
    # TODO: push_front
    # TODO: remove?
    # TODO: removeAll
    # TODO: removeOne?
    # TODO: split?
    # TODO: swap
    # TODO: toList/toVector? (already have nodes property)

    # Also:
    # TODO: __sub__
    # TODO: __isub__
    # TODO: __radd__, __rsub__

    @override  # QItemSelection
    def contains(self, index_or_node: Union[ModelIndex, _N]) -> bool:
        return super().contains(self.__to_index(index_or_node))

    __contains__ = contains

    @property
    def nodes(self) -> Iterable[_N]:  # Generator declared as Iterable to be in-line with the setter
        gen = self.__node_model.nodes_for_indexes(self.indexes())
        try:
            while True:
                try:
                    yield next(gen)
                except IndexError:  # Node was removed
                    pass
        except StopIteration:
            pass

    @nodes.setter
    def nodes(self, nodes: Iterable[_N]) -> None:
        select = super().select
        index_for_node = self.__node_model.index_for_node
        for node in nodes:
            index = index_for_node(node)
            select(index, index)

    @override  # QItemSelection
    def select(self, top_left: Union[ModelIndex, _N], bottom_right: Union[ModelIndex, _N]) -> None:
        super().select(self.__to_index(top_left), self.__to_index(bottom_right))

    def __str__(self) -> str:
        return f'{type(self).__name__}[{", ".join([str(node) for node in self.nodes])}]'


class NodeSelectionModel(QItemSelectionModel, Generic[_N]):

    def __init__(self, model: NodeModel[_N], **kwargs: Any) -> None:
        assert isinstance(model, NodeModel), 'Model must be a subclass of NodeModel'

        super().__init__(model=model, **kwargs)

        self.currentChanged.connect(self.__watch_current_changed)
        self.selectionChanged.connect(self.__watch_selection_changed)

    def __to_index(self, index_or_node: Union[ModelIndex, _N, None]) -> ModelIndex:
        if index_or_node is None:
            return QModelIndex()
        elif isinstance(index_or_node, (QModelIndex, QPersistentModelIndex)):
            return index_or_node
        else:
            # A non-allowed None will be forwarded to NodeModel
            return self.node_model.index_for_node(index_or_node)

    # def connectNotify(self, signal):
    #     # from qtpy.QtCore import QMetaMethod
    #     # if signal == QMetaMethod.fromSignal(NodeSelectionModel.current_node_changed):
    #     meta = self.metaObject()
    #     print(str(meta.normalizedSignature('current_node_changed')))
    #     if signal == meta.method(meta.indexOfSignal(str(meta.normalizedSignature('current_node_changed')))):
    #         print('>>>', signal.name())

    # Model

    @override  # QItemSelectionModel
    def model(self) -> NodeModel[_N]:
        return cast(NodeModel[_N], super().model())

    @override  # QItemSelectionModel
    def setModel(self, model: Union[QAbstractItemModel, NodeModel[_N]]) -> None:
        assert isinstance(model, NodeModel), 'Model must be a subclass of NodeModel'

        super().setModel(model)

    @property
    def node_model(self) -> NodeModel[_N]:
        return self.model()

    @node_model.setter
    def node_model(self, model: NodeModel[_N]) -> None:
        self.setModel(model)

    # TODO: override modelChanged, just for type?

    # Current

    # clear_current_node = clearCurrentIndex
    clear_current_node = QItemSelectionModel.clearCurrentIndex
    # @Slot()
    # def clear_current_node(self) -> None:
    #     ...

    @property
    def current_node(self) -> _N:
        return self.node_model.node_for_index(self.currentIndex())

    @current_node.setter
    def current_node(self, node: _N) -> None:
        self.set_current_node(node, QItemSelectionModel.SelectionFlag.Select)

    @Slot(Node)
    def set_current_node(self, node: _N, command: QItemSelectionModel.SelectionFlag) -> None:
        self.setCurrentIndex(self.node_model.index_for_node(node), command)

    @Slot(QModelIndex, QModelIndex)
    def __watch_current_changed(self, current: QModelIndex, previous: QModelIndex) -> None:
        node_model = self.node_model
        try:
            previous_node = node_model.node_for_index(previous)
        except IndexError:  # Current Node was removed, and so the current moved
            previous_node = None

        self.current_node_changed.emit(
            node_model.node_for_index(current),
            previous_node,
        )

    # Actually, is (Node, Optional[Node])
    current_node_changed = Signal(Node, Node, arguments=['current', 'previous'])

    # Selection, get

    @override  # QItemSelectionModel
    def isColumnSelected(self, column: int, parent: Union[ModelIndex, _N, None] = None) -> bool:
        return super().isColumnSelected(column, self.__to_index(parent))

    @override  # QItemSelectionModel
    def isRowSelected(self, row: int, parent: Union[ModelIndex, _N, None] = None) -> bool:
        return super().isRowSelected(row, self.__to_index(parent))

    @override  # QItemSelectionModel
    def isSelected(self, index_or_node: Union[ModelIndex, _N]) -> bool:
        return super().isSelected(self.__to_index(index_or_node))

    def selected_columns(self, row: int = 0) -> Generator[_N, None, None]:
        return self.node_model.nodes_for_indexes(super().selectedColumns(row))

    def selected_nodes(self) -> Generator[_N, None, None]:
        return self.node_model.nodes_for_indexes(super().selectedIndexes())

    def selected_rows(self, column: int = 0) -> Generator[_N, None, None]:
        return self.node_model.nodes_for_indexes(super().selectedRows(column))

    @override  # QItemSelectionModel
    def selection(self) -> NodeSelection[_N]:
        return NodeSelection[_N](super().selection(), node_model=self.node_model)

    # Selection, set

    @override  # QItemSelectionModel
    @Slot(QItemSelection, QItemSelectionModel.SelectionFlag)
    @Slot(QModelIndex, QItemSelectionModel.SelectionFlag)
    @Slot(Node, QItemSelectionModel.SelectionFlag)
    @Slot(Iterable, QItemSelectionModel.SelectionFlag)
    def select(
        self,
        to_select: Union[QItemSelection, QModelIndex, _N, Iterable[_N]],
        command: QItemSelectionModel.SelectionFlag
    ) -> None:
        if isinstance(to_select, QItemSelection):
            super().select(to_select, command)
        elif isinstance(to_select, Iterable) and not isinstance(to_select, Node):
            selection = NodeSelection[_N](node_model=self.node_model)
            selection.nodes = to_select
            super().select(selection, command)
        else:
            super().select(self.__to_index(to_select), command)

    # TODO: Pythonic interface, like in NodeSelection?

    @Slot(QModelIndex, QModelIndex)
    def __watch_selection_changed(
        self,
        selected: QItemSelection,
        deselected: QItemSelection
    ) -> None:
        node_model = self.node_model
        self.selection_node_changed.emit((
            NodeSelection[_N](selected, node_model=node_model),
            NodeSelection[_N](deselected, node_model=node_model),
        ))

    # We have to mangle our NodeSelection instances behind a tuple
    # to avoid Qt detecting these are QItemSelection, and pass them around
    # by QItemSelection copy constructor... which strips away our NodeSelection type...
    # tuple[NodeSelection[N], NodeSelection[N]]
    selection_node_changed = Signal(tuple, arguments=['selected_deselected'])

    def __str__(self) -> str:
        return (
            f'{type(self).__name__}['
            f'current={self.current_node!s}, '
            f'selected={self.selection()!s}'
            ']'
        )

# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from functools import partial
from itertools import takewhile
from operator import is_not
from typing import TYPE_CHECKING, overload, TypeVar, Generic
# from weakref import ReferenceType

# Third-party imports
from qtpy.QtCore import Qt, QAbstractItemModel, QModelIndex, QPersistentModelIndex

# Local imports
from openide.utils.classes import QABC
from openide.utils.typing import override
from openide.nodes._like_netbeans import Node, NodeListener


_N = TypeVar('_N', bound=Node)

if TYPE_CHECKING:
    from collections.abc import Iterable, Generator
    from typing import Any, Optional, Union
    from typing_extensions import TypeAlias
    from qtpy.QtCore import QObject

    from openide.nodes._like_netbeans import NodeEvent, NodeMemberEvent, NodeReorderEvent, GenericNode
    from openide.explorer.selection import NodeSelectionModel

    ModelIndex: TypeAlias = Union[QModelIndex, QPersistentModelIndex]


class NodeModel(Generic[_N], NodeListener, QABC, QAbstractItemModel):

    def __init__(self, **kwargs: Any) -> None:
        self.__root: _N = Node.EMPTY  # TODO: Node.EMPTY is not necessarily a N
        # self.__explored_context: N = self.__root
        self.__shared_selection_model: Optional[NodeSelectionModel] = None
        super().__init__(**kwargs)

    # Node interface

    @property
    def root_node(self) -> _N:
        return self.__root

    @root_node.setter
    def root_node(self, node: Optional[_N]) -> None:
        if node is None:
            node = Node.EMPTY  # TODO: Node.EMPTY is not necessarily a N

        if node is self.__root:
            return

        def _remove_listener(current_node: _N) -> None:
            current_node.remove_node_listener(self)
            for child in current_node._children.get_nodes():
                _remove_listener(child)

        def _add_listener(current_node: _N) -> None:
            current_node.add_node_listener(self)  # Should be a weak ref
            for child in current_node._children.get_nodes():
                _add_listener(child)

        self.beginResetModel()
        try:
            _remove_listener(self.__root)

            self.__root = node
            _add_listener(self.__root)
        finally:
            self.endResetModel()
            pass

    # @property
    # def explored_context(self) -> N:
    #     return self.__explored_context

    # @explored_context.setter
    # def explored_context(self, node: Optional[N]) -> None:
    #     if node is None:
    #         node = self.root_node
    #     elif not self._is_under_root:
    #         raise ValueError(f'Explored context must be under the root node')

    #     if (selection_model := self.__shared_selection_model) is not None:
    #         selection_model.clear()

    #     if node is self.__explored_context:
    #         return

    #     # TODO: continue... Maybe do that with model proxy instead?

    # def _is_under_root(self, node: N) -> bool:
    #     root = self.__root
    #     while node is not None:
    #         if node is root:
    #             return True
    #         node = node.parent_node

    #     return False

    def node_for_index(self, index: ModelIndex) -> _N:
        if not index.isValid():
            return self.__root

        parent_node = self.__get_index_parent_node(index)
        to_return = parent_node._children.get_nodes()[index.row()]
        # print(f'node_for_index {index=} {parent_node=}, {to_return=}')
        return to_return

    def nodes_for_indexes(self, indexes: Iterable[ModelIndex]) -> Generator[_N, None, None]:
        node_for_index = self.node_for_index
        for index in indexes:
            yield node_for_index(index)

    def index_for_node(self, node: _N, column: int = 0) -> QModelIndex:
        if node is self.__root:
            return QModelIndex()

        parent_node = node.parent_node
        if parent_node is None:
            raise ValueError(f'{node=} has no parent')
        # print(f'index_for_node {node=} {parent_node=}')
        siblings = parent_node._children.get_nodes()
        # print(f'index_for_node {siblings=}')

        # Finding row by using list.index() does not work well
        # because it uses equality, and FeatureDescriptor redefines
        # equality (and hash) based on system_name only...
        # row = siblings.index(node)
        #
        # Instead, use a solution based on "is" identity.
        # To be faster than a plain loop (to be confirmed),
        # use itertools, functools and operator modules.
        predicate = partial(is_not, node)
        row = len(tuple(takewhile(predicate, siblings)))
        if row >= len(siblings):  # Not found
            raise RuntimeError(f'Could not find {node=} in {parent_node=} children')

        # print(f'index_for_node {row=}, {parent_node=}')
        return self.createIndex(row, 0, parent_node)

    @property
    def shared_selection_model(self) -> NodeSelectionModel[_N]:
        if (selection_model := self.__shared_selection_model) is None:
            selection_model = self.__shared_selection_model = self.make_selection_model()

        return selection_model

    def make_selection_model(self) -> NodeSelectionModel[_N]:
        from openide.explorer.selection import NodeSelectionModel

        return NodeSelectionModel[_N](model=self)

    # NodeListener

    def property_change(self, node: _N, name: str, old: Any, new: Any) -> None:
        if name == 'parentNode':
            return
        print(f'property_change {node=}, {name=}, {old=}, {new=}')

        if name == 'display_name':
            node_index = self.index_for_node(node)
            self.dataChanged.emit(
                node_index, node_index,
                [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]
            )

    def children_added(self, event: NodeMemberEvent) -> None:
        # print(f'children_added {event=}, {event.delta_indices=}')
        if not event.is_add_event:
            return

        parent_index = self.index_for_node(event.node)
        delta_indices = event.delta_indices
        # TODO: Handle discontinuous adds
        # print('Adding!', parent_index, delta_indices[0], delta_indices[-1])

        # TODO: Should be done before it is inserted in the model...
        # Otherwise, just keep snaptshots here? But that would be quite a duplication...
        # Also, even tougher to handle when indices are discontinuous...
        # Would need to have the model do its modifications in batches...
        # Which does not fit well with how child factory works neither
        self.beginInsertRows(parent_index, delta_indices[0], delta_indices[-1])
        self.endInsertRows()

        for node in event.delta:
            node.add_node_listener(self)  # Should be a weak ref

    def children_removed(self, event: NodeMemberEvent) -> None:
        # print(f'children_removed {event=}')
        if event.is_add_event:
            return

        parent_index = self.index_for_node(event.node)
        delta_indices = event.delta_indices
        # TODO: Handle discontinuous removes
        # print('Removing!', parent_index, delta_indices[0], delta_indices[-1])

        # TODO: Should be done before it is removed in the model...
        # Otherwise, just keep snapshots here? But that would be quite a duplication...
        # Also, even tougher to handle when indices are discontinuous...
        # Would need to have the model do its modifications in batches...
        # Which does not fit well with how child factory works neither
        self.beginRemoveRows(parent_index, delta_indices[0], delta_indices[-1])
        self.endRemoveRows()

        for node in event.delta:
            node.remove_node_listener(self)

    def children_reordered(self, event: NodeReorderEvent) -> None:
        # print(f'children_reordered {event=}')
        parent_node = event.node

        self.layoutAboutToBeChanged.emit()  # For unknown reasons, we cannot pass args

        self.changePersistentIndexList(*zip(*[
            # TODO: Should we support columns (eg. indexed node)?
            (self.createIndex(old, 0, parent_node), self.createIndex(new, 0, parent_node))
            for old, new in enumerate(event.permutation) if old != new
        ]))

        self.layoutChanged.emit()  # For unknown reasons, we cannot pass args

    def node_destroyed(self, event: NodeEvent) -> None:
        print(f'>>> node_destroyed {event=}')
        if event.node is self.root_node:
            self.root_node = Node.EMPTY
        else:
            ...  # TODO

    # Qt interface

    @override  # QAbstractItemModel
    def index(
        self,
        row: int,
        column: int,
        parent: Optional[ModelIndex] = None,
    ) -> QModelIndex:
        assert parent is not None
        # print(f'index {row=}, {column=}, {parent=}')

        parent_node = self.node_for_index(parent)
        to_return = self.createIndex(row, column, parent_node)
        # print(f'index {parent_node=}, {to_return=}')
        return to_return

    def __get_index_parent_node(self, index: ModelIndex) -> Node:
        return index.internalPointer()

    @overload
    def parent(self) -> QObject:
        ...

    @overload
    def parent(self, index: ModelIndex) -> QModelIndex:
        ...

    @override  # QObject,QAbstractItemModel
    def parent(self, index: Optional[ModelIndex] = None) -> Union[QObject, QModelIndex]:
        if index is None:
            return super().parent()
        else:
            parent_node = self.__get_index_parent_node(index)
            # print(f'parent {index=}, {parent_node=}')
            return self.index_for_node(parent_node, column=index.column())

    @override  # QAbstractItemModel
    def hasChildren(self, index: Optional[ModelIndex] = None) -> bool:
        assert index is not None
        # print(f'hasChildren {index=}')

        node = self.node_for_index(index)
        # print(f'hasChildren {index=} {node=}')
        return not node.is_leaf

    @override  # QAbstractItemModel
    def rowCount(self, index: Optional[ModelIndex] = None) -> int:
        assert index is not None
        # print(f'rowCount {index=}')

        node = self.node_for_index(index)
        # print(f'rowCount {index=} {node=}')
        count = node._children.get_nodes_count()
        # print(f'rowCount => {count}')
        return count

    @override  # QAbstractItemModel
    def columnCount(self, index: Optional[ModelIndex] = None) -> int:
        assert index is not None
        return 1  # TODO: Support IndexedNode?

    @override  # QAbstractItemModel
    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if section == 0:
            return 'Node'
        else:
            return None

    @override  # QAbstractItemModel
    def data(
        self,
        index: ModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        # print(f'data {index=}, {role=}')

        node = self.node_for_index(index)
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return node.display_name

        if role == Qt.ItemDataRole.DecorationRole:
            return node.icon

        return None

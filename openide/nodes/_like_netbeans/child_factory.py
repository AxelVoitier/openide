# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# From: https://github.com/apache/netbeans/blob/master/platform/openide.nodes/src/org/openide/nodes/ChildFactory.java  # noqa: E501

from __future__ import annotations

# System imports
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, final, Generic, TypeVar
from weakref import ReferenceType

# Third-party imports

# Local imports
from openide.utils.classes import Debug
from openide.nodes._like_netbeans.children import Children
from openide.nodes._like_netbeans.filter_node import FilterNode
from openide.nodes._like_netbeans.generic_node import GenericNode


T = TypeVar('T')
if TYPE_CHECKING:
    from collections.abc import Sequence, MutableSequence
    from typing import Optional, Any
    from openide.nodes._like_netbeans.node import Node


class ChildFactory(ABC, Generic[T], Debug(f'{__name__}.ChildFactory')):

    class Observer(ABC):
        @abstractmethod
        def refresh(self, immediate: bool) -> None:
            raise NotImplementedError()  # pragma: no cover

    class __WaitFilterNode(FilterNode):
        '''This class exists to mark any node returned by create_wait_node()
        such that AsyncChildren can identify it and not forward it to create_nodes_for_key()
        '''

    class __DefaultWaitNode(GenericNode):

        def __init__(self) -> None:
            super().__init__(Children.LEAF)

            self.icon_base_with_extension = 'TODO/wait.gif'
            self.display_name = 'Please Wait...'

        @property
        def actions(self):  # type: ignore[no-untyped-def]
            return tuple()

    def __init__(self) -> None:
        super().__init__()

        self.__observer_ref: Optional[ReferenceType[ChildFactory.Observer]] = None

    def _create_node_for_key(self, key: T) -> Optional[Node]:
        raise NotImplementedError(
            'Neither create_node_for_key() nor create_nodes_for_key() '
            f'have been overridden in {type(self).__name__}'
        )

    def _create_nodes_for_key(self, key: T) -> Optional[Sequence[Node]]:
        node = self._create_node_for_key(key)
        return (node, ) if node is not None else None

    @abstractmethod
    def _create_keys(self, to_populate: MutableSequence[T]) -> bool:
        raise NotImplementedError()  # pragma: no cover

    @final
    def _refresh(self, immediate: bool) -> None:
        if (observer := self.__observer) is not None:
            observer.refresh(immediate)

    @property
    def _wait_node(self) -> Optional[Node]:
        if (node := self._create_wait_node()) is not None:
            return ChildFactory.__WaitFilterNode(node)
        else:
            return None

    def _create_wait_node(self) -> Node:
        node = ChildFactory.__DefaultWaitNode()
        node.display_name = 'Please Wait...'
        node.icon_base_with_extension = 'openide/nodes/wait.gif'
        return node

    @property
    def __observer(self) -> Optional[ChildFactory.Observer]:
        if (observer_ref := self.__observer_ref) is not None:
            return observer_ref()
        else:
            return None

    @final
    def __set_observer(self, observer: ChildFactory.Observer) -> None:
        if self.__observer_ref is not None:
            raise RuntimeError(
                'Attempting to create two Children objects for a single '
                f'ChildFactory {type(self).__name__}. Use FilterNode.Children '
                'over the existing Children object instead'
            )

        self.__observer_ref = ReferenceType(observer)
    _observer = property(None, __set_observer, None)

    def _remove_notify(self) -> None:
        pass

    def _add_notify(self) -> None:
        pass

    def _destroy_nodes(self, nodes: Sequence[Node]) -> None:
        pass

    @staticmethod
    def _is_wait_node(node: Any) -> bool:
        return isinstance(node, ChildFactory.__WaitFilterNode)


# Note: Original ChildFactory.Detachable class seems... useless?!

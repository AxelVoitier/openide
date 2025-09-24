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
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar, final
from weakref import ReferenceType

# Third-party imports
# Local imports
from .children import Children
from .filter_node import FilterNode
from .generic_node import GenericNode
from .node import ANode

Key = TypeVar('Key')

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableSequence
    from typing import Final

    from PySide6.QtGui import QAction

__all__: Final = (
    'ChildFactory',
    'Key',
)

_logger = logging.getLogger(__name__)


class _ChildFactoryImplInterface(ABC, Generic[Key, ANode]):
    @abstractmethod
    # def _create_keys(self) -> Iterable[Key]:
    def _create_keys(self, to_populate: MutableSequence[K]) -> bool:
        raise NotImplementedError  # pragma: no cover

    def _create_node_for_key(self, key: Key) -> ANode | None:
        msg = (
            'Neither create_node_for_key() nor create_nodes_for_key() '
            f'have been overridden in {type(self).__name__}'
        )
        raise NotImplementedError(msg)

    def _create_nodes_for_key(self, key: Key) -> Iterable[ANode] | None:
        node = self._create_node_for_key(key)
        return (node,) if node is not None else None


class _ChildFactoryObserverInterface:
    class Observer(ABC):
        @abstractmethod
        def refresh(self, *, immediate: bool) -> None:
            raise NotImplementedError  # pragma: no cover

    def __init__(self, **kwargs: Any) -> None:
        self.__observer_ref: ReferenceType[ChildFactory.Observer] | None = None

        super().__init__(**kwargs)

    @final
    def _refresh(self, *, immediate: bool) -> None:
        if (observer := self.__observer) is not None:
            observer.refresh(immediate=immediate)

    @property
    def __observer(self) -> ChildFactory.Observer | None:
        if (observer_ref := self.__observer_ref) is not None:
            return observer_ref()
        else:
            return None

    @final
    def __set_observer(self, observer: ChildFactory.Observer) -> None:
        if self.__observer_ref is not None:
            msg = (
                'Attempting to create two Children objects for a single '
                f'ChildFactory {type(self).__name__}. Use FilterNode.Children '
                'over the existing Children object instead'
            )
            raise RuntimeError(msg)

        self.__observer_ref = ReferenceType(observer)

    _observer = property(None, __set_observer, None)


class _ChildFactoryWaitNode:
    class __WaitFilterNode(FilterNode[Any, Any]):
        """This class exists to mark any node returned by create_wait_node()
        such that AsyncChildren can identify it and not forward it to create_nodes_for_key()
        """

    class __DefaultWaitNode(GenericNode[Any, Any]):
        def __init__(self) -> None:
            super().__init__(Children.LEAF)

            self.icon_base_with_extension = 'TODO/wait.gif'
            self.display_name = 'Please Wait...'

        @property
        def actions(self) -> Iterable[QAction | str | None]:  # type: ignore[no-untyped-def]
            return ()

    @property
    def _wait_node(self) -> ANode | None:
        if (node := self._create_wait_node()) is not None:
            return ChildFactory.__WaitFilterNode(node)
        else:
            return None

    def _create_wait_node(self) -> ANode:
        node = ChildFactory.__DefaultWaitNode()
        node.display_name = 'Please Wait...'
        node.icon_base_with_extension = 'openide/nodes/wait.gif'
        return node

    @staticmethod
    def _is_wait_node(node: Any) -> bool:  # noqa: ANN401
        return isinstance(node, ChildFactory.__WaitFilterNode)


class _ChildFactoryUnknown:
    def _remove_notify(self) -> None:
        pass

    def _add_notify(self) -> None:
        pass

    def _destroy_nodes(self, nodes: Iterable[ANode]) -> None:
        pass


class ChildFactory(
    _ChildFactoryImplInterface[Key, ANode],
    _ChildFactoryWaitNode,
    _ChildFactoryUnknown,
    _ChildFactoryObserverInterface,
    Generic[Key, ANode],
):
    def __init__(self) -> None:
        super().__init__()

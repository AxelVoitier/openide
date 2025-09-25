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
from typing import TYPE_CHECKING, Any, Generic, TypeVar, final, override
from weakref import ReferenceType

# Third-party imports
# Local imports
from .children import ChildNode, Children
from .filter_node import FilterNode
from .generic_node import GenericNode

Key = TypeVar('Key')

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableSequence
    from typing import Final

    from PySide6.QtGui import QAction

    from .node import AnyNode

__all__: Final = (
    'ChildFactory',
    'ChildFactoryObserver',
    'Key',
)

_logger = logging.getLogger(__name__)


class _ChildFactorSubClassInterface(ABC, Generic[Key, ChildNode]):
    """Factory used to create Children objects.

    Children objects supply child Nodes for a Node. Usage is to write a class that
    extends ChildFactory and pass that to `Children.create()`. When the Node is expanded
    or its children are programmatically requested, the `_create_keys()` method will
    be invoked to create the list of objects to be modelled as Nodes.
    Later, on demand, each object from the list will be passed in turn to `_create_nodes_for_key()`,
    which may return an array of zero or more Nodes for the object.

    A ChildFactory can be used either to create typical Children object, or one
    which will be initialised on a background thread (providing a "Please Wait"
    Node in the meantime). It can be used in most simple cases that ChildrenKeys
    has been historically used for, and makes it easy to change a Children object
    to compute its keys asynchronously if that is needed for performance reasons.

    Only one ChildFactory object may be used per Children object; if you wish to
    have multiple Nodes modelling children produced by a single ChildFactory,
    use FilterNode to wrap the Node that owns the Children object for this ChildFactory.

    To use, simply override `_create_keys()`, and either `_create_nodes_for_key()`
    or `_create_node_for_key()`.

    Args:
        Key: The type of objects in the keys collection.
        ChildNode: The type of Node this factory will create.
    """

    @abstractmethod
    # def _create_keys(self) -> Iterable[Key]:
    def _create_keys(self, to_populate: MutableSequence[Key]) -> bool:
        """Create a list of keys which can be individually passed to `_create_nodes_for_key()`
        to create child Nodes.

        Implementation of this method should regularly check Thread.interrupted(),
        and if it returns True (meaning the parent Node was collapsed or destroyed),
        stop creating keys immediatelyand return True. This method guaranteed *not*
        to be called on the event thread if this ChildFactory was passed to
        `Children.create()` with the `asynchronous` parameter set to True. If not,
        then no guarantees are mde as to what the calling thread is.

        Returning False is tricky since there is no way to tell whether the loop
        has been restarted except by examining what is already in the list. It is
        generally unnecessary since calls to list.append() will immediately display
        the new element as well as checking for interruption.


        Args:
            to_populate: A list to add key objects to.

        Returns:
            True if the list of keys has been completely populated. Or False if
            the list has only been partially populated and this method should be
            called again to batch more keys.
        """

        raise NotImplementedError  # pragma: no cover

    def _create_node_for_key(self, key: Key) -> ChildNode | None:
        """Create a Node for a given key that was put into the list passed into `_create_keys()`.

        Either override this method if there will always be 0 or 1 nodes per key,
        or `_create_nodes_for_key()` it there may be more than one.

        The default implementation throws a NotImplementedError. If you override
        `_create_nodes_for_key()` and do not call super(), then you do not need
        to override this method; but at least one of the two must be overridden.

        Args:
            key: An object that was previously put into the list returned by `_create_keys()`.

        Returns:
            A node, or None if no node should be shown for this object.
        """

        msg = (
            'Neither create_node_for_key() nor create_nodes_for_key() '
            f'have been overridden in {type(self).__name__}'
        )
        raise NotImplementedError(msg)

    def _create_nodes_for_key(self, key: Key) -> Iterable[ChildNode] | None:
        """Create Nodes for a given key object (one from the list passed to `_create_keys()`).

        The default implementation simply delegates to `_create_node_for_key()`
        and returns the result of that call in an array of nodes.

        Most Children objects have a 1:1 mapping between keys and nodes. For
        convenience in that situation, simply override `_create_node_for_key()`.

        Args:
            key: An object from the list returned by `_create_keys()`.

        Returns:
            None if no nodes, or zero or more Nodes to represent this key.
        """

        node = self._create_node_for_key(key)
        return (node,) if node is not None else None

    def _refresh(self, *, immediate: bool) -> None:
        """Call this method when the list of objects being modelled by the factory
        has changed, and the child Nodes should be updated.

        The boolean argument `immediate` is a *hint* to the refresh mechanism
        (which will cause _create_keys() to be invoked again) that it is safe to
        synchronously recreate.

        Args:
            immediate: If True, the refresh should occur in the calling thread
                (be careful not to be holding any lock that might deadlock with your
                key/child creation methods of you pass True).
                Note that this parameter is only meaningful when using an asynchronous
                children instance (ie. True was passed as the second parameter to
                `Children.create()`). If the Children object for this ChildFactory is
                called with `immediate=True` on the event dispatch thread, and it is
                an asynchronous Children object, this parameter will be ignored, and
                computation will be scheduled on a background thread.
        """

        # Implemented in _ChildFactoryObserverInterface

    def _add_notify(self) -> None:
        """Called immediately before the first call to `_create_keys()`.

        Override to set up listening for changes, allocating expensive-to-create
        resources, etc.
        """

    def _remove_notify(self) -> None:
        """Called when this ChildFactory is no longer in memory.

        Does nothing by default; override if you need notification when not in
        use anymore.

        Note that this is usually not the best place for unregistering listeners, etc.,
        as listeners might keep the child nodes in memory, preventing them from
        being collected, and thus preventing this method to be called in the first place.
        """

    def _destroy_nodes(self, nodes: Iterable[ChildNode]) -> None:
        """Called when the nodes have been removed from the children.

        This method should allow subclasses to clean the nodes, somehow.

        Args:
            nodes: Iterable of deleted nodes.
        """


class ChildFactoryObserver(ABC):
    @abstractmethod
    def refresh(self, *, immediate: bool) -> None:
        raise NotImplementedError  # pragma: no cover


class _ChildFactoryObserverInterface(_ChildFactorSubClassInterface[Key, ChildNode]):
    def __init__(self, **kwargs: Any) -> None:
        self.__observer_ref: ReferenceType[ChildFactoryObserver] | None = None

        super().__init__(**kwargs)

    @final
    @override
    def _refresh(self, *, immediate: bool) -> None:
        if (observer := self.__observer) is not None:
            observer.refresh(immediate=immediate)

    @property
    def __observer(self) -> ChildFactoryObserver | None:
        if (observer_ref := self.__observer_ref) is not None:
            return observer_ref()
        else:
            return None

    @final
    def __set_observer(self, observer: ChildFactoryObserver) -> None:
        if self.__observer_ref is not None:
            msg = (
                'Attempting to create two Children objects for a single '
                f'ChildFactory {type(self).__name__}. Use FilterNode.Children '
                'over the existing Children object instead'
            )
            raise RuntimeError(msg)

        self.__observer_ref = ReferenceType(observer)

    _observer = property(None, __set_observer, None)


class _ChildFactoryWaitNode(Generic[ChildNode]):
    class __WaitFilterNode(FilterNode[Any, Any]):
        """This class exists to mark any node returned by `_create_wait_node()`
        such that AsyncChildren can identify it and not forward it to `_create_nodes_for_key()`.
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
    def _wait_node(self) -> ChildNode | None:
        if (node := self._create_wait_node()) is not None:
            return _ChildFactoryWaitNode.__WaitFilterNode(node)
        else:
            return None

    def _create_wait_node(self) -> ChildNode | None:
        """Create the Node that should be shown while the keys are being computed
        on a background thread.

        This method will not be called if this ChildFactory is used for a synchronous
        children which does not compute its keys on a background thread. Whether
        an instance is synchronous or not is determined by a parameter to `Children.create()`.

        To show no node at all when the Children object is initially expanded in
        the UI, simply return None.

        The default implementation returns a Node that shows an hourglass cursor
        and the text "Please Wait...".

        Returns:
            A Node, or None if no wait node should be shown.
        """

        node = _ChildFactoryWaitNode.__DefaultWaitNode()
        node.display_name = 'Please Wait...'
        node.icon_base_with_extension = 'openide/nodes/wait.gif'
        return node  # pyright: ignore[reportReturnType]

    @staticmethod
    def _is_wait_node(node: AnyNode) -> bool:
        return isinstance(node, ChildFactory.__WaitFilterNode)


class ChildFactory(
    _ChildFactoryWaitNode[ChildNode],
    _ChildFactoryObserverInterface[Key, ChildNode],
    _ChildFactorSubClassInterface[Key, ChildNode],
    Generic[Key, ChildNode],
):
    def __init__(self) -> None:
        super().__init__()

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
from threading import RLock
from typing import TYPE_CHECKING, Generic, TypeVar, final

# Third-party imports
from typing_extensions import override

# Local imports
from openide.utils import Mutex

# Second Any should be our own ChildNode
ANode = TypeVar('ANode', bound='_NodeChildrenInterface[Any, Any]')
# First Any should be our own ANode
ChildNode = TypeVar('ChildNode', bound='_NodeChildrenInterface[Any, Any]')

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, MutableSequence, Sequence
    from typing import Any, ClassVar, Final

    from typing_extensions import Self

    from .child_factory import ChildFactory
    from .children_implementations import _Empty
    from .entry_support import EntrySupport
    from .node import _NodeChildrenInterface

    T = TypeVar('T')

__all__: Final = (
    'Children',
    'ChildrenEntry',
)

_logger = logging.getLogger(__name__)


class ChildrenEntry(ABC, Generic[ChildNode]):
    """Interface that provides a set of nodes"""

    @abstractmethod
    def nodes(self, source: Any) -> MutableSequence[ChildNode]:  # noqa: ANN401
        """Set of nodes associated with this entry"""

        raise NotImplementedError  # pragma: no cover


class _ChildrenBase(Generic[ANode, ChildNode]):
    MUTEX: ClassVar = Mutex()
    """Lock for access to hierarchy of all node lists.

    Anyone who needs to ensure that there will not be shared accesses to hierarchy
    nodes can use this mutex.

    All operations on the hierarchy of nodes (add, remove, etc.) are done in the
    Mutex.write_access() method of this lock. So if someone needs for a certain
    amount of time to forbid modification, they can execute their code in Mutex.read_access().
    """

    _LOCK: ClassVar = RLock()  # Class lock

    def __init__(self, *, _lazy: bool = False) -> None:
        self._lock = RLock()  # Instance lock
        self._lazy_support = _lazy

        super().__init__()

    # OK, Match
    @property
    def _is_lazy(self) -> bool:
        return self._lazy_support

    if TYPE_CHECKING:
        # Following methods are defined in _ChildrenEntrySupportInterface
        @property
        def _entry_support(self) -> EntrySupport[ANode, ChildNode]: ...
        @property
        def _entry_support_raw(self) -> EntrySupport[ANode, ChildNode] | None: ...
        @_entry_support_raw.setter
        def _entry_support_raw(self, value: EntrySupport[ANode, ChildNode] | None) -> None: ...

        # Following methods are defined in _ChildrenSubClassInterface
        def remove(self, nodes: Sequence[ChildNode]) -> bool: ...  # Needed in Node.destroy()
        def _check_support(self) -> None: ...
        def _add_notify(self) -> None: ...
        def _destroy_nodes(
            self,
            nodes: Iterable[ChildNode],
        ) -> None: ...  # used in EntrySupportDefault._notify_remove()
        def _remove_notify(self) -> None: ...


class _ChildrenSubClassInterface(ABC, Generic[ChildNode]):
    # NB: As understood from the various Children implementations, these add() and remove()
    # interfaces are remanent from an old, simplistic behaviour pretty much suitable only
    # for ChildrenArray.
    # --> Set to dissapear in _refactor2, most likely.

    @abstractmethod
    def add(self, nodes: Sequence[ChildNode]) -> bool:
        """Add nodes to this container.

        Do NOT call this method. If you think you need to do this, you probably
        actually want to use ChildrenKeys._set_keys() instead.

        The parent node of these nodes is changed to the parent node of this container.
        Each node can be added only once. If there are some reason a node cannot
        be added, for example if the parent node expects only a special typo of
        child nodes, this method should do nothing and return False to signal that
        the addition has not been successfull.

        This method should be implemented by subclasses to filter some nodes, etc.

        Args:
            nodes: Set of nodes to add to the container.

        Returns:
            bool: True if successfully added. False otherwise.
        """

        raise NotImplementedError

    @abstractmethod
    def remove(self, nodes: Sequence[ChildNode]) -> bool:
        """Remove nodes from the list.

        Only nodes that are present are removed.

        Args:
            nodes: Set of nodes to be removed.

        Returns:
            bool: True if the nodes could be removed. False otherwise.
        """

        raise NotImplementedError

    # Theory: ChildrenKeys._check_support() implementation kind-of point us toward the idea that
    # this is part of ensuring compatibility with a legacy ChildrenArray interface.
    #
    # OK, Match
    def _check_support(self) -> None:
        pass

    # OK, Match
    def _add_notify(self) -> None:
        """Called when children are first asked for nodes.

        Typical implementation at this time calculate their node list (or keys for
        ChildrenKeys, etc.).

        NB: Call to get_nodes() inside of this method will return an empty array of nodes.
        """

    # OK, Match
    def _destroy_nodes(self, nodes: Iterable[ChildNode]) -> None:
        """Called when the nodes have been removed from the children.

        This method should allow subclasses to clean the nodes, somehow.
        Current implementations notifies all listeners on the nodes that nodes
        have been deleted.

        Args:
            nodes: Iterable of deleted nodes.
        """

    # OK, Match
    def _remove_notify(self) -> None:
        """Called when all children nodes have been freed from memory.

        Typical implementation at this time clear all the keys (in case of ChildrenKeys
        for instance).

        Note that this is usually not the best place for unregistering listeners, etc.,
        as listeners might keep the child nodes in memory, preventing them from
        being collected, and thus preventing this method to be called in the first place.
        """


class _ChildrenParentNodeInterface(_ChildrenBase[ANode, ChildNode]):
    def __init__(self, **kwargs: Any) -> None:
        self._parent: ANode | None = None
        """Parent node for all nodes in this list"""

        super().__init__(**kwargs)

    @property
    def node(self) -> ANode | None:
        """The parent node of these children, or none if they are detached"""

        return self._parent

    # OK, Match
    @final
    def _attach_to(self, parent: ANode) -> None:
        """Setter of parent node for this list of children.

        Each children in the list will have this node set as parent. The parent
        node will return nodes in this list as its children.

        This method is called from the Node constructor.

        Args:
            parent: The node to attach to.

        Raises:
            RuntimeError: When this object is already used with a different node.
        """

        # Special treatment for LEAF object
        if self is Children[ANode, ChildNode].LEAF:
            # Do not attach the node because the LEAF cannot have children
            return

        with self._lock:
            if self._parent is not None:
                msg = 'An instance of Children may not be used for more than one parent node'
                raise RuntimeError(msg)

            self._parent = parent

        # Do not get Children.MUTEX if not necessary
        nodes = self.__test_nodes()
        if not nodes:
            return

        # This is the only place where parent is changed, but only under read_access()
        # => Double check if it happened correctly.
        with Children.MUTEX.read_access():
            nodes = self.__test_nodes()
            if not nodes:
                return

            for i, node in enumerate(nodes):
                node._assign_to(self, i)
                node._fire_own_property_change('parentNode', None, parent)

    # OK, Match
    @final
    def _detach_from(self) -> None:
        """Called when node changes it's children to different nodes.

        Raises:
            RuntimeError: If the children were already detached.
        """

        # Special treatment for LEAF object
        if self is Children[ANode, ChildNode].LEAF:
            # Nothing to do
            return

        with self._lock:
            if (old_parent := self._parent) is None:
                msg = 'Trying to detach children which do not have parent'
                raise RuntimeError(msg)

            self._parent = None

        with Children.MUTEX.read_access():
            nodes = self.__test_nodes()
            if not nodes:
                return

            for node in nodes:
                node._deassign_from(self)
                node._fire_own_property_change('parentNode', old_parent, None)

    # OK, Match
    @final
    def snapshot(self) -> Sequence[ChildNode]:
        """Creates an immutable snapshot representing the current view of the nodes.

        There are no attempt to remove incorrect or invalid nodes from the list.
        As a result, the value may not be exactly the same as returned by get_nodes().

        Returns:
            An immutable sequence of nodes in this Children object.
        """
        return self._entry_support._snapshot()

    # OK, Match
    # TODO: __len__? (Using the False default for optimal)
    # Or just let client code do len(children.nodes) or len(children.nodes_optimal)?
    # Note: getNodesCount() is final, but getNodesCount(optimalResult) is not.
    def get_nodes_count(self, *, optimal_result: bool = False) -> int:
        """Get the number of nodes in the list.

        Args:
            optimal_result: Whether to try to perform a full initialisation.

        Returns:
            The count.
        """

        self._check_support()
        return self._entry_support.get_nodes_count(optimal_result=optimal_result)

    # OK, Match
    @property
    @final
    def _is_initialised(self) -> bool:
        """Tests whether the children content has ever been used or it is still not initialised"""

        return self._entry_support.is_initialised

    # OK, Match
    def __test_nodes(self) -> Sequence[ChildNode] | None:
        """Returns either nodes associated with this children, or None if they are not created."""

        if (entry_support := self._entry_support_raw) is not None:
            # Note: Compared to original, we are skipping the getter, sparing us a lock acquisition
            return entry_support.test_nodes()
        else:
            return None


# Needs to subclass _ChildrenParentNodeInterface because ChildrenStorage pass us
# around from an EntrySupport to a Node.
class _ChildrenEntrySupportInterface(_ChildrenParentNodeInterface[ANode, ChildNode]):
    def __init__(self, **kwargs: Any) -> None:
        self.__entry_support: EntrySupport[ANode, ChildNode] | None = None
        """Access to entries/nodes"""

        super().__init__(**kwargs)

    # OK, Match
    @property
    @override
    def _entry_support(self) -> EntrySupport[ANode, ChildNode]:
        """Initialises entry support if needed"""

        with Children._LOCK:
            if (entry_support := self._entry_support_raw) is None:
                if self._lazy_support:
                    raise NotImplementedError
                    from openide.nodes._like_netbeans.entry_support_lazy import EntrySupportLazy  # noqa: I001, PLC0415

                    entry_support = EntrySupportLazy(self)
                else:
                    from .entry_support_default import (  # noqa: PLC0415
                        EntrySupportDefault,
                    )

                    entry_support = EntrySupportDefault(self)

                self._entry_support_raw = entry_support
                self._post_init_entry_support(entry_support)

            return entry_support

    # OK, Match
    def _post_init_entry_support(self, entry_support: EntrySupport[ANode, ChildNode]) -> None:
        """Let a subclass do further initialisation of entry support.

        It is called just once, under internal lock so subclasses should behave sanely.
        """

    # OK, Match
    @property
    @override
    def _entry_support_raw(self) -> EntrySupport[ANode, ChildNode] | None:
        """The entry support, without attempt to initialise it first"""
        return self.__entry_support

    # OK, Match
    @_entry_support_raw.setter
    @final
    def _entry_support_raw(self, value: EntrySupport[ANode, ChildNode] | None) -> None:
        assert Children._LOCK._is_owned()  # type: ignore[attr-defined]
        self.__entry_support = value

    # OK, Match
    def find_child(self, system_name: str | None) -> ChildNode | None:
        """Find a child by name.

        This may be overridden in subclasses to provide more advanced way of finding
        the child. But the default implementation simply scans through the list
        of nodes to find the first one with the requested name.

        Normally, the list of nodes should have been computed by the time this
        returns, but see get_nodes() for an important caveat as to why this may
        not be doing what you want, and what to do instead.

        Args:
            system_name: System name of child node to find, or None if any
                         arbitrary child may be returned.
        Returns:
            The node, or None if it could not be found.
        """

        nodes = self.get_nodes()

        if not nodes:
            return None

        if system_name is None:
            return nodes[0]

        for node in nodes:
            if node.system_name == system_name:
                return node

        return None

    # OK, Match
    # TODO: __getitem__?
    @final
    def get_node_at(self, index: int) -> ChildNode | None:
        """Getter for a child at a given position.

        If child with such index does not exists, it returns None.
        """

        self._check_support()
        return self._entry_support.get_node_at(index)

    # OK, Match
    # TODO: Transform into 2 properties, "nodes" (final), and "nodes_optimal" (or something
    # like that). Potentially propagate to EntrySupport (and all its implementations).
    # Note: getNodes() is final, but getNodes(optimalResult) is not.
    def get_nodes(self, *, optimal_result: bool = False) -> Sequence[ChildNode]:
        """Get a (sorted) array of nodes in this list.

        If the children object is not yet initialised, it will be (using _add_notify())
        before the nodes are returned.

        WARNING: If optimal_result is False (default), not all children implementations
                 will do a complete calculation at this point.

        If you are extending Children, you should make sure this method will return
        a complete list of nodes if optimal_result is True. The default implementation
        will do this correctly so long as your subclass implements find_child(None)
        to initialise all subnodes.

        NOTE: You should not call this method from inside Children.MUTEX.read_access().
              If you do so, the Node will be unable to update its state before you
              leave the read_access().

        Args:
            optimal_result: Whether to try to get a fully initialised array.

        Returns:
            Sequence of nodes.
        """

        self._check_support()
        return self._entry_support.get_nodes(optimal_result=optimal_result)

    # OK, Match
    def _call_add_notify(self) -> None:
        """Method that can be overridden by subclasses to do additional work,
        and then call add_notify()."""

        self._add_notify()

    # OK, Match
    def _call_remove_notify(self) -> None:
        self._remove_notify()


class _ChildrenUnknown(Generic[ANode, ChildNode]):
    # OK, Match
    @final
    def _get_snapshot_indexes(self, snapshot: Sequence[ChildNode]) -> Sequence[int]:
        return list(range(len(snapshot)))  # Seriously? Java needs a 4 lines function for that??


class Children(
    _ChildrenSubClassInterface[ChildNode],
    _ChildrenEntrySupportInterface[ANode, ChildNode],
    _ChildrenParentNodeInterface[ANode, ChildNode],
    _ChildrenUnknown[ANode, ChildNode],
    _ChildrenBase[ANode, ChildNode],
    Generic[ANode, ChildNode],
):
    """Factory for the child Nodes of a Node.

    Every Node has a Children object.
    Children are initially un-initialised, and child Nodes are created on demand
    when, for example, the Node is expanded in an Explorer view.
    If you know your Node has no child nodes, pass `Children.LEAF`.
    Typically, a Children object will create a Collection of objects from some
    data model, and create one or more Nodes for each object on demand.

    If initialising the list of children of a Node is time-consuming (ie. it does
    I/O, parses a file, or some other expensive operation), implement ChildFactory
    and pass it to `Children.create(the_factory, True)` to have the child nodes be
    computed asynchronously on a background thread.

    In almost all cases youwant to subclass ChildFactory and pass it to `Children.create()`,
    or subclass ChildrenKeys. Subclassing Children directly is not recommended.

    Args:
        ParentNode: The type of those children parent node.
        ChildNode: The type of node those children have.
    """

    LEAF: ClassVar[_Empty]
    """The object representing an empty set of children.

    Should be used to represent the children of leaf nodes. The same object may
    be used by all such nodes.
    """

    Array: type[Array] = None  # type: ignore[assignment]
    SortedArray: type[SortedArray] = None  # type: ignore[assignment]
    Map: type[Map] = None  # type: ignore[assignment]
    Keys: type[Keys] = None  # type: ignore[assignment]

    # OK, Match
    @staticmethod
    def create(
        factory: ChildFactory[T, ChildNode],
        *,
        asynchronous: bool,
    ) -> Children[ANode, ChildNode]:
        """Create a Children object using the passed ChildFactory object.

        The ChildFactory will be asked to create a list of arbitrary model objects
        (aka keys) that are the children; then for each object in the list,
        ChildFactory._create_nodes_for_key() will be called to instantiate one or
        more Node for each modeel object.

        Args:
            factory: A factory which will provide child objects.
            asynchronous: If True, the factory will always be called to create the list of keys on
                          a background thread, displaying a "Please Wait" child node util some or
                          all child nodes have been computed.
                          Pass True for any case where computing child nodes is expensive and
                          should not be done in the event thread.

        Returns:
            A children object which will invoke the factory instance as needed to
            supply model objects and child nodes for it.

        Raises:
            RuntimeError: If the passed factory has already been used in a previous
                          call to this method.
        """

        children: Children[ANode, ChildNode]
        if not asynchronous:
            from .sync_children import SyncChildren  # noqa: PLC0415

            children = SyncChildren(factory)

        else:
            raise NotImplementedError
            from .async_children import AsyncChildren  # noqa: PLC0415

            children = AsyncChildren(factory)

        factory._observer = children

        return children

    # OK, Match
    @staticmethod
    def create_lazy(
        factory_cb: Callable[[], Children[ANode, ChildNode]],
    ) -> Children[ANode, ChildNode]:
        """Create a lazy children implementation.

        Args:
            factory: The callable which is called when node's children are really needed.

        Returns:
            Provides a lazy children implementation that can be passed to Node
            constructor, and thus allows the client code to decide what children
            the node should have when the callable is called.
        """

        from .children_implementations import _LazyChildren  # noqa: PLC0415

        return _LazyChildren(factory_cb)

    def __init__(self, *, _lazy: bool = False) -> None:
        super().__init__(_lazy=_lazy)

    # TODO: Review
    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        """
        Subclasses should first call super().__deepcopy__() to get
        an instance. And then call their own SubClass.__init__(instance, ...)
        (or do the initialisation in __deepcopy__ as they see fit).

        Subclasses that don't want to be cloned should overload
        and just return Children.LEAF.
        """

        new = Children.__new__(type(self))
        Children[ANode, ChildNode].__init__(new, _lazy=self._lazy_support)

        return new


# Needed to let these implementations provision their "scope shortcut" into the main Children class
# TODO: Just get rid of these shortcuts...
from . import children_array, children_implementations, children_keys, children_map  # pyright: ignore[reportUnusedImport]  # noqa: E402, F401, I001

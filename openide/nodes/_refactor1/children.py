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
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, final

# Third-party imports
# Local imports
from openide.utils import Mutex

ParentNode = TypeVar('ParentNode', bound='_NodeChildrenInterface[Any, Any]')
ChildNode = TypeVar('ChildNode', bound='_NodeChildrenInterface[Any, Any]')

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, MutableSequence, Sequence
    from typing import Final, Self

    from .child_factory import ChildFactory
    from .children_implementations import _Empty
    from .entry_support import EntrySupport
    from .node import AnyNode, _NodeChildrenInterface

    T = TypeVar('T')

__all__: Final = (
    'Children',
    'ChildrenEntry',
)

_logger = logging.getLogger(__name__)


class ChildrenEntry(ABC, Generic[ChildNode]):
    @abstractmethod
    def nodes(self, source: Any) -> MutableSequence[ChildNode]:  # noqa: ANN401
        raise NotImplementedError  # pragma: no cover


class _ChildrenLock:
    MUTEX: ClassVar = Mutex()
    _LOCK: ClassVar = RLock()  # Class lock

    def __init__(self, **kwargs: Any) -> None:
        self._lock = RLock()  # Instance lock

        super().__init__(**kwargs)


class _ChildrenCopy(Generic[ParentNode, ChildNode]):
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
        Children[ParentNode, ChildNode].__init__(new, _lazy=self._lazy_support)

        return new


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

        NB: Call to get_nodes() inside of thi method will return an empty array of nodes.
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


class _ChildrenParentNodeInterface(_ChildrenLock, Generic[ParentNode, ChildNode]):
    def __init__(self, **kwargs: Any) -> None:
        self._parent: ParentNode | None = None

        super().__init__(**kwargs)

    @property
    def node(self) -> ParentNode | None:
        return self._parent

    # OK, Match
    @final
    def _attach_to(self, parent: ParentNode) -> None:
        if self is Children[ParentNode, ChildNode].LEAF:
            return

        with self._lock:
            if self._parent is not None:
                msg = 'An instance of Children may not be used for more than one parent node'
                raise RuntimeError(msg)

            self._parent = parent

        nodes = self.__test_nodes()
        if not nodes:
            return

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
        if self is Children[ParentNode, ChildNode].LEAF:
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
        return self._entry_support._snapshot()

    # OK, Match
    # TODO: __len__? (Using the False default for optimal)
    # Or just let client code do len(children.nodes) or len(children.nodes_optimal)?
    # Note: getNodesCount() is final, but getNodesCount(optimalResult) is not.
    def get_nodes_count(self, *, optimal_result: bool = False) -> int:
        self._check_support()
        return self._entry_support.get_nodes_count(optimal_result=optimal_result)

    # OK, Match
    @property
    @final
    def _is_initialised(self) -> bool:
        return self._entry_support.is_initialised

    # OK, Match
    def __test_nodes(self) -> Sequence[ChildNode] | None:
        """Returns either nodes associated with this children, or None if they are not created."""

        if (entry_support := self._ChildrenEntrySupport__entry_support) is not None:
            # Note: Compared to original, we are skipping the getter, sparing us a lock acquisition
            return entry_support.test_nodes()
        else:
            return None


class ChildrenEntrySupport(Generic[ParentNode, ChildNode]):
    def __init__(self, **kwargs: Any) -> None:
        self.__entry_support: EntrySupport[ParentNode, ChildNode] | None = None

        super().__init__(**kwargs)

    # OK, Match
    @property
    def _entry_support(self) -> EntrySupport[ParentNode, ChildNode]:
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
    def _post_init_entry_support(self, entry_support: EntrySupport[ParentNode, ChildNode]) -> None:
        pass

    # OK, Match
    @property
    def _entry_support_raw(self) -> EntrySupport[ParentNode, ChildNode] | None:
        return self.__entry_support

    # OK, Match
    @_entry_support_raw.setter
    @final
    def _entry_support_raw(self, value: EntrySupport[ParentNode, ChildNode] | None) -> None:
        assert Children._LOCK._is_owned()  # type: ignore[attr-defined]
        self.__entry_support = value

    # OK, Match
    def find_child(self, system_name: str | None) -> ChildNode | None:
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
        self._check_support()
        return self._entry_support.get_node_at(index)

    # OK, Match
    # TODO: Transform into 2 properties, "nodes" (final), and "nodes_optimal" (or something
    # like that). Potentially propagate to EntrySupport (and all its implementations).
    # Note: getNodes() is final, but getNodes(optimalResult) is not.
    def get_nodes(self, *, optimal_result: bool = False) -> Sequence[ChildNode]:
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


class _ChildrenUnknown(Generic[ParentNode, ChildNode]):
    # OK, Match
    @final
    def _get_snapshot_indexes(self, snapshot: Sequence[ChildNode]) -> Sequence[int]:
        return list(range(len(snapshot)))  # Seriously? Java needs a 4 lines function for that??


class Children(
    _ChildrenSubClassInterface[ChildNode],
    _ChildrenParentNodeInterface[ParentNode, ChildNode],
    ChildrenEntrySupport[ParentNode, ChildNode],
    _ChildrenUnknown[ParentNode, ChildNode],
    _ChildrenCopy[ParentNode, ChildNode],
    _ChildrenLock,
    Generic[ParentNode, ChildNode],
):
    LEAF: ClassVar[_Empty[AnyNode]]
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
    ) -> Children[ParentNode, ChildNode]:
        children: Children[ParentNode, ChildNode]
        if not asynchronous:
            from .sync_children import SyncChildren  # noqa: PLC0415

            children = SyncChildren(factory)

        else:
            from .async_children import AsyncChildren  # noqa: PLC0415

            children = AsyncChildren(factory)

        factory._observer = children

        return children

    # OK, Match
    @staticmethod
    def create_lazy(
        factory_cb: Callable[[], Children[ParentNode, ChildNode]],
    ) -> Children[ParentNode, ChildNode]:
        from .children_implementations import _LazyChildren  # noqa: PLC0415

        return _LazyChildren(factory_cb)

    def __init__(self, *, _lazy: bool = False) -> None:
        self._lazy_support = _lazy

        super().__init__()

    # OK, Match
    @property
    def _is_lazy(self) -> bool:
        return self._lazy_support


from . import children_implementations, children_array, children_keys, children_map

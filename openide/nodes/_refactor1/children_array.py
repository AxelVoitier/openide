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

# DEV NOTES:
# - Even if Netbeans consider it deprecated, or legacy, consider keeping it for it simplicity.
# - Bloating features to probably remove:
#   - Passing an instance of the backing collection in the constuctor:
#       In theory it shouldn't even contain any node (but seems to work when prepopulated).
#       If a user has specific need for the type of the backing collection they should
#       subclass instead.
#       Can't even use a tuple for a static list of child nodes, or a set,
#       because it wants a mutable sequence specifically.
#       => Would their actually be a need to make a tuple or set backed Children?
# - Could try to support a way to do reordering without removing first, somehow
# - NB BUG #1 affects ChildrenArray: https://github.com/AxelVoitier/openide/issues/1
# - NB BUG #2: https://github.com/AxelVoitier/openide/issues/2

from __future__ import annotations

# System imports
import logging
from threading import RLock
from typing import TYPE_CHECKING, Generic, final

# Third-party imports
from typing_extensions import override

# Local imports
from .children import (
    ANode,
    ChildNode,
    Children,
    ChildrenEntry,
    _ChildrenEntrySupportInterface,
    _ChildrenSubClassInterface,
)

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, MutableSequence, Sequence
    from typing import Any, Final

    from typing_extensions import Self

    from .entry_support import EntrySupport

__all__: Final = (
    'ChildrenArray',
    'SortedChildrenArray',
)

_logger = logging.getLogger(__name__)


# OK, Match
class _ArrayEntry(ChildrenEntry[ChildNode], Generic[ANode, ChildNode]):
    """One entry that holds all the nodes in the collection"""

    def __init__(self, array: _ChildrenArrayBase[ANode, ChildNode]) -> None:
        super().__init__()
        self._array = array

    # OK, Match
    @override  # ChildrenEntry
    def nodes(self, source: Any) -> MutableSequence[ChildNode]:
        if not (collection := self._array._collection):
            return []
        else:
            with ChildrenArray._COLLECTION_LOCK:
                return list(collection)


class _ChildrenArrayBase(Children[ANode, ChildNode]):
    _COLLECTION_LOCK = RLock()

    # OK, Match
    def __init__(self, *, _nodes: MutableSequence[ChildNode] | None, _lazy: bool) -> None:
        if _nodes is not None:
            # Match original behaviour of protected constructors
            _lazy = False

        super().__init__(_lazy=_lazy)

        self._nodes_entry: ChildrenEntry[ChildNode] | None = None
        """The entry used for all nodes in the following collection"""

        if not _lazy:
            self._nodes_entry = self._create_nodes_entry()

        self._nodes = _nodes  # TODO: Aim at making it __ private
        """Collection of added children"""

    # OK, Match
    @property
    @final
    def _collection(self) -> MutableSequence[ChildNode]:
        """Getter of child nodes.

        Instantiate the collection if needed.
        """

        with ChildrenArray._COLLECTION_LOCK:
            if (nodes := self._nodes) is None:
                nodes = self._nodes = self._init_collection()

        return nodes

    if TYPE_CHECKING:  # pragma: no cover
        # Following methods are defined in _ChildrenArraySubClassInterface
        def _init_collection(self) -> MutableSequence[ChildNode]: ...
        def _create_nodes_entry(self) -> ChildrenEntry[ChildNode]: ...
        def _refresh(self) -> None: ...


class _ChildrenArrayChildrenSubClassInterface(
    _ChildrenArrayBase[ANode, ChildNode],
    _ChildrenSubClassInterface[ChildNode],
):
    # OK, Match
    @override  # _ChildrenSubClassInterface
    def add(self, nodes: Sequence[ChildNode]) -> bool:
        with ChildrenArray._COLLECTION_LOCK:
            collection = self._collection
            len_before = len(collection)
            collection.extend(nodes)
            len_after = len(collection)

        changed = len_after - len_before
        if not changed:
            return False
        else:
            self._refresh()
            return True

    # OK, Match
    @override  # _ChildrenSubClassInterface
    def remove(self, nodes: Sequence[ChildNode]) -> bool:
        with ChildrenArray._COLLECTION_LOCK:
            collection = self._collection

            if collection == nodes:
                collection.clear()
            else:
                changed = False
                for node in nodes:
                    try:
                        collection.remove(node)
                    except ValueError:  # noqa: PERF203
                        continue
                    else:
                        changed = True
                if not changed:
                    return False

        if not nodes:
            # If we are empty, and nodes is an empty list, avoid the refresh
            return False
        else:
            self._refresh()
            return True


class _ChildrenArraySubClassInterface(_ChildrenArrayBase[ANode, ChildNode]):
    # OK, Match
    @override  # _ChildrenArrayBase
    def _init_collection(self) -> MutableSequence[ChildNode]:
        """Allows subclasses to instantiate the collection the first time the children are used.

        It is called only if the collection has not been passed in the constructor.

        Returns:
            Default implementation returns an empty list. Subclasses may return a
            collection already containing child nodes.
        """

        return []

    # OK, Match
    @override  # _ChildrenArrayBase
    def _create_nodes_entry(self) -> ChildrenEntry[ChildNode]:
        """Allows subclasses to provide own version of ChildrenEntry"""

        return _ArrayEntry[ANode, ChildNode](self)

    # OK, Match
    # Note: Inlined refreshImpl as it did not seemed to be (locally) subclassed
    @final
    @override  # _ChildrenArrayBase
    def _refresh(self) -> None:
        """Updates the state of nodes in the collection.

        Can be called by subclasses that directly modify the nodes collection
        to update the state of nodes appropriately.
        """

        self._check_support()
        if self._lazy_support:
            return

        def _implementation() -> None:
            assert self._nodes_entry is not None  # Because it can be None only if lazy. For mypy.

            if self._is_initialised:
                self._entry_support._refresh_entry(self._nodes_entry)
                self._entry_support.get_nodes(optimal_result=False)

            elif self._nodes is not None:
                for node in self._nodes:
                    node._assign_to(self, -1)

        Children.MUTEX.post_write_request(_implementation)


class _ChildrenArrayEntrySupport(
    _ChildrenArrayBase[ANode, ChildNode],
    _ChildrenEntrySupportInterface[ANode, ChildNode],
):
    # OK, Match
    @override  # ChildrenEntrySupport
    def _post_init_entry_support(self, entry_support: EntrySupport[ANode, ChildNode]) -> None:
        if not self._lazy_support:
            assert self._nodes_entry is not None  # Because it can be None only if lazy. For mypy.
            # if self._nodes_entry is None:
            #     self._nodes_entry = self._create_nodes_entry()

            entry_support._set_entries((self._nodes_entry,), no_check=True)

        elif self._nodes_entry is not None:
            self._nodes_entry = None


class ChildrenArray(
    _ChildrenArraySubClassInterface[ANode, ChildNode],
    _ChildrenArrayChildrenSubClassInterface[ANode, ChildNode],
    _ChildrenArrayEntrySupport[ANode, ChildNode],
    _ChildrenArrayBase[ANode, ChildNode],
    Children[ANode, ChildNode],
):
    """Implements the storage of node children by an array.

    Each new child is added at the end of the array. The nodes are
    returned in the order they were inserted.

    Args:
        ParentNode: The type of those children parent node.
        ChildNode: The type of node those children have.
    """

    # OK, Match
    def __init__(
        self,
        _nodes: MutableSequence[ChildNode] | None = None,
        *,
        _lazy: bool = False,
    ) -> None:
        """Initialises a new ChildrenArray.

        Args:
            _nodes: Allows a subclass to provide its own implementation for the
                    collection in which child nodes are stored in.
                    The collection should be empty and should never be accessed
                    directly after giving it to this ChildrenArray.
                    If None, the internal collection will be created after a call
                    to _init_collection() the first time it needs it.
        """

        super().__init__(_nodes=_nodes, _lazy=_lazy)

    # TODO: Review
    @override  # Children
    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        new = super().__deepcopy__(memo)

        new._nodes_entry = None
        if not new._lazy_support:
            new._nodes_entry = new._create_nodes_entry()

        with Children.MUTEX.read_access():
            if self._nodes is not None:
                new._nodes = new._init_collection()
                new._nodes.clear()
                for node in self._nodes:
                    new._nodes.append(node.clone())

        return new


Children.Array = ChildrenArray


# OK, Match
class __SortedArrayEntry(ChildrenEntry[ChildNode], Generic[ANode, ChildNode]):
    """One entry that holds all the nodes in the collection."""

    def __init__(self, array: SortedChildrenArray[ANode, ChildNode]) -> None:
        super().__init__()
        self._array = array

    # OK, reversed is an additional behaviour
    @override  # Children.Entry
    def nodes(self, source: Any) -> MutableSequence[ChildNode]:
        collection = self._array._collection
        return sorted(collection, key=self._array.key, reverse=self._array.is_reversed)  # pyright: ignore[reportArgumentType, reportUnknownVariableType, reportCallIssue]  # Somehow just because key might be None that trips the type checker... despite None being a valid value (a default value even!)


class SortedChildrenArray(ChildrenArray[ANode, ChildNode]):
    """Maintains a list of children sorted by the provided comparator.

    The comparator can change during the lifetime of the children, in which case
    the children are resorted.

    Args:
        ParentNode: The type of those children parent node.
        ChildNode: The type of node those children have.
    """

    # OK, reversed is an additional behaviour
    def __init__(self, _nodes: MutableSequence[ChildNode] | None = None) -> None:
        super().__init__(_nodes=_nodes)

        self.__key: Callable[[ChildNode], Any] | None = None
        self._reversed = False

    # OK, Match
    @override  # _ChildrenArraySubClassInterface
    def _create_nodes_entry(self) -> ChildrenEntry[ChildNode]:
        return __SortedArrayEntry(self)

    # OK, Match
    @property
    def key(self) -> Callable[[ChildNode], Any] | None:
        """The current comparison key.

        When setting it, the children will be resorted. The comparison key is
        used to compare Nodes. If no key is used then nodes will be compared by
        the use of natural ordering.
        """

        return self.__key

    # OK, Match
    @key.setter
    def key(self, key: Callable[[ChildNode], Any] | None) -> None:
        with Children.MUTEX.write_access():
            self.__key = key
            self._refresh()

    @property
    def is_reversed(self) -> bool:
        """Tells if the list is reversed or not.

        When setting it, the children will be resorted.
        """
        return self._reversed

    @is_reversed.setter
    def is_reversed(self, reversed: bool) -> None:
        with Children.MUTEX.write_access():
            self._reversed = reversed
            self._refresh()


Children.SortedArray = SortedChildrenArray

# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words updator
# spell-checker:ignore dupl
""""""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

# System imports
from copy import copy
from threading import RLock
from typing import TYPE_CHECKING, Generic, TypeVar, final

# Third-party imports
from typing_extensions import override

# Local imports
from .children import ChildNode, Children, ChildrenEntry, ParentNode
from .children_array import (
    ChildrenArray,
    _ChildrenArrayBase,
    _ChildrenArrayChildrenSubClassInterface,
)

Key = TypeVar('Key')

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, MutableMapping, MutableSequence, Sequence
    from typing import Any, ClassVar, Final, Self

__all__: Final = ('ChildrenKeys',)

_logger = logging.getLogger(__name__)


# OK, Match
# Note: Original separates it in two classes Dupl+KE, with Dupl being
# protected (ie. package-private). But apparently, that's just for testing reason.
class __KeyEntry(ChildrenEntry[ChildNode], Generic[Key, ChildNode]):
    """Entry for a key

    Supports duplicated objects that still should not be equal.

    It counts the number of times an object has been added to the collection, and
    if the same object is added more than once it is indexed by a number.
    """

    # OK, Match
    def __init__(
        self,
        keys: _ChildrenKeysSubClassInterface[Key, ParentNode, ChildNode],
        key: Key | None = None,
    ) -> None:
        """Initialise the __KeyEntry.

        Args:
            keys: The ChildrenKey the entry is associated with.
            key: The key object. Defaults to None.
                 If None, the entry is used as a factory of entries for update_list(),
                 used in ChildrenKeys._set_keys().
        """
        super().__init__()

        self._keys = keys
        self._key: Key | __KeyEntry[Key, ChildNode] | None = key
        """The key. Either a real value, or another instance of ourself, for some recursivity."""

    # OK, Match
    @override  # Children.Entry
    def nodes(self, source: Any) -> MutableSequence[ChildNode]:
        nodes = self._keys._create_nodes(self.key)
        return list(nodes) if nodes is not None else []

    # OK, Match
    # Note: Merged both updateList with updateListAndMap
    # Note: Original was weirdly convoluted for such a simple counter...
    # Note: The counter argument is probably useless as an argument, since we
    #       merged both methods. But updateListAndMap was originally public
    #       (despite not finding any user).
    @final
    def update_list(
        self,
        source: Sequence[Key],
        target: MutableSequence[ChildrenEntry[ChildNode]],
        counter: MutableMapping[Key, int] | None = None,
    ) -> None:
        """Update the target collection with values from the source.

        If there are multiple occurrences of an object in the first collection,
        an __KeyEntry for the object is created to encapsulate it.
        """

        if counter is None:
            counter = {}

        for obj in source:
            count = counter.get(obj, 0)
            counter[obj] = count + 1
            target.append(self.__create_instance(obj, count))

    # OK, Match
    @property
    def key(self) -> Key:
        """The key represented by this object"""

        assert self._key is not None
        if isinstance(self._key, __KeyEntry):
            return self._key.key  # Yo dawg
        else:
            return self._key

    # OK, Match
    # TODO: Rename index?
    @property
    def count(self) -> int:
        """Counts the index of this key"""

        counter = 0
        d: Key | __KeyEntry[Key, ChildNode] | None = self

        while isinstance(d, __KeyEntry):
            d = d._key
            counter += 1

        return counter

    # OK, Match
    @final
    def __create_instance(self, obj: Key, counter: int) -> __KeyEntry[Key, ChildNode]:
        """Creates a cloned instance of ourself, with a recursive representation for the key"""
        first = d = copy(self)

        while counter > 0:
            counter -= 1
            n = copy(self)
            d._key = n
            d = n

        d._key = obj

        return first

    # OK, Match
    @override  # object
    def __hash__(self) -> int:
        return hash(self.key)

    # OK, Match
    @override  # object
    def __eq__(self, other: object) -> bool:
        if isinstance(other, __KeyEntry):
            return (self.key == other.key) and (self.count == other.count)
        else:
            return False


class _ChildrenKeysBase(_ChildrenArrayBase[ParentNode, ChildNode]):
    _LOCK = RLock()
    __LAST_RUNS: ClassVar[MutableMapping[_ChildrenKeysBase[Any, Any], Callable[[], None]]] = {}
    """The last runnable (created in method _set_keys()) for each children object"""

    # OK, Match
    # Should be __ private, but we need to call it from other internal classes
    def _apply_keys(self, new_keys: Iterable[ChildrenEntry[ChildNode]]) -> None:
        def implementation() -> None:
            if not self.__keys_check(self, implementation):
                return

            self._entry_support._set_entries(new_keys)
            self.__keys_exit(self, implementation)

        self.__keys_enter(self, implementation)
        Children.MUTEX.post_write_request(implementation)

    # OK, Match
    @classmethod
    def __keys_enter(
        cls,
        children: _ChildrenKeysBase[ParentNode, ChildNode],
        call: Callable[[], None],
    ) -> None:
        """Enter of _set_keys()"""

        with cls._LOCK:
            cls.__LAST_RUNS[children] = call

    # OK, Match
    @classmethod
    def __keys_exit(
        cls,
        children: _ChildrenKeysBase[ParentNode, ChildNode],
        call: Callable[[], None],
    ) -> None:
        """Clears the entry for the children"""

        with cls._LOCK:
            was = cls.__LAST_RUNS.pop(children, None)

            if (was is not None) and (was != call):
                cls.__LAST_RUNS[children] = was

    # OK, Match
    @classmethod
    def __keys_check(
        cls,
        children: _ChildrenKeysBase[ParentNode, ChildNode],
        call: Callable[[], None],
    ) -> bool:
        """Check whether the callable is "the current" for a given children"""

        with cls._LOCK:
            return call == cls.__LAST_RUNS.get(children)

    if TYPE_CHECKING:
        # Following methods are defined in _ChildrenKeysSubClassInterface
        @property
        def _before(self) -> bool: ...
        @_before.setter
        def _before(self, value: bool) -> None: ...


class _ChildrenKeysChildrenSubClassInterface(
    _ChildrenKeysBase[ParentNode, ChildNode],
    _ChildrenArrayChildrenSubClassInterface[ParentNode, ChildNode],
):
    # OK, Match
    # Deprecated
    @override
    def add(self, nodes: Sequence[ChildNode]) -> bool:
        """Do not use! Just call _set_keys() with a larger set."""

        if self._lazy_support:
            self._fallback_to_default_support()

        return super().add(nodes)

    # OK, Match
    # Deprecated
    @override
    def remove(self, nodes: Sequence[ChildNode]) -> bool:
        """Do not use! Just call _set_keys() with a smaller set."""

        if self._lazy_support:
            return False

        with Children.MUTEX.write_access():
            if self._nodes is not None:
                # Removing from array, just if the array nodes are really created.
                # Expecting  len(nodes) == 1, which is the usual case
                nodes = [node for node in nodes if (node in self._nodes)]

            super().remove(nodes)

        return True

    # Compatibility with legacy ChildrenArray API
    # OK, Match
    @override  # Children
    def _check_support(self) -> None:
        if self._lazy_support and self._nodes:
            self._fallback_to_default_support()

    # Compatibility with legacy ChildrenArray API
    # OK, Match
    def _fallback_to_default_support(self) -> None:
        _logger.warning('Falling back to non lazy entry support. A Children.Array methods was used')
        self._switch_support(to_lazy=False)

    # Compatibility with legacy ChildrenArray API
    # OK, Match
    def _switch_support(self, *, to_lazy: bool) -> None:
        if to_lazy == self._lazy_support:
            return

        with Children.MUTEX.write_access():
            entry_support = self._entry_support
            entries = entry_support._entries
            init = entry_support.is_initialised

            if init and (self._parent is not None):
                snapshot = entry_support._snapshot()
                if snapshot:
                    indexes = list(range(len(snapshot)))
                    self._parent._fire_sub_nodes_change_idx(False, indexes, None, [], snapshot)  # noqa: FBT003

            with Children._LOCK:
                self._entry_support_raw = None

            self._lazy_support = to_lazy
            if to_lazy:
                self._nodes_entry = None
            else:
                self._nodes_entry = self._create_nodes_entry()
                entries.insert(0 if self._before else len(entries), self._nodes_entry)

            entry_support = self._entry_support
            if init:
                entry_support._notify_set_entries()
            entry_support._set_entries(entries)

    # OK, Match
    @override  # Children
    def _destroy_nodes(self, nodes: Iterable[ChildNode]) -> None:
        for node in nodes:
            node._fire_node_destroyed()


class _ChildrenKeysSubClassInterface(
    _ChildrenKeysBase[ParentNode, ChildNode],
    Generic[Key, ParentNode, ChildNode],
):
    def __init__(self, **kwargs: Any) -> None:
        self.__before = False
        """Tells if we add array children before or after keys ones"""

        super().__init__(**kwargs)

    # OK, Match
    @final
    def _refresh_key(self, key: Key) -> None:
        """Refresh the child nodes for a given key"""

        def call() -> None:
            self._entry_support._refresh_entry(self._create_entry_for_key(key))

        Children.MUTEX.post_write_request(call)

    # OK, Match
    def _create_entry_for_key(self, key: Key) -> ChildrenEntry[ChildNode]:
        """To be overridden by FilterNode.Children"""

        return __KeyEntry[Key, ChildNode](self, key)

    # OK, Match (skipping the assert stuffs)
    @final
    def _set_keys(self, keys_set: Sequence[Key]) -> None:
        """Set the new keys for this children object.

        Setting of keys does not necessarily lead to the creation of nodes.
        It happens only when the list has already been initialised.

        Args:
            keys_set: The keys for the nodes (collection of any objects)
        """

        new_keys: list[ChildrenEntry[ChildNode]] = []
        updator = __KeyEntry[Key, ChildNode](self)
        if self._lazy_support:
            updator.update_list(keys_set, new_keys)
        else:
            if self._before and (self._nodes_entry is not None):
                new_keys.append(self._nodes_entry)

            updator.update_list(keys_set, new_keys)

            if not self._before and (self._nodes_entry is not None):
                new_keys.append(self._nodes_entry)

        self._apply_keys(new_keys)

    # OK, Match
    @abstractmethod
    def _create_nodes(self, key: Key) -> Iterable[ChildNode] | None:
        """Creates nodes for a given key.

        Args:
            key: The key.

        Returns:
            Child nodes for this key, or None if there should be no nodes for this key.
        """

        raise NotImplementedError  # pragma: no cover

    @property
    def _before(self) -> bool:  # pyright: ignore[reportImplicitOverride]
        """Tells if we add array children before or after keys ones"""

        return self.__before

    # OK, Match
    @_before.setter
    @final
    def _before(self, value: bool) -> None:
        """Sets whether new nodes should be added to the beginning or end of sublists
        for a given key.

        Generally should not be used.
        """

        with Children.MUTEX.write_access():
            if (self.__before is not value) and not self._lazy_support:
                entry_support = self._entry_support
                entries = entry_support._entries
                self.__before = value

                if (nodes_entry := self._nodes_entry) is not None:
                    entries.remove(nodes_entry)
                    entries.insert(0 if value else len(entries), nodes_entry)

                entry_support._set_entries(entries)


class ChildrenKeys(
    _ChildrenKeysSubClassInterface[Key, ParentNode, ChildNode],
    _ChildrenKeysChildrenSubClassInterface[ParentNode, ChildNode],
    _ChildrenKeysBase[ParentNode, ChildNode],
    ChildrenArray[ParentNode, ChildNode],
    ABC,
    Generic[Key, ParentNode, ChildNode],
):
    """Implements an array of child nodes associated nonuniquely with keys and sorted by these keys.

    There is a _create_nodes() method that should for each key create an array of
    nodes that represents the key.

    This class is preferable to ChildrenArray because:
    - It more clearly separates model for view, and encourages use of a discrete model.
    - It correctly handles adding, removing, and reordering children while preserving
      existing node selections in a tree (or other) view where possible.

    Typical usage:
    - Subclass.
    - Decide what type your key should be.
    - Implements _create_nodes() to create some nodes (usually exactly one) per key.
    - Override _add_notify() to compute a set of keys, and set it using _set_keys().
      The collection of keys may be ordered.
    - Override _remove_notify() to just call _set_keys() with an empty collection.
    - When your model changes, call _set_keys() with the new set of keys. ChildrenKeys
      will be smart and calculate exactly what it needs to do efficiently.
    - Optional: if your notion of what the node for a given key changes (but the key
      stays the same), you can call _refresh_key(). Usually this is not necessary

    Note that for simple case, it may be preferable to subclass ChildFactory and
    pass the result to Children.create(). Doing so makes it easy to switch to using
    child nodes computed on a background thread if necessary for performance reasons.

    Args:
        Key: The type of a key.
        ParentNode: The type of those children parent node.
        ChildNode: The type of node those children have.
    """

    # OK, Match
    def __init__(self, *, _lazy: bool = False) -> None:
        """Initialises a new ChildrenKeys.

        There are certain requirements for usage of lazy mode:
        It is forbidden to create more than 1 node in _create_nodes() for a given key.
        In optimal case, there should be 1:1 pairing between key and node. But it
        is also possible to have 1:0 pairing (ie. create no node by returning None).
        In such case, after detection that there is no node for a key, the key is
        automatically removed and a change event is fired (removal of "dummy" node).

        Args:
            _lazy: Optional lazy behaviour that tries to avoid computation of nodes if possible.
        """

        super().__init__(_lazy=_lazy)

    # TODO: Review
    @override  # Array
    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        new = super().__deepcopy__(memo)
        new.__before = self.__before

        return new


Children.Keys = ChildrenKeys

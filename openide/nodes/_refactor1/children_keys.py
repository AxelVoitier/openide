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

import logging
from abc import ABC, abstractmethod

# System imports
from copy import copy
from threading import RLock
from typing import TYPE_CHECKING, Generic, TypeVar, final

# Third-party imports
from typing_extensions import override

# Local imports
from .children import Children
from .children_array import ChildrenArray
from .node import ANode, ParentNode

T = TypeVar('T')
K = TypeVar('K')

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, MutableMapping, MutableSequence, Sequence
    from typing import Any, ClassVar, Final, Self

__all__: Final = ()

_logger = logging.getLogger(__name__)


class Keys(ChildrenArray[ParentNode, ANode], ABC, Generic[T, ParentNode, ANode]):
    _LOCK = RLock()
    __LAST_RUNS: ClassVar[MutableMapping[Keys[T, ParentNode, ANode], Callable[[], None]]] = {}

    # OK, Match
    # Note: Original separates it in two classes Dupl+KE, with Dupl being
    # protected (ie. package-private). But apparently, that's just for testing reason.
    class _KeyEntry(Children.Entry, Generic[K]):
        # OK, Match
        def __init__(self, keys: Keys[T, ParentNode, ANode], key: K | None = None) -> None:
            super().__init__()

            self._keys = keys
            self._key: K | Keys._KeyEntry[K] | None = key

        # OK, Match
        @override  # Children.Entry
        def nodes(self, source: Any) -> MutableSequence[ANode]:
            nodes = self._keys._create_nodes(self.key)
            return list(nodes) if nodes is not None else []

        # OK, Match
        # Note: Merged both updateList with updateListAndMap
        # Note: Original was weirdly convoluted for such a simple counter...
        @final
        def update_list(
            self,
            source: Sequence[K],
            target: MutableSequence[Children.Entry],
            counter: MutableMapping[K, int] | None = None,
        ) -> None:
            if counter is None:
                counter = {}

            for obj in source:
                count = counter.get(obj, 0)
                counter[obj] = count + 1
                target.append(self.__create_instance(obj, count))

        # OK, Match
        @property
        def key(self) -> K | None:
            if isinstance(self._key, Keys._KeyEntry):
                return self._key.key  # Yo dawg
            else:
                return self._key

        # OK, Match
        # TODO: Rename index?
        @property
        def count(self) -> int:
            counter = 0
            d: K | Keys._KeyEntry[K] | None = self

            while isinstance(d, Keys._KeyEntry):
                d = d._key
                counter += 1

            return counter

        # OK, Match
        @final
        def __create_instance(self, obj: K, counter: int) -> Keys._KeyEntry[K]:
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
            if isinstance(other, Keys._KeyEntry):
                return (self.key == other.key) and (self.count == other.count)
            else:
                return False

    # OK, Match
    def __init__(self, *, _lazy: bool = False) -> None:
        super().__init__(_lazy=_lazy)

        self.__before = False

    # TODO: Review
    @override  # Array
    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        new = super().__deepcopy__(memo)
        new.__before = self.__before

        return new

    # OK, Match
    @override  # Children
    def _check_support(self) -> None:
        if self._lazy_support and self.__nodes:
            self._fallback_to_default_support()

    # OK, Match
    def _fallback_to_default_support(self) -> None:
        _logger.warning('Falling back to non lazy entry support. A Children.Array methods was used')
        self._switch_support(to_lazy=False)

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

    # Note: add (L1402) is deprecated

    # Note: remove (L1414) is deprecated

    # OK, Match
    @final
    def _refresh_key(self, key: T) -> None:
        def call() -> None:
            self._entry_support._refresh_entry(self._create_entry_for_key(key))

        Children.MUTEX.post_write_request(call)

    # OK, Match
    def _create_entry_for_key(self, key: T) -> Children.Entry:
        return Keys._KeyEntry[T](self, key)

    # OK, Match (skipping the assert stuffs)
    @final
    def _set_keys(self, keys_set: Sequence[T]) -> None:
        new_keys: MutableSequence[Children.Entry] = []
        updator = Keys._KeyEntry[T](self)
        if self._lazy_support:
            updator.update_list(keys_set, new_keys)
        else:
            if self._before and (self._nodes_entry is not None):
                new_keys.append(self._nodes_entry)

            updator.update_list(keys_set, new_keys)

            if not self._before and (self._nodes_entry is not None):
                new_keys.append(self._nodes_entry)

        self.__apply_keys(new_keys)

    # OK, Match
    def __apply_keys(self, new_keys: Sequence[Children.Entry]) -> None:
        def implementation() -> None:
            if not self.__keys_check(self, implementation):
                return

            self._entry_support._set_entries(new_keys)
            self.__keys_exit(self, implementation)

        self.__keys_enter(self, implementation)
        Children.MUTEX.post_write_request(implementation)

    @property
    def _before(self) -> bool:
        return self.__before

    # OK, Match
    @_before.setter
    @final
    def _before(self, value: bool) -> None:
        with Children.MUTEX.write_access():
            if (self.__before is not value) and not self._lazy_support:
                entry_support = self._entry_support
                entries = entry_support._entries
                self.__before = value

                if (nodes_entry := self._nodes_entry) is not None:
                    entries.remove(nodes_entry)
                    entries.insert(0 if value else len(entries), nodes_entry)

                entry_support._set_entries(entries)

    # OK, Match
    @abstractmethod
    def _create_nodes(self, key: T) -> Sequence[ANode] | None:
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @override  # Children
    def _destroy_nodes(self, nodes: Iterable[ANode]) -> None:
        for node in nodes:
            node._fire_node_destroyed()

    # OK, Match
    @classmethod
    def __keys_enter(cls, children: Keys[T, ParentNode, ANode], call: Callable[[], None]) -> None:
        with cls._LOCK:
            cls.__LAST_RUNS[children] = call

    # OK, Match
    @classmethod
    def __keys_exit(cls, children: Keys[T, ParentNode, ANode], call: Callable[[], None]) -> None:
        with cls._LOCK:
            was = cls.__LAST_RUNS.pop(children, None)

            if (was is not None) and (was != call):
                cls.__LAST_RUNS[children] = was

    # OK, Match
    @classmethod
    def __keys_check(cls, children: Keys[T, ParentNode, ANode], call: Callable[[], None]) -> bool:
        with cls._LOCK:
            return call == cls.__LAST_RUNS.get(children)


Children.Keys = Keys  # type: ignore[misc]

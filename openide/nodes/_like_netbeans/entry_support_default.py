# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# From: https://github.com/apache/netbeans/blob/master/platform/openide.nodes/src/org/openide/nodes/EntrySupportDefault.java  # noqa: E501

from __future__ import annotations

# System imports
import logging
import threading
import time
from threading import RLock, Condition, Thread
from typing import TYPE_CHECKING, final
from weakref import ReferenceType

# Third-party imports

# Local imports
from openide.utils.classes import Debug
from openide.utils.typing import override
from openide.nodes._like_netbeans.entry_support import EntrySupport
from openide.nodes._like_netbeans.children import Children
from openide.nodes._like_netbeans.children_storage import ChildrenStorage
from openide.nodes._like_netbeans.node import Node
from openide.nodes._like_netbeans import node_operations


if TYPE_CHECKING:
    from collections.abc import (
        Iterable, Sized, Collection, Sequence, Mapping,
        MutableSequence,
    )
    from typing import Optional, Any


_logger = logging.getLogger(__name__)


# OK, Match
class _DefaultSnapshot(tuple[Node]):

    def __new__(
        cls,
        nodes: Iterable[Node],
        storage: Optional[ChildrenStorage]
    ) -> _DefaultSnapshot:
        return super().__new__(cls, nodes)  # type: ignore[arg-type]

    def __init__(
        self,
        nodes: Iterable[Node],
        storage: Optional[ChildrenStorage]
    ) -> None:
        super().__init__()  # In that case it seems to go directly to object.__init__()

        self._holder = storage


# OK, Match
class _StorageRef(ReferenceType[ChildrenStorage]):

    def __new__(
        cls, entry_support: Optional[EntrySupportDefault],
        reference: ChildrenStorage, weak: bool,
    ) -> _StorageRef:
        # We need to redefine __new__ because a ref() object initialise itself
        # with __new__ and not __init__.
        # For the finaliser, we can pass our unbounded _finaliser method as
        # when called it will actually be given the reference to self as argument.
        return super().__new__(cls, reference, cls._finaliser)  # type: ignore[arg-type]

    # OK, Match
    def __init__(
        self, entry_support: Optional[EntrySupportDefault],
        reference: ChildrenStorage, weak: bool,
    ) -> None:
        super().__init__(reference, self._finaliser)  # type: ignore[call-arg]

        self._hard_ref = reference if not weak else None
        self._entry_support = entry_support

        # print('instantiated a _StorageRef', time.monotonic(), self, entry_support, reference, weak)

    # def __del__(self):
    #     print('_StorageRef.__del__', self, self._entry_support)
    #     if (super_del := getattr(super(), '__del__', None)) is not None:
    #         super_del()

    # OK, Match
    def __call__(self) -> Optional[ChildrenStorage]:
        return super().__call__() if self._is_weak else self._hard_ref

    # OK, Match
    @property
    def _is_weak(self) -> bool:
        return self._hard_ref is None

    # OK, Match
    # Give it an *args just in case one day behaviour of ref.__init__()
    # changes and do redefine the finaliser as the bounded method
    def _finaliser(self, *args: Any) -> None:
        # print('_StorageRef._finaliser')
        if self._entry_support is not None:
            self._entry_support._finalised_children_storage(self)


class EntrySupportDefault(EntrySupport, Debug(f'{__name__}.EntrySupportDefault')):

    # OK, Match
    @final
    class _Info:

        # OK, Match
        def __init__(self, entry_support: EntrySupportDefault, entry: Children.Entry) -> None:
            self._entry_support = entry_support
            self.__entry = entry
            self._length = 0  # Set by ChildrenStorage

        # To make that protected attribute read-only
        @property
        def _entry(self) -> Children.Entry:
            return self.__entry

        # OK, Match
        def nodes(self, has_to_exist: bool) -> MutableSequence[Node]:
            assert (not has_to_exist) or (
                self._entry_support._EntrySupportDefault__storage() is not None), 'ChildrenStorage is not initialised'

            storage = self._entry_support._EntrySupportDefault__get_storage()
            return storage.nodes_for(self, has_to_exist)

        # OK, Match
        def use_nodes(self, nodes: MutableSequence[Node]) -> None:
            storage = self._entry_support._EntrySupportDefault__get_storage()
            storage.use_nodes(self, nodes)

            children = self._entry_support.children
            for node in nodes:
                node._assign_to(children, -1)
                # print(f'EntrySupportDefault._Info.use_nodes: fire parentNode on {node=}')
                node._fire_own_property_change('parentNode', None, children._parent)

    # This storage gets deleted immediately, effectively making it a dead ref
    # TODO: Review
    __EMPTY = _StorageRef(None, ChildrenStorage(_fake=True), True)

    __LOCK = Condition()

    # OK, Match
    # Note: map is already initialised to avoid having it Optional
    # (original does not actually check it everytime it tries to use it!).
    def __init__(self, children: Children) -> None:
        # print('starting to instantiate an entry support default', time.monotonic(), self, children)
        super().__init__(children)

        self.__entries: MutableSequence[Children.Entry] = []
        self.__storage: _StorageRef = EntrySupportDefault.__EMPTY
        self.__map = dict[Children.Entry, EntrySupportDefault._Info]()
        self.__map_lock = RLock()
        self.__init_thread: Optional[Thread] = None
        self.__inited = False
        self.__must_notify_set_entries = False

        # print('done instantiating an entry support default', time.monotonic(), self, children)

    # def __del__(self):
    #     print('EntrySupportDefault.__del__', time.monotonic(), self, self._EntrySupport__children)
    #     if (super_del := getattr(super(), '__del__', None)) is not None:
    #         super_del()

    # OK, Match
    @property
    @override  # EntrySupport
    def is_initialised(self) -> bool:
        return (
            self.__inited and
            ((storage := self.__storage()) is not None) and
            (storage.is_initialised)
        )

    # OK, Match
    @override  # EntrySupport
    def _snapshot(self) -> _DefaultSnapshot:
        self.get_nodes()  # As in original. Maybe to create them outside of the mutex?
        with Children.MUTEX.read_access():
            return self._create_snapshot()

    # OK, Match
    # Note: Do not inline, it can be subclassed and/or used independently of _snapshot
    def _create_snapshot(self) -> _DefaultSnapshot:
        return _DefaultSnapshot(self.get_nodes(), self.__storage())

    # OK, Match
    # TODO: Two properties, nodes and nodes_optimal?
    @final
    @override  # EntrySupport
    def get_nodes(self, optimal_result: bool = False) -> list[Node]:
        # print(f'get_nodes, {optimal_result=}')
        if optimal_result:
            hold = self.__get_storage()  # noqa: F841
            find = self.children.find_child(None)  # noqa: F841

        results = [False, False]
        while True:
            # print(f'get_nodes, {results=}')
            tmp_storage = self.__get_storage(results)
            # print(f'get_nodes, {tmp_storage=}, {results=}')
            with Children.MUTEX.read_access():
                # print(f'get_nodes, in mutex read, {self.children._entry_support_raw}')
                if self is not self.children._entry_support_raw:
                    return []
                results[1] = self.is_initialised
                # print(f'get_nodes, is_initialised={results[1]}')
                nodes = tmp_storage.nodes
                # print(f'get_nodes, got nodes {nodes}')

            # print(f'get_nodes, after mutex {results=}')
            if results[1]:
                return nodes if nodes is not None else []

            elif results[0]:
                self._notify_set_entries()
                return nodes if nodes is not None else []

            # Else, keep trying (loop)

    # OK, Match
    @final
    @override  # EntrySupport
    def get_nodes_count(self, optimal_result: bool) -> int:
        return len(self.get_nodes(optimal_result))

    # OK, Match
    @override  # EntrySupport
    def get_node_at(self, index: int) -> Optional[Node]:
        nodes = self.get_nodes()
        return nodes[index] if index < len(nodes) else None

    # OK, Match
    @final
    def _just_compute_nodes(self) -> list[Node]:
        # print('EntrySupportDefault._just_compute_nodes', time.monotonic(), self, self.__entries)
        nodes = list[Node]()
        for entry in self.__entries:
            info = self.__find_info(entry)
            nodes += info.nodes(False)

        for i, node in enumerate(nodes):
            if node is None:
                _logger.warning('None node among children! index=%d ; nodes=%s', i, nodes)
                raise RuntimeError(f'Node {i} is None')

            node._assign_to(self.children, i)
            # print(f'EntrySupportDefault._just_compute_nodes: fire parentNode on {node=}')
            node._fire_own_property_change('parentNode', None, self.children._parent)

        return nodes

    # OK, Match
    def __find_info(self, entry: Children.Entry) -> EntrySupportDefault._Info:
        with self.__map_lock:
            if (info := self.__map.get(entry)) is None:
                info = EntrySupportDefault._Info(self, entry)
                self.__map[entry] = info

            return info

    # OK, Match
    @override  # EntrySupport
    def _notify_set_entries(self) -> None:
        self.__must_notify_set_entries = True

    # OK, Match
    def __check_consistency(self) -> None:
        map_len = len(self.__map)
        entries_len = len(self.__entries)
        assert map_len == entries_len, f'Map length={map_len} ; Entries length={entries_len}'

    # OK, Match
    @override  # EntrySupport
    def _set_entries(self, entries: Iterable[Children.Entry], no_check: bool = False) -> None:
        # print('EntrySupportDefault._set_entries', time.monotonic(), self, no_check)
        assert no_check or Children.MUTEX.is_write_access

        holder = self.__storage()
        current = holder.nodes if holder is not None else None

        # print(
        #     f'EntrySupportDefault._set_entries: {holder=}, {current=}, {self.__must_notify_set_entries=}')
        if self.__must_notify_set_entries:
            if holder is None:
                holder = self.__get_storage()

            if current is None:
                holder.entry_support = self
                current = holder.nodes
                assert current is not None

            self.__must_notify_set_entries = False

        elif (holder is None) or (current is None):
            # print(f'EntrySupportDefault._set_entries: setting entries {entries}')
            self.__entries = list(entries)
            with self.__map_lock:
                self.__map = {k: v for k, v in self.__map.items() if k in entries}
            return

        self.__check_consistency()

        # print(f'EntrySupportDefault._set_entries: {self.__entries=}, {entries=}')

        to_remove = set(self.__entries) - set(entries)
        # print(f'EntrySupportDefault._set_entries: {to_remove=}')
        if to_remove:
            self.__update_remove(current, to_remove)
            current = holder.nodes
            assert current is not None

        to_add = self.__update_order(current, entries)
        # print(f'EntrySupportDefault._set_entries: {to_add=}')
        if to_add:
            self.__update_add(to_add, list(entries))

    # OK, Match
    def __check_info(
        self,
        info: Optional[EntrySupportDefault._Info],
        entry: Children.Entry,
        entries: Iterable[Children.Entry],
        map: Mapping[Children.Entry, EntrySupportDefault._Info],
    ) -> None:
        if info is None:
            raise RuntimeError(
                f'Error in {type(self).__name__} with entry {entry} from among entries:\n  ' +
                '\n  '.join([f'{entry} contained: {entry in map}' for entry in entries]) + '\n'
                'probably caused by faulty key implementation. The key __hash__() and __eq__() '
                'methods must behave as for an IMMUTABLE object and __hash__() must return the '
                ' same value for __eq__() keys.\nmapping:\n  ' +
                '\n  '.join([f'{k} => {v}' for k, v in map.items()])
            )

    # OK, Match
    def __update_remove(
        self,
        current: Sequence[Node],
        to_remove: Iterable[Children.Entry],
    ) -> None:
        assert Children.MUTEX.is_write_access

        nodes = list[Node]()
        storage = self.__storage()
        assert storage is not None

        with self.__map_lock:
            for entry in to_remove:
                info = self.__map.get(entry)
                del self.__map[entry]

                self.__check_info(info, entry, tuple(), self.__map)
                assert info is not None

                nodes += info.nodes(True)
                storage._remove(info)
                self.__entries.remove(entry)

        self.__check_consistency()

        if nodes:
            self.__clear_nodes()
            self._notify_remove(nodes, current)

    # OK, Match
    def __update_order(
        self,
        current: Sized,
        new_entries: Iterable[Children.Entry],
    ) -> list[EntrySupportDefault._Info]:
        assert Children.MUTEX.is_write_access

        offsets = dict[EntrySupportDefault._Info, int]()
        previous_pos = 0
        with self.__map_lock:
            for entry in self.__entries:
                info = self.__map.get(entry)
                self.__check_info(info, entry, self.__entries, self.__map)
                assert info is not None

                offsets[info] = previous_pos
                previous_pos += info._length

        to_add = list[EntrySupportDefault._Info]()
        perm = [0] * len(current)
        current_pos = 0
        perm_size = 0
        reordered_entries = list[Children.Entry]()
        with self.__map_lock:
            for entry in new_entries:
                info = self.__map.get(entry)

                if info is None:
                    info = EntrySupportDefault._Info(self, entry)
                    to_add.append(info)
                else:
                    reordered_entries.append(entry)
                    previous_pos = offsets[info]
                    if current_pos != previous_pos:
                        for i in range(info._length):
                            perm[previous_pos + i] = 1 + current_pos + i
                        perm_size += info._length

                current_pos += info._length

        if perm_size > 0:
            for i in range(len(perm)):
                if perm[i] == 0:
                    perm[i] = i
                else:
                    perm[i] -= 1

            self.__entries = reordered_entries
            self.__check_consistency()

            self.__clear_nodes()
            if (parent := self.children._parent) is not None:
                parent._fire_reorder_change(perm)

        return to_add

    # OK, Match
    def __update_add(
        self,
        infos: Iterable[EntrySupportDefault._Info],
        entries: MutableSequence[Children.Entry],
    ) -> None:
        assert Children.MUTEX.is_write_access

        nodes = list[Node]()
        with self.__map_lock:
            for info in infos:
                nodes += info.nodes(False)
                self.__map[info._entry] = info

        self.__entries = entries
        self.__check_consistency()

        # print(f'EntrySupportDefault.__update_add: {nodes=}')
        if nodes:
            self.__clear_nodes()
            self._notify_add(nodes)

    # OK, Match
    @final
    @override  # EntrySupport
    def _refresh_entry(self, entry: Children.Entry) -> None:
        if (holder := self.__storage()) is None:
            return
        if (current := holder.nodes) is None:
            return

        self.__check_consistency()
        with self.__map_lock:
            if (info := self.__map.get(entry)) is None:
                return

        old_nodes = info.nodes(False)
        # Warning, entry.nodes() could return None, from Children.Map._refresh_key
        new_nodes = info._entry.nodes(None)
        if old_nodes == new_nodes:
            return

        to_remove = set(old_nodes) - set(new_nodes)
        if to_remove:
            for node in to_remove:
                old_nodes.remove(node)
            self.__clear_nodes()
            self._notify_remove(to_remove, current)
            current = holder.nodes

        to_add = self.__refresh_order(entry, old_nodes, new_nodes)
        info.use_nodes(new_nodes)
        if to_add:
            self.__clear_nodes()
            self._notify_add(to_add)

    # OK, Match
    def __refresh_order(
        self,
        entry: Children.Entry,
        old_nodes: Collection[Node],
        new_nodes: MutableSequence[Node]
    ) -> list[Node]:
        to_add = list[Node]()
        old_nodes_set = set(old_nodes)
        to_process = set(old_nodes_set)
        perm_array: MutableSequence[Node] = []

        for node in new_nodes:
            if node in old_nodes_set:
                old_nodes_set.remove(node)
                perm_array.append(node)
            else:
                if node not in to_process:
                    to_add.append(node)
                else:
                    new_nodes.remove(node)

        perm = node_operations.compute_permutation(old_nodes, perm_array)
        if perm:
            self.__clear_nodes()
            self.__find_info(entry).use_nodes(perm_array)
            parent = self.children._parent
            if parent is not None:
                parent._fire_reorder_change(perm)

        return to_add

    # OK, Match
    def _notify_remove(
        self,
        nodes: Collection[Node],
        current: Sequence[Node]
    ) -> Collection[Node]:
        children = self.children

        if children._parent is not None:
            if children._entry_support_raw is self:
                children._parent._fire_sub_nodes_change(False, nodes, current)

            for node in nodes:
                node._deassign_from(children)
                node._fire_own_property_change('parentNode', children._parent, None)

        children._destroy_nodes(nodes)
        return nodes

    # OK, Match
    def _notify_add(self, nodes: Sequence[Node]) -> None:
        for node in nodes:
            node._assign_to(self.children, -1)
            # print(f'EntrySupportDefault._notify_add: fire parentNode on {node=}')
            node._fire_own_property_change('parentNode', None, self.children._parent)

        parent = self.children._parent
        # print(
        #     f'EntrySupportDefault._notify_add: {nodes=}, {parent=}, {self.children._entry_support_raw=}, {self=}')
        if (parent is not None) and (self.children._entry_support_raw is self):
            parent._fire_sub_nodes_change(True, nodes, None)

    # OK, Match
    @override  # EntrySupport
    def test_nodes(self) -> Optional[list[Node]]:
        storage = self.__storage()
        if storage is None:
            return None

        with Children.MUTEX.read_access():
            return storage.nodes

    # OK, Match
    def __get_storage(
        self, cannot_work_better: Optional[MutableSequence[bool]] = None
    ) -> ChildrenStorage:
        do_initialise = False

        with EntrySupportDefault.__LOCK:
            if (storage := self.__storage()) is None:
                storage = ChildrenStorage()
                self._register_children_storage(storage, False)
                do_initialise = True
                self.__init_thread = threading.current_thread()

        if do_initialise:
            try:
                self.children._call_add_notify()
            finally:
                notify_later = Children.MUTEX.is_read_access
                storage.entry_support = self
                self.__inited = True

                def set_and_notify() -> None:
                    with EntrySupportDefault.__LOCK:
                        self.__init_thread = None
                        EntrySupportDefault.__LOCK.notify_all()

                if notify_later:
                    Children.MUTEX.post_write_request(set_and_notify)
                else:
                    set_and_notify()

        elif self.__init_thread is not None:
            if (
                Children.MUTEX.is_read_access or
                Children.MUTEX.is_write_access or
                (self.__init_thread == threading.current_thread())
            ):
                if cannot_work_better is not None:
                    cannot_work_better[0] = True

                storage.entry_support = self
                return storage

            with EntrySupportDefault.__LOCK:
                EntrySupportDefault.__LOCK.wait_for(lambda: self.__init_thread is None)

        return storage

    # OK, Match
    def __clear_nodes(self) -> None:
        storage = self.__storage()
        if storage is not None:
            storage.clear()

    # OK, Match
    @final
    def _register_children_storage(self, storage: ChildrenStorage, weak: bool) -> None:
        with EntrySupportDefault.__LOCK:
            if (
                (self.__storage is not None) and
                (self.__storage() is storage) and
                (self.__storage._is_weak is weak)
            ):
                return

            self.__storage = _StorageRef(self, storage, weak)

    # OK, Match
    @final
    def _finalised_children_storage(self, caller: ReferenceType[ChildrenStorage]) -> None:
        assert caller() is None

        def run() -> None:
            with EntrySupportDefault.__LOCK:
                if (self.__storage is caller) and (self.children._entry_support_raw is self):
                    self.__must_notify_set_entries = False
                    self.__storage = EntrySupportDefault.__EMPTY
                    self.__inited = False
                    self.children._call_remove_notify()
                    assert self.__storage is EntrySupportDefault.__EMPTY

        try:
            Children.MUTEX.post_write_request(run)
        except RuntimeError:
            raise RuntimeError(
                f'Proot at {time.monotonic()} in {self} with storage ref={caller}=>{caller()}')

    # OK, Match
    @property
    @override  # EntrySupport
    def _entries(self) -> list[Children.Entry]:
        return list(self.__entries)

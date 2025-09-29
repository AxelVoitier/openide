# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words finaliser deserialisation
# spell-checker:ignore
""""""

from __future__ import annotations

# System imports
import logging
import threading
import time
from threading import Condition, RLock, Thread
from typing import TYPE_CHECKING, Generic, final
from weakref import ReferenceType

# Third-party imports
from typing_extensions import override

# Local imports
from . import node_operations
from .children import ANode, ChildNode, Children, ChildrenEntry, _ChildrenEntrySupportInterface
from .children_storage import ChildrenStorage
from .entry_support import EntrySupport

if TYPE_CHECKING:
    from collections.abc import (
        Collection,
        Iterable,
        Mapping,
        MutableSequence,
        Sequence,
        Sized,
    )
    from typing import Any, ClassVar, Final

    from typing_extensions import Self

__all__: Final = ('EntrySupportDefault',)

_logger = logging.getLogger(__name__)


# OK, Match
class _DefaultSnapshot(tuple[ChildNode], Generic[ANode, ChildNode]):  # noqa: SLOT001
    # Sadly, we cannot define a descendent of tuple with a non-empty __slots__.
    # But we need the extra attribute _holder
    # Therefore, we have to stick with a dict instance on that one.

    def __new__(
        cls,
        nodes: Iterable[ChildNode],
        storage: ChildrenStorage[ANode, ChildNode] | None,
    ) -> Self:
        return super().__new__(cls, nodes)

    def __init__(
        self,
        nodes: Iterable[ChildNode],
        storage: ChildrenStorage[ANode, ChildNode] | None,
    ) -> None:
        super().__init__()  # In that case it seems to go directly to object.__init__()

        self._holder = storage


# OK, Match
class _StorageRef(ReferenceType[ChildrenStorage[ANode, ChildNode]]):
    def __new__(
        cls,
        entry_support: EntrySupportDefault[ANode, ChildNode] | None,
        reference: ChildrenStorage[ANode, ChildNode],
        *,
        weak: bool,
    ) -> Self:
        # We need to redefine __new__ because a ref() object initialise itself
        # with __new__ and not __init__.
        # For the finaliser, we can pass our unbounded _finaliser method as
        # when called it will actually be given the reference to self as argument.
        return super().__new__(cls, reference, cls._finaliser)

    # OK, Match
    def __init__(
        self,
        entry_support: EntrySupportDefault[ANode, ChildNode] | None,
        reference: ChildrenStorage[ANode, ChildNode],
        *,
        weak: bool,
    ) -> None:
        super().__init__(reference, self._finaliser)  # type: ignore[call-arg]

        self._hard_ref = reference if not weak else None
        self._entry_support = entry_support

        # print('instantiated _StorageRef', time.monotonic(), self, entry_support, reference, weak)

    # def __del__(self):
    #     print('_StorageRef.__del__', self, self._entry_support)
    #     if (super_del := getattr(super(), '__del__', None)) is not None:
    #         super_del()

    # OK, Match
    @override  # ReferenceType
    def __call__(self) -> ChildrenStorage[ANode, ChildNode] | None:
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


# OK, Match
@final
class EntrySupportDefaultInfo(Generic[ChildNode]):
    """Information about an entry.

    Contains number of nodes, position in the array of nodes, etc.
    """

    # OK, Match
    def __init__(
        self,
        entry_support: EntrySupportDefault[ANode, ChildNode],
        entry: ChildrenEntry[ChildNode],
    ) -> None:
        self._entry_support = entry_support
        self.__entry = entry
        self._length = 0  # Set by ChildrenStorage

    # To make that protected attribute read-only
    @property
    def _entry(self) -> ChildrenEntry[ChildNode]:
        return self.__entry

    # OK, Match
    def nodes(self, *, has_to_exist: bool) -> MutableSequence[ChildNode]:
        return self._entry_support._nodes_for_info(self, has_to_exist=has_to_exist)

    # OK, Match
    def use_nodes(self, nodes: MutableSequence[ChildNode]) -> None:
        # Force creation of the array
        self._entry_support._info_use_nodes(self, nodes)

        children = self._entry_support.children
        # Assign all their nodes the new children
        for node in nodes:
            node._assign_to(children, -1)
            # print(f'EntrySupportDefault._Info.use_nodes: fire parentNode on {node=}')
            node._fire_own_property_change('parentNode', None, children._parent)


class EntrySupportDefault(EntrySupport[ANode, ChildNode]):
    """Default support that just fires changes directly to children and is
    suitable for simple mappings."""

    # This storage gets deleted immediately, effectively making it a dead ref
    # TODO: Review
    __EMPTY: ClassVar = _StorageRef(
        None,
        ChildrenStorage[ANode, ChildNode](_fake=True),
        weak=True,
    )

    __LOCK = Condition()

    # OK, Match
    # Note: map is already initialised to avoid having it Optional
    # (original does not actually check it everytime it tries to use it!).
    def __init__(self, children: _ChildrenEntrySupportInterface[ANode, ChildNode]) -> None:
        # print('instantiating an entry support default', time.monotonic(), self, children)
        super().__init__(children)

        self.__entries: MutableSequence[ChildrenEntry[ChildNode]] = []
        self.__storage: _StorageRef[ANode, ChildNode] = self.__EMPTY
        """Storage of children references"""
        self.__map = dict[ChildrenEntry[ChildNode], EntrySupportDefaultInfo[ChildNode]]()
        """Mapping from entries to info about them."""
        self.__map_lock = RLock()
        self.__init_thread: Thread | None = None
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
            self.__inited
            and ((storage := self.__storage()) is not None)
            and (storage.is_initialised)
        )

    # OK, Match
    @override  # EntrySupport
    def _snapshot(self) -> _DefaultSnapshot[ANode, ChildNode]:
        self.get_nodes()  # As in original. Maybe to create them outside of the mutex?
        with Children.MUTEX.read_access():
            return self._create_snapshot()

    # OK, Match
    # Note: Do not inline, it can be subclassed and/or used independently of _snapshot
    def _create_snapshot(self) -> _DefaultSnapshot[ANode, ChildNode]:
        return _DefaultSnapshot(self.get_nodes(), self.__storage())

    # OK, Match
    # TODO: Two properties, nodes and nodes_optimal?
    @final
    @override  # EntrySupport
    def get_nodes(self, *, optimal_result: bool = False) -> list[ChildNode]:
        # print(f'get_nodes, {optimal_result=}')
        if optimal_result:
            hold = self.__get_storage()  # pyright: ignore[reportUnusedVariable] # noqa: F841
            find = self.children.find_child(None)  # pyright: ignore[reportUnusedVariable] # noqa: F841

        results = [False, False]
        while True:
            # Initialises the storage possibly calls _add_notify if this is for the first time

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
            # If not initialised that means that after we computed the nodes, somebody
            # changed them (as a result of _add_notify()) => We have to compute them again.
            if results[1]:
                # Otherwise is is OK
                return nodes if nodes is not None else []

            elif results[0]:
                # Looks like the result cannot be computed, just give empty one
                self._notify_set_entries()
                return nodes if nodes is not None else []

            # Else, keep trying (loop)

    # OK, Match
    @final
    @override  # EntrySupport
    def get_nodes_count(self, *, optimal_result: bool) -> int:
        return len(self.get_nodes(optimal_result=optimal_result))

    # OK, Match
    @override  # EntrySupport
    def get_node_at(self, index: int) -> ChildNode | None:
        nodes = self.get_nodes()
        return nodes[index] if index < len(nodes) else None

    # OK, Match
    @final
    def _just_compute_nodes(self) -> list[ChildNode]:
        """Computes the nodes now."""

        # print('EntrySupportDefault._just_compute_nodes', time.monotonic(), self, self.__entries)
        nodes = list[ChildNode]()
        for entry in self.__entries:
            info = self.__find_info(entry)
            nodes += info.nodes(has_to_exist=False)

        # Initialises parent nodes
        for i, node in enumerate(nodes):
            if node is None:  # pyright: ignore[reportUnnecessaryComparison]
                _logger.warning('None node among children! index=%d ; nodes=%s', i, nodes)
                msg = f'Node {i} is None'
                raise RuntimeError(msg)

            node._assign_to(self.children, i)
            # print(f'EntrySupportDefault._just_compute_nodes: fire parentNode on {node=}')
            node._fire_own_property_change('parentNode', None, self.children._parent)

        return nodes

    # OK, Match
    def __find_info(self, entry: ChildrenEntry[ChildNode]) -> EntrySupportDefaultInfo[ChildNode]:
        """Finds info for given entry, or registers it, if not registered yet."""

        with self.__map_lock:
            if (info := self.__map.get(entry)) is None:
                info = EntrySupportDefaultInfo(self, entry)
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
    def _set_entries(
        self,
        entries: Iterable[ChildrenEntry[ChildNode]],
        *,
        no_check: bool = False,
    ) -> None:
        # print('EntrySupportDefault._set_entries', time.monotonic(), self, no_check)
        assert no_check or Children.MUTEX.is_write_access

        holder = self.__storage()
        current = holder.nodes if holder is not None else None

        # print(
        #     'EntrySupportDefault._set_entries: '
        #     f'{holder=}, {current=}, {self.__must_notify_set_entries=}',
        # )
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

        # What should be removed
        to_remove = set(self.__entries) - set(entries)
        # print(f'EntrySupportDefault._set_entries: {to_remove=}')
        if to_remove:
            # Notify removing. The set must be ready  for callbacks with questions.
            self.__update_remove(current, to_remove)
            current = holder.nodes
            assert current is not None

        # Change the order of entries. Notifies it and again brings children to up-to-date state.
        to_add = self.__update_order(current, entries)
        # print(f'EntrySupportDefault._set_entries: {to_add=}')
        if to_add:
            # to_add contains Info objects that should be added
            self.__update_add(to_add, list(entries))

    # OK, Match
    def __check_info(
        self,
        info: EntrySupportDefaultInfo[ChildNode] | None,
        entry: ChildrenEntry[ChildNode],
        entries: Iterable[ChildrenEntry[ChildNode]],
        map: Mapping[ChildrenEntry[ChildNode], EntrySupportDefaultInfo[ChildNode]],
    ) -> None:
        if info is None:
            raise RuntimeError(
                f'Error in {type(self).__name__} with entry {entry} from among entries:\n  '
                + '\n  '.join([f'{entry} contained: {entry in map}' for entry in entries])
                + '\n'
                'probably caused by faulty key implementation. The key __hash__() and __eq__() '
                'methods must behave as for an IMMUTABLE object and __hash__() must return the '
                ' same value for __eq__() keys.\nmapping:\n  '
                + '\n  '.join([f'{k} => {v}' for k, v in map.items()]),
            )

    # OK, Match
    def __update_remove(
        self,
        current: Sequence[ChildNode],
        to_remove: Iterable[ChildrenEntry[ChildNode]],
    ) -> None:
        """Removes the objects from the children"""

        assert Children.MUTEX.is_write_access

        nodes = list[ChildNode]()
        storage = self.__storage()
        assert storage is not None

        with self.__map_lock:
            for entry in to_remove:
                info = self.__map.pop(entry, None)

                self.__check_info(info, entry, (), self.__map)
                assert info is not None

                nodes += info.nodes(has_to_exist=True)
                storage._remove(info)
                # Modify the current set of entries
                self.__entries.remove(entry)

        self.__check_consistency()

        # Empty the list of nodes so iit has to be recreated again
        if nodes:
            self.__clear_nodes()
            self._notify_remove(nodes, current)

    # OK, Match
    def __update_order(
        self,
        current: Sized,
        new_entries: Iterable[ChildrenEntry[ChildNode]],
    ) -> list[EntrySupportDefaultInfo[ChildNode]]:
        """Updates the order of entries.

        Args:
            current: Current state of nodes.
            new_entries: New set of entries.

        Returns:
            List of infos that should be added.
        """

        assert Children.MUTEX.is_write_access

        # That assigns entries their beginning position in the array of nodes
        offsets = dict[EntrySupportDefaultInfo[ChildNode], int]()
        previous_pos = 0
        with self.__map_lock:
            for entry in self.__entries:
                info = self.__map.get(entry)
                self.__check_info(info, entry, self.__entries, self.__map)
                assert info is not None

                offsets[info] = previous_pos
                previous_pos += info._length

        to_add = list[EntrySupportDefaultInfo[ChildNode]]()
        perm = [0] * len(current)
        current_pos = 0
        perm_size = 0
        reordered_entries = list[ChildrenEntry[ChildNode]]()
        with self.__map_lock:
            for entry in new_entries:
                info = self.__map.get(entry)

                if info is None:
                    # This info has to be added
                    info = EntrySupportDefaultInfo(self, entry)
                    to_add.append(info)
                else:
                    reordered_entries.append(entry)
                    # Already there => Test if it should not be reordered
                    previous_pos = offsets[info]
                    if current_pos != previous_pos:
                        for i in range(info._length):
                            perm[previous_pos + i] = 1 + current_pos + i
                        perm_size += info._length

                current_pos += info._length

        if perm_size > 0:
            # Now the perm array contains numbers 1 to ... and 0 one places where
            # no permutation occurs => Decrease numbers, replace zeros.
            for i in range(len(perm)):
                if perm[i] == 0:
                    perm[i] = i
                else:
                    perm[i] -= 1

            # reordered_entries are not None
            self.__entries = reordered_entries
            self.__check_consistency()

            # Notify the permutation to the parent
            self.__clear_nodes()
            if (parent := self.children._parent) is not None:
                parent._fire_reorder_change(perm)

        return to_add

    # OK, Match
    def __update_add(
        self,
        infos: Iterable[EntrySupportDefaultInfo[ChildNode]],
        entries: MutableSequence[ChildrenEntry[ChildNode]],
    ) -> None:
        """Update the state of children by adding given Infos.

        Args:
            infos: List of Info objects to add.
            entries: The final state of entries that should occur.
        """

        assert Children.MUTEX.is_write_access

        nodes = list[ChildNode]()
        with self.__map_lock:
            for info in infos:
                nodes += info.nodes(has_to_exist=False)
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
    def _refresh_entry(self, entry: ChildrenEntry[ChildNode]) -> None:
        """Refreshes content of one entry.

        Update the state of children appropriately.
        """

        if (holder := self.__storage()) is None:
            return
        if (current := holder.nodes) is None:
            # The initialisation is not finished yet
            return

        self.__check_consistency()
        with self.__map_lock:
            if (info := self.__map.get(entry)) is None:
                # Refresh of entry that is not present
                return

        old_nodes = info.nodes(has_to_exist=False)
        # Warning, entry.nodes() could return None, from Children.Map._refresh_key
        new_nodes = info._entry.nodes(None)
        if old_nodes == new_nodes:
            # Nodes are the same
            return

        to_remove = set(old_nodes) - set(new_nodes)
        if to_remove:
            # Notify removing, the set must be ready for callbacks with questions
            # modifies the list associated with the info
            for node in to_remove:
                old_nodes.remove(node)
            self.__clear_nodes()
            # Now everythin should be consistent => notify the remove
            self._notify_remove(to_remove, current)
            current = holder.nodes

        to_add = self.__refresh_order(entry, old_nodes, new_nodes)
        info.use_nodes(new_nodes)
        if to_add:
            # Notifies the list associated with the info
            self.__clear_nodes()
            self._notify_add(to_add)

    # OK, Match
    def __refresh_order(
        self,
        entry: ChildrenEntry[ChildNode],
        old_nodes: Collection[ChildNode],
        new_nodes: MutableSequence[ChildNode],
    ) -> list[ChildNode]:
        """Update the order of nodes after a refresh.

        Args:
            entry: The refreshed entry.
            old_nodes: Nodes that are currently in the list.
            new_nodes: New nodes (defining the order of old_nodes and some more)

        Returns:
            List of infos that should be added.
        """

        to_add = list[ChildNode]()
        old_nodes_set = set(old_nodes)
        to_process = set(old_nodes_set)
        perm_array: list[ChildNode] = []

        for i, node in enumerate(new_nodes[:]):
            if node in old_nodes_set:
                # If the node is in the old set, test it for permutation
                old_nodes_set.remove(node)
                perm_array.append(node)
            elif node not in to_process:
                # The node have not been processed yet
                to_add.append(node)
            else:
                new_nodes.pop(i)

        perm = node_operations.compute_permutation(old_nodes, perm_array)
        if perm:
            # Apply the permutation
            self.__clear_nodes()
            # Temporarily change the nodes the entry should use
            self.__find_info(entry).use_nodes(perm_array)
            parent = self.children._parent
            if parent is not None:
                parent._fire_reorder_change(perm)

        return to_add

    # OK, Match
    def _notify_remove(
        self,
        nodes: Collection[ChildNode],
        current: Sequence[ChildNode],
    ) -> Collection[ChildNode]:
        """Notifies that a set of nodes has been removed from children.

        It is necessary that the system is already in consistentstate, so any
        callbacks will return valid values.

        Args:
            nodes: List of removed nodes.
            current: State of nodes.

        Returns:
            Collection of nodes that were deleted.
        """

        children = self.children

        # During a deserialisation it may have parent == None
        if children._parent is not None:
            # Fire change of nodes
            if children._entry_support_raw is self:
                children._parent._fire_sub_nodes_change(False, nodes, current)  # noqa: FBT003

            # Fire change of parent
            for node in nodes:
                node._deassign_from(children)
                node._fire_own_property_change('parentNode', children._parent, None)

        children._destroy_nodes(nodes)
        return nodes

    # OK, Match
    def _notify_add(self, nodes: Sequence[ChildNode]) -> None:
        """Notifies that a set of nodes has been added to children.

        It is necessary that the system is already in consistent state, so any
        callbacks will return valid values.
        """

        # Notifies about parent change
        for node in nodes:
            node._assign_to(self.children, -1)
            # print(f'EntrySupportDefault._notify_add: fire parentNode on {node=}')
            node._fire_own_property_change('parentNode', None, self.children._parent)

        parent = self.children._parent
        # print(
        #     f'EntrySupportDefault._notify_add: '
        #     f'{nodes=}, {parent=}, {self.children._entry_support_raw=}, {self=}',
        # )
        if (parent is not None) and (self.children._entry_support_raw is self):
            parent._fire_sub_nodes_change(True, nodes, None)  # noqa: FBT003

    # OK, Match
    @override  # EntrySupport
    def test_nodes(self) -> list[ChildNode] | None:
        """Returns either nodes associated with this children, or None if they are not created."""

        storage = self.__storage()
        if storage is None:
            return None

        with Children.MUTEX.read_access():
            return storage.nodes

    # OK, Match
    def __get_storage(
        self,
        cannot_work_better: MutableSequence[bool] | None = None,
    ) -> ChildrenStorage[ANode, ChildNode]:
        """Obtains reference to storage.

        If it does not exist, it is created.

        Args:
            cannot_work_better: Array of sizes 1 or None. Will contain True if the
            `__get_storage()` cannot be initialised (we are under read access and
            another thread is responsible for initialisation). In such case, give
            up on computation of best result.
        """

        do_initialise = False

        with EntrySupportDefault.__LOCK:
            if (storage := self.__storage()) is None:
                storage = ChildrenStorage[ANode, ChildNode]()
                # Register the storage with the children
                self._register_children_storage(storage, weak=False)
                do_initialise = True
                self.__init_thread = threading.current_thread()

        if do_initialise:
            # This call can cause a lot of callbacks. Be prepared to handle as
            # clean as possible.
            try:
                self.children._call_add_notify()
            finally:
                notify_later = Children.MUTEX.is_read_access
                # Now attach to entry_support, so when entry_support is None
                # we are not fully initialised!!
                storage.entry_support = self
                self.__inited = True

                def set_and_notify() -> None:
                    with EntrySupportDefault.__LOCK:
                        self.__init_thread = None
                        EntrySupportDefault.__LOCK.notify_all()

                if notify_later:
                    # The notify to the lock has to be done later than _set_keys()
                    # is executed, otherwise the result of _add_notify() might
                    # not be visible to other threads.
                    Children.MUTEX.post_write_request(set_and_notify)
                else:
                    set_and_notify()

        elif self.__init_thread is not None:
            # Otherwise, if not initialised yet (storage.children) wait for the
            # initialisation to finish, but only if we can wait.
            if (
                Children.MUTEX.is_read_access
                or Children.MUTEX.is_write_access
                or (self.__init_thread == threading.current_thread())
            ):
                # Fail, we are in read access
                if cannot_work_better is not None:
                    cannot_work_better[0] = True

                storage.entry_support = self
                return storage

            # Otherwise we can wait
            with EntrySupportDefault.__LOCK:
                EntrySupportDefault.__LOCK.wait_for(lambda: self.__init_thread is None)

        return storage

    def _get_raw_storage(self) -> ChildrenStorage[ANode, ChildNode]:
        return self.__get_storage()

    def _nodes_for_info(
        self,
        info: EntrySupportDefaultInfo[ChildNode],
        *,
        has_to_exist: bool,
    ) -> MutableSequence[ChildNode]:
        # Force creation of the array
        assert (not has_to_exist) or (self.__storage() is not None), (
            'ChildrenStorage is not initialised'
        )

        storage = self.__get_storage()
        return storage.nodes_for(info, has_to_exist=has_to_exist)

    def _info_use_nodes(
        self,
        info: EntrySupportDefaultInfo[ChildNode],
        nodes: MutableSequence[ChildNode],
    ) -> None:
        storage = self.__get_storage()
        storage.use_nodes(info, nodes)

    # OK, Match
    def __clear_nodes(self) -> None:
        """Clear the nodes"""

        storage = self.__storage()
        if storage is not None:
            storage.clear()

    # OK, Match
    @final
    def _register_children_storage(
        self,
        storage: ChildrenStorage[ANode, ChildNode],
        *,
        weak: bool,
    ) -> None:
        """Registration of ChildrenStorage.

        Args:
            storage: The associated ChildrenStorage.
            weak: Use weak or hard reference.
        """

        with EntrySupportDefault.__LOCK:
            if (self.__storage() is storage) and (self.__storage._is_weak is weak):
                return

            self.__storage = _StorageRef(self, storage, weak=weak)

    # OK, Match
    @final
    def _finalised_children_storage(
        self,
        caller: ReferenceType[ChildrenStorage[ANode, ChildNode]],
    ) -> None:
        """_StorageRef has a finaliser, that ends up calling this method for itself"""
        assert caller() is None

        def run() -> None:
            with EntrySupportDefault.__LOCK:
                if (self.__storage is caller) and (self.children._entry_support_raw is self):
                    # Really finalised and not reconstructed
                    self.__must_notify_set_entries = False
                    self.__storage = EntrySupportDefault[ANode, ChildNode].__EMPTY
                    self.__inited = False
                    self.children._call_remove_notify()
                    assert self.__storage is EntrySupportDefault[ANode, ChildNode].__EMPTY

        # Usually in _remove_notify() _set_keys() is called => better require write access
        try:
            Children.MUTEX.post_write_request(run)
        except RuntimeError as ex:
            msg = f'Proot at {time.monotonic()} in {self} with storage ref={caller}=>{caller()}'
            raise RuntimeError(msg) from ex

    # OK, Match
    @property
    @override  # EntrySupport
    def _entries(self) -> list[ChildrenEntry[ChildNode]]:
        return list(self.__entries)

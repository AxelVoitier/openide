# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# From: https://github.com/apache/netbeans/blob/master/platform/openide.nodes/src/org/openide/nodes/Children.java  # noqa: E501

from __future__ import annotations

# System imports
import logging
from abc import ABC, abstractmethod
from collections.abc import Hashable
from copy import copy
from threading import RLock
from typing import TYPE_CHECKING, final, cast, Generic, TypeVar

# Third-party imports

# Local imports
from openide.utils import Mutex
from openide.utils.classes import Debug
from openide.utils.typing import override


T = TypeVar('T')
T_Hashable = TypeVar('T_Hashable', bound=Hashable)
K = TypeVar('K')
if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence, MutableSequence, MutableMapping
    from typing import Optional, Union, Callable, Type, Any
    from openide.nodes._like_netbeans.node import Node
    from openide.nodes._like_netbeans.entry_support import EntrySupport
    from openide.nodes._like_netbeans.child_factory import ChildFactory


_logger = logging.getLogger(__name__)


# TODO: Clarify privileged API between Children and all the subclasses here (Array, Map, Keys, ...).
# TODO: Possible rewrite while still keeping model/view separation.
# TODO: Not all subclasses seems to implement/be cloneable?!


class Children(ABC, Debug(f'{__name__}.Children')):

    MUTEX = Mutex()
    _LOCK = RLock()  # Class lock

    class Entry(ABC):

        @abstractmethod
        def nodes(self, source: Any) -> MutableSequence[Node]:
            raise NotImplementedError()  # pragma: no cover

    # Set later, for Java API compat
    LEAF: Children = None  # type: ignore[assignment]
    Array: Type[Array] = None  # type: ignore[assignment]
    SortedArray: Type[SortedArray] = None  # type: ignore[assignment]
    Map: Type[Map] = None  # type: ignore[assignment]
    Keys: Type[Keys] = None  # type: ignore[assignment]

    # OK, Match
    def __init__(self, _lazy: bool = False) -> None:
        super().__init__()

        self.__entry_support: Optional[EntrySupport] = None
        self._lazy_support = _lazy
        self._parent: Optional[Node] = None
        self._lock = RLock()  # Instance lock

    # OK, Match
    @property
    def _entry_support(self) -> EntrySupport:
        with Children._LOCK:
            if (entry_support := self._entry_support_raw) is None:
                if self._lazy_support:
                    from openide.nodes._like_netbeans.entry_support_lazy import EntrySupportLazy

                    entry_support = EntrySupportLazy(self)
                else:
                    from openide.nodes._like_netbeans.entry_support_default import EntrySupportDefault

                    entry_support = EntrySupportDefault(self)

                self._entry_support_raw = entry_support
                self._post_init_entry_support(entry_support)

            return entry_support

    # OK, Match
    def _post_init_entry_support(self, entry_support: EntrySupport) -> None:
        pass

    # OK, Match
    def _check_support(self) -> None:
        pass

    # OK, Match
    @property
    def _is_lazy(self) -> bool:
        return self._lazy_support

    # OK, Match
    @final
    def _attach_to(self, parent: Node) -> None:
        if self is Children.LEAF:
            return

        with self._lock:
            if self._parent is not None:
                raise RuntimeError(
                    'An instance of Children may not be used for more than one parent node')

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
        if self is Children.LEAF:
            return

        with self._lock:
            if (old_parent := self._parent) is None:
                raise RuntimeError('Trying to detach children which do not have parent')

            self._parent = None

        with Children.MUTEX.read_access():
            nodes = self.__test_nodes()
            if not nodes:
                return

            for i, node in enumerate(nodes):
                node._deassign_from(self)
                node._fire_own_property_change('parentNode', old_parent, None)

    # OK, Match
    @staticmethod
    def create(factory: ChildFactory, asynchronous: bool) -> Children:
        children: Children
        if not asynchronous:
            from openide.nodes._like_netbeans.sync_children import SyncChildren

            children = SyncChildren(factory)

        else:
            from openide.nodes._like_netbeans.async_children import AsyncChildren

            children = AsyncChildren(factory)

        factory._observer = children

        return children

    # OK, Match
    @staticmethod
    def create_lazy(factory_cb: Callable[[], Children]) -> Children:
        return _LazyChildren(factory_cb)

    # OK, Match
    @property
    def node(self) -> Optional[Node]:
        return self._parent

    # TODO: Review
    def __deepcopy__(self, memo: dict[int, Any]) -> Children:
        '''
        Subclasses should first call super().__deepcopy__() to get
        an instance. And then call their own SubClass.__init__(instance, ...)
        (or do the initialisation in __deepcopy__ as they see fit).

        Subclasses that don't want to be cloned should overload
        and just return Children.LEAF.
        '''

        new = Children.__new__(type(self))
        Children.__init__(new, self._lazy_support)

        return new

    # OK, Match
    @abstractmethod
    def add(self, nodes: Sequence[Node]) -> bool:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    @abstractmethod
    def remove(self, nodes: Sequence[Node]) -> bool:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    def find_child(self, system_name: Optional[str]) -> Optional[Node]:
        nodes = self.get_nodes()

        if not nodes:
            return None

        if system_name is None:
            return nodes[0]

        for node in nodes:
            if node.system_name == system_name:
                return node
        else:
            return None

    # OK, Match
    @property
    @final
    def _is_initialised(self) -> bool:
        return self._entry_support.is_initialised

    # OK, Match
    # TODO: __getitem__?
    @final
    def get_node_at(self, index: int) -> Optional[Node]:
        self._check_support()
        return self._entry_support.get_node_at(index)

    # OK, Match
    # TODO: Transform into 2 properties, "nodes" (final), and "nodes_optimal" (or something
    # like that). Potentially propagate to EntrySupport (and all its implementations).
    # Note: getNodes() is final, but getNodes(optimalResult) is not.
    def get_nodes(self, optimal_result: bool = False) -> Sequence[Node]:
        self._check_support()
        return self._entry_support.get_nodes(optimal_result)

    # OK, Match
    # TODO: __len__? (Using the False default for optimal)
    # Or just let client code do len(children.nodes) or len(children.nodes_optimal)?
    # Note: getNodesCount() is final, but getNodesCount(optimalResult) is not.
    def get_nodes_count(self, optimal_result: bool = False) -> int:
        self._check_support()
        return self._entry_support.get_nodes_count(optimal_result)

    # OK, Match
    @final
    def snapshot(self) -> Sequence[Node]:
        return self._entry_support._snapshot()

    # OK, Match
    @final
    def _get_snapshot_indexes(self, snapshot: Sequence[Node]) -> Sequence[int]:
        return list(range(len(snapshot)))  # Seriously? Java needs a 4 lines function for that??

    # OK, Match
    def _add_notify(self) -> None:
        pass

    # OK, Match
    def _remove_notify(self) -> None:
        pass

    # OK, Match
    def _call_add_notify(self) -> None:
        self._add_notify()

    # OK, Match
    def _call_remove_notify(self) -> None:
        self._remove_notify()

    # OK, Match
    def _destroy_nodes(self, array: Iterable[Node]) -> None:
        pass

    # OK, Match
    def __test_nodes(self) -> Optional[Sequence[Node]]:
        if (entry_support := self.__entry_support) is not None:
            # Note: Compared to original, we are skipping the getter, sparing us a lock acquisition
            return entry_support.test_nodes()
        else:
            return None

    # OK, Match
    @property
    def _entry_support_raw(self) -> Optional[EntrySupport]:
        return self.__entry_support

    # OK, Match
    @_entry_support_raw.setter
    @final
    def _entry_support_raw(self, value: Optional[EntrySupport]) -> None:
        assert Children._LOCK._is_owned()  # type: ignore[attr-defined]
        self.__entry_support = value


class __Empty(Children):

    @override  # Children
    def add(self, nodes: Sequence[Node]) -> bool:
        return False

    @override  # Children
    def remove(self, nodes: Sequence[Node]) -> bool:
        return False


Children.LEAF = __Empty()


class Array(Children):

    __COLLECTION_LOCK = RLock()

    # OK, Match
    class __ArrayEntry(Children.Entry):

        def __init__(self, array: Array) -> None:
            super().__init__()
            self._array = array

        # OK, Match
        @override  # Children.Entry
        def nodes(self, source: Any) -> MutableSequence[Node]:
            if not (collection := self._array._collection):
                return []
            else:
                with Array._Array__COLLECTION_LOCK:
                    return list(collection)

    # OK, Match
    def __init__(self, _nodes: Optional[MutableSequence[Node]] = None, _lazy: bool = False) -> None:
        if _nodes is not None:
            # Match original behaviour of protected constructors
            _lazy = False

        super().__init__(_lazy)

        self._nodes_entry: Optional[Children.Entry] = None
        if not _lazy:
            self._nodes_entry = self._create_nodes_entry()

        self._nodes = _nodes

    # OK, Match
    @override  # Children
    def _post_init_entry_support(self, entry_support: EntrySupport) -> None:
        if not self._lazy_support:
            if self._nodes_entry is None:
                self._nodes_entry = self._create_nodes_entry()

            entry_support._set_entries((self._nodes_entry, ), True)

        elif self._nodes_entry is not None:
            self._nodes_entry = None

    # TODO: Review
    def __deepcopy__(self, memo: dict[int, Any]) -> Array:
        new = cast(Array, super().__deepcopy__(memo))

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

    # OK, Match
    def _init_collection(self) -> MutableSequence[Node]:
        return list()

    # OK, Match
    # Note: Inlined refreshImpl as it did not seemed to be (locally) subclassed
    @final
    def _refresh(self) -> None:
        self._check_support()
        if self._lazy_support:
            return

        def _implementation() -> None:
            assert self._nodes_entry is not None  # Because it can be None only if lazy. For mypy.

            if self._is_initialised:
                self._entry_support._refresh_entry(self._nodes_entry)
                self._entry_support.get_nodes(False)

            elif self._nodes is not None:
                for node in self._nodes:
                    node._assign_to(self, -1)

        Children.MUTEX.post_write_request(_implementation)

    # OK, Match
    def _create_nodes_entry(self) -> Children.Entry:
        return Array.__ArrayEntry(self)

    # OK, Match
    @property
    @final
    def _collection(self) -> MutableSequence[Node]:
        with Array.__COLLECTION_LOCK:
            if (nodes := self._nodes) is None:
                nodes = self._nodes = self._init_collection()

        return nodes

    # OK, Match
    @override  # Children
    def add(self, nodes: Sequence[Node]) -> bool:
        with Array.__COLLECTION_LOCK:
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
    @override  # Children
    def remove(self, nodes: Sequence[Node]) -> bool:
        with Array.__COLLECTION_LOCK:
            collection = self._collection
            len_before = len(collection)

            if collection == nodes:
                collection.clear()
            else:
                for node in nodes:
                    collection.remove(node)
            len_after = len(collection)

        changed = len_after - len_before
        if not changed:
            return False
        else:
            self._refresh()
            return True


Children.Array = Array


class SortedArray(Array):

    # OK, Match
    class __SortedArrayEntry(Children.Entry):

        def __init__(self, array: SortedArray) -> None:
            super().__init__()
            self._array = array

        # OK, reversed is an additional behaviour
        @override  # Children.Entry
        def nodes(self, source: Any) -> MutableSequence[Node]:
            collection = self._array._collection
            return sorted(collection, key=self._array.key, reverse=self._array.is_reversed)

    # OK, reversed is an additional behaviour
    def __init__(self, _nodes: Optional[MutableSequence[Node]] = None) -> None:
        super().__init__(_nodes=_nodes)

        self.__key: Optional[Callable[[Node], Any]] = None
        self._reversed = False

    # OK, Match
    @property
    def key(self) -> Optional[Callable[[Node], Any]]:
        return self.__key

    # OK, Match
    @key.setter
    def key(self, key: Optional[Callable[[Node], Any]]) -> None:
        with Children.MUTEX.write_access():
            self.__key = key
            self._refresh()

    @property
    def is_reversed(self) -> bool:
        return self._reversed

    @is_reversed.setter
    def is_reversed(self, reversed: bool) -> None:
        with Children.MUTEX.write_access():
            self._reversed = reversed
            self._refresh()

    # OK, Match
    @override  # Array
    def _create_nodes_entry(self) -> Children.Entry:
        return SortedArray.__SortedArrayEntry(self)


Children.SortedArray = SortedArray


class Map(Children, Generic[T_Hashable]):

    # OK, Match
    # TODO: For some reasons, original does not have this one private?!
    class _MapEntry(Children.Entry):

        def __init__(self, key: T_Hashable, node: Node) -> None:
            super().__init__()

            self.key = key
            self.node = node

        # OK, Match
        @override  # Children.Entry
        def nodes(self, source: Any) -> MutableSequence[Node]:
            return [self.node]

        # OK, Match
        def __hash__(self) -> int:
            return hash(self.key)

        # OK, Match
        def __eq__(self, other: Any) -> bool:
            if isinstance(other, Map._MapEntry):
                return self.key == (other.key)
            else:
                return False

    # OK, Match
    def __init__(self, _map: Optional[MutableMapping[T_Hashable, Node]] = None) -> None:
        super().__init__()

        self._nodes = _map

    # OK, Match
    @property
    @final
    def _map(self) -> MutableMapping[T_Hashable, Node]:
        if (nodes := self._nodes) is None:
            nodes = self._nodes = self._init_map()

        return nodes

    # OK, Match
    @final
    @override  # Children
    def _call_add_notify(self) -> None:
        self._entry_support._set_entries(self._create_entries(self._map), True)
        super()._call_add_notify()

    # OK, Match
    def _create_entries(self, map: MutableMapping[T_Hashable, Node]) -> Sequence[Children.Entry]:
        return [Map._MapEntry(k, v) for k, v in map.items()]

    # OK, Match
    # Note: Inlined refreshImpl as it did not seemed to be (locally) subclassed
    @final
    def _refresh(self) -> None:
        with Children.MUTEX.write_access():
            self._entry_support._set_entries(self._create_entries(self._map))

    # OK, Match
    # Note: Inlined refreshImpl as it did not seemed to be (locally) subclassed
    @final
    def _refresh_key(self, key: T_Hashable) -> None:
        with Children.MUTEX.write_access():
            self._entry_support._refresh_entry(Map._MapEntry(key, None))

    # OK, Match
    @final
    def _put_all(self, map: MutableMapping[T_Hashable, Node]) -> None:
        with Children.MUTEX.write_access():
            self._map.update(map)
            self._refresh()

    # OK, Match
    # Note: Calling the mutex-wrapped refresh methods as we inlined the implementation ones
    @final
    def _put(self, key: T_Hashable, node: Node) -> None:
        with Children.MUTEX.write_access():
            changed = key in self._map
            self._map[key] = node

            if changed:
                self._refresh_key(key)
            else:
                self._refresh()

    # OK, but why does it take a mapping instead of a collection, like in the original?
    # Also, we take the opportunity to be able to detect when there is a change
    # to refresh conditionaly.
    @final
    def _remove_all(self, map: MutableMapping[T_Hashable, Node]) -> None:
        with Children.MUTEX.write_access():
            our_map = self._map
            changed = False
            for key in map.keys():
                if key in our_map:
                    del our_map[key]
                    changed = True

            if changed:
                self._refresh()

    # OK, Match (with name change)
    def _remove_key(self, key: T_Hashable) -> None:
        with Children.MUTEX.write_access():
            if (self._nodes is not None) and (key in self._nodes):
                del self._nodes[key]
                self._refresh()

    # OK, Match
    def _init_map(self) -> MutableMapping[T_Hashable, Node]:
        return dict()

    # OK, Match
    @override  # Children
    def add(self, nodes: Sequence[Node]) -> bool:
        return False

    # OK, Match
    @override  # Children
    def remove(self, nodes: Sequence[Node]) -> bool:
        return False


Children.Map = Map


# TODO: SortedMap (any use?)


class Keys(Array, ABC, Generic[T]):

    _LOCK = RLock()
    __LAST_RUNS: MutableMapping[Keys, Callable[[], None]] = dict()

    # OK, Match
    # Note: Original separates it in two classes Dupl+KE, with Dupl being
    # protected (ie. package-private). But apparently, that's just for testing reason.
    class _KeyEntry(Children.Entry, Generic[K]):

        # OK, Match
        def __init__(self, keys: Keys, key: Optional[K] = None) -> None:
            super().__init__()

            self._keys = keys
            self._key: Optional[Union[K, Keys._KeyEntry[K]]] = key

        # OK, Match
        @override  # Children.Entry
        def nodes(self, source: Any) -> MutableSequence[Node]:
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
            counter: Optional[MutableMapping[K, int]] = None,
        ) -> None:
            if counter is None:
                counter = dict()

            for obj in source:
                count = counter.get(obj, 0)
                counter[obj] = count + 1
                target.append(self.__create_instance(obj, count))

        # OK, Match
        @property
        def key(self) -> Optional[K]:
            if isinstance(self._key, Keys._KeyEntry):
                return self._key.key  # Yo dawg
            else:
                return self._key

        # OK, Match
        # TODO: Rename index?
        @property
        def count(self) -> int:
            counter = 0
            d: Optional[Union[K, Keys._KeyEntry]] = self

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
        def __hash__(self) -> int:
            return hash(self.key)

        # OK, Match
        def __eq__(self, other: Any) -> bool:
            if isinstance(other, Keys._KeyEntry):
                return (self.key == other.key) and (self.count == other.count)
            else:
                return False

    # OK, Match
    def __init__(self, _lazy: bool = False) -> None:
        super().__init__(_lazy=_lazy)

        self.__before = False

    # TODO: Review
    def __deepcopy__(self, memo: dict[int, Any]) -> Keys:
        new = cast(Keys, super().__deepcopy__(memo))
        new.__before = self.__before

        return new

    # OK, Match
    @override  # Children
    def _check_support(self) -> None:
        if self._lazy_support and self._nodes:
            self._fallback_to_default_support()

    # OK, Match
    def _fallback_to_default_support(self) -> None:
        _logger.warning(
            'Falling back to non lazy entry support. A Children.Array methods was used')
        self._switch_support(False)

    # OK, Match
    def _switch_support(self, to_lazy: bool) -> None:
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
                    self._parent._fire_sub_nodes_change_idx(False, indexes, None, [], snapshot)

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
    def _create_nodes(self, key: T) -> Optional[Sequence[Node]]:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    @override  # Children
    def _destroy_nodes(self, nodes: Iterable[Node]) -> None:
        for node in nodes:
            node._fire_node_destroyed()

    # OK, Match
    @classmethod
    def __keys_enter(cls, children: Keys, call: Callable[[], None]) -> None:
        with cls._LOCK:
            cls.__LAST_RUNS[children] = call

    # OK, Match
    @classmethod
    def __keys_exit(cls, children: Keys, call: Callable[[], None]) -> None:
        with cls._LOCK:
            was = cls.__LAST_RUNS.pop(children, None)

            if (was is not None) and (was != call):
                cls.__LAST_RUNS[children] = was

    # OK, Match
    @classmethod
    def __keys_check(cls, children: Keys, call: Callable[[], None]) -> bool:
        with cls._LOCK:
            return call == cls.__LAST_RUNS.get(children)


Children.Keys = Keys  # type: ignore[misc]


class _LazyChildren(Children):

    # OK, Match
    def __init__(self, factory: Callable[[], Children]) -> None:
        super().__init__()

        self.__factory = factory
        self.__original: Optional[Children] = None
        self.__original_lock = RLock()

    # OK, Match
    @property
    def _original(self) -> Children:
        with self.__original_lock:
            if self.__original is None:
                self.__original = self.__factory()

            return self.__original

    # OK, Match
    @override  # Children
    def add(self, nodes: Sequence[Node]) -> bool:
        return self._original.add(nodes)

    # OK, Match
    @override  # Children
    def remove(self, nodes: Sequence[Node]) -> bool:
        return self._original.remove(nodes)

    # OK, Match
    @override  # Children
    def _add_notify(self) -> None:
        self._original._add_notify()

    # OK, Match
    @override  # Children
    def _remove_notify(self) -> None:
        self._original._remove_notify()

    # OK, Match
    @property
    @override  # Children
    def _entry_support(self) -> EntrySupport:
        return self._original._entry_support

    # OK, Match
    @override  # Children
    def find_child(self, name: Optional[str]) -> Optional[Node]:
        return self._original.find_child(name)

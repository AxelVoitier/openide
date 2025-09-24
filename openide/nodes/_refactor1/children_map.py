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
from collections.abc import Hashable, Iterable
from typing import TYPE_CHECKING, Generic, TypeVar, final

# Third-party imports
from typing_extensions import override

# Local imports
from .children import Children, ChildrenEntry, _ChildrenSubClassInterface
from .node import ChildNode, ParentNode

T_Hashable = TypeVar('T_Hashable', bound=Hashable)

if TYPE_CHECKING:
    from collections.abc import MutableMapping, MutableSequence, Sequence
    from typing import Any, Final

__all__: Final = ('ChildrenMap',)

_logger = logging.getLogger(__name__)


# OK, Match
# TODO: For some reasons, original does not have this one private?!
class __MapEntry(ChildrenEntry[ChildNode], Generic[T_Hashable, ChildNode]):
    """Entry mapping one key to a node"""

    def __init__(self, key: T_Hashable, node: ChildNode) -> None:
        super().__init__()

        self.key = key
        self.node = node

    # OK, Match
    @override  # ChildrenEntry
    def nodes(self, source: Any) -> MutableSequence[ChildNode]:
        return [self.node]

    # OK, Match
    @override  # object
    def __hash__(self) -> int:
        return hash(self.key)

    # OK, Match
    @override  # object
    def __eq__(self, other: object) -> bool:
        if isinstance(other, __MapEntry):
            return self.key == (other.key)
        else:
            return False


class _ChildrenMapBase(Children[ParentNode, ChildNode], Generic[T_Hashable, ParentNode, ChildNode]):
    # OK, Match
    def __init__(self, *, _map: MutableMapping[T_Hashable, ChildNode] | None) -> None:
        super().__init__()

        self._nodes = _map
        """A map to store children in.

        Do NOT modify elements directly in this map! Use it only for read access.
        """

    # OK, Match
    @property
    @final
    def _map(self) -> MutableMapping[T_Hashable, ChildNode]:
        """Getter of child nodes map.

        Instantiate the map if needed.
        """

        if (nodes := self._nodes) is None:
            nodes = self._nodes = self._init_map()

        return nodes

    # OK, Match
    @final
    @override  # Children
    def _call_add_notify(self) -> None:
        self._entry_support._set_entries(self._create_entries(self._map), no_check=True)
        super()._call_add_notify()

    # Following methods are defined in _ChildrenMapSubClassInterface
    def _init_map(self) -> MutableMapping[T_Hashable, ChildNode]: ...
    def _create_entries(
        self,
        map: MutableMapping[T_Hashable, ChildNode],
    ) -> Sequence[ChildrenEntry[ChildNode]]: ...


class _ChildrenMapChildrenSubClassInterface(
    # _MapBase[T_Hashable, ParentNode, ChildNode],
    _ChildrenSubClassInterface[ChildNode],
):
    # OK, Match
    @override  # Children
    def add(self, nodes: Sequence[ChildNode]) -> bool:
        """Does nothing.

        Should be reimplemented in a subclass wishing to support external addition
        of nodes.
        """

        return False

    # OK, Match
    @override  # Children
    def remove(self, nodes: Sequence[ChildNode]) -> bool:
        """Does nothing.

        Should be reimplemented in a subclass wishing to support external removal
        of nodes.
        """

        return False


class _ChildrenMapSubClassInterface(_ChildrenMapBase[T_Hashable, ParentNode, ChildNode]):
    # OK, Match
    @override  # _ChildrenMapBase
    def _init_map(self) -> MutableMapping[T_Hashable, ChildNode]:
        """Allows subclasses to instantiate the map the first time the children are used.

        It is called only if the map has not been passed in the constructor.

        Returns:
            Default implementation returns an empty map. Subclasses may return a
            map already containing child nodes.
        """

        return {}

    # OK, Match
    @override  # _ChildrenMapBase
    def _create_entries(
        self,
        map: MutableMapping[T_Hashable, ChildNode],
    ) -> Sequence[ChildrenEntry[ChildNode]]:
        """Allows subclasses to redefine order of entries"""

        return [__MapEntry(k, v) for k, v in map.items()]

    # OK, Match
    # Note: Inlined refreshImpl as it did not seemed to be (locally) subclassed
    @final
    def _refresh(self) -> None:
        """Updates the state of nodes in the map.

        Can be called by subclasses that directly modify the nodes map to update
        the state of nodes appropriately.
        """

        with Children.MUTEX.write_access():
            self._entry_support._set_entries(self._create_entries(self._map))

    # OK, Match
    # Note: Inlined refreshImpl as it did not seemed to be (locally) subclassed
    @final
    def _refresh_key(self, key: T_Hashable) -> None:
        """Updates the state of a node in the map.

        Can be called by subclasses that directly modify a node in the map map
        to update the state of it appropriately.

        Args:
            key: The key that should be refreshed.
        """

        with Children.MUTEX.write_access():
            self._entry_support._refresh_entry(__MapEntry(key, None))

    # OK, Match
    # Note: Calling the mutex-wrapped refresh methods as we inlined the implementation ones
    @final
    def _put(self, key: T_Hashable, node: ChildNode) -> None:
        """Adds one key-node pair to the map

        Args:
            key: The key to add.
            node: The node to add associated with the key.
        """

        with Children.MUTEX.write_access():
            changed = key in self._map
            self._map[key] = node

            if changed:
                self._refresh_key(key)
            else:
                self._refresh()

    # OK, Match
    @final
    def _put_all(self, map: MutableMapping[T_Hashable, ChildNode]) -> None:
        """Adds a collection of new key/value pairs into the map.

        The supplied map may contain any keys, but the values must be Nodes.

        Args:
            map: The map with pairs to add.
        """

        with Children.MUTEX.write_access():
            self._map.update(map)
            self._refresh()

    # OK, Match (with name change)
    def _remove_key(self, key: T_Hashable) -> None:
        """Remove a given child node from the map by its key.

        Args:
            key: The key to remove.
        """

        with Children.MUTEX.write_access():
            if (self._nodes is not None) and (key in self._nodes):
                del self._nodes[key]
                self._refresh()

    # We take the opportunity to be able to detect when there is a change
    # to refresh conditionally.
    @final
    def _remove_all(self, keys: Iterable[T_Hashable]) -> None:
        """Removes some children from the map by key

        Args:
            keys: The collection of keys to remove.
        """

        with Children.MUTEX.write_access():
            our_map = self._map
            changed = False
            for key in keys:
                if key in our_map:
                    del our_map[key]
                    changed = True

            if changed:
                self._refresh()


class ChildrenMap(
    _ChildrenMapSubClassInterface[T_Hashable, ParentNode, ChildNode],
    _ChildrenMapChildrenSubClassInterface[ChildNode],
    _ChildrenMapBase[T_Hashable, ParentNode, ChildNode],
    Children[ParentNode, ChildNode],
):
    """Implements the storage of node children in a map.

    This class also premits association of a key with any node, and to remove
    nodes by key.
    Subclasses should reasonably implement add() and remove().

    Args:
        T_Hashable: The type of the keys. Must be Hashable.
        ParentNode: The type of those children parent node.
        ChildNode: The type of node those children have.
    """

    # OK, Match
    def __init__(self, _map: MutableMapping[T_Hashable, ChildNode] | None = None) -> None:
        """Initialises a new ChildrenMap.

        Args:
            _nodes: Allows a subclass to provide its own implementation for the
                    map in which child nodes are stored in.
                    The map must not be directly modified afterwards.
                    If None, the internal map will be created after a call
                    to _init_map() the first time it needs it.
        """

        super().__init__(_map=_map)


Children.Map = ChildrenMap


# TODO: SortedMap (any use?)

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
from threading import RLock
from typing import TYPE_CHECKING, Generic, final
from weakref import WeakKeyDictionary

# Third-party imports
from typing_extensions import override

# Local imports
from .children import ANode, ChildNode
from .node import AnyNode
from .node_listener import NodeListener

if TYPE_CHECKING:
    from collections.abc import MutableMapping, MutableSequence
    from typing import Any, Final

    from .children import _ChildrenParentNodeInterface as Children
    from .entry_support_default import EntrySupportDefault, EntrySupportDefaultInfo
    from .node_listener import (
        NodeEvent,
        NodeMemberEvent,
        NodeReorderEvent,
    )

__all__: Final = ('ChildrenStorage',)

_logger = logging.getLogger(__name__)


# Normally, the AnyNode to NodeListener is actually the same than our own ANode.
# But since we split up things into classes that have separate concerns, the ANode
# parameter of NodeListener is a _NodeListenersMixins, whereas our own ANode is
# a _NodeChildrenInterface. In practice, they both end up being an actual Node.
@final
class ChildrenStorage(NodeListener[AnyNode, ChildNode], Generic[ANode, ChildNode]):
    """Holder of nodes for a children object.

    Communicates with children to notify when created/finalised.
    """

    # OK, Match (_fake is an addition)
    def __init__(self, *, _fake: bool = False) -> None:
        if _fake:  # For light instantiation of a quickly deleted storage
            return

        super().__init__()

        self._lock = RLock()
        self.entry_support: EntrySupportDefault[ANode, ChildNode] | None = None
        """Children's EntrySupport"""
        self.__nodes: list[ChildNode] | None = None
        """Associated nodes"""
        self.__map: (
            MutableMapping[EntrySupportDefaultInfo[ChildNode], MutableSequence[ChildNode]] | None
        ) = None

        # print('instantiated a children storage', time.monotonic(), self)

    # def __del__(self):
    #     print('ChildrenStorage.__del__', time.monotonic(), self, getattr(self, '__nodes', None))
    #     if (super_del := getattr(super(), '__del__', None)) is not None:
    #         super_del()

    # OK, Match

    @property
    def children(self) -> Children[ANode, ChildNode] | None:
        if (entry_support := self.entry_support) is not None:
            return entry_support.children
        else:
            return None

    # OK, Match
    @property
    def nodes(self) -> list[ChildNode] | None:
        """Getter method to receive ("pull" from EntrySupport) a set of computed nodes."""

        if (entry_support := self.entry_support) is None:
            return None

        if (nodes := self.__nodes) is None:
            nodes = self.__nodes = entry_support._just_compute_nodes()
            # print('got new set of nodes', self.__nodes)

            children = entry_support.children
            for node in nodes:
                # Keeps a hard reference from the children node to this so we can
                # be GCed only when child nodes are gone.
                node._reassign_to(children, self)

            # If at least one node => be weak
            entry_support._register_children_storage(self, weak=bool(nodes))

        return nodes

    # OK, Match
    def clear(self) -> None:
        """Clears the array of nodes."""

        if self.__nodes is not None:
            self.__nodes = None

            # Register in the children to be held by hard reference. Because we
            # keep no reference to nodes, we can be hard held by children
            if self.entry_support is not None:
                self.entry_support._register_children_storage(self, weak=False)

    # OK, Match
    def _remove(self, info: EntrySupportDefaultInfo[ChildNode]) -> None:
        if ((map := self.__map) is not None) and (info in map):
            del map[info]

    # OK, Match
    @property
    def is_initialised(self) -> bool:
        """Initialised if has some nodes."""

        return self.__nodes is not None

    # Note: Ignoring logInfo

    # OK, Match
    def nodes_for(
        self,
        info: EntrySupportDefaultInfo[ChildNode],
        *,
        has_to_exist: bool,
    ) -> MutableSequence[ChildNode]:
        """Gets the nodes for given info."""

        with self._lock:
            if (map := self.__map) is None:
                assert not has_to_exist, 'Should already be initialised'
                map = self.__map = WeakKeyDictionary()

            nodes = map.get(info)
            if nodes is None:
                assert not has_to_exist, f'Cannot find nodes for {info} in {map}'

                try:
                    new_nodes = info._entry.nodes(None)
                except RuntimeError:
                    _logger.exception('Error during node processing')
                    new_nodes: MutableSequence[ChildNode] = []
                else:
                    if new_nodes is None:  # pyright: ignore[reportUnnecessaryComparison]
                        _logger.warning('None returned by %s', info._entry)
                        new_nodes: MutableSequence[ChildNode] = []

                info._length = len(new_nodes)
                map[info] = new_nodes
                nodes = new_nodes  # Somehow, typing is getting real weird if we keep reusing nodes

            return nodes

    # OK, Match
    def use_nodes(
        self,
        info: EntrySupportDefaultInfo[ChildNode],
        nodes: MutableSequence[ChildNode],
    ) -> None:
        """Refreshes the nodes for given info."""

        with self._lock:
            if (map := self.__map) is None:
                map = self.__map = WeakKeyDictionary()

            info._length = len(nodes)
            map[info] = nodes

    ###

    # OK, Match
    @override  # NodeListener
    def property_change(self, node: AnyNode, name: str, old: Any, new: Any) -> None:
        pass

    # OK, Match
    @override  # NodeListener
    def children_added(self, event: NodeMemberEvent[AnyNode, ChildNode]) -> None:
        pass

    # OK, Match
    @override  # NodeListener
    def children_removed(self, event: NodeMemberEvent[AnyNode, ChildNode]) -> None:
        pass

    # OK, Match
    @override  # NodeListener
    def children_reordered(self, event: NodeReorderEvent[AnyNode, ChildNode]) -> None:
        pass

    # OK, Match
    @override  # NodeListener
    def node_destroyed(self, event: NodeEvent[AnyNode]) -> None:
        pass

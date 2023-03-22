# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# From: https://github.com/apache/netbeans/blob/master/platform/openide.nodes/src/org/openide/nodes/ChildrenArray.java  # noqa: E501

from __future__ import annotations

# System imports
import logging
import time
from threading import RLock
from typing import TYPE_CHECKING, final
from weakref import WeakKeyDictionary

# Third-party imports

# Local imports
from openide.utils.classes import Debug
from openide.utils.typing import override
from openide.nodes._like_netbeans.node_listener import NodeListener


if TYPE_CHECKING:
    from collections.abc import MutableSequence, MutableMapping
    from typing import Any, Optional
    from openide.nodes._like_netbeans.node import Node
    from openide.nodes._like_netbeans.node_listener import NodeEvent, NodeMemberEvent, NodeReorderEvent
    from openide.nodes._like_netbeans.children import Children
    from openide.nodes._like_netbeans.entry_support_default import EntrySupportDefault


_logger = logging.getLogger(__name__)


@final
class ChildrenStorage(NodeListener, Debug(f'{__name__}.ChildrenStorage')):

    # OK, Match (_fake is an addition)
    def __init__(self, _fake: bool = False) -> None:
        if _fake:  # For light instantiation of a quickly deleted storage
            return

        super().__init__()

        self._lock = RLock()
        self.entry_support: Optional[EntrySupportDefault] = None
        self.__nodes: Optional[list[Node]] = None
        self.__map: Optional[MutableMapping[EntrySupportDefault._Info,
                                            MutableSequence[Node]]] = None

        # print('instantiated a children storage', time.monotonic(), self)

    # def __del__(self):
    #     print('ChildrenStorage.__del__', time.monotonic(), self, getattr(self, '__nodes', None))
    #     if (super_del := getattr(super(), '__del__', None)) is not None:
    #         super_del()

    # OK, Match

    @property
    def children(self) -> Optional[Children]:
        if (entry_support := self.entry_support) is not None:
            return entry_support.children
        else:
            return None

    # OK, Match
    @property
    def nodes(self) -> Optional[list[Node]]:
        if (entry_support := self.entry_support) is None:
            return None

        if (nodes := self.__nodes) is None:
            nodes = self.__nodes = entry_support._just_compute_nodes()
            # print('got new set of nodes', self.__nodes)

            children = entry_support.children
            for node in nodes:
                node._reassign_to(children, self)

            entry_support._register_children_storage(self, bool(nodes))

        return nodes

    # OK, Match
    def clear(self) -> None:
        if self.__nodes is not None:
            self.__nodes = None

            if self.entry_support is not None:
                self.entry_support._register_children_storage(self, False)

    # OK, Match
    def _remove(self, info: EntrySupportDefault._Info) -> None:
        if ((map := self.__map) is not None) and (info in map):
            del map[info]

    # OK, Match
    @property
    def is_initialised(self) -> bool:
        return self.__nodes is not None

    # Note: Ignoring logInfo

    # OK, Match
    def nodes_for(
        self,
        info: EntrySupportDefault._Info,
        has_to_exist: bool
    ) -> MutableSequence[Node]:
        with self._lock:
            if (map := self.__map) is None:
                assert not has_to_exist, "Should already be initialised"
                map = self.__map = WeakKeyDictionary()

            nodes = map.get(info)
            if nodes is None:
                assert not has_to_exist, f'Cannot find nodes for {info} in {map}'

                try:
                    nodes = info._entry.nodes(None)
                except RuntimeError:
                    _logger.exception('Error during node processing')
                    nodes = []

                if nodes is None:
                    _logger.warning('None returned by %s', info._entry)
                    nodes = []

                info._length = len(nodes)
                map[info] = nodes

            return nodes

    # OK, Match
    def use_nodes(self, info: EntrySupportDefault._Info, nodes: MutableSequence[Node]) -> None:
        with self._lock:
            if (map := self.__map) is None:
                map = self.__map = WeakKeyDictionary()

            info._length = len(nodes)
            map[info] = nodes

    ###

    # OK, Match
    @override  # NodeListener
    def property_change(self, node: Node, name: str, old: Any, new: Any) -> None:
        pass

    # OK, Match
    @override  # NodeListener
    def children_added(self, event: NodeMemberEvent) -> None:
        pass

    # OK, Match
    @override  # NodeListener
    def children_removed(self, event: NodeMemberEvent) -> None:
        pass

    # OK, Match
    @override  # NodeListener
    def children_reordered(self, event: NodeReorderEvent) -> None:
        pass

    # OK, Match
    @override  # NodeListener
    def node_destroyed(self, event: NodeEvent) -> None:
        pass

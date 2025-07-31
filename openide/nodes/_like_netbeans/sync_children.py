# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# From: https://github.com/apache/netbeans/blob/master/platform/openide.nodes/src/org/openide/nodes/SynchChildren.java  # noqa: E501

from __future__ import annotations

# System imports
from typing import TYPE_CHECKING, Any, TypeVar

# Third-party imports
from typing_extensions import override

# Local imports
from openide.nodes._like_netbeans.child_factory import ChildFactory
from openide.nodes._like_netbeans.children import Keys

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableSequence, Sequence

    from openide.nodes._like_netbeans.node import Node

K = TypeVar('K')
PN = TypeVar('PN', bound='Node[Any, Any]')
N = TypeVar('N', bound='Node[Any, Any]')


class SyncChildren(Keys[K, PN, N], ChildFactory.Observer):
    # OK, Match
    def __init__(self, factory: ChildFactory[K, N]) -> None:
        super().__init__()

        self.__factory = factory
        self._active = False  # Volatile, do not persist

    # OK, Match
    @override  # Children
    def _add_notify(self) -> None:
        self._active = True
        self.__factory._add_notify()
        self.refresh(immediate=True)

    # OK, Match
    @override  # Children
    def _remove_notify(self) -> None:
        self._active = False
        self._set_keys([])
        self.__factory._remove_notify()

    # OK, Match
    @override  # Keys
    def _create_nodes(self, key: K) -> Sequence[N] | None:
        return self.__factory._create_nodes_for_key(key)

    # OK, Match
    @override  # Children and Keys
    def _destroy_nodes(self, nodes: Iterable[N]) -> None:
        super()._destroy_nodes(nodes)
        self.__factory._destroy_nodes(nodes)

    # OK, Match
    @override  # ChildFactory.Observer
    def refresh(self, *, immediate: bool) -> None:
        print(f'SyncChildren.refresh: {self._active=}')
        if self._active:
            to_populate: MutableSequence[K] = []
            while not self.__factory._create_keys(to_populate):
                pass

            self._set_keys(to_populate)

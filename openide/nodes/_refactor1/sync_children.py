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
from typing import TYPE_CHECKING

# Third-party imports
from typing_extensions import override

# Local imports
from .child_factory import ChildFactory
from .children import ChildNode, ParentNode
from .children_keys import ChildrenKeys, Key

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableSequence, Sequence
    from typing import Final

__all__: Final = ('SyncChildren',)

_logger = logging.getLogger(__name__)


class SyncChildren(ChildrenKeys[Key, ParentNode, ChildNode], ChildFactory.Observer):
    # OK, Match
    def __init__(self, factory: ChildFactory[Key, ChildNode]) -> None:
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
    def _create_nodes(self, key: Key) -> Sequence[ChildNode] | None:
        return self.__factory._create_nodes_for_key(key)

    # OK, Match
    @override  # Children and Keys
    def _destroy_nodes(self, nodes: Iterable[ChildNode]) -> None:
        super()._destroy_nodes(nodes)
        self.__factory._destroy_nodes(nodes)

    # OK, Match
    @override  # ChildFactory.Observer
    def refresh(self, *, immediate: bool) -> None:
        print(f'SyncChildren.refresh: {self._active=}')
        if self._active:
            to_populate: MutableSequence[Key] = []
            while not self.__factory._create_keys(to_populate):
                pass

            self._set_keys(to_populate)

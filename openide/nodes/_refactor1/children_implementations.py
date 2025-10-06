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
from typing import TYPE_CHECKING, Any

# Third-party imports
from typing_extensions import override

# Local imports
from .children import ANode, ChildNode, Children

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence
    from typing import Final

    from .entry_support import EntrySupport
    from .node import NoNode

__all__: Final = ()

_logger = logging.getLogger(__name__)


class _EmptyChildren(Children[Any, Any]):
    """Empty list of children.

    Does not allow anybody to insert a node. Treated especially in the _attach_to() method.
    """

    @override  # Children
    def add(self, nodes: Sequence[NoNode]) -> bool:
        return False

    @override  # Children
    def remove(self, nodes: Sequence[NoNode]) -> bool:
        return False


Children.LEAF = _EmptyChildren()


class _LazyChildren(Children[ANode, ChildNode]):  # pyright: ignore[reportUnusedClass]  # Used in Children.create_lazy(), and Node._update_children()
    # OK, Match
    def __init__(self, factory: Callable[[], Children[ANode, ChildNode]]) -> None:
        super().__init__()

        self.__factory = factory
        self.__original: Children[ANode, ChildNode] | None = None
        self.__original_lock = RLock()

    # OK, Match
    @property
    def _original(self) -> Children[ANode, ChildNode]:
        with self.__original_lock:
            if self.__original is None:
                self.__original = self.__factory()

            return self.__original

    # OK, Match
    @override  # Children
    def add(self, nodes: Sequence[ChildNode]) -> bool:
        return self._original.add(nodes)

    # OK, Match
    @override  # Children
    def remove(self, nodes: Sequence[ChildNode]) -> bool:
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
    def _entry_support(self) -> EntrySupport[ANode, ChildNode]:
        return self._original._entry_support

    # OK, Match
    @override  # Children
    def find_child(self, system_name: str | None) -> ChildNode | None:
        return self._original.find_child(system_name)

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
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic

# Third-party imports
# Local imports
from .node import ChildNode, ParentNode

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableSequence, Sequence
    from typing import Final

    from .children import ChildrenEntry, _ChildrenEntrySupportInterface

__all__: Final = ('EntrySupport',)

_logger = logging.getLogger(__name__)


class EntrySupport(ABC, Generic[ParentNode, ChildNode]):
    # OK, Match
    def __init__(self, children: _ChildrenEntrySupportInterface[ParentNode, ChildNode]) -> None:
        super().__init__()

        self.__children = children
        """Children we are attached to"""

    # Note: This is to keep children as a RO public attribute
    @property
    def children(self) -> _ChildrenEntrySupportInterface[ParentNode, ChildNode]:
        """Children we are attached to"""

        return self.__children

    # Interfaces to be called from Children

    # OK, Match
    @abstractmethod
    def get_nodes_count(self, *, optimal_result: bool) -> int:
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @abstractmethod
    def get_nodes(self, *, optimal_result: bool) -> Sequence[ChildNode]:
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    # TODO: __getitem__?
    @abstractmethod
    def get_node_at(self, index: int) -> ChildNode | None:
        """Getter for a node at a given position.

        If node with such index does not exists, it should return None.
        """

        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @abstractmethod
    def test_nodes(self) -> Sequence[ChildNode] | None:
        """Returns currently created nodes, os None if no nodes is created."""

        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @property
    @abstractmethod
    def is_initialised(self) -> bool:
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @abstractmethod
    def _notify_set_entries(self) -> None:
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @abstractmethod
    def _set_entries(
        self,
        entries: Iterable[ChildrenEntry[ChildNode]],
        *,
        no_check: bool = False,
    ) -> None:
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @property
    @abstractmethod
    def _entries(self) -> MutableSequence[ChildrenEntry[ChildNode]]:
        """Access to copy of current entries."""

        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @abstractmethod
    def _snapshot(self) -> Sequence[ChildNode]:
        """Returns an immutable list of Nodes that represent the children at the present moment."""

        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @abstractmethod
    def _refresh_entry(self, entry: ChildrenEntry[ChildNode]) -> None:
        """Refreshes content of one entry.

        Updates the state of children appropriately."""

        raise NotImplementedError  # pragma: no cover

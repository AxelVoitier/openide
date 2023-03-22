# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# From: https://github.com/apache/netbeans/blob/master/platform/openide.nodes/src/org/openide/nodes/EntrySupport.java  # noqa: E501

from __future__ import annotations

# System imports
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

# Third-party imports

# Local imports

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence, MutableSequence
    from typing import Optional
    from openide.nodes._like_netbeans.node import Node
    from openide.nodes._like_netbeans.children import Children


class EntrySupport(ABC):

    # OK, Match
    def __init__(self, children: Children) -> None:
        super().__init__()

        self.__children = children

    # Note: This is to keep children as a RO public attribute
    @property
    def children(self) -> Children:
        return self.__children

    # OK, Match
    @abstractmethod
    def get_nodes_count(self, optimal_result: bool) -> int:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    @abstractmethod
    def get_nodes(self, optimal_result: bool) -> Sequence[Node]:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    # TODO: __getitem__?
    @abstractmethod
    def get_node_at(self, index: int) -> Optional[Node]:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    @abstractmethod
    def test_nodes(self) -> Optional[Sequence[Node]]:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    @property
    @abstractmethod
    def is_initialised(self) -> bool:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    @abstractmethod
    def _notify_set_entries(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    @abstractmethod
    def _set_entries(self, entries: Iterable[Children.Entry], no_check: bool = False) -> None:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    @property
    @abstractmethod
    def _entries(self) -> MutableSequence[Children.Entry]:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    @abstractmethod
    def _snapshot(self) -> Sequence[Node]:
        raise NotImplementedError()  # pragma: no cover

    # OK, Match
    @abstractmethod
    def _refresh_entry(self, entry: Children.Entry) -> None:
        raise NotImplementedError()  # pragma: no cover

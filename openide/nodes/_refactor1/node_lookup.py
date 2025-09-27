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
import functools
import logging
from threading import RLock
from typing import TYPE_CHECKING, Any, Generic, TypeVar

# Third-party imports
from lookups import GenericLookup
from lookups.instance_content import SimpleItem
from typing_extensions import override

# Local imports
from openide.lookup.cookie_set import Cookie, CookieSet, _PairWrap
from openide.nodes._like_netbeans import Node

from .node import _NodeLookupAndCookieMixin

if TYPE_CHECKING:
    from lookups.generic_lookup import Pair

# If you use AnyNode instead of Any, it messes up typing of self in _NodeLookupAndCookieMixin...
ANode = TypeVar('ANode', bound=_NodeLookupAndCookieMixin[Any])
T = TypeVar('T')

_logger = logging.getLogger(__name__)


class NodeLookup(GenericLookup, Generic[ANode]):
    def __init__(self, node: ANode) -> None:
        super().__init__()

        self.__queried_cookie_classes: set[Any] = set()
        self.__lock = RLock()

        self._node = node
        self._add_pair(SimpleItem(node))

    @override
    def _before_lookup(self, cls: type[object]) -> None:
        # with self._node._block_events():
        self.__blocking_before_lookup(cls)

    def __blocking_before_lookup(self, cls: type[object]) -> None:
        # if cls in (object, Cookie):  # Query everything

        if cls not in self.__queried_cookie_classes:
            self.update_lookup_as_cookies_are_changed(cls)

    # TODO: Rename _sync
    def update_lookup_as_cookies_are_changed(self, to_add: type[object] | None) -> None:
        with self.__lock:
            if to_add is not None:
                if to_add in self.__queried_cookie_classes:
                    return
                self.__queried_cookie_classes.add(to_add)

            instances: list[Pair[Any]] = []
            from_pair_to_query_class: dict[Pair[Any], type[Any]] = {}
            it = iter(self.__queried_cookie_classes)  # Acquire iterator under lock?

            # Insert the node pair first
            node_pair = SimpleItem(self._node)
            instances.append(node_pair)
            from_pair_to_query_class[node_pair] = Node

        cookie_set = self._node._cookie_set if self._node._supports_cookie_set else None
        for cls in it:
            self.__add_cookie(self._node, cookie_set, cls, instances, from_pair_to_query_class)

        def cmp(p1: Pair[Any], p2: Pair[Any]) -> int:
            c1 = from_pair_to_query_class[p1]
            c2 = from_pair_to_query_class[p2]

            if c1 == c2:
                return 0
            if issubclass(c2, c1):
                return -1
            if issubclass(c1, c2):
                return 1
            if issubclass(type(p2), c1):
                return -1
            if issubclass(type(p1), c2):
                return 1

            return 0

        instances = sorted(instances, key=functools.cmp_to_key(cmp))
        if to_add is None:  # Triggered by cookie change event
            self._set_pairs(instances)
        else:  # First time asking for class X
            self._set_pairs(instances, self.EXECUTOR)

    @staticmethod
    def __add_cookie(
        node: ANode,
        cookie_set: CookieSet | None,
        cls: type[Any],
        collection: list[Pair[Any]],
        from_pair_to_class: dict[Pair[Any], type[Any]],
    ) -> None:
        pairs: list[Pair[Any]] | None = None

        if cookie_set is not None:
            result, pairs = cookie_set._lookup_cookie_or_pairs(cls)

        else:
            result = node.get_cookie(cls)
            if ((lookup := node._internal_lookup) is not None) and (not isinstance(result, Cookie)):
                pairs = CookieSet._wrap_pairs_from_lookup(lookup, cls)

        if pairs is None:
            if result is None:
                return

            orig = SimpleItem(result)
            pair = orig if isinstance(result, Node) else _PairWrap(orig)

            pairs = [pair]

        collection.extend(pairs)

        for pair in pairs:
            old_cls = from_pair_to_class.get(pair)
            if (old_cls is None) or issubclass(old_cls, cls):
                from_pair_to_class[pair] = cls

# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore

from __future__ import annotations

# System imports
from collections import defaultdict
from typing import Any, Generic

# Third-party imports
from typing_extensions import override

# Local imports
from openide.nodes._refactor1 import (
    ChildNode,
    NodeEvent,
    NodeListener,
    NodeMemberEvent,
    NodeReorderEvent,
    ParentNode,
)

from .minimal_node import MinimalNode


class Listener(
    NodeListener[MinimalNode[ParentNode, ChildNode], ChildNode],
    Generic[ParentNode, ChildNode],
):
    def __init__(self) -> None:
        super().__init__()
        self.called: dict[str, list[dict[str, Any]]] = defaultdict(list)

    @override
    def property_change(
        self,
        node: MinimalNode[ParentNode, ChildNode],
        name: str,
        old: Any,
        new: Any,
    ) -> None:
        self.called['property_change'].append(
            dict(
                node=node,
                name=name,
                old=old,
                new=new,
            ),
        )

    @override
    def children_added(
        self,
        event: NodeMemberEvent[MinimalNode[ParentNode, ChildNode], ChildNode],
    ) -> None:
        self.called['children_added'].append(dict(event=event))

    @override
    def children_removed(
        self,
        event: NodeMemberEvent[MinimalNode[ParentNode, ChildNode], ChildNode],
    ) -> None:
        self.called['children_removed'].append(dict(event=event))

    @override
    def children_reordered(
        self,
        event: NodeReorderEvent[MinimalNode[ParentNode, ChildNode], ChildNode],
    ) -> None:
        self.called['children_reordered'].append(dict(event=event))

    @override
    def node_destroyed(self, event: NodeEvent[MinimalNode[ParentNode, ChildNode]]) -> None:
        self.called['node_destroyed'].append(dict(event=event))

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
from collections import defaultdict
from typing import TYPE_CHECKING, TypeVar

# Third-party imports
from lookups import ProxyLookup

# Local imports
from openide.actions.utils import actions_to_context_menu

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Collection, Iterable, Iterator
    from typing import Any, Final

    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QMenu

    from .node import _NodeActionsInterface

    ANodeAction = TypeVar('ANodeAction', bound=_NodeActionsInterface[Any])
    N = TypeVar('N')

__all__: Final = ()

_logger = logging.getLogger(__name__)


def get_default_actions() -> Iterable[QAction | str | None]:
    # TODO
    return ()


def find_context_menu(nodes: Iterable[ANodeAction]) -> QMenu | None:
    """Computes a common context menu for the specified nodes.

    Provides only those actions supplied by all nodes in the list.

    nodes: Iterable of the nodes.

    Returns the menu for all nodes
    """

    actions = tuple(find_common_actions(nodes))
    if not actions:
        return None

    proxy_lookup = ProxyLookup(*[node.get_lookup() for node in nodes])
    return actions_to_context_menu(actions, proxy_lookup)


def find_common_actions(nodes: Iterable[ANodeAction]) -> Iterator[QAction | str | None]:
    """Asks the provided nodes for their actions, and returns those that are common to all of them.

    nodes: Iterable of nodes to compose actions for

    Returns an iterator of actions (and separators) for the nodes.
    """

    action_counters: dict[QAction, int] = defaultdict(int)
    actions_by_node: dict[ANodeAction, Iterable[QAction | str | None]] = {}

    n_nodes = 0
    for node in nodes:
        n_nodes += 1
        actions_by_node[node] = actions = node.actions

        counted: set[QAction] = set()
        for action in actions:
            if (action is None) or isinstance(action, str) or (action in counted):
                continue
            action_counters[action] += 1
            counted.add(action)

    if not action_counters:
        return

    added: set[QAction] = set()
    for action in next(iter(actions_by_node.values())):
        if (action is None) or isinstance(action, str):  # Separators
            yield action

        else:
            if action in added:
                continue
            added.add(action)
            if action_counters[action] != n_nodes:
                continue

            yield action


def compute_permutation(nodes1: Collection[N], nodes2: Collection[N]) -> list[int] | None:
    if len(nodes1) != len(nodes2):
        msg = (
            'Cannot compute permutations between two collections of Node '
            f'that do not have the same length: {nodes1=} ; {nodes2=}'
        )
        raise ValueError(msg)

    new_positions_map = {node: i for i, node in enumerate(nodes2)}
    perm = [-1] * len(nodes1)
    diff = 0
    for i, node in enumerate(nodes1):
        new_pos = new_positions_map.get(node)
        if new_pos is None:
            msg = f'Missing permutation index {i}'
            raise ValueError(msg)

        perm[i] = new_pos
        if new_pos != i:
            diff += 1

    return perm if diff else None

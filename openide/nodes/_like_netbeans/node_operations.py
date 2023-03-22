# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from typing import TYPE_CHECKING

# Third-party imports

# Local imports

if TYPE_CHECKING:
    from typing import Optional
    from collections.abc import Collection
    from openide.nodes._like_netbeans.node import Node


def compute_permutation(
    nodes1: Collection[Node],
    nodes2: Collection[Node]
) -> Optional[list[int]]:
    if len(nodes1) != len(nodes2):
        raise ValueError(
            'Cannot compute permutations between two collections of Node '
            f'that do not have the same length: {nodes1=} ; {nodes2=}'
        )

    new_positions_map = {node: i for i, node in enumerate(nodes2)}
    perm = [-1] * len(nodes1)
    diff = 0
    for i, node in enumerate(nodes1):
        new_pos = new_positions_map.get(node)
        if new_pos is None:
            raise ValueError(f'Missing permutation index {i}')

        perm[i] = new_pos
        if new_pos != i:
            diff += 1

    return perm if diff else None

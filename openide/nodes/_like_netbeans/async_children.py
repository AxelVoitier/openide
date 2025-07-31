# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# From: https://github.com/apache/netbeans/blob/master/platform/openide.nodes/src/org/openide/nodes/AsynchChildren.java  # noqa: E501

from __future__ import annotations

# System imports
# from collections.abc import MutableSequence, MutableMapping, Hashable
from typing import (
    # Optional, Callable, Sequence, Collection,
    # Type, cast, Union,
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
)

# Third-party imports
# Local imports
from openide.nodes._like_netbeans.child_factory import ChildFactory
from openide.nodes._like_netbeans.children import Keys

if TYPE_CHECKING:
    from openide.nodes._like_netbeans.node import Node

T = TypeVar('T')
PN = TypeVar('PN', bound='Node[Any, Any]')
N = TypeVar('N', bound='Node[Any, Any]')


class AsyncChildren(Keys[T, PN, N], ChildFactory.Observer, Generic[T]):
    def __init__(self, factory: ChildFactory[T, N]) -> None:
        super().__init__()

        self.__factory = factory
        self._active = False  # Volatile, do not persist

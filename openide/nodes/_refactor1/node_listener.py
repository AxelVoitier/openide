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
from threading import RLock
from typing import TYPE_CHECKING, Generic, cast, final

# Third-party imports
from typing_extensions import override

# Local imports
from .node import ANode, ChildNode

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Iterator, Sequence
    from typing import Any, Final

    from .children import ChildrenEntry
    from .node import Node

    # from .node import N

__all__: Final = (
    'Event',
    'NodeEvent',
    'NodeListener',
    'NodeMemberEvent',
    'NodeReorderEvent',
)

_logger = logging.getLogger(__name__)


class Event(Generic[ANode]):
    def __init__(self, source: ANode) -> None:
        super().__init__()

        self._source = source  # transient

    @property
    def source(self) -> ANode:
        return self._source

    @override  # object
    def __str__(self) -> str:
        return f'{type(self).__name__}({", ".join(self.__str_add__())})'

    __repr__ = __str__

    def __str_add__(self) -> Iterator[str]:
        yield f'source={self._source}'


class NodeEvent(Event[ANode]):
    """Event describing a change in node."""

    def __init__(self, node: ANode) -> None:
        super().__init__(node)

    @property
    @final
    def node(self) -> ANode:
        """The node where the change occurred."""

        return self.source

    @override  # Event
    def __str_add__(self) -> Iterator[str]:
        yield f'node={self.node}'


class NodeMemberEvent(NodeEvent[ANode], Generic[ANode, ChildNode]):
    """Event describing change in the list of a node's children."""

    def __init__(
        self,
        node: ANode,
        *,
        add: bool,
        delta: Collection[ChildNode] | None = None,
        from_: Sequence[ChildNode] | None = None,
        indices: Iterable[int] | None = None,
        current: Sequence[ChildNode] | None = None,
        previous: Sequence[ChildNode] | None = None,
    ) -> None:
        """
        Args:
            node: Node that should fire change.
            add: True if nodes has been added. False if removed.
            delta: Array of nodes that have changed.
            from_: Nodes to find indices in.
            indices: The indices that changed.
            previous: snapshot of the state before this event happened or None.
        """
        super().__init__(node)

        self.__delta: Collection[ChildNode] | None
        """List of changed nodes"""
        self.__indices: list[int] | None
        """List of nodes indexes, can be null if it should be computed lazily"""
        self.__prev_snapshot: Sequence[ChildNode] | None
        """Previous snapshot or None"""
        self.__curr_snapshot: Sequence[ChildNode]
        """Current snapshot"""

        self.__lock = RLock()
        self.__add = add
        """Is this add event?"""
        self._source_entry: ChildrenEntry[ChildNode] | None = None
        if delta is not None:
            self.__delta = delta
            self.__prev_snapshot = from_
            self.__curr_snapshot = cast('Node[Any, ChildNode]', node)._children.snapshot()
            self.__indices = None
        else:
            assert indices is not None
            assert current is not None
            self.__indices = sorted(indices)
            self.__curr_snapshot = current
            self.__prev_snapshot = previous
            self.__delta = None

    @property
    @final
    def snapshot(self) -> Collection[ChildNode]:
        """Provides static and immutable info about the number, and instances of
        nodes available during the time the event was emited."""

        return self.__curr_snapshot

    @property
    @final
    def is_add_event(self) -> bool:
        """Get the type of action: True if children were added, False if removed."""

        return self.__add

    @property
    def prev_snapshot(self) -> Sequence[ChildNode]:
        return self.__prev_snapshot if self.__prev_snapshot is not None else self.__curr_snapshot

    @property
    @final
    def delta(self) -> Collection[ChildNode]:
        """Get a list of children that changed."""

        if (delta := self.__delta) is None:
            indices = cast('list[int]', self.__indices)
            prev = self.prev_snapshot
            delta = self.__delta = [prev[index] for index in indices]

        return delta

    @property
    def delta_indices(self) -> Sequence[int]:
        """Get a list of indices of the changed nodes.

        The returned list has the same length than the one returned by delta property.
        """

        with self.__lock:
            if (indices := self.__indices) is None:
                nodes = self.prev_snapshot
                delta = self.__delta
                assert delta is not None
                delta_set = set(delta)
                indices = self.__indices = [i for i, node in enumerate(nodes) if node in delta_set]

                if len(indices) != len(delta):
                    msg = (
                        'Some of a set of deleted nodes are not present in the original one. '
                        'You may need to check that your Children.Keys keys are safely comparable.'
                    )
                    raise RuntimeError(msg)

        return indices

    @override  # NodeEvent
    def __str_add__(self) -> Iterator[str]:
        yield from super().__str_add__()
        yield f'add={self.__add}'
        if self.__delta is not None:
            yield f'delta={self.__delta}'
            yield f'prev={self.__prev_snapshot}'
            yield f'curr={self.__curr_snapshot}'
        else:
            yield f'indices={self.__indices}'
            yield f'prev={self.__prev_snapshot}'
            yield f'curr={self.__curr_snapshot}'


class NodeReorderEvent(NodeEvent[ANode], Generic[ANode, ChildNode]):
    """Event describing change in the list of a Node's children."""

    # TODO: Be a Sequence, proxying self.__new_indices

    def __init__(self, node: ANode, new_indices: Sequence[int]) -> None:
        """
        Args:
            node: The node that has changed.
            new_indices: New indexes of the nodes.
        """
        super().__init__(node)

        self.__new_indices = new_indices
        """List of new nodes indexes on the original positions"""
        self.__curr_snapshot = cast('Node[Any, ChildNode]', node)._children.snapshot()
        """Current snapshot"""

    @property
    @final
    def snapshot(self) -> Collection[ChildNode]:
        """Provides static and immutable info about the number, and instances of
        nodes available during the time the event was emited."""

        return self.__curr_snapshot

    # TODO: __getitem__?
    def new_index_of(self, i: int) -> int:
        """Get the new position of the child that had been at a given position before.

        Args:
            i: The original position of the child.

        Returns:
            The new position of the child.
        """

        return self.__new_indices[i]

    @property
    def permutation(self) -> Sequence[int]:
        """Get the permutation used for reordering.

        Returns:
            Array of integers used for reordering.
        """

        return self.__new_indices

    # TODO: __len__?
    @property
    def permutation_size(self) -> int:
        """Get the number of children reordered."""

        return len(self.__new_indices)

    @override  # NodeEvent
    def __str_add__(self) -> Iterator[str]:
        yield from super().__str_add__()
        yield f'new_indices={self.__new_indices}'
        yield f'curr_snapshot={self.__curr_snapshot}'


class NodeListener(ABC, Generic[ANode, ChildNode]):
    """Listeners to special changes in Nodes.

    Can also listen to Node properties at the same time.

    Methods `children_added()`, `children_removed()`, and `children_reordered()`
    are called with `Children.MUTEX.write_access()` which guarantees that no other
    thread can change the hierarchy during that time, but also requires proper
    implementation of all NodeListeners which should avoid calls to other threads
    which might require access to Children.MUTEX due to changes nodes hierarchy
    or no any other kind of starvation.
    """

    @abstractmethod
    def property_change(self, node: ANode, name: str, old: Any, new: Any) -> None:  # noqa: ANN401
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def children_added(self, event: NodeMemberEvent[ANode, ChildNode]) -> None:
        """Fired when a set of new children is added."""

        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def children_removed(self, event: NodeMemberEvent[ANode, ChildNode]) -> None:
        """Fired when a set of children is removed."""

        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def children_reordered(self, event: NodeReorderEvent[ANode, ChildNode]) -> None:
        """Fired when the order of children is changed."""

        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def node_destroyed(self, event: NodeEvent[ANode]) -> None:
        """Fired when the node is deleted."""

        raise NotImplementedError  # pragma: no cover


# class NodeEvent(Enum):
#     ChildrenAdded = auto()
#     ChildrenRemoved = auto()
#     ChildrenReordered = auto()
#     NodeDestroyed = auto()


# class NodeListenersProtocol(Protocol):
#     def __call__(self, event: NodeEvent) -> Any: ...  # noqa: ANN401

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

    from .children import Children
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
    def __init__(self, node: ANode) -> None:
        super().__init__(node)

    @property
    @final
    def node(self) -> ANode:
        return self.source

    @override  # Event
    def __str_add__(self) -> Iterator[str]:
        yield f'node={self.node}'


class NodeMemberEvent(NodeEvent[ANode], Generic[ANode, ChildNode]):
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
        super().__init__(node)

        self.__delta: Collection[ChildNode] | None
        self.__indices: list[int] | None
        self.__prev_snapshot: Sequence[ChildNode] | None
        self.__curr_snapshot: Sequence[ChildNode]

        self.__lock = RLock()
        self.__add = add
        self._source_entry: Children.Entry | None = None
        if delta is not None:
            self.__delta = delta
            self.__prev_snapshot = from_
            self.__curr_snapshot = cast('Node[Any, CN]', node)._children.snapshot()
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
        return self.__curr_snapshot

    @property
    @final
    def is_add_event(self) -> bool:
        return self.__add

    @property
    def prev_snapshot(self) -> Sequence[ChildNode]:
        return self.__prev_snapshot if self.__prev_snapshot is not None else self.__curr_snapshot

    @property
    @final
    def delta(self) -> Collection[ChildNode]:
        if (delta := self.__delta) is None:
            indices = cast('list[int]', self.__indices)
            prev = self.prev_snapshot
            delta = self.__delta = [prev[index] for index in indices]

        return delta

    @property
    def delta_indices(self) -> Sequence[int]:
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
    # TODO: Be a Sequence, proxying self.__new_indices

    def __init__(self, node: ANode, new_indices: Sequence[int]) -> None:
        super().__init__(node)

        self.__new_indices = new_indices
        self.__curr_snapshot = cast('Node[Any, CN]', node)._children.snapshot()

    @property
    @final
    def snapshot(self) -> Collection[ChildNode]:
        return self.__curr_snapshot

    # TODO: __getitem__?
    def new_index_of(self, i: int) -> int:
        return self.__new_indices[i]

    @property
    def permutation(self) -> Sequence[int]:
        return self.__new_indices

    # TODO: __len__?
    @property
    def permutation_size(self) -> int:
        return len(self.__new_indices)

    @override  # NodeEvent
    def __str_add__(self) -> Iterator[str]:
        yield from super().__str_add__()
        yield f'new_indices={self.__new_indices}'
        yield f'curr_snapshot={self.__curr_snapshot}'


class NodeListener(ABC, Generic[ANode, ChildNode]):
    @abstractmethod
    def property_change(self, node: ANode, name: str, old: Any, new: Any) -> None:  # noqa: ANN401
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def children_added(self, event: NodeMemberEvent[ANode, ChildNode]) -> None:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def children_removed(self, event: NodeMemberEvent[ANode, ChildNode]) -> None:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def children_reordered(self, event: NodeReorderEvent[ANode, ChildNode]) -> None:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def node_destroyed(self, event: NodeEvent[ANode]) -> None:
        raise NotImplementedError  # pragma: no cover


# class NodeEvent(Enum):
#     ChildrenAdded = auto()
#     ChildrenRemoved = auto()
#     ChildrenReordered = auto()
#     NodeDestroyed = auto()


# class NodeListenersProtocol(Protocol):
#     def __call__(self, event: NodeEvent) -> Any: ...  # noqa: ANN401

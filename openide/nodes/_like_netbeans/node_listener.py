# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from abc import ABC, abstractmethod
from threading import RLock
from typing import TYPE_CHECKING, cast, final, TypeVar, Generic

# Third-party imports

# Local imports


T = TypeVar('T')
if TYPE_CHECKING:
    from collections import Iterable, Collection, Sequence, Generator
    from typing import Optional, Any
    from openide.nodes._like_netbeans.node import Node
    from openide.nodes._like_netbeans.children import Children


class Event(Generic[T]):

    def __init__(self, source: T) -> None:
        self._source = source  # transient

    @property
    def source(self) -> T:
        return self._source

    def __str__(self) -> str:
        return f'{type(self).__name__}({", ".join(self.__str_add__())})'

    __repr__ = __str__

    def __str_add__(self) -> Generator[str, None, None]:
        yield f'source={self._source}'


class NodeEvent(Event):

    def __init__(self, node: Node) -> None:
        super().__init__(node)

    @property
    @final
    def node(self) -> Node:
        return self.source

    def __str_add__(self) -> Generator[str, None, None]:
        yield f'node={self.node}'


class NodeMemberEvent(NodeEvent):

    def __init__(
        self,
        node: Node,
        add: bool,
        *,
        delta: Optional[Collection[Node]] = None,
        from_: Optional[Sequence[Node]] = None,
        indices: Optional[Iterable[int]] = None,
        current: Optional[Sequence[Node]] = None,
        previous: Optional[Sequence[Node]] = None,
    ) -> None:
        super().__init__(node)

        self.__delta: Optional[Collection[Node]]
        self.__indices: Optional[list[int]]
        self.__prev_snapshot: Optional[Sequence[Node]]
        self.__curr_snapshot: Sequence[Node]

        self.__lock = RLock()
        self.__add = add
        self._source_entry: Optional[Children.Entry] = None
        if (delta is not None):
            self.__delta = delta
            self.__prev_snapshot = from_
            self.__curr_snapshot = node._children.snapshot()
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
    def snapshot(self) -> Collection[Node]:
        return self.__curr_snapshot

    @property
    @final
    def is_add_event(self) -> bool:
        return self.__add

    @property
    def prev_snapshot(self) -> Sequence[Node]:
        return self.__prev_snapshot if self.__prev_snapshot is not None else self.__curr_snapshot

    @property
    @final
    def delta(self) -> Collection[Node]:
        if (delta := self.__delta) is None:
            indices = cast(list[int], self.__indices)
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
                    raise RuntimeError(
                        'Some of a set of deleted nodes are not present in the original one. '
                        'You may need to check that your Children.Keys keys are safely comparable.'
                    )

        return indices

    def __str_add__(self) -> Generator[str, None, None]:
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


class NodeReorderEvent(NodeEvent):
    # TODO: Be a Sequence, proxying self.__new_indices

    def __init__(self, node: Node, new_indices: Sequence[int]) -> None:
        super().__init__(node)

        self.__new_indices = new_indices
        self.__curr_snapshot = node._children.snapshot()

    @property
    @final
    def snapshot(self) -> Collection[Node]:
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

    def __str_add__(self) -> Generator[str, None, None]:
        yield from super().__str_add__()
        yield f'new_indices={self.__new_indices}'
        yield f'curr_snapshot={self.__curr_snapshot}'


class NodeListener(ABC):

    @abstractmethod
    def property_change(self, node: Node, name: str, old: Any, new: Any) -> None:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def children_added(self, event: NodeMemberEvent) -> None:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def children_removed(self, event: NodeMemberEvent) -> None:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def children_reordered(self, event: NodeReorderEvent) -> None:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def node_destroyed(self, event: NodeEvent) -> None:
        raise NotImplementedError()  # pragma: no cover

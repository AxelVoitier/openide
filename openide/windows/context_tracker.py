# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from collections.abc import Set
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, TypeVar
from weakref import WeakSet, ref

# Third-party imports
from listeners import KeyedListeners, KeyedObservable
from typing_extensions import override

# Local imports
from openide.utils import SingletonABCMeta

T = TypeVar('T')
if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Final
    from weakref import ReferenceType

    from openide.windows.top_component import TopComponent

__all__: Final = (
    'ContextTracker',
    'ContextTrackerChangeProtocol',
    'ContextTrackerEvents',
)


class _ReadOnlySet(Set[T]):
    def __init__(self, delegate: WeakSet[T]) -> None:
        super().__init__()

        self._delegate = delegate

    @override  # Collection
    def __len__(self) -> int:
        return len(self._delegate)

    @override  # AbstractSet
    def __contains__(self, other: object) -> bool:
        return other in self._delegate

    @override  # Iterable
    def __iter__(self) -> Iterator[T]:
        return iter(self._delegate)


class ContextTrackerEvents(Enum):
    Opened = 'opened'
    Closed = 'closed'
    Activated = 'activated'


class ContextTrackerChangeProtocol(Protocol):
    def __call__(
        self,
        event: ContextTrackerEvents,
        top_component: TopComponent,
        previous: TopComponent | None = None,
    ) -> Any: ...  # noqa: ANN401


class ContextTracker(
    KeyedListeners[ContextTrackerEvents, ContextTrackerChangeProtocol],
    metaclass=SingletonABCMeta,
):
    def __init__(self) -> None:
        super().__init__(keys=ContextTrackerEvents)

        self._activated_tc: ReferenceType[TopComponent] | None = None
        self._open_components: WeakSet[TopComponent] = WeakSet()
        self._observables = KeyedObservable(self)

    @property
    def opened(self) -> Set[TopComponent]:
        return _ReadOnlySet(self._open_components)

    @property
    def activated(self) -> TopComponent | None:
        if self._activated_tc is not None:
            return self._activated_tc()
        else:
            return None

    def top_component_activated(self, tc: TopComponent | None) -> None:
        old = self._activated_tc() if self._activated_tc is not None else None

        if old == tc:
            return

        if tc is not None:
            self._activated_tc = ref(tc)
        else:
            self._activated_tc = None

        event = ContextTrackerEvents.Activated
        self._observables[event](event, tc, old)

    def top_component_opened(self, tc: TopComponent) -> None:
        if tc in self._open_components:
            return

        self._open_components.add(tc)
        event = ContextTrackerEvents.Opened
        self._observables[event](event, tc)

    def top_component_closed(self, tc: TopComponent) -> None:
        if tc not in self._open_components:
            return

        self._open_components.remove(tc)
        event = ContextTrackerEvents.Closed
        self._observables[event](event, tc)

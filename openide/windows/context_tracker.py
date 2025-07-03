# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from collections.abc import Set  # noqa: PYI025
from enum import Enum
from typing import TYPE_CHECKING, TypeVar
from weakref import WeakSet, ref

# Third-party imports
from listeners import KeyedObservable

# Local imports
from openide.utils import MetaClassResolver, SingletonMeta

if TYPE_CHECKING:
    from collections.abc import Iterator
    from weakref import ReferenceType

    from openide.windows.top_component import TopComponent


T = TypeVar('T')


class _ReadOnlySet(Set[T]):
    def __init__(self, delegate: WeakSet[T]) -> None:
        self._delegate = delegate

    def __len__(self) -> int:
        return len(self._delegate)

    def __contains__(self, other: object) -> bool:
        return other in self._delegate

    def __iter__(self) -> Iterator[T]:
        return iter(self._delegate)


class ContextTracker(MetaClassResolver(KeyedObservable, extra_metas=[SingletonMeta])):
    class Events(Enum):
        Opened = 'opened'
        Closed = 'closed'
        Activated = 'activated'

    def __init__(self) -> None:
        super().__init__(keys=ContextTracker.Events)

        self._activated_tc: ReferenceType[TopComponent] | None = None
        self._open_components: WeakSet[TopComponent] = WeakSet()

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

        event = ContextTracker.Events.Activated
        self[event](event, tc, old)

    def top_component_opened(self, tc: TopComponent) -> None:
        if tc in self._open_components:
            return

        self._open_components.add(tc)
        event = ContextTracker.Events.Opened
        self[event](event, tc)

    def top_component_closed(self, tc: TopComponent) -> None:
        if tc not in self._open_components:
            return

        self._open_components.remove(tc)
        event = ContextTracker.Events.Closed
        self[event](event, tc)

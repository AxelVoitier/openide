# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# System imports
from collections.abc import Set
from enum import Enum
from weakref import ref, WeakSet

# Third-party imports
from lookups.weak_observable import WeakObservable

# Local imports
from openide.utils import SingletonMeta


class _ReadOnlySet(Set):

    def __init__(self, delegate):
        self._delegate = delegate

    def __len__(self):
        return len(self._delegate)

    def __contains__(self, other):
        return other in self._delegate

    def __iter__(self):
        return iter(self._delegate)


class ContextTracker(WeakObservable, metaclass=SingletonMeta):

    class Events(Enum):
        Opened = 'opened'
        Closed = 'closed'
        Activated = 'activated'

    def __init__(self):
        super().__init__()

        self._activated_tc = None
        self._open_components = WeakSet()

    @property
    def opened(self):
        return _ReadOnlySet(self._open_components)

    @property
    def activated(self):
        if self._activated_tc is not None:
            return self._activated_tc()
        else:
            return None

    def top_component_activated(self, tc):
        old = self._activated_tc() if self._activated_tc is not None else None

        if old == tc:
            return

        if tc is not None:
            self._activated_tc = ref(tc)
        else:
            self._activated_tc = None

        event = ContextTracker.Events.Activated
        self.trigger(event, event, tc, old)

    def top_component_opened(self, tc):
        if tc in self._open_components:
            return

        self._open_components.add(tc)
        event = ContextTracker.Events.Opened
        self.trigger(event, event, tc)

    def top_component_closed(self, tc):
        if tc not in self._open_components:
            return

        self._open_components.remove(tc)
        event = ContextTracker.Events.Closed
        self.trigger(event, event, tc)

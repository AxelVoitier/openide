# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from typing import TYPE_CHECKING

# Third-party imports
from lookups import DelegatedLookup, EmptyLookup, Lookup, LookupProvider

# Local imports
from openide.services import GlobalContext, ServiceProvider
from openide.windows import ContextTracker

if TYPE_CHECKING:
    from lookups import Lookup

    from openide.windows.top_component import TopComponent


@ServiceProvider(service=GlobalContext)
class DefaultGlobalContext(DelegatedLookup, LookupProvider, GlobalContext):
    def __init__(self) -> None:
        self._default_lookup: Lookup = EmptyLookup()
        self._current_lookup: Lookup = self._default_lookup
        ContextTracker()[ContextTracker.Events.Activated].add(self._context_changed)

        super().__init__(self)

    def get_lookup(self) -> Lookup:
        return self._current_lookup

    def _context_changed(
        self,
        event: ContextTracker.Events,
        tc: TopComponent | None,
        old=None,
    ) -> None:
        if event != ContextTracker.Events.Activated:
            return

        lookup = None
        if tc is not None:
            lookup = tc.get_lookup()
        self._current_lookup = lookup if lookup is not None else self._default_lookup
        self.lookup_updated()

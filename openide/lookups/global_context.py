# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# System imports

# Third-party imports
from lookups import Lookup, LookupProvider, DelegatedLookup, EmptyLookup

# Local imports
from openide.lookups import ServiceProvider, ServiceSingletonABCMeta
from openide.windows import ContextTracker


class GlobalContext(Lookup, metaclass=ServiceSingletonABCMeta):

    pass


@ServiceProvider(service=GlobalContext)
class DefaultGlobalContext(DelegatedLookup, LookupProvider, GlobalContext):

    def __init__(self):
        self._default_lookup = EmptyLookup()
        self._current_lookup = self._default_lookup
        ContextTracker().on(ContextTracker.Events.Activated, self._context_changed)

        super().__init__(self)

    def get_lookup(self):
        return self._current_lookup

    def _context_changed(self, event, tc, old=None):
        if event != ContextTracker.Events.Activated:
            return

        lookup = None
        if tc is not None:
            lookup = tc.get_lookup()
        self._current_lookup = lookup if lookup is not None else self._default_lookup
        self.lookup_updated()

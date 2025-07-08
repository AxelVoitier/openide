# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from typing import Any

# Third-party imports
from lookups import Convertor, GenericLookup, InstanceContent, ProxyLookup

# Local imports
from openide.lookup import EggInfoLookup
from openide.utils import MetaClassResolver, SingletonMeta


class MainLookup(MetaClassResolver(ProxyLookup, extra_metas=[SingletonMeta])):
    def __init__(self) -> None:
        super().__init__()

        self._egg_info_lookup = EggInfoLookup('services')
        self._instance_content = InstanceContent()
        self.register(self)
        self._instance_lookup = GenericLookup(self._instance_content)

        super().__init__(self._egg_info_lookup, self._instance_lookup)

    def register(self, instance: object, convertor: Convertor[Any, Any] | None = None) -> None:
        self._instance_content.add(instance, convertor)

    def unregister(self, instance: object, convertor: Convertor[Any, Any] | None = None) -> None:
        self._instance_content.remove(instance, convertor)

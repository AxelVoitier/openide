# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# System imports

# Third-party imports
from lookups import ProxyLookup, GenericLookup, InstanceContent, Convertor

# Local imports
from openide.lookups import EggInfoLookup
from openide.utils import SingletonMeta, MetaClassResolver


class MainLookup(MetaClassResolver(ProxyLookup, extra_metas=[SingletonMeta])):

    def __init__(self):
        self._egg_info_lookup = EggInfoLookup('services')
        self._instance_content = InstanceContent()
        self.register(self)
        self._instance_lookup = GenericLookup(self._instance_content)

        super().__init__(self._egg_info_lookup, self._instance_lookup)

    def register(self, instance: object, convertor: Convertor = None) -> None:
        self._instance_content.add(instance, convertor)

    def unregister(self, instance: object, convertor: Convertor = None) -> None:
        self._instance_content.remove(instance, convertor)

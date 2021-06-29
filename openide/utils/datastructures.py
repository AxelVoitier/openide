# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# System imports
from collections.abc import Mapping

# Third-party imports

# Local imports


class RecursiveDict(dict):

    def merge(self, other):
        for k, v in other.items():
            if isinstance(v, Mapping):
                if k not in self:
                    self[k] = RecursiveDict()
                self[k].merge(v)
            elif isinstance(v, list):
                if k not in self:
                    self[k] = []
                self[k] += v
            else:
                self[k] = v

        return self

    def prune_none(self):
        for k, v in list(self.items()):
            if v is None:
                del self[k]
            elif isinstance(v, RecursiveDict):
                v.prune_none()

        return self

    def to_dict(self):
        d = {}
        for k, v in self.items():
            if isinstance(v, RecursiveDict):
                d[k] = v.to_dict()
            else:
                d[k] = v

        return d

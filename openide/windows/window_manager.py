# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# System imports
from abc import abstractmethod

# Third-party imports

# Local imports
from openide.lookups import ServiceSingletonABCMeta


class WindowManager(metaclass=ServiceSingletonABCMeta):

    @abstractmethod
    def find_mode(self, name):
        raise NotImplementedError()

    @abstractmethod
    def find_top_component(self, target_id: str):
        raise NotImplementedError()

    @abstractmethod
    def top_component_open(self, tc, tab_position: int = -1):
        raise NotImplementedError()

    @abstractmethod
    def top_component_request_active(self, tc):
        raise NotImplementedError()

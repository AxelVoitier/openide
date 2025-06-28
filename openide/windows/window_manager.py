# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from abc import abstractmethod
from typing import TYPE_CHECKING

# Third-party imports
# Local imports
from openide.lookup import ServiceSingletonABCMeta

if TYPE_CHECKING:
    from openide.windows.top_component import TopComponent


class WindowManager(metaclass=ServiceSingletonABCMeta):
    @abstractmethod
    def find_mode(self, name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_top_component(self, target_id: str) -> TopComponent | None:
        raise NotImplementedError

    @abstractmethod
    def top_component_open(self, tc: TopComponent, tab_position: int = -1) -> None:
        raise NotImplementedError

    @abstractmethod
    def top_component_request_active(self, tc: TopComponent) -> None:
        raise NotImplementedError

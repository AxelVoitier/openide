# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore

from __future__ import annotations

import importlib.metadata
import logging

# System imports
from typing import TYPE_CHECKING, TypedDict, cast

# Third-party imports
import yaml
from typing_extensions import NotRequired

# Local imports
from openide.utils.datastructures import RecursiveDict

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from openide.actions import ActionConfig
    from openide.layout import LayoutConfig
    from openide.services.registration import ServiceConfig
    from openide.windows import ComponentConfig


_logger = logging.getLogger(__name__)


class Config(TypedDict):
    services: NotRequired[dict[str, ServiceConfig]]
    components: NotRequired[dict[str, ComponentConfig]]
    actions: NotRequired[list[ActionConfig]]
    layout: NotRequired[LayoutConfig]


def load_config(per_package_cb: Callable[[str, str], Any] | None = None) -> Config:
    full_config = RecursiveDict()
    for dist in importlib.metadata.distributions():
        config = dist.read_text('extra_metadata/openide.yaml')
        if not config:
            continue

        if per_package_cb:
            per_package_cb(dist.name, config)

        full_config.merge(yaml.safe_load(config))

    return cast('Config', full_config)

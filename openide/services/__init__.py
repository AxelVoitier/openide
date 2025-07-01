# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# /!\ Be careful of what is included here (in terms of third-party dependencies),
# as this gets imported during the integration/setup hooks.

# ruff: noqa: I001

# Order matters to avoid cyclic imports

from .registration import ServiceProvider, ServiceSingletonABCMeta, ServiceSingletonMeta

from .global_context import GlobalContext
from .window_manager import WindowManager

__all__ = [
    'GlobalContext',
    'ServiceProvider',
    'ServiceSingletonABCMeta',
    'ServiceSingletonMeta',
    'WindowManager',
]

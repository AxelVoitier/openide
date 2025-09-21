# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# /!\ Be careful of what is included here (in terms of third-party dependencies),
# as this gets imported during the integration/setup hooks.

# ruff: noqa: I001

# Order matters to avoid cyclic imports
from . import registration
from . import global_context, package_lifecycle, status_displayer, window_manager

from .registration import *  # noqa: F403
from .global_context import *  # noqa: F403
from .package_lifecycle import *  # noqa: F403
from .status_displayer import *  # noqa: F403
from .window_manager import *  # noqa: F403

__all__: list[str] = []
__all__ += registration.__all__
__all__ += global_context.__all__
__all__ += package_lifecycle.__all__
__all__ += status_displayer.__all__
__all__ += window_manager.__all__

# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import Literal

# Initially we are mostly going to re-export from _like_netbeans.
# And as it progress towards a more pythonic interfaces, the various original
#  bits will be replaced with newer from here.
IMPLEMENTATION: Literal['_like_netbeans', '_refactor1'] = '_refactor1'
match IMPLEMENTATION:
    case '_like_netbeans':
        from . import _like_netbeans as _implementation
        from ._like_netbeans import *  # noqa: F403
    case '_refactor1':
        from . import _refactor1 as _implementation
        from ._refactor1 import *  # noqa: F403

# from . import abstract_sheet_user, properties, properties_support, sheet_support  # noqa: E402
from .abstract_sheet_user import *  # noqa: F403
from .properties import *  # noqa: F403
from .properties_support import *  # noqa: F403
from .sheet_support import *  # noqa: F403

__all__: list[str] = []
__all__ += _implementation.__all__
__all__ += abstract_sheet_user.__all__
__all__ += properties.__all__
__all__ += properties_support.__all__
__all__ += sheet_support.__all__

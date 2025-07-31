# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# Initially we are mostly going to re-export from _like_netbeans.
# And as it progress towards a more pythonic interfaces, the various original
#  bits will be replaced with newer from here.
from ._like_netbeans import *  # noqa: F403

__all__: list[str] = []
__all__ += _like_netbeans.__all__

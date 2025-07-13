# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Defining LayoutConfig part
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from typing_extensions import NotRequired

if TYPE_CHECKING:
    # Fenced by TYPE_CHECKING to avoid cyclic imports
    from .location import LocationConfig


class LayoutConfig(TypedDict):
    locations: NotRequired[dict[str, LocationConfig]]


# Re-export part
from .location import (  # noqa: E402
    Location,
    LocationConfig,
    LocationKind,
    LocationPathConfig,
    LocationsModel,
)

__all__ = [
    'Location',
    'LocationConfig',
    'LocationKind',
    'LocationPathConfig',
    'LocationsModel',
]

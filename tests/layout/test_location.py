# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore
""""""

from __future__ import annotations

# System imports
import logging
from typing import TYPE_CHECKING

# Third-party imports
import pytest
from PySide6.QtCore import Qt

# Local imports
from openide.layout import Location, LocationPathConfig, LocationsModel
from openide.layout.location import (
    BottomPanelLocation,
    CentralLocation,
    FloatLocation,
    LeftPanelLocation,
    RightPanelLocation,
    TopPanelLocation,
)

if TYPE_CHECKING:
    pass

_logger = logging.getLogger(__name__)


@Location.Registration(
    name='super-left-panel',
    kind='dock',
    paths=[LocationPathConfig(orientation='horizontal', index=-75)],
)
class SuperLeftPanelLocation(Location):
    pass


@Location.Registration(
    name='above-super-left-panel',
    kind='dock',
    paths=[
        LocationPathConfig(orientation='horizontal', index=-75),
        LocationPathConfig(orientation='vertical', index=-25),
    ],
)
class AboveSuperLeftPanelLocation(Location):
    pass


@Location.Registration(
    name='below-left-panel',
    kind='dock',
    paths=[
        LocationPathConfig(orientation='horizontal', index=-50),
        LocationPathConfig(orientation='vertical', index=25),
    ],
)
class BelowLeftPanelLocation(Location):
    pass


@pytest.fixture
def locations_model_default() -> LocationsModel:
    model = LocationsModel()
    model.add_location(CentralLocation())
    model.add_location(LeftPanelLocation())
    model.add_location(RightPanelLocation())
    model.add_location(TopPanelLocation())
    model.add_location(BottomPanelLocation())
    model.add_location(FloatLocation())

    return model


@pytest.fixture
def locations_model_extended(locations_model_default: LocationsModel) -> LocationsModel:
    locations_model_default.add_location(SuperLeftPanelLocation())
    locations_model_default.add_location(AboveSuperLeftPanelLocation())
    locations_model_default.add_location(BelowLeftPanelLocation())

    return locations_model_default


@pytest.mark.parametrize(
    ('target_name', 'fixture'),
    [
        ('central', []),
        ('left-panel', []),
        ('right-panel', []),
        ('top-panel', []),
        ('bottom-panel', []),
        ('float', []),
    ],
)
def test_model_get_split_path_default(
    locations_model_default: LocationsModel,
    target_name: str,
    fixture: list[tuple[Location, Location, Qt.Orientation]],
) -> None:
    model = locations_model_default
    target = model[target_name]
    result = list(model.get_split_path(target))

    assert result == fixture


@pytest.mark.parametrize(
    ('target_name', 'fixture'),
    [
        ('central', []),
        ('left-panel', []),
        ('right-panel', []),
        ('top-panel', []),
        ('bottom-panel', []),
        ('float', []),
    ],
)
def test_model_get_split_path_extended(
    locations_model_extended: LocationsModel,
    target_name: str,
    fixture: list[tuple[Location, Location, Qt.Orientation]],
) -> None:
    model = locations_model_extended
    target = model[target_name]
    result = list(model.get_split_path(target))

    assert result == fixture

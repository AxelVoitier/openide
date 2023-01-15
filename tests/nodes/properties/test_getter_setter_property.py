# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports

# Third-party imports
import pytest

# Local imports
from openide.nodes.properties_support import GetterSetterProperty


class RWMethods:

    def __init__(self) -> None:
        self.__attr = 0

    def get_attr(self) -> int:
        return self.__attr

    def set_attr(self, value: int) -> None:
        self.__attr = value

    not_a_method = 45


def test_read_write() -> None:
    rw = RWMethods()
    prop = GetterSetterProperty(rw.get_attr, rw.set_attr)

    assert prop.value_type is int
    assert prop.can_read is True
    assert prop.can_write is True

    assert prop.value == 0
    prop.value = 12
    assert prop.value == 12
    assert rw.get_attr() == 12


class ROMethods:

    def __init__(self, value: int) -> None:
        self.__attr = value

    def get_attr(self) -> int:
        return self.__attr


def test_read_only() -> None:
    ro = ROMethods(72)
    prop = GetterSetterProperty(ro.get_attr)

    assert prop.value_type is int
    assert prop.can_read is True
    assert prop.can_write is False

    assert prop.value == 72

    with pytest.raises(AttributeError):
        prop.value = 12


def test_write_only() -> None:
    wo = RWMethods()
    prop = GetterSetterProperty(None, wo.set_attr)

    assert prop.value_type is int
    assert prop.can_read is False
    assert prop.can_write is True

    assert wo.get_attr() == 0
    prop.value = 27
    assert wo.get_attr() == 27

    with pytest.raises(AttributeError):
        _ = prop.value


def test_not_method() -> None:
    rw = RWMethods()

    with pytest.raises(TypeError):
        GetterSetterProperty(rw.not_a_method)  # type: ignore

    with pytest.raises(TypeError):
        GetterSetterProperty(None, rw.not_a_method)  # type: ignore


def test_no_getter_and_setter() -> None:
    with pytest.raises(ValueError):
        GetterSetterProperty()


class NoTypeGetter:

    def __init__(self, value: int) -> None:
        self.__attr = value

    def get_attr(self):  # type: ignore
        return self.__attr


def test_no_type_hint() -> None:
    ro = NoTypeGetter(83)

    with pytest.raises(ValueError):
        GetterSetterProperty(ro.get_attr)

    prop = GetterSetterProperty(ro.get_attr, value_type=int)

    assert prop.value_type is int
    assert prop.can_read is True
    assert prop.can_write is False

    assert prop.value == 83

    with pytest.raises(AttributeError):
        prop.value = 12

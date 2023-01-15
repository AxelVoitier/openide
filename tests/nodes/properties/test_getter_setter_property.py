# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from copy import copy

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

    def check(prop: GetterSetterProperty, init_value: int, set_value: int) -> None:
        assert prop.value_type is int
        assert prop.can_read is True
        assert prop.can_write is True

        assert prop.value == init_value
        assert rw.get_attr() == init_value
        prop.value = set_value
        assert prop.value == set_value
        assert rw.get_attr() == set_value

    prop = GetterSetterProperty(rw.get_attr, rw.set_attr)
    check(prop, 0, 12)

    cloned_prop = copy(prop)
    check(cloned_prop, 12, 24)
    check(prop, 24, 36)


class ROMethods:

    def __init__(self, value: int) -> None:
        self.__attr = value

    def get_attr(self) -> int:
        return self.__attr

    def set_attr(self, value: int) -> None:
        self.__attr = value


def test_read_only() -> None:
    ro = ROMethods(72)

    def check(prop: GetterSetterProperty, init_value: int) -> None:
        assert prop.value_type is int
        assert prop.can_read is True
        assert prop.can_write is False

        assert prop.value == init_value

        with pytest.raises(AttributeError):
            prop.value = 12

    prop = GetterSetterProperty(ro.get_attr)
    check(prop, 72)

    cloned_prop = copy(prop)
    check(cloned_prop, 72)

    ro.set_attr(46)
    check(prop, 46)
    check(cloned_prop, 46)


def test_write_only() -> None:
    wo = RWMethods()

    def check(prop: GetterSetterProperty, init_value: int, set_value: int) -> None:
        assert prop.value_type is int
        assert prop.can_read is False
        assert prop.can_write is True

        assert wo.get_attr() == init_value
        prop.value = set_value
        assert wo.get_attr() == set_value

        with pytest.raises(AttributeError):
            _ = prop.value

    prop = GetterSetterProperty(None, wo.set_attr)
    check(prop, 0, 27)

    cloned_prop = copy(prop)
    check(cloned_prop, 27, 54)
    check(prop, 54, 81)


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

    def set_attr(self, value: int) -> None:
        self.__attr = value


def test_no_type_hint() -> None:
    ro = NoTypeGetter(83)

    with pytest.raises(ValueError):
        GetterSetterProperty(ro.get_attr)

    def check(prop: GetterSetterProperty, init_value: int) -> None:
        assert prop.value_type is int
        assert prop.can_read is True
        assert prop.can_write is False

        assert prop.value == init_value

        with pytest.raises(AttributeError):
            prop.value = 12

    prop = GetterSetterProperty(ro.get_attr, value_type=int)
    check(prop, 83)

    cloned_prop = copy(prop)
    check(cloned_prop, 83)

    ro.set_attr(41)
    check(prop, 41)
    check(cloned_prop, 41)

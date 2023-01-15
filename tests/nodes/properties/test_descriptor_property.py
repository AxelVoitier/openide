# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from typing import Optional, Protocol, Type

# Third-party imports
import pytest

# Local imports
from openide.nodes.properties_support import (
    DescriptorProperty,
    GettableDescriptorProtocol,
    SettableDescriptorProtocol,
)


class RWDescriptorProtocol(GettableDescriptorProtocol, SettableDescriptorProtocol, Protocol):
    ...


class RWTestProtocol(Protocol):
    def __init__(self) -> None: ...

    attr: RWDescriptorProtocol


class RWProperty:

    def __init__(self) -> None:
        self.__attr = 0

    @property
    def attr(self) -> int:
        return self.__attr

    @attr.setter
    def attr(self, value: int) -> None:
        self.__attr = value

    not_a_descriptor = 45


class RWDescriptor:

    class _RWDescriptor:

        def __get__(
            self,
            obj: Optional[RWDescriptor],
            objtype: Optional[Type[RWDescriptor]] = None
        ) -> int:
            if obj is not None:
                return obj._value
            else:
                return -1

        def __set__(self, obj: RWDescriptor, value: int) -> None:
            obj._value = value

    def __init__(self) -> None:
        self._value = 0

    attr = _RWDescriptor()


@pytest.mark.parametrize(
    'rw', [
        RWProperty(),
        RWDescriptor(),
    ]
)
def test_read_write(rw: RWTestProtocol) -> None:
    prop: DescriptorProperty[int] = DescriptorProperty(rw, 'attr')

    assert prop.system_name == 'attr'
    assert prop.value_type is int
    assert prop.can_read is True
    assert prop.can_write is True

    assert prop.value == 0
    prop.value = 12
    assert prop.value == 12
    assert rw.attr == 12


class ROTestProtocol(Protocol):
    def __init__(self, value: int) -> None: ...

    attr: GettableDescriptorProtocol


class ROProperty:

    def __init__(self, value: int) -> None:
        self.__attr = value

    @property
    def attr(self) -> int:
        return self.__attr


class RODescriptor:

    class _RODescriptor:

        def __get__(
            self,
            obj: Optional[RODescriptor],
            objtype: Optional[Type[RODescriptor]] = None
        ) -> int:
            if obj is not None:
                return obj._value
            else:
                return -1

    def __init__(self, value: int) -> None:
        self._value = value

    attr = _RODescriptor()


@pytest.mark.parametrize(
    'ro', [
        ROProperty(72),
        RODescriptor(72),
    ]
)
def test_read_only(ro: ROTestProtocol) -> None:
    prop: DescriptorProperty[int] = DescriptorProperty(ro, 'attr')

    assert prop.system_name == 'attr'
    assert prop.value_type is int
    assert prop.can_read is True
    assert prop.can_write is False

    assert prop.value == 72

    with pytest.raises(AttributeError):
        prop.value = 12


class WOTestProtocol(Protocol):
    def __init__(self) -> None: ...

    def get_attr(self) -> int: ...

    attr: SettableDescriptorProtocol


class WOProperty:

    def __init__(self) -> None:
        self.__attr = 0

    def get_attr(self) -> int:
        return self.__attr

    def _set_attr(self, value: int) -> None:
        self.__attr = value

    attr = property(None, _set_attr, None)


class WODescriptor:

    class _WODescriptor:

        def __set__(self, obj: WODescriptor, value: int) -> None:
            obj._value = value

    def __init__(self) -> None:
        self._value = 0

    def get_attr(self) -> int:
        return self._value

    attr = _WODescriptor()


@pytest.mark.parametrize(
    'wo', [
        WOProperty(),
        WODescriptor(),
    ]
)
def test_write_only(wo: WOTestProtocol) -> None:
    prop: DescriptorProperty[int] = DescriptorProperty(wo, 'attr')

    assert prop.system_name == 'attr'
    assert prop.value_type is int
    assert prop.can_read is False
    assert prop.can_write is True

    assert wo.get_attr() == 0
    prop.value = 27
    assert wo.get_attr() == 27

    with pytest.raises(AttributeError):
        _ = prop.value


def test_not_descriptor_direct() -> None:
    rw = RWProperty()
    with pytest.raises(TypeError):
        DescriptorProperty(
            rw,
            RWProperty.not_a_descriptor  # type: ignore
        )


def test_not_descriptor_by_name() -> None:
    rw = RWProperty()
    with pytest.raises(TypeError):
        DescriptorProperty(rw, 'not_a_descriptor')


def test_unknown() -> None:
    rw = RWProperty()
    with pytest.raises(ValueError):
        DescriptorProperty(rw, 'nop')


class Plenty:

    # Check it does not try to use some special descriptors
    # (slot members, function, class method and static method,
    # and few other peculiar attributes).
    __slots__ = ('_value',)

    def __init__(self) -> None:
        self._value = 14

    def method(self) -> None:
        ...

    @classmethod
    def class_method(cls) -> None:
        ...

    @staticmethod
    def static_method() -> None:
        ...

    class_attr = 'no'

    @property
    def attr_int(self) -> int:
        return 12

    @property
    def attr_str(self) -> str:
        return 'hello'

    # attr_bool value_type will be detected from setter
    @property
    def attr_bool(self):  # type: ignore
        return True

    @attr_bool.setter
    def attr_bool(self, value: bool) -> None:
        ...

    # attr_something value_type will be given explicitly
    @property
    def attr_something(self):  # type: ignore
        return RWProperty()

    attr_descr = RODescriptor._RODescriptor()


def test_all_properties() -> None:
    plenty = Plenty()

    properties = dict(DescriptorProperty.all_properties(plenty, dict(attr_something=RWProperty)))
    seen = dict(attr_int=False, attr_str=False, attr_bool=False, attr_something=False)
    for name, prop in properties.items():
        assert name == prop.system_name

        if name == 'attr_int':
            assert prop.value_type is int
            assert prop.can_read is True
            assert prop.can_write is False
            assert prop.value == 12

        elif name == 'attr_str':
            assert prop.value_type is str
            assert prop.can_read is True
            assert prop.can_write is False
            assert prop.value == 'hello'

        elif name == 'attr_bool':
            assert prop.value_type is bool
            assert prop.can_read is True
            assert prop.can_write is True
            assert isinstance(prop.value, bool)
            assert prop.value is True

        elif name == 'attr_something':
            assert prop.value_type is RWProperty
            assert prop.can_read is True
            assert prop.can_write is False
            assert isinstance(prop.value, RWProperty)

        elif name == 'attr_descr':
            assert prop.value_type is int
            assert prop.can_read is True
            assert prop.can_write is False
            assert prop.value == 14

        else:
            assert False, f'{prop.system_name} property should not be here'

        seen[prop.system_name] = True

    assert all(seen.values())


class PlentyBad:

    @property
    def no_value_type_getter(self):  # type: ignore
        ...

    def _bad_setter(self) -> None:
        ...

    bad_setter = property(None, _bad_setter, None)  # type: ignore

    only_deleter_property = property(None, None, lambda _: None)

    class _DeleteDescriptor:
        def __delete__(self, obj: PlentyBad) -> None: ...

    only_deleter_descriptor = _DeleteDescriptor()


@pytest.mark.parametrize(
    'attribute, expected_exception', [
        ('no_value_type_getter', ValueError),
        ('bad_setter', ValueError),
        ('only_deleter_descriptor', TypeError),
        # A property will appear of the right type. However, it will lack getter and setter values
        ('only_deleter_property', ValueError),
    ]
)
def test_bad_properties(attribute: str, expected_exception: Type[Exception]) -> None:
    plenty_bad = PlentyBad()

    with pytest.raises(expected_exception):
        DescriptorProperty(plenty_bad, attribute)

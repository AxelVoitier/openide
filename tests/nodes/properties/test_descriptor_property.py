# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:words openide netbeans
# spell-checker:ignore descr objtype

from __future__ import annotations

# System imports
from collections.abc import Mapping
from copy import copy, deepcopy
from typing import Any, Protocol, Self, TypeVar

# Third-party imports
import pytest

# Local imports
from openide.nodes import (
    DescriptorProperty,
    DescriptorProtocol,
    FeatureDescriptor,
    GettableDescriptorProtocol,
    SettableDescriptorProtocol,
)

T = TypeVar('T')


def find_in_mro(instance: Any, name: str) -> Any:  # noqa: ANN401
    for base in type(instance).__mro__:
        if (attr := vars(base).get(name, None)) is not None:
            return attr
    raise AttributeError(name)


class RWTestProtocol(Protocol[T]):
    # def __init__(self) -> None: ...

    attr: DescriptorProtocol[Self, T, T]


class RWProperty:
    def __init__(self) -> None:
        super().__init__()

        self.__attr = 0

    @property
    def attr(self) -> int:
        return self.__attr

    @attr.setter
    def attr(self, value: int) -> None:
        self.__attr = value

    not_a_descriptor = 45


class RWPropertySub(RWProperty):
    pass


class RWDescriptor:
    class _RWDescriptor:
        __name__: str | None = None

        def __set_name__(self, owner: RWDescriptor, name: str) -> None:
            self.__name__ = name

        def __get__(
            self,
            obj: RWDescriptor | None,
            objtype: type[RWDescriptor] | None = None,
        ) -> int:
            if obj is not None:
                return obj._value
            else:
                # We want it to work even with "non-cooperative" descriptor not returning self
                return -1

        def __set__(self, obj: RWDescriptor, value: int) -> None:
            obj._value = value

    def __init__(self) -> None:
        super().__init__()

        self._value = 0

    attr = _RWDescriptor()


class RWDescriptorSub(RWDescriptor):
    pass


@pytest.mark.parametrize(
    'rw',
    [
        RWProperty(),
        RWPropertySub(),
        RWDescriptor(),
        RWDescriptorSub(),
    ],
)
def test_read_write(rw: RWTestProtocol[int]) -> None:
    called: dict[str, Any] = {}

    def listener(
        source: DescriptorProperty[int],
        name: str,
        old_value: int | None,
        new_value: int,
    ) -> None:
        nonlocal called
        print(f'listener called: {source=}, {name=}, {old_value=}, {new_value=}')
        called |= dict(source=source, name=name, old_value=old_value, new_value=new_value)

    def check(prop: DescriptorProperty[int], init_value: int, set_value: int) -> None:
        assert prop.system_name == 'attr'
        assert prop.value_type is int
        assert prop.can_read is True
        assert prop.can_write is True

        assert prop.value == init_value
        assert rw.attr == init_value
        assert not called

        prop.value = set_value
        assert prop.value == set_value
        assert rw.attr == set_value
        assert called
        assert called == dict(source=prop, name='attr', old_value=init_value, new_value=set_value)

    # By name and giving the type
    prop = DescriptorProperty(rw, 'attr', int)
    prop.listeners += listener
    check(prop, 0, 12)
    called.clear()

    cloned_prop = copy(prop)
    cloned_prop.listeners += listener
    check(cloned_prop, 12, 24)
    called.clear()
    check(prop, 24, 36)
    called.clear()

    # By property/descriptor and guessing the type
    prop = DescriptorProperty(rw, find_in_mro(rw, 'attr'))
    prop.listeners += listener
    check(prop, 36, 24)
    called.clear()

    cloned_prop = copy(prop)
    cloned_prop.listeners += listener
    check(cloned_prop, 24, 12)
    called.clear()
    check(prop, 12, 0)


class ROTestProtocol(Protocol):
    def __init__(self, value: int) -> None: ...  # pyright: ignore[reportMissingSuperCall]

    attr: GettableDescriptorProtocol[Self, int]

    def set_attr(self, value: int) -> None: ...


class ROProperty:
    def __init__(self, value: int) -> None:
        super().__init__()

        self.__attr = value

    @property
    def attr(self) -> int:
        return self.__attr

    def set_attr(self, value: int) -> None:
        self.__attr = value


class ROPropertySub(ROProperty):
    pass


class RODescriptor:
    class _RODescriptor:
        __name__: str | None = None

        def __set_name__(self, owner: RWDescriptor, name: str) -> None:
            self.__name__ = name

        def __get__(
            self,
            obj: RODescriptor | None,
            objtype: type[RODescriptor] | None = None,
        ) -> int:
            if obj is not None:
                return obj._value
            else:
                # We want it to work even with "non-cooperative" descriptor not returning self
                return -1

    def __init__(self, value: int) -> None:
        super().__init__()

        self._value = value

    attr = _RODescriptor()

    def set_attr(self, value: int) -> None:
        self._value = value


class RODescriptorSub(RODescriptor):
    pass


@pytest.mark.parametrize(
    'ro',
    [
        ROProperty(72),
        ROPropertySub(72),
        RODescriptor(72),
        RODescriptorSub(72),
    ],
)
def test_read_only(ro: ROTestProtocol) -> None:
    def check(prop: DescriptorProperty[int], init_value: int) -> None:
        assert prop.system_name == 'attr'
        assert prop.value_type is int
        assert prop.can_read is True
        assert prop.can_write is False

        assert prop.value == init_value

        with pytest.raises(AttributeError):
            prop.value = 12

    # By name and giving the type
    prop = DescriptorProperty(ro, 'attr', int)
    check(prop, 72)

    cloned_prop = copy(prop)
    check(cloned_prop, 72)

    ro.set_attr(46)
    check(prop, 46)
    check(cloned_prop, 46)

    # By property/descriptor and guessing the type
    prop = DescriptorProperty(ro, find_in_mro(ro, 'attr'))
    check(prop, 46)

    cloned_prop = copy(prop)
    check(cloned_prop, 46)

    ro.set_attr(72)
    check(prop, 72)
    check(cloned_prop, 72)


class WOTestProtocol(Protocol):
    def __init__(self) -> None: ...  # pyright: ignore[reportMissingSuperCall]

    def get_attr(self) -> int: ...

    attr: SettableDescriptorProtocol[Self, int]


class WOProperty:
    def __init__(self) -> None:
        super().__init__()

        self.__attr = 0

    def get_attr(self) -> int:
        return self.__attr

    def _set_attr(self, value: int) -> None:
        self.__attr = value

    attr = property(None, _set_attr, None)


class WOPropertySub(WOProperty):
    pass


class WODescriptor:
    class _WODescriptor:
        __name__: str | None = None

        def __set_name__(self, owner: RWDescriptor, name: str) -> None:
            self.__name__ = name

        def __set__(self, obj: WODescriptor, value: int) -> None:
            obj._value = value

    def __init__(self) -> None:
        super().__init__()

        self._value = 0

    def get_attr(self) -> int:
        return self._value

    attr = _WODescriptor()


class WODescriptorSub(WODescriptor):
    pass


@pytest.mark.parametrize(
    'wo',
    [
        WOProperty(),
        WOPropertySub(),
        WODescriptor(),
        WODescriptorSub(),
    ],
)
def test_write_only(wo: WOTestProtocol) -> None:
    called: dict[str, Any] = {}

    def listener(
        source: DescriptorProperty[int],
        name: str,
        old_value: int | None,
        new_value: int,
    ) -> None:
        nonlocal called
        print(f'listener called: {source=}, {name=}, {old_value=}, {new_value=}')
        called |= dict(source=source, name=name, old_value=old_value, new_value=new_value)

    def check(prop: DescriptorProperty[int], init_value: int, set_value: int) -> None:
        assert prop.system_name == 'attr'
        assert prop.value_type is int
        assert prop.can_read is False
        assert prop.can_write is True

        assert wo.get_attr() == init_value
        prop.value = set_value
        assert wo.get_attr() == set_value
        assert called
        assert called == dict(source=prop, name='attr', old_value=None, new_value=set_value)

        with pytest.raises(AttributeError):
            _ = prop.value

    # By name and giving the type
    prop = DescriptorProperty(wo, 'attr', int)
    prop.listeners += listener
    check(prop, 0, 27)
    called.clear()

    cloned_prop = copy(prop)
    cloned_prop.listeners += listener
    check(cloned_prop, 27, 54)
    called.clear()
    check(prop, 54, 81)
    called.clear()

    # By property/descriptor and guessing the type
    prop = DescriptorProperty(wo, find_in_mro(wo, 'attr'))
    prop.listeners += listener
    check(prop, 81, 54)
    called.clear()

    cloned_prop = copy(prop)
    cloned_prop.listeners += listener
    check(cloned_prop, 54, 27)
    called.clear()
    check(prop, 27, 0)


def test_not_descriptor_direct() -> None:
    rw = RWProperty()
    with pytest.raises(TypeError):
        DescriptorProperty(
            rw,
            RWProperty.not_a_descriptor,  # pyright: ignore[reportArgumentType]
        )


def test_not_descriptor_by_name() -> None:
    rw = RWProperty()
    with pytest.raises(TypeError):
        DescriptorProperty(rw, 'not_a_descriptor')


def test_unknown() -> None:
    rw = RWProperty()
    with pytest.raises(AttributeError):
        DescriptorProperty(rw, 'nop')


class Plenty:
    # Check it does not try to use some special descriptors
    # (slot members, function, class method and static method,
    # and few other peculiar attributes).
    __slots__ = ('_value',)

    def __init__(self) -> None:
        super().__init__()

        self._value = 14

    def method(self) -> None: ...

    @classmethod
    def class_method(cls) -> None: ...

    @staticmethod
    def static_method() -> None: ...

    class_attr = 'no'

    @property
    def attr_int(self) -> int:
        return 12

    @property
    def attr_str(self) -> str:
        return 'hello'

    # attr_bool value_type will be detected from setter
    @property
    def attr_bool(self) -> bool:
        return True

    @attr_bool.setter
    def attr_bool(self, value: bool) -> None: ...

    # attr_something value_type will be given explicitly
    @property
    def attr_something(self) -> RWProperty:
        return RWProperty()

    attr_descr = RODescriptor._RODescriptor()


class PlentySub(Plenty):
    pass


@pytest.mark.parametrize(
    'plenty',
    [
        Plenty(),
        PlentySub(),
    ],
)
def test_all_properties(plenty: Plenty) -> None:
    def check(properties: Mapping[str, DescriptorProperty[Any]]) -> None:
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
                pytest.fail(f'{prop.system_name} property should not be here')

            seen[name] = True

        assert all(seen.values())

    all_properties = {
        class_name: dict(props)
        for class_name, props in DescriptorProperty[Any].all_properties(
            plenty,
            dict(attr_something=RWProperty),
        )
    }
    properties = all_properties[Plenty]
    check(properties)

    cloned_properties = deepcopy(properties)
    check(cloned_properties)


class PlentyBad:
    @property
    def no_value_type_getter(self):  # type: ignore
        ...

    def _bad_setter(self) -> None: ...

    bad_setter = property(None, _bad_setter, None)  # type: ignore

    only_deleter_property = property(None, None, lambda _: None)

    class _DeleteDescriptor:
        def __delete__(self, obj: PlentyBad) -> None: ...

    only_deleter_descriptor = _DeleteDescriptor()


@pytest.mark.parametrize(
    ('attribute', 'expected_exception'),
    [
        ('no_value_type_getter', ValueError),
        ('bad_setter', ValueError),
        ('only_deleter_descriptor', TypeError),
        # A property will appear of the right type. However, it will lack getter and setter values
        ('only_deleter_property', ValueError),
    ],
)
def test_bad_properties(attribute: str, expected_exception: type[Exception]) -> None:
    plenty_bad = PlentyBad()

    with pytest.raises(expected_exception):
        DescriptorProperty(plenty_bad, attribute)


class WithFeatureDescriptor(FeatureDescriptor):
    pass


def test_feature_descriptor() -> None:
    def check(properties: Mapping[str, DescriptorProperty[Any]]) -> None:
        seen = dict(
            system_name=False,
            display_name=False,
            is_expert=False,
            is_hidden=False,
            is_preferred=False,
            short_description=False,
            attribute_names=False,
        )
        for name, prop in properties.items():
            assert name == prop.system_name

            if name in ('system_name', 'display_name', 'short_description'):
                # assert prop.value_type is str | None
                assert prop.can_read is True
                assert prop.can_write is True
                assert prop.value is None

            elif name in ('is_expert', 'is_hidden', 'is_preferred'):
                assert prop.value_type is bool
                assert prop.can_read is True
                assert prop.can_write is True
                assert isinstance(prop.value, bool)
                assert prop.value is False

            elif name == 'attribute_names':
                # assert prop.value_type is frozenset[str]
                assert prop.can_read is True
                assert prop.can_write is False
                assert prop.value == frozenset()

            else:
                pytest.fail(f'{prop.system_name} property should not be here')

            seen[name] = True

        assert all(seen.values())

    fd = WithFeatureDescriptor()

    all_properties = {
        class_name: dict(props)
        for class_name, props in DescriptorProperty[Any].all_properties(
            fd,
        )
    }
    properties = all_properties[FeatureDescriptor]
    check(properties)

    cloned_properties = deepcopy(properties)
    check(cloned_properties)

    properties['system_name'].value = 'test system_name'
    assert fd.system_name == 'test system_name'

    properties['display_name'].value = 'test display_name'
    assert fd.display_name == 'test display_name'

    properties['is_expert'].value = True
    assert fd.is_expert is True

    properties['is_hidden'].value = True
    assert fd.is_hidden is True

    properties['is_preferred'].value = True
    assert fd.is_preferred is True

    properties['short_description'].value = 'test short_description'
    assert fd.short_description == 'test short_description'

# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from copy import copy, deepcopy
from typing import Any, Generator, MutableMapping, Optional, Sequence, TypeVar, Union, cast
from weakref import ref

# Third-party imports
import pytest
from typing_extensions import TypeAlias

# Local imports
from openide.nodes.properties import FeatureDescriptor


FD = TypeVar('FD', bound=FeatureDescriptor)
ValuesType: 'TypeAlias' = MutableMapping[str, Optional[Any]]
AttrType: 'TypeAlias' = Optional[Union[str, bool, ValuesType]]
AttrDict: 'TypeAlias' = MutableMapping[str, AttrType]


DEFAULT_ATTRS: AttrDict = dict(
    system_name=None,
    display_name=None,
    is_expert=False,
    is_hidden=False,
    is_preferred=False,
    short_description=None,
    values={},
)


def make_attrs(**additional_attrs: AttrType) -> AttrDict:
    attrs = deepcopy(DEFAULT_ATTRS)
    if 'values' in additional_attrs:
        if 'values' not in attrs:
            attrs['values'] = dict()
        cast(ValuesType, attrs['values']).update(
            cast(ValuesType, additional_attrs.pop('values')))
    attrs.update(additional_attrs)

    return attrs


def apply_attributes(fd: FeatureDescriptor, attrs: AttrDict) -> None:
    for attr_name, attr_value in attrs.items():
        if attr_name == 'values':
            for name, value in cast(ValuesType, attr_value).items():
                fd.set_value(name, value)
        else:
            setattr(fd, attr_name, attr_value)


def check_attributes(
    sut: FeatureDescriptor,
    attrs: AttrDict,
    exclude: Optional[Sequence[str]] = None
) -> None:
    if exclude is None:
        exclude = tuple()

    for attr_name, attr_value in attrs.items():
        if attr_name in exclude:
            continue

        if attr_name == 'values':
            attr_value = cast(ValuesType, attr_value)
            for name, value in attr_value.items():
                assert sut.get_value(name) is value, (
                    f'Expected value {name}={value}, but got {sut.get_value(name)} instead'
                )
            assert sut.attribute_names == frozenset(attr_value.keys())
        else:
            assert getattr(sut, attr_name) is attr_value, (
                f'Expected attribute {attr_name}={attr_value}, '
                f'got {getattr(sut, attr_name)} instead'
            )


def test_initialisation() -> None:
    sut = FeatureDescriptor()
    assert sut
    check_attributes(sut, DEFAULT_ATTRS)
    assert sut.get_value('test') is None


@pytest.mark.parametrize(
    'value', [
        None,
        '',
        'test',
    ],
)
def test_system_name(value: Optional[str]) -> None:
    sut = FeatureDescriptor()
    assert sut.system_name is None

    # Check setting and getting back
    sut.system_name = value
    assert sut.system_name == value

    # Check nothing else changed
    check_attributes(sut, make_attrs(
        display_name=sut.system_name,
        short_description=sut.short_description,
    ), exclude=['system_name'])

    # Check reinitialising
    sut.system_name = None
    check_attributes(sut, DEFAULT_ATTRS)


@pytest.mark.parametrize(
    'value, system_name_value, expected', [
        (None, None, None),
        (None, 'sys', 'sys'),
        ('', None, ''),
        ('', 'sys', ''),
        ('test', None, 'test'),
        ('test', 'sys', 'test'),
    ],
)
def test_display_name(
    value: Optional[str],
    system_name_value: Optional[str],
    expected: Optional[str],
) -> None:
    sut = FeatureDescriptor()
    assert sut.display_name is None

    # Check setting and getting back
    sut.system_name = system_name_value
    sut.display_name = value
    assert sut.display_name == expected

    # Check nothing else changed
    check_attributes(sut, make_attrs(
        system_name=system_name_value,
        short_description=sut.display_name,
    ), exclude=['display_name'])

    # Check reinitialising
    sut.display_name = None
    check_attributes(sut, make_attrs(
        system_name=system_name_value,
        display_name=system_name_value,
        short_description=system_name_value,
    ))


@pytest.mark.parametrize(
    'value', [
        False,
        True,
    ],
)
def test_is_expert(value: bool) -> None:
    sut = FeatureDescriptor()
    assert sut.is_expert is False

    # Check setting and getting back
    sut.is_expert = value
    assert sut.is_expert is value

    # Check nothing else changed
    check_attributes(sut, make_attrs(), exclude=['is_expert'])


@pytest.mark.parametrize(
    'value', [
        False,
        True,
    ],
)
def test_is_hidden(value: bool) -> None:
    sut = FeatureDescriptor()
    assert sut.is_hidden is False

    # Check setting and getting back
    sut.is_hidden = value
    assert sut.is_hidden is value

    # Check nothing else changed
    check_attributes(sut, make_attrs(), exclude=['is_hidden'])


@pytest.mark.parametrize(
    'value', [
        False,
        True,
    ],
)
def test_is_preferred(value: bool) -> None:
    sut = FeatureDescriptor()
    assert sut.is_preferred is False

    # Check setting and getting back
    sut.is_preferred = value
    assert sut.is_preferred is value

    # Check nothing else changed
    check_attributes(sut, make_attrs(), exclude=['is_preferred'])


@pytest.mark.parametrize(
    'value, display_name_value, system_name_value, expected', [
        (None, None, None, None),
        (None, None, 'sys', 'sys'),
        (None, 'dis', 'sys', 'dis'),
        ('', None, None, ''),
        ('', None, 'sys', ''),
        ('', 'dis', 'sys', ''),
        ('test', None, None, 'test'),
        ('test', None, 'sys', 'test'),
        ('test', 'dis', 'sys', 'test'),
    ]
)
def test_short_description(
    value: Optional[str],
    display_name_value: Optional[str],
    system_name_value: Optional[str],
    expected: Optional[str],
) -> None:
    sut = FeatureDescriptor()
    assert sut.short_description is None

    # Check setting and getting back
    sut.system_name = system_name_value
    sut.display_name = display_name_value
    sut.short_description = value
    assert sut.short_description == expected

    # Check nothing else changed
    replacing_value = display_name_value if display_name_value is not None else system_name_value
    check_attributes(sut, make_attrs(
        system_name=system_name_value,
        display_name=replacing_value,
    ), exclude=['short_description'])

    # Check reinitialising
    sut.short_description = None
    check_attributes(sut, make_attrs(
        system_name=system_name_value,
        display_name=replacing_value,
        short_description=replacing_value,
    ))


class DummyObject:

    def __str__(self) -> str:
        return 'Dummy!'


object1 = DummyObject()
object1_ref = ref(object1)


@pytest.mark.parametrize(
    'values', [
        {},
        dict(a_str='abcd', an_int=12, a_float=3.14, a_bool=True, a_none=None),
        dict(an_object=object1, a_ref=object1_ref),
    ],
)
def test_values(values: ValuesType) -> None:
    sut = FeatureDescriptor()
    assert sut.attribute_names == frozenset()

    apply_attributes(sut, dict(values=values))
    check_attributes(sut, make_attrs(values=values))


COPY_PARAMETERS = [
    ({}, None, None),
    (dict(system_name='sys'), 'another sys', None),
    (dict(system_name='sys', display_name='dis'), 'another_sys', 'another_dis'),
    (
        dict(system_name='sys', display_name='dis', short_description='descr'),
        'another_sys', 'another_dis'
    ),
    (dict(is_expert=True), None, None),
    (dict(is_hidden=True), None, None),
    (dict(is_preferred=True), None, None),
    (dict(values={}), None, None),
    (
        dict(values=dict(a_str='abcd', an_int=12, a_float=3.14, a_bool=True, a_none=None)),
        None, None
    ),
    (dict(values=dict(an_object=object1, a_ref=object1_ref)), None, None),
]


def check_copy(
    initial: FD,
    attributes: AttrDict,
    post_system_name: Optional[str],
    post_display_name: Optional[str],
) -> FD:
    apply_attributes(initial, attributes)
    sut = copy(initial)

    assert sut
    assert sut.system_name == initial.system_name
    initial.system_name = sut.system_name = post_system_name
    assert sut.display_name == initial.display_name
    initial.display_name = sut.display_name = post_display_name
    assert sut.is_expert == initial.is_expert
    assert sut.is_hidden == initial.is_hidden
    assert sut.is_preferred == initial.is_preferred
    assert sut.short_description == initial.short_description
    for name in initial.attribute_names:
        assert sut.get_value(name) is initial.get_value(name)

    return sut


@pytest.mark.parametrize(
    'attributes, post_system_name, post_display_name', COPY_PARAMETERS,
)
def test_copy(
    attributes: AttrDict,
    post_system_name: Optional[str],
    post_display_name: Optional[str],
) -> None:
    initial = FeatureDescriptor()
    check_copy(initial, attributes, post_system_name, post_display_name)


class SubFeatureDescriptorNoInitArg(FeatureDescriptor):

    def __init__(self) -> None:
        super().__init__()
        self.__other_field: Optional[str] = None

    def __copy_super__(self, new: FeatureDescriptor) -> None:
        super().__copy_super__(new)

        if isinstance(new, SubFeatureDescriptorNoInitArg):
            new.other_field = self.other_field

    @property
    def other_field(self) -> Optional[str]:
        return self.__other_field

    @other_field.setter
    def other_field(self, value: Optional[str]) -> None:
        self.__other_field = value

    def __str_add__(self) -> Generator[str, None, None]:
        yield from super().__str_add__()

        attr_str = self.__str_value__('other_field', self.__other_field)
        if attr_str is not None:
            yield attr_str


@pytest.mark.parametrize(
    'attributes, post_system_name, post_display_name', COPY_PARAMETERS + [
        (dict(other_field='test'), None, None),
    ],
)
def test_copy_sub_no_init_arg(
    attributes: AttrDict,
    post_system_name: Optional[str],
    post_display_name: Optional[str],
) -> None:
    initial = SubFeatureDescriptorNoInitArg()
    sut = check_copy(initial, attributes, post_system_name, post_display_name)
    assert sut.other_field == initial.other_field


class SubFeatureDescriptorWithInitArg(FeatureDescriptor):

    def __init__(self, other_field: Optional[str]) -> None:
        super().__init__()
        self.__other_field: Optional[str] = other_field

    def __copy__(self) -> SubFeatureDescriptorWithInitArg:
        new = type(self)(self.other_field)
        self.__copy_super__(new)
        return new

    @property
    def other_field(self) -> Optional[str]:
        return self.__other_field


@pytest.mark.parametrize(
    'attributes, post_system_name, post_display_name', COPY_PARAMETERS + [
        (dict(other_field='test'), None, None),
    ],
)
def test_copy_sub_with_init_arg(
    attributes: AttrDict,
    post_system_name: Optional[str],
    post_display_name: Optional[str],
) -> None:
    attributes = dict(attributes)
    other_field = cast(Optional[str], attributes.pop('other_field', 'default'))
    initial = SubFeatureDescriptorWithInitArg(other_field)
    sut = check_copy(initial, attributes, post_system_name, post_display_name)
    assert sut.other_field == initial.other_field


class SupFeatureDescriptorMixins:

    def __init__(self) -> None:
        self.__other_field: Optional[str] = None

    def __copy_super__(self, new: FeatureDescriptor) -> None:
        if hasattr(super(), '__copy_super__'):
            super().__copy_super__(new)  # type: ignore

        if isinstance(new, SupFeatureDescriptorMixins):
            new.other_field = self.other_field

    @property
    def other_field(self) -> Optional[str]:
        return self.__other_field

    @other_field.setter
    def other_field(self, value: Optional[str]) -> None:
        self.__other_field = value


class SubFeatureDescriptorWithSupMixins(FeatureDescriptor, SupFeatureDescriptorMixins):
    ...


@pytest.mark.parametrize(
    'attributes, post_system_name, post_display_name', COPY_PARAMETERS + [
        (dict(other_field='test'), None, None),
    ],
)
def test_copy_sub_with_sup_mixins(
    attributes: AttrDict,
    post_system_name: Optional[str],
    post_display_name: Optional[str],
) -> None:
    initial = SubFeatureDescriptorWithSupMixins()
    sut = check_copy(initial, attributes, post_system_name, post_display_name)
    assert sut.other_field == initial.other_field


MERGE_PARAMETERS = [
    # Defaults
    ({}, {}, {}),
    # system_name
    (dict(system_name='sys1'), dict(), dict(system_name=None)),
    (dict(system_name='sys1'), dict(system_name='sys2'), dict(system_name='sys2')),
    # display_name
    (
        dict(system_name='sys1'),
        dict(system_name='sys2'),
        dict(system_name='sys2', display_name='sys2'),
    ),
    (
        dict(display_name='dis1'),
        dict(system_name='sys2'),
        dict(system_name='sys2', display_name='dis1'),
    ),
    (dict(display_name='dis1'), dict(display_name='dis2'), dict(display_name='dis2')),
    # is_expert
    (dict(is_expert=False), dict(is_expert=False), dict(is_expert=False)),
    (dict(is_expert=True), dict(is_expert=False), dict(is_expert=True)),
    (dict(is_expert=False), dict(is_expert=True), dict(is_expert=True)),
    (dict(is_expert=True), dict(is_expert=True), dict(is_expert=True)),
    # is_hidden
    (dict(is_hidden=False), dict(is_hidden=False), dict(is_hidden=False)),
    (dict(is_hidden=True), dict(is_hidden=False), dict(is_hidden=True)),
    (dict(is_hidden=False), dict(is_hidden=True), dict(is_hidden=True)),
    (dict(is_hidden=True), dict(is_hidden=True), dict(is_hidden=True)),
    # is_preferred
    (dict(is_preferred=False), dict(is_preferred=False), dict(is_preferred=False)),
    (dict(is_preferred=True), dict(is_preferred=False), dict(is_preferred=True)),
    (dict(is_preferred=False), dict(is_preferred=True), dict(is_preferred=True)),
    (dict(is_preferred=True), dict(is_preferred=True), dict(is_preferred=True)),
    # short_description
    (
        dict(system_name='sys1', display_name='dis1'),
        dict(system_name='sys2', display_name='dis2'),
        dict(system_name='sys2', display_name='dis2', short_description='dis2'),
    ),
    (
        dict(system_name='sys1', display_name='dis1', short_description='descr1'),
        dict(system_name='sys2', display_name='dis2'),
        dict(system_name='sys2', display_name='dis2', short_description='descr1'),
    ),
    (
        dict(system_name='sys1', display_name='dis1', short_description='descr1'),
        dict(system_name='sys2', display_name='dis2', short_description='descr2'),
        dict(system_name='sys2', display_name='dis2', short_description='descr2'),
    ),
    # Values
    (
        dict(values=dict(from1=True, common=12)),
        dict(values=dict(from2=True, common=45)),
        dict(values=dict(from1=True, from2=True, common=45)),
    )
]


@pytest.mark.parametrize(
    'first_attrs, second_attrs, expected', MERGE_PARAMETERS
)
def test_merge(
    first_attrs: AttrDict,
    second_attrs: AttrDict,
    expected: AttrDict,
) -> None:
    first = FeatureDescriptor()
    apply_attributes(first, first_attrs)
    second = FeatureDescriptor()
    apply_attributes(second, second_attrs)

    sut = FeatureDescriptor.merge(first, second)
    assert sut
    if 'display_name' not in expected:
        expected['display_name'] = expected.get('system_name', None)
    if 'short_description' not in expected:
        expected['short_description'] = expected.get(
            'display_name', expected.get('system_name', None))
    check_attributes(sut, make_attrs(**expected))


@pytest.mark.parametrize(
    'first_attrs, second_attrs, expected', MERGE_PARAMETERS + [
        (dict(other_field='other1'), dict(other_field=None), dict(other_field=None)),
        (dict(other_field='other1'), dict(other_field='other2'), dict(other_field='other2')),
    ]
)
def test_merge_sub_no_init(
    first_attrs: AttrDict,
    second_attrs: AttrDict,
    expected: AttrDict,
) -> None:
    first = SubFeatureDescriptorNoInitArg()
    apply_attributes(first, first_attrs)
    second = SubFeatureDescriptorNoInitArg()
    apply_attributes(second, second_attrs)

    sut = SubFeatureDescriptorNoInitArg.merge(first, second)
    assert sut
    if 'display_name' not in expected:
        expected['display_name'] = expected.get('system_name', None)
    if 'short_description' not in expected:
        expected['short_description'] = expected.get(
            'display_name', expected.get('system_name', None))
    check_attributes(sut, make_attrs(**expected))


@pytest.mark.parametrize(
    'first_attrs, second_attrs, expected', MERGE_PARAMETERS + [
        (dict(other_field='other1'), dict(other_field=None), dict(other_field=None)),
        (dict(other_field='other1'), dict(other_field='other2'), dict(other_field='other2')),
    ]
)
def test_merge_sub_with_init(
    first_attrs: AttrDict,
    second_attrs: AttrDict,
    expected: AttrDict,
) -> None:
    first = SubFeatureDescriptorWithInitArg(
        cast(Optional[str], first_attrs.pop('other_field', None)))
    apply_attributes(first, first_attrs)
    second = SubFeatureDescriptorWithInitArg(
        cast(Optional[str], second_attrs.pop('other_field', None)))
    apply_attributes(second, second_attrs)

    sut = SubFeatureDescriptorWithInitArg.merge(first, second)
    assert sut
    if 'display_name' not in expected:
        expected['display_name'] = expected.get('system_name', None)
    if 'short_description' not in expected:
        expected['short_description'] = expected.get(
            'display_name', expected.get('system_name', None))
    check_attributes(sut, make_attrs(**expected))


STR_PARAMETERS = [
    ({}, '<<CLASS_NAME>>(system_name=None)'),
    (dict(system_name='sys'), '<<CLASS_NAME>>(system_name=sys)'),
    (dict(display_name='dis'), '<<CLASS_NAME>>(system_name=None, display_name=dis)'),
    (dict(is_expert=True), '<<CLASS_NAME>>(system_name=None, is_expert)'),
    (dict(is_hidden=True), '<<CLASS_NAME>>(system_name=None, is_hidden)'),
    (dict(is_preferred=True), '<<CLASS_NAME>>(system_name=None, is_preferred)'),
    (
        dict(short_description='descr'),
        '<<CLASS_NAME>>(system_name=None, short_description=descr)',
    ),
    (
        dict(values=dict(a_str='abcd', an_int=12, a_float=3.14,
                         a_bool=True, another_bool=False, a_none=None)),
        '<<CLASS_NAME>>(system_name=None, values={a_str=abcd, an_int=12, a_float=3.14, '
        'a_bool=True, another_bool=False, a_none=None})'
    ),
    (
        dict(values=dict(an_object=object1, a_ref=object1_ref)),
        '<<CLASS_NAME>>(system_name=None, values={an_object=Dummy!, a_ref=Dummy!})'
    )
]


@pytest.mark.parametrize(
    'attributes, expected', STR_PARAMETERS
)
def test_str(
    attributes: AttrDict,
    expected: str
) -> None:
    sut = FeatureDescriptor()
    apply_attributes(sut, attributes)

    assert str(sut) == expected.replace('<<CLASS_NAME>>', type(sut).__name__)


@pytest.mark.parametrize(
    'attributes, expected', STR_PARAMETERS + [
        (dict(other_field='other'), '<<CLASS_NAME>>(system_name=None, other_field=other)'),
    ]
)
def test_str_sub(
    attributes: AttrDict,
    expected: str
) -> None:
    sut = SubFeatureDescriptorNoInitArg()
    apply_attributes(sut, attributes)

    assert str(sut) == expected.replace('<<CLASS_NAME>>', type(sut).__name__)

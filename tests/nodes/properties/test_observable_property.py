# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore

from __future__ import annotations

# System imports
from copy import copy
from typing import Any, Literal

# Third-party imports
from listeners import Listeners, PropertyListener, observable_property

# Local imports
from openide.nodes import DescriptorProperty


class RWObservableProperty:
    def __init__(self) -> None:
        super().__init__()

        self.__attr = 0

    @observable_property
    def attr(self) -> int:
        return self.__attr

    @attr.setter
    def attr(self, value: int) -> None:
        self.__attr = value

    attr_listeners = attr.listeners_property()


def test_read_write() -> None:
    called_on_object: dict[str, Any] = dict(n_called=0)
    called_on_property: dict[str, Any] = dict(n_called=0)

    def callback_on_object(
        instance: RWObservableProperty,
        attr_name: str,
        old_value: int | None,
        new_value: int,
    ) -> None:
        nonlocal called_on_object
        print(f'callback on object: {instance = } {attr_name = } {old_value = } {new_value = }')
        n_called = called_on_object['n_called']
        called_on_object |= dict(
            n_called=n_called + 1,
            instance=instance,
            attr_name=attr_name,
            old_value=old_value,
            new_value=new_value,
        )

    def callback_on_property(
        instance: DescriptorProperty[int],
        attr_name: str,
        old_value: int | None,
        new_value: int,
    ) -> None:
        nonlocal called_on_property
        print(f'callback on property: {instance = } {attr_name = } {old_value = } {new_value = }')
        n_called = called_on_property['n_called']
        called_on_property |= dict(
            n_called=n_called + 1,
            instance=instance,
            attr_name=attr_name,
            old_value=old_value,
            new_value=new_value,
        )

    def check(
        prop: DescriptorProperty[int],
        init_value: int,
        set_value: int,
        set_on: Literal['object', 'property'],
        n_called_prop: int = 1,
    ) -> None:
        assert prop.value_type is int
        assert prop.can_read is True
        assert prop.can_write is True

        assert prop.value == init_value
        assert rw.attr == init_value
        assert called_on_object == dict(n_called=0)
        assert called_on_property == dict(n_called=0)

        if set_on == 'object':
            rw.attr = set_value
        else:
            prop.value = set_value

        assert prop.value == set_value
        assert rw.attr == set_value
        assert called_on_object
        assert called_on_object == dict(
            n_called=1,
            instance=rw,
            attr_name='attr',
            old_value=init_value,
            new_value=set_value,
        )
        assert called_on_property
        assert called_on_property == dict(
            n_called=n_called_prop,
            instance=prop,
            attr_name='attr',
            old_value=init_value,
            new_value=set_value,
        )

        called_on_object.clear()
        called_on_object['n_called'] = 0
        called_on_property.clear()
        called_on_property['n_called'] = 0
        print()

    rw = RWObservableProperty()
    rw.attr_listeners += callback_on_object

    prop = DescriptorProperty(rw, 'attr', int)
    prop.display_name = 'original'
    prop.listeners += callback_on_property
    check(prop, 0, 12, 'object')
    check(prop, 12, 24, 'property')

    cloned_prop = copy(prop)
    cloned_prop.display_name = 'cloned'
    cloned_prop.listeners += callback_on_property
    check(cloned_prop, 24, 36, 'object')
    check(
        cloned_prop,
        36,
        48,
        'property',
        n_called_prop=2,  # Because it roundtrips through the object listeners
    )
    check(prop, 48, 60, 'object')
    check(prop, 60, 72, 'property')  # Not 2 because cloned_prop listener is later in the list

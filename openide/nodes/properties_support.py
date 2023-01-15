# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
import typing
from abc import abstractmethod
from collections.abc import Generator
from functools import partial
from typing import (
    TYPE_CHECKING, Any, Callable, Generic, Mapping, Optional, Protocol,
    Type, TypeVar, Union, cast, runtime_checkable,
)

# Third-party imports

# Local imports
from openide.nodes.properties import Property, IndexedProperty, VT, ET


if TYPE_CHECKING:
    from typing_extensions import TypeAlias  # pragma: no cover


class PropertySupport(Property, Generic[VT]):

    def __init__(
        self,
        system_name: str,
        value_type: Type[VT],
        can_read: bool,
        can_write: bool,
        display_name: Optional[str] = None,
        short_description: Optional[str] = None,
    ) -> None:
        if (not can_read) and (not can_write):
            raise ValueError('A property should be at least either readable or writable')

        super().__init__(value_type)

        self.system_name = system_name
        self.display_name = display_name
        self.short_description = short_description
        self.__can_read = can_read
        self.__can_write = can_write

    def __copy__(self) -> PropertySupport:
        new = type(self)(
            cast(str, self.system_name),
            self.value_type,
            self.can_read,
            self.can_write,
            self.display_name,
            self.short_description,
        )
        self.__copy_super__(new)
        return new

    @property
    def can_read(self) -> bool:
        return self.__can_read
    can_read.__doc__ = Property.can_read.__doc__

    @property
    def can_write(self) -> bool:
        return self.__can_write
    can_write.__doc__ = Property.can_write.__doc__


class ReadWriteProperty(PropertySupport[VT]):

    def __init__(
        self,
        system_name: str,
        value_type: Type[VT],
        display_name: Optional[str] = None,
        short_description: Optional[str] = None,
    ) -> None:
        super().__init__(
            system_name, value_type,
            True, True,
            display_name, short_description,
        )


class ReadOnlyProperty(PropertySupport[VT]):

    def __init__(
        self,
        system_name: str,
        value_type: Type[VT],
        display_name: Optional[str] = None,
        short_description: Optional[str] = None,
    ) -> None:
        super().__init__(
            system_name, value_type,
            True, False,
            display_name, short_description,
        )

    @property
    @abstractmethod
    def value(self) -> VT:
        '''The value of this property.'''
        raise NotImplementedError()  # pragma: no cover

    @value.setter
    def value(self, value: VT) -> None:
        raise AttributeError('Property is not writable')


class WriteOnlyProperty(PropertySupport[VT]):

    def __init__(
        self,
        system_name: str,
        value_type: Type[VT],
        display_name: Optional[str] = None,
        short_description: Optional[str] = None,
    ) -> None:
        super().__init__(
            system_name, value_type,
            False, True,
            display_name, short_description,
        )

    @property
    def value(self) -> VT:
        '''The value of this property.'''
        raise AttributeError('Property is not readable')

    @value.setter
    @abstractmethod
    def value(self, value: VT) -> None:
        raise NotImplementedError()  # pragma: no cover


# TODO: NodeNameProperty

GetterProtocol: 'TypeAlias' = Callable[[], VT]
SetterProtocol: 'TypeAlias' = Callable[[VT], None]
DVT = TypeVar('DVT')


class GetterSetterProperty(Property[VT]):

    class _ValueDescriptor(Generic[DVT]):

        def __get__(
            self,
            obj: Optional[GetterSetterProperty],
            objtype: Optional[Type[GetterSetterProperty]] = None
        ) -> DVT:
            if obj is None:
                raise AttributeError('Can only get on an instance')

            if (get := obj._get) is None:
                raise AttributeError('Property is not readable')

            return get()

        def __set__(self, obj: GetterSetterProperty, value: DVT) -> None:
            if (set := obj._set) is None:
                raise AttributeError('Property is not writable')

            set(value)

    def __init__(
        self,
        getter: Optional[GetterProtocol[VT]] = None,
        setter: Optional[SetterProtocol[VT]] = None,
        value_type: Optional[Type[VT]] = None,
        **kwargs: Any,
    ) -> None:
        self._get = getter
        self._set = setter

        if not self._get and not self._set:
            raise ValueError('Need to specify at least one of getter or setter')

        if (self._get is not None) and (not callable(self._get)):
            raise TypeError('Provided getter is not callable')

        if (self._set is not None) and (not callable(self._set)):
            raise TypeError('Provided setter is not callable')

        if value_type is None:
            value_type = self._guess_getset_type(self._get, self._set)

        if value_type is None:
            raise ValueError('Value type is not provided, and it was not possible to guess it')

        super().__init__(value_type=value_type, **kwargs)

    @staticmethod
    def _guess_getset_type(
        getter: Optional[Callable],
        setter: Optional[Callable]
    ) -> Optional[Type]:
        def guess_get_type(getter: Optional[Callable]) -> Optional[Type]:
            if getter is None:
                return None
            type_hints = typing.get_type_hints(getter)
            if 'return' not in type_hints:
                return None
            return type_hints['return']

        def guess_set_type(setter: Optional[Callable]) -> Optional[Type]:
            if setter is None:
                return None
            type_hints = typing.get_type_hints(setter)
            if 'return' in type_hints:
                del type_hints['return']
            if not type_hints:
                return None
            return next(reversed(type_hints.values()))

        value_type = guess_get_type(getter)
        if value_type is None:
            value_type = guess_set_type(setter)

        return value_type

    value: VT = _ValueDescriptor[VT]()  # type: ignore

    @property
    def can_read(self) -> bool:
        return self._get is not None
    can_read.__doc__ = Property.can_read.__doc__

    @property
    def can_write(self) -> bool:
        return self._set is not None
    can_write.__doc__ = Property.can_write.__doc__


T_contra = TypeVar('T_contra', contravariant=True)
GV_co = TypeVar('GV_co', covariant=True)
SV_contra = TypeVar('SV_contra', contravariant=True)


@runtime_checkable
class GettableDescriptorProtocol(Protocol[T_contra, GV_co]):
    def __get__(
        self,
        obj: Optional[T_contra],
        objtype: Optional[Type[T_contra]] = None
    ) -> GV_co:
        ...  # pragma: no cover


@runtime_checkable
class SettableDescriptorProtocol(Protocol[T_contra, SV_contra]):
    def __set__(self, obj: T_contra, value: SV_contra) -> None:
        ...  # pragma: no cover


Descriptor: 'TypeAlias' = Union[GettableDescriptorProtocol, SettableDescriptorProtocol]


class _ClassWithSlot:

    __slots__ = ('a_slot',)


_function = type(Property.__init__)
# getset_descriptor is usually used for special attributes
# like __dict__ or __weakref__, which we probably don't want to include.
_getset_descriptor = type(Property.__weakref__)  # type: ignore
_member_descriptor = type(_ClassWithSlot.a_slot)  # type: ignore
_filter_types = (
    _function, classmethod, staticmethod, _getset_descriptor, _member_descriptor,
)


class DescriptorProperty(GetterSetterProperty[VT]):

    def __init__(
        self, instance: Any,
        descriptor: Union[Descriptor, str],
        value_type: Optional[Type[VT]] = None,
    ) -> None:
        descriptor_name = None
        if isinstance(descriptor, str):
            descriptor_name = descriptor
            try:
                descriptor = vars(type(instance))[descriptor_name]
            except KeyError:
                raise ValueError(f'Unknown attribute {descriptor_name}')

        if not isinstance(descriptor, (GettableDescriptorProtocol, SettableDescriptorProtocol)):
            if descriptor_name is None:
                raise TypeError(
                    'Provided descriptor is not a valid one (missing __get__ or __set__)')
            else:
                raise TypeError(
                    f'Attribute {descriptor_name} on class {type(instance).__name__} '
                    'is not a valid descriptor (missing __get__ or __set__)'
                )

        if isinstance(descriptor, property):
            getter = descriptor.fget
            setter = descriptor.fset
        else:
            getter = getattr(descriptor, '__get__', None)
            setter = getattr(descriptor, '__set__', None)

        if value_type is None:
            value_type = self._guess_getset_type(getter, setter)

        if value_type is None:
            raise ValueError('Value type is not provided, and it was not possible to guess it')

        if getter is not None:
            getter = partial(getter, instance)
        if setter is not None:
            setter = partial(setter, instance)

        super().__init__(getter, setter, value_type)

        if descriptor_name is not None:
            self.system_name = descriptor_name

    @classmethod
    def all_properties(
        cls,
        instance: Any,
        types: Optional[Mapping[str, Type]] = None
    ) -> Generator[tuple[str, DescriptorProperty], None, None]:
        if types is None:
            types = {}

        for name, attr in vars(type(instance)).items():
            if isinstance(attr, _filter_types):
                continue
            if not isinstance(attr, (GettableDescriptorProtocol, SettableDescriptorProtocol)):
                continue

            value_type = types.get(name, None)
            prop = cls(instance, attr, value_type)
            prop.system_name = name
            yield name, prop

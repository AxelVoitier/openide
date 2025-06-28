# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
import typing
from abc import abstractmethod
from collections.abc import Sequence
from functools import partial
from itertools import islice
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    Protocol,
    TypeVar,
    Union,
    cast,
    overload,
    runtime_checkable,
)

# Third-party imports
# Local imports
from openide.nodes._like_netbeans.properties import IT, KT, VT, IndexedProperty, Property

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator, Mapping
    from typing import Any, TypeAlias


class PropertySupport(Property, Generic[VT]):
    def __init__(
        self,
        system_name: str,
        value_type: type[VT],
        display_name: str | None = None,
        short_description: str | None = None,
        *,
        can_read: bool,
        can_write: bool,
    ) -> None:
        if (not can_read) and (not can_write):
            msg = 'A property should be at least either readable or writable'
            raise ValueError(msg)

        super().__init__(value_type)

        self.system_name = system_name
        self.display_name = display_name
        self.short_description = short_description
        self.__can_read = can_read
        self.__can_write = can_write

    def __copy__(self) -> PropertySupport:
        new = type(self)(
            cast('str', self.system_name),
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
        value_type: type[VT],
        display_name: str | None = None,
        short_description: str | None = None,
    ) -> None:
        super().__init__(
            system_name,
            value_type,
            display_name,
            short_description,
            can_read=True,
            can_write=True,
        )


class ReadOnlyProperty(PropertySupport[VT]):
    def __init__(
        self,
        system_name: str,
        value_type: type[VT],
        display_name: str | None = None,
        short_description: str | None = None,
    ) -> None:
        super().__init__(
            system_name,
            value_type,
            display_name,
            short_description,
            can_read=True,
            can_write=False,
        )

    @property
    @abstractmethod
    def value(self) -> VT:
        """The value of this property."""
        raise NotImplementedError  # pragma: no cover

    @value.setter
    def value(self, value: VT) -> None:
        msg = 'Property is not writable'
        raise AttributeError(msg)


class WriteOnlyProperty(PropertySupport[VT]):
    def __init__(
        self,
        system_name: str,
        value_type: type[VT],
        display_name: str | None = None,
        short_description: str | None = None,
    ) -> None:
        super().__init__(
            system_name,
            value_type,
            display_name,
            short_description,
            can_read=False,
            can_write=True,
        )

    @property
    def value(self) -> VT:
        """The value of this property."""
        msg = 'Property is not readable'
        raise AttributeError(msg)

    @value.setter
    @abstractmethod
    def value(self, value: VT) -> None:
        raise NotImplementedError  # pragma: no cover


# TODO: NodeNameProperty

GetterProtocol: TypeAlias = Callable[[], VT]
SetterProtocol: TypeAlias = Callable[[VT], None]
DVT = TypeVar('DVT')


def _get_return_type(func: Callable | None) -> type | None:
    if func is None:
        return None
    type_hints = typing.get_type_hints(func)
    if 'return' not in type_hints:
        return None
    return type_hints['return']


def _get_last_arg_type(func: Callable | None, n: int = 0) -> type | None:
    if func is None:
        return None
    type_hints = typing.get_type_hints(func)
    if 'return' in type_hints:
        del type_hints['return']
    if not type_hints:
        return None
    return next(islice(reversed(type_hints.values()), n, n + 1))


class GetterSetterProperty(Property[VT]):
    class _ValueDescriptor(Generic[DVT]):
        def __get__(
            self,
            obj: GetterSetterProperty | None,
            objtype: type[GetterSetterProperty] | None = None,
        ) -> DVT:
            if obj is None:
                msg = 'Can only get on an instance'
                raise AttributeError(msg)

            if (get := obj._get) is None:
                msg = 'Property is not readable'
                raise AttributeError(msg)

            return get()

        def __set__(self, obj: GetterSetterProperty, value: DVT) -> None:
            if (set := obj._set) is None:
                msg = 'Property is not writable'
                raise AttributeError(msg)

            set(value)

    @staticmethod
    def _guess_getset_type(getter: Callable | None, setter: Callable | None) -> type | None:
        value_type = _get_return_type(getter)
        if value_type is None:
            value_type = _get_last_arg_type(setter)
        return value_type

    def __init__(
        self,
        value_getter: GetterProtocol[VT] | None = None,
        value_setter: SetterProtocol[VT] | None = None,
        value_type: type[VT] | None = None,
        **kwargs: Any,
    ) -> None:
        if not value_getter and not value_setter:
            msg = 'Need to specify at least one of getter or setter'
            raise ValueError(msg)

        if (value_getter is not None) and (not callable(value_getter)):
            msg = 'Provided getter is not callable'
            raise TypeError(msg)

        if (value_setter is not None) and (not callable(value_setter)):
            msg = 'Provided setter is not callable'
            raise TypeError(msg)

        if value_type is None:
            value_type = self._guess_getset_type(value_getter, value_setter)

        if value_type is None:
            msg = 'Value type is not provided, and it was not possible to guess it'
            raise ValueError(msg)

        self._get = value_getter
        self._set = value_setter

        super().__init__(value_type=value_type, **kwargs)

    def __copy_init_kwargs__(self) -> dict[str, Any]:
        kwargs = super().__copy_init_kwargs__()
        kwargs.update(
            dict(
                value_getter=self._get,
                value_setter=self._set,
            ),
        )
        return kwargs

    value: VT = _ValueDescriptor[VT]()  # pyright: ignore[reportAssignmentType,reportIncompatibleMethodOverride]

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
        obj: T_contra | None,
        objtype: type[T_contra] | None = None,
    ) -> GV_co: ...  # pragma: no cover


@runtime_checkable
class SettableDescriptorProtocol(Protocol[T_contra, SV_contra]):
    def __set__(self, obj: T_contra, value: SV_contra) -> None: ...  # pragma: no cover


Descriptor: TypeAlias = Union[GettableDescriptorProtocol, SettableDescriptorProtocol]


class _ClassWithSlot:
    __slots__ = ('a_slot',)


_function = type(Property.__init__)
# getset_descriptor is usually used for special attributes
# like __dict__ or __weakref__, which we probably don't want to include.
_getset_descriptor = type(Property.__weakref__)  # pyright: ignore[reportAttributeAccessIssue]
_member_descriptor = type(_ClassWithSlot.a_slot)
_filter_types = (
    _function,
    classmethod,
    staticmethod,
    _getset_descriptor,
    _member_descriptor,
)


class _DescriptorPropertyMixins(GetterSetterProperty[VT]):
    def __init__(
        self,
        *,
        instance: Any,  # noqa: ANN401
        descriptor: Descriptor | str,
        value_type: type[VT] | None = None,
        **kwargs: Any,
    ) -> None:
        descriptor_name = None
        if isinstance(descriptor, str):
            descriptor_name = descriptor
            try:
                descriptor = vars(type(instance))[descriptor_name]
            except KeyError as ex:
                msg = f'Unknown attribute {descriptor_name}'
                raise ValueError(msg) from ex

        if not isinstance(descriptor, (GettableDescriptorProtocol, SettableDescriptorProtocol)):
            if descriptor_name is None:
                msg = 'Provided descriptor is not a valid one (missing __get__ or __set__)'
                raise TypeError(msg)

            msg = (
                f'Attribute {descriptor_name} on class {type(instance).__name__} '
                'is not a valid descriptor (missing __get__ or __set__)'
            )
            raise TypeError(msg)

        if isinstance(descriptor, property):
            getter = descriptor.fget
            setter = descriptor.fset
        else:
            getter = getattr(descriptor, '__get__', None)
            setter = getattr(descriptor, '__set__', None)

        if value_type is None:
            value_type = self._guess_getset_type(getter, setter)

        if value_type is None:
            msg = 'Value type is not provided, and it was not possible to guess it'
            raise ValueError(msg)

        if getter is not None:
            getter = partial(getter, instance)
        if setter is not None:
            setter = partial(setter, instance)

        super().__init__(value_getter=getter, value_setter=setter, value_type=value_type, **kwargs)

        if descriptor_name is not None:
            self.system_name = descriptor_name

        # For copy
        self._instance = instance
        self._descriptor = descriptor

    def __copy_init_kwargs__(self) -> dict[str, Any]:
        kwargs = super().__copy_init_kwargs__()
        kwargs.pop('value_getter', None)
        kwargs.pop('value_setter', None)
        kwargs.update(
            dict(
                instance=self._instance,
                descriptor=self._descriptor,
            ),
        )
        return kwargs


class DescriptorProperty(_DescriptorPropertyMixins[VT]):
    def __init__(
        self,
        instance: Any,  # noqa: ANN401
        descriptor: Descriptor | str,
        value_type: type[VT] | None = None,
    ) -> None:
        super().__init__(
            instance=instance,
            descriptor=descriptor,
            value_type=value_type,
        )

    @classmethod
    def all_properties(
        cls,
        instance: Any,  # noqa: ANN401
        types: Mapping[str, type] | None = None,
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


IndexedGetterProtocol: TypeAlias = Callable[[KT], IT]
IndexedSetterProtocol: TypeAlias = Callable[[KT, IT], None]


class _IndexedGetterSetterPropertyMixins(IndexedProperty[VT, KT, IT]):
    @staticmethod
    def _guess_index_type(getter: Callable | None, setter: Callable | None) -> type | None:
        index_type = _get_last_arg_type(getter)
        if index_type is None:
            index_type = _get_last_arg_type(setter, n=1)

        return index_type

    def __init__(
        self,
        indexed_getter: IndexedGetterProtocol[KT, IT] | None = None,
        indexed_setter: IndexedSetterProtocol[KT, IT] | None = None,
        index_type: type[KT] | None = None,
        item_type: type[IT] | None = None,
        **kwargs: Any,
    ) -> None:
        if not indexed_getter and not indexed_setter:
            msg = 'Need to specify at least one of indexed getter or setter'
            raise ValueError(msg)

        if (indexed_getter is not None) and (not callable(indexed_getter)):
            msg = 'Provided indexed getter is not callable'
            raise TypeError(msg)

        if (indexed_setter is not None) and (not callable(indexed_setter)):
            msg = 'Provided indexed setter is not callable'
            raise TypeError(msg)

        if index_type is None:
            index_type = self._guess_index_type(indexed_getter, indexed_setter)

        if index_type is None:
            msg = 'Index type is not provided, and it was not possible to guess it'
            raise ValueError(msg)

        if item_type is None:
            item_type = GetterSetterProperty._guess_getset_type(indexed_getter, indexed_setter)

        if item_type is None:
            msg = 'Item type is not provided, and it was not possible to guess it'
            raise ValueError(msg)

        self._indexed_getter = indexed_getter
        self._indexed_setter = indexed_setter

        super().__init__(
            index_type=index_type,
            item_type=item_type,
            **kwargs,
        )

    def __copy_init_kwargs__(self) -> dict[str, Any]:
        kwargs = super().__copy_init_kwargs__()
        kwargs.update(
            dict(
                indexed_getter=self._indexed_getter,
                indexed_setter=self._indexed_setter,
            ),
        )
        return kwargs

    def __getitem__(self, index: KT) -> IT:
        if self._indexed_getter is None:
            msg = 'Property is not readable by index'
            raise AttributeError(msg)

        return self._indexed_getter(index)

    __getitem__.__doc__ = IndexedProperty.__getitem__.__doc__

    def __setitem__(self, index: KT, value: IT) -> None:
        if self._indexed_setter is None:
            msg = 'Property is not writable by index'
            raise AttributeError(msg)

        return self._indexed_setter(index, value)

    __setitem__.__doc__ = IndexedProperty.__setitem__.__doc__

    @property
    def can_indexed_read(self) -> bool:
        return self._indexed_getter is not None

    can_indexed_read.__doc__ = IndexedProperty.can_indexed_read.__doc__

    @property
    def can_indexed_write(self) -> bool:
        return self._indexed_setter is not None

    can_indexed_write.__doc__ = IndexedProperty.can_indexed_write.__doc__


class IndexedGetterSetterProperty(
    _IndexedGetterSetterPropertyMixins[VT, KT, IT],
    GetterSetterProperty[VT],
):
    def __init__(
        self,
        indexed_getter: IndexedGetterProtocol[KT, IT] | None = None,
        indexed_setter: IndexedSetterProtocol[KT, IT] | None = None,
        index_type: type[KT] | None = None,
        item_type: type[IT] | None = None,
        value_getter: GetterProtocol[VT] | None = None,
        value_setter: SetterProtocol[VT] | None = None,
        value_type: type[VT] | None = None,
    ) -> None:
        super().__init__(
            indexed_getter=indexed_getter,
            indexed_setter=indexed_setter,
            index_type=index_type,
            item_type=item_type,
            value_getter=value_getter,
            value_setter=value_setter,
            value_type=value_type,
        )


class IndexedGetterSetterDescriptorProperty(
    _IndexedGetterSetterPropertyMixins[VT, KT, IT],
    _DescriptorPropertyMixins[VT],
):
    def __init__(
        self,
        *,
        indexed_getter: IndexedGetterProtocol[KT, IT] | None = None,
        indexed_setter: IndexedSetterProtocol[KT, IT] | None = None,
        index_type: type[KT] | None = None,
        item_type: type[IT] | None = None,
        instance: Any,  # noqa: ANN401
        descriptor: Descriptor | str,
        value_type: type[VT] | None = None,
    ) -> None:
        super().__init__(
            indexed_getter=indexed_getter,
            indexed_setter=indexed_setter,
            index_type=index_type,
            item_type=item_type,
            instance=instance,
            descriptor=descriptor,
            value_type=value_type,
        )


class _SequencePropertyMixins(_IndexedGetterSetterPropertyMixins[VT, int, IT], Sequence[IT]):
    def __init__(
        self,
        *,
        sequence: Sequence[IT],
        item_type: type[IT] | None = None,
        **kwargs: Any,
    ) -> None:
        self._sequence = sequence

        # for attr in '__len__ __contains__ __iter__ __reversed__ index count'.split():
        #     setattr(self, attr, getattr(self._sequence, attr))

        super().__init__(
            indexed_getter=self._sequence.__getitem__,
            indexed_setter=None,
            index_type=int,
            item_type=item_type,
            **kwargs,
        )

    def __copy_init_kwargs__(self) -> dict[str, Any]:
        kwargs = super().__copy_init_kwargs__()
        kwargs.update(
            dict(
                sequence=self._sequence,
                item_type=self.item_type,
            ),
        )
        return kwargs

    @overload
    def __getitem__(self, index: int) -> IT: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[IT]: ...

    def __getitem__(self, index: int | slice) -> IT | Sequence[IT]:
        if self._indexed_getter is None:
            msg = 'Property is not readable by index'
            raise AttributeError(msg)

        return self._indexed_getter(index)

    # __getitem__.__doc__ = IndexedProperty.__getitem__.__doc__

    def __len__(self) -> int:
        return self._sequence.__len__()

    def __contains__(self, item: Any) -> bool:  # noqa: ANN401
        return self._sequence.__contains__(item)

    def __iter__(self) -> Iterator[IT]:
        return self._sequence.__iter__()

    def __reversed__(self) -> Iterator[IT]:
        return self._sequence.__reversed__()

    def index(self, item: Any, *args: int) -> int:  # noqa: ANN401
        return self._sequence.index(item, *args)

    def count(self, value: Any) -> int:  # noqa: ANN401
        return self._sequence.count(value)


# TODO: Try to find a fix for the type error, later,
# once we have IndexedNode working to see what is needed
class SequenceGetterSetterProperty(_SequencePropertyMixins[VT, IT], GetterSetterProperty[VT]):
    def __init__(
        self,
        *,
        sequence: Sequence[IT],
        item_type: type[IT] | None = None,
        value_getter: GetterProtocol[VT] | None = None,
        value_setter: SetterProtocol[VT] | None = None,
        value_type: type[VT] | None = None,
    ) -> None:
        super().__init__(
            sequence=sequence,
            item_type=item_type,
            value_getter=value_getter,
            value_setter=value_setter,
            value_type=value_type,
        )


# TODO: Try to find a fix for the type error, later,
# once we have IndexedNode working to see what is needed
class SequenceDescriptorProperty(_SequencePropertyMixins[VT, IT], _DescriptorPropertyMixins[VT]):
    def __init__(
        self,
        *,
        sequence: Sequence[IT],
        item_type: type[IT] | None = None,
        instance: Any,  # noqa: ANN401
        descriptor: Descriptor | str,
        value_type: type[VT] | None = None,
    ) -> None:
        super().__init__(
            sequence=sequence,
            item_type=item_type,
            instance=instance,
            descriptor=descriptor,
            value_type=value_type,
        )

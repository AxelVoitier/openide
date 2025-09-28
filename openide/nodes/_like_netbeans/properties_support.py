# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:words openide netbeans
# spell-checker:ignore objtype getset

from __future__ import annotations

# System imports
import typing
from abc import abstractmethod
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from functools import partial
from itertools import islice
from typing import (
    TYPE_CHECKING,
    Generic,
    Protocol,
    TypeVar,
    cast,
    overload,
    runtime_checkable,
)

# Third-party imports
from listeners import ObservablePropertySupport, observable_property
from typing_extensions import Never, Self, override

# Local imports
from openide.nodes._like_netbeans.properties import (
    IT,
    KT,
    VT,
    IndexedProperty,
    Property,
    PropertyChangeProtocol,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from typing import Any, TypeAlias

    from listeners import Observable


class PropertySupport(Property[VT], Generic[VT]):
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

    @override  # Feature descriptor
    def __copy__(self) -> Self:
        new = type(self)(
            cast('str', self.system_name),
            self.value_type,
            self.display_name,
            self.short_description,
            can_read=self.can_read,
            can_write=self.can_write,
        )
        self.__copy_super__(new)
        return new

    @property
    @override  # Property
    def can_read(self) -> bool:
        return self.__can_read

    can_read.__doc__ = Property.can_read.__doc__

    @property
    @override  # Property
    def can_write(self) -> bool:
        return self.__can_write

    can_write.__doc__ = Property.can_write.__doc__


class ReadWriteProperty(PropertySupport[VT]):
    """A simple read/write property"""

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
    """A simple read-only property"""

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

    # Cannot reimplement a property setter without reimplementing its getter
    @property
    @abstractmethod
    @override  # Property
    def value(self) -> VT:
        """The value of this property."""
        raise NotImplementedError  # pragma: no cover

    @value.setter
    def value(self, value: VT) -> Never:
        msg = 'Property is not writable'
        raise AttributeError(msg)


class WriteOnlyProperty(PropertySupport[VT]):
    """A simple write-only property"""

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
    @override  # Property
    def value(self) -> Never:
        """The value of this property."""
        msg = 'Property is not readable'
        raise AttributeError(msg)

    # If a property getter is reimplemented, its setter needs to be re-done as well
    @value.setter
    @abstractmethod
    def value(self, value: VT) -> None:
        raise NotImplementedError  # pragma: no cover


# TODO: NodeNameProperty

GetterProtocol: TypeAlias = Callable[[], VT]
SetterProtocol: TypeAlias = Callable[[VT], None]
DVT = TypeVar('DVT')


def _get_return_type(func: Callable[..., Any] | None) -> type | None:
    if func is None:
        return None
    type_hints = typing.get_type_hints(func)
    if 'return' not in type_hints:
        return None
    return type_hints['return']


def _get_last_arg_type(func: Callable[..., Any] | None, n: int = 0) -> type | None:
    if func is None:
        return None
    type_hints = typing.get_type_hints(func)
    if 'return' in type_hints:
        del type_hints['return']
    if not type_hints:
        return None
    return next(islice(reversed(type_hints.values()), n, n + 1))


class GetterSetterProperty(Property[VT]):
    class _ValueDescriptor(ObservablePropertySupport['GetterSetterProperty[DVT]', DVT]):
        __slots__ = ('__name__',)

        def __init__(self) -> None:
            super().__init__()
            self.__name__ = 'value'

        def __set_name__(self, owner: type[DVT], name: str) -> None:
            self.__name__ = name

        def __get__(
            self,
            obj: GetterSetterProperty[DVT] | None,
            objtype: type[GetterSetterProperty[DVT]] | None = None,
        ) -> DVT | Self:
            if obj is None:
                return self
                # msg = 'Can only get on an instance'
                # raise AttributeError(msg)

            if (get := obj._get) is None:
                msg = 'Property is not readable'
                raise AttributeError(msg)

            return get()

        def __set__(self, obj: GetterSetterProperty[DVT], new_value: DVT) -> None:
            if (set := obj._set) is None:
                msg = 'Property is not writable'
                raise AttributeError(msg)

            observable = self._get_observable(obj)
            name = obj.system_name or self.__name__
            old_value = get() if (get := obj._get) is not None else None
            obj._firing = True
            try:
                with observable.fire(obj, name, old_value, new_value):
                    set(new_value)
            finally:
                obj._firing = False

    @staticmethod
    def _guess_getset_type(
        getter: Callable[..., Any] | None,
        setter: Callable[..., None] | None,
    ) -> type | None:
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
        self._firing = False

        super().__init__(value_type=value_type, **kwargs)

    @override  # Property
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
    def listeners(self) -> Observable[PropertyChangeProtocol[Self, VT]]:
        return type(self).value._get_observable(self)

    @listeners.setter
    def listeners(self, _: Observable[PropertyChangeProtocol[Self, VT]]) -> None:
        pass

    @property
    @override  # Property
    def can_read(self) -> bool:
        return self._get is not None

    can_read.__doc__ = Property.can_read.__doc__

    def force_no_getter(self) -> None:
        self._get = None

    @property
    @override  # Property
    def can_write(self) -> bool:
        return self._set is not None

    can_write.__doc__ = Property.can_write.__doc__

    def force_no_setter(self) -> None:
        self._set = None


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


class DescriptorProtocol(
    GettableDescriptorProtocol[T_contra, GV_co],
    SettableDescriptorProtocol[T_contra, SV_contra],
    Protocol[T_contra, GV_co, SV_contra],
):
    pass


class _ClassWithSlot:
    __slots__ = ('a_slot',)

    def __init__(self, a_slot: Any) -> None:  # noqa: ANN401
        super().__init__()
        self.a_slot = a_slot


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
        instance: T_contra,
        descriptor: DescriptorProtocol[T_contra, VT, VT] | str,
        value_type: type[VT] | None = None,
        **kwargs: Any,
    ) -> None:
        descriptor_name = None
        if isinstance(descriptor, str):
            descriptor_name = descriptor
            for base in type(instance).__mro__:
                # We manually search across all base classes using vars because a simple getattr
                # Might return an unexpected value in case the descriptor is "non-cooperative"
                # and does not return itself when calling __get__(None, cls).
                if (descriptor := vars(base).get(descriptor_name, None)) is not None:
                    break
            else:
                msg = f"'{type(instance).__name__}' object has no attribute '{descriptor_name}'"
                raise AttributeError(msg)

        if not isinstance(descriptor, (GettableDescriptorProtocol, SettableDescriptorProtocol)):
            if descriptor_name is None:
                msg = (
                    'Provided descriptor is not a valid one (missing __get__ or __set__).'
                    f'{descriptor = }, {type(descriptor) =}'
                )
                raise TypeError(msg)

            msg = (
                f'Attribute {descriptor_name} on class {type(instance).__name__} '
                f'is not a valid descriptor (missing __get__ ({hasattr(descriptor, "__get__")}) or __set__ ({hasattr(descriptor, "__set__")})) {descriptor=} {instance=}'
            )
            raise TypeError(msg)

        getter = getattr(descriptor, '__get__', None)
        setter = getattr(descriptor, '__set__', None)
        if descriptor_name is None:
            descriptor_name = getattr(descriptor, '__name__', None)
        if isinstance(descriptor, property):
            if descriptor.fget is None:
                getter = None
            if descriptor.fset is None:
                setter = None

        if value_type is None:
            guess_type_getter = getter
            guess_type_setter = setter
            if isinstance(descriptor, property):
                guess_type_getter = descriptor.fget
                guess_type_setter = descriptor.fset
            value_type = self._guess_getset_type(guess_type_getter, guess_type_setter)

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

        if isinstance(descriptor, (observable_property, ObservablePropertySupport)):
            descriptor.watch(instance, self.__forward_event)

        # For copy
        self._instance = instance
        self._descriptor = descriptor

    @override  # GetterSetterProperty
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

    @contextmanager
    def __forward_event(
        self,
        owner: Any,  # noqa: ANN401
        attr_name: str,
        old_value: VT | None,
        new_value: VT,
    ) -> Iterator[None]:
        if self._firing:
            yield
            return

        with self.listeners.fire(self, attr_name, old_value, new_value):
            yield


class DescriptorProperty(_DescriptorPropertyMixins[VT]):
    def __init__(
        self,
        instance: T_contra,
        descriptor: DescriptorProtocol[T_contra, VT, VT] | str,
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
        instance: object,
        types: Mapping[str, type] | None = None,
        *,
        skip_errors: bool = True,
        # ) -> Iterator[tuple[str, DescriptorProperty[VT]]]:
    ) -> Iterator[tuple[str, Iterator[tuple[str, DescriptorProperty[VT]]]]]:
        if types is None:
            types = {}

        def iterator_for_class(base: type[Any]) -> Iterator[tuple[str, DescriptorProperty[VT]]]:
            for name, attr in vars(base).items():
                if isinstance(attr, _filter_types):
                    continue
                if not isinstance(attr, (GettableDescriptorProtocol, SettableDescriptorProtocol)):
                    continue
                # We can now assume it's a descriptor
                attr = cast('DescriptorProtocol[Any, VT, VT]', attr)

                value_type = types.get(name, None)
                try:
                    prop = cls(instance, attr, value_type)
                except Exception:
                    if skip_errors:
                        continue
                    raise
                prop.system_name = name
                yield name, prop

        for base in type(instance).__mro__:
            if base is object:
                # Avoid trying to get descriptors like __repr__ (which fails at guessing type)
                continue

            yield base.__name__, iterator_for_class(base)


IndexedGetterProtocol: TypeAlias = Callable[[KT], IT]
IndexedSetterProtocol: TypeAlias = Callable[[KT, IT], None]


class _IndexedGetterSetterPropertyMixins(IndexedProperty[VT, KT, IT]):
    @staticmethod
    def _guess_index_type(
        getter: Callable[..., Any] | None,
        setter: Callable[..., None] | None,
    ) -> type | None:
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

    @override  # IndexedProperty
    def __copy_init_kwargs__(self) -> dict[str, Any]:
        kwargs = super().__copy_init_kwargs__()
        kwargs.update(
            dict(
                indexed_getter=self._indexed_getter,
                indexed_setter=self._indexed_setter,
            ),
        )
        return kwargs

    @override  # IndexedProperty
    def __getitem__(self, index: KT) -> IT:
        if self._indexed_getter is None:
            msg = 'Property is not readable by index'
            raise AttributeError(msg)

        return self._indexed_getter(index)

    __getitem__.__doc__ = IndexedProperty.__getitem__.__doc__  # pyright: ignore[reportUnknownMemberType]

    @override  # IndexedProperty
    def __setitem__(self, index: KT, value: IT) -> None:
        if self._indexed_setter is None:
            msg = 'Property is not writable by index'
            raise AttributeError(msg)

        return self._indexed_setter(index, value)

    __setitem__.__doc__ = IndexedProperty.__setitem__.__doc__  # pyright: ignore[reportUnknownMemberType]

    @property
    @override  # IndexedProperty
    def can_indexed_read(self) -> bool:
        return self._indexed_getter is not None

    can_indexed_read.__doc__ = IndexedProperty.can_indexed_read.__doc__

    @property
    @override  # IndexedProperty
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
        instance: T_contra,
        descriptor: DescriptorProtocol[T_contra, VT, VT] | str,
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

    @override  # _IndexedGetterSetterPropertyMixins
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

    @override  # _IndexedGetterSetterPropertyMixins
    def __getitem__(self, index: int | slice) -> IT | Sequence[IT]:
        if self._indexed_getter is None:
            msg = 'Property is not readable by index'
            raise AttributeError(msg)

        return self._indexed_getter(index)

    # __getitem__.__doc__ = IndexedProperty.__getitem__.__doc__

    @override  # Collection
    def __len__(self) -> int:
        return self._sequence.__len__()

    @override  # Sequence
    def __contains__(self, item: Any) -> bool:
        return self._sequence.__contains__(item)

    @override  # Sequence
    def __iter__(self) -> Iterator[IT]:
        return self._sequence.__iter__()

    @override  # Sequence
    def __reversed__(self) -> Iterator[IT]:
        return self._sequence.__reversed__()

    @override  # Sequence
    def index(self, value: Any, *args: Any, **kwargs: Any) -> int:
        return self._sequence.index(value, *args, **kwargs)

    @override  # Sequence
    def count(self, value: Any) -> int:
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
        instance: T_contra,
        descriptor: DescriptorProtocol[T_contra, VT, VT] | str,
        value_type: type[VT] | None = None,
    ) -> None:
        super().__init__(
            sequence=sequence,
            item_type=item_type,
            instance=instance,
            descriptor=descriptor,
            value_type=value_type,
        )

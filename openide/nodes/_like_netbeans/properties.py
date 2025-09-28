# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:words
# spell-checker:ignore observable_property

""""""

from __future__ import annotations

# System imports
from abc import ABC, abstractmethod
from copy import copy
from typing import TYPE_CHECKING, Generic, Protocol, TypeAlias, TypeVar, cast
from weakref import ReferenceType

# Third-party imports
from listeners import Observable, PropertyListener, observable_property
from typing_extensions import Self, override

# Local imports

VT = TypeVar('VT')  # Value Type
VT_contra = TypeVar('VT_contra', contravariant=True)  # Value Type
KT = TypeVar('KT')  # Key Type
IT = TypeVar('IT')  # Item Type
ES_contra = TypeVar('ES_contra', contravariant=True)  # Event source
if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import Any


class FeatureDescriptor:
    """
    FeatureDescriptor is a base class for things like a property, an event, a method, a node.

    It provides expressions for a base set of properties that are common
    to all instances of FeatureDescriptor subclasses:

    - system_name
    - display_name
    - is_expert
    - is_hidden
    - is_preferred
    - short_description

    It also provides a generic way of adding dynamic attribute values.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialises a FeatureDescriptor with defaults.

        - system_name = None
        - display_name = None
        - is_expert = False
        - is_hidden = False
        - is_preferred = False
        - short_description = None
        - No extra attribute value

        Calls super().__init__() at the end with all the provided keyword arguments.
        """
        self.__system_name: str | None = None
        self.__display_name: str | None = None
        self.__is_expert = False
        self.__is_hidden = False
        self.__is_preferred = False
        self.__short_description: str | None = None
        # Lazy instantiation of dynamic attribute dict
        self.__values: dict[str, Any] | None = None

        super().__init__(**kwargs)

    def __copy_init_kwargs__(self) -> dict[str, Any]:
        if hasattr(super(), '__copy_init_kwargs__'):
            return super().__copy_init_kwargs__()  # pyright: ignore[reportAttributeAccessIssue]
        else:
            return {}

    def __copy__(self) -> FeatureDescriptor:
        """
        Participate in shallow-copy protocol.

        This method only instantiate a new object, and call self.__copy_super__(new) to get
        all the members copied to the new instance.

        Subclasses that also have a no-arg __init__ don't need to overload this method.
        Instead, they should overload __copy_super__ to set their own members.

        Subclasses that do have args in their __init__ should overload __copy__.
        They should NOT call super().__copy__, but instead instantiate their own object,
        and call self.__copy_super__(new) to get parent, and children, classes copy behaviour.
        """
        new = type(self)(**self.__copy_init_kwargs__())
        self.__copy_super__(new)
        return new

    def __copy_super__(self, new: FeatureDescriptor) -> None:
        """
        Does the actual member copying, avoid the object instantiation.

        Subclasses overloading this method should call super().__copy_super__(new).

        In case there is a class further down in the MRO with also a __copy_super__ method,
        this implementation will call it.

        - new: The new object to copy members onto.
        """
        if hasattr(super(), '__copy_super__'):
            super().__copy_super__(new)  # pyright: ignore[reportAttributeAccessIssue]

        new.system_name = self.system_name
        new.__display_name = self.__display_name
        new.is_expert = self.is_expert
        new.is_hidden = self.is_hidden
        new.is_preferred = self.is_preferred
        new.__short_description = self.__short_description

        if self.__values:
            if new.__values is None:
                new.__values = {}
            new.__values.update(self.__values)

    @classmethod
    def merge(cls, first: FeatureDescriptor, second: FeatureDescriptor) -> FeatureDescriptor:
        """
        Merge two FeatureDescriptor together.

        Starts by copying the second FeatureDescriptor.

        String properties display_name and short_description that
        are None are then replaced with values from the first FeatureDescriptor.

        Boolean properties is_expert, is_hidden and is_preferred are ORed
        between first and second FeatureDescriptor.

        Dynamic attribute values are merged (like a dict update), with values from
        second FeatureDescriptor taking precedence.

        A subclass rarely needs to overload this, unless it wants a different
        behaviour than "second takes precedence". This is because, as we start
        off a copy of second, the complexity of subclass init-args and added
        fields should already be handled by overload of __copy__ and/or __copy_super__.
        """
        new = copy(second)

        if new.__display_name is None:
            new.__display_name = first.__display_name

        new.is_expert = first.is_expert or second.is_expert
        new.is_hidden = first.is_hidden or second.is_hidden
        new.is_preferred = first.is_preferred or second.is_preferred

        if new.__short_description is None:
            new.__short_description = first.__short_description

        if first.__values:
            if new.__values is None:
                new.__values = {}

            for k in first.__values.keys() - new.__values.keys():
                new.__values[k] = first.__values[k]

        return new

    @observable_property
    def system_name(self) -> str | None:
        """Programmatic name for this object."""
        return self.__system_name

    @system_name.setter
    def system_name(self, value: str | None) -> None:
        self.__system_name = value

    def with_system_name(self, value: str | None) -> FeatureDescriptor:
        """Sets programmatic name for this object, and returns itself."""
        self.system_name = value
        return self

    @observable_property
    def display_name(self) -> str | None:
        """
        Display name for this object.

        If none is set, returns the system_name instead.
        """
        return self.__display_name if self.__display_name is not None else self.system_name

    @display_name.setter
    def display_name(self, value: str | None) -> None:
        self.__display_name = value

    def with_display_name(self, value: str | None) -> FeatureDescriptor:
        """Sets display name for this object, and returns itself."""
        self.display_name = value
        return self

    @observable_property
    def is_expert(self) -> bool:
        """Tells if this feature is flagged as an expert feature
        (ie. shown to end users only when an expert context is activated)."""
        return self.__is_expert

    @is_expert.setter
    def is_expert(self, value: bool) -> None:
        self.__is_expert = value

    def with_is_expert(self, value: bool) -> FeatureDescriptor:  # noqa: FBT001
        """Sets the expert flag for this feature, and returns itself."""
        self.is_expert = value
        return self

    @observable_property
    def is_hidden(self) -> bool:
        """Tells if this feature is flagged as an hidden feature
        (ie. for programmatic access only, not shown to end users)."""
        return self.__is_hidden

    @is_hidden.setter
    def is_hidden(self, value: bool) -> None:
        self.__is_hidden = value

    def with_is_hidden(self, value: bool) -> FeatureDescriptor:  # noqa: FBT001
        """Sets the hidden flag for this feature, and returns itself."""
        self.is_hidden = value
        return self

    @observable_property
    def is_preferred(self) -> bool:
        """Tells if this feature is flagged as a preferred feature
        (ie. shown with importance (eg. highlighted, first) to end users)."""
        return self.__is_preferred

    @is_preferred.setter
    def is_preferred(self, value: bool) -> None:
        self.__is_preferred = value

    def with_is_preferred(self, value: bool) -> FeatureDescriptor:  # noqa: FBT001
        """Sets the preferred flag for this feature, and returns itself."""
        self.is_preferred = value
        return self

    @observable_property
    def short_description(self) -> str | None:
        """
        Short description for this object.

        If none is set, returns the display_name instead.
        """
        if self.__short_description is not None:
            return self.__short_description
        else:
            return self.display_name

    @short_description.setter
    def short_description(self, value: str | None) -> None:
        self.__short_description = value

    def with_short_description(self, value: str | None) -> FeatureDescriptor:
        """Sets short description for this object, and returns itself."""
        self.short_description = value
        return self

    def get_value(self, name: str) -> Any | None:  # noqa: ANN401
        """
        Returns a named dynamic attribute value for this object.

        If the attribute name is unknown, returns None.
        """
        if self.__values:
            return self.__values.get(name, None)
        else:
            return None

    def set_value(self, name: str, value: Any | None) -> None:  # noqa: ANN401
        """
        Sets a named dynamic attribute value for this object.

        Can also be set to None.
        """
        if self.__values is None:
            self.__values = {}

        self.__values[name] = value

    def with_value(self, name: str, value: Any | None) -> FeatureDescriptor:  # noqa: ANN401
        """Sets a named dynamic attribute value for this object, and returns itself."""
        self.set_value(name, value)
        return self

    @property
    def attribute_names(self) -> frozenset[str]:
        """Returns set of known dynamic attribute names."""
        if self.__values is not None:
            return frozenset(self.__values.keys())
        else:
            return frozenset()

    @override  # object
    def __str__(self) -> str:
        """
        Returns a basic string representation of this feature,
        mentioning all its set properties (non-None and non-False),
        and its dynamic values.

        Subclasses should not overload this method unless they want to customise
        the string format. Instead, they should overload __str_add__ generator
        to represent their own members.
        """
        return f'{type(self).__name__}({", ".join(self.__str_add__())})'

    __repr__ = __str__

    def __str_add__(self) -> Iterator[str]:
        """
        Returns a generator yielding string representation of each members to include
        in the __str__ representation.

        Subclasses should overload this method, calling "yield from super().__str_add__()"
        to get the base classes member representations, and yield their own.
        """
        names = 'system_name display_name is_preferred is_hidden is_expert short_description'
        for attr_name in names.split():
            attr_value = getattr(self, f'_FeatureDescriptor__{attr_name}')
            attr_str = self.__str_value__(
                attr_name,
                attr_value,
                force_value=(attr_name == 'system_name'),
            )
            if attr_str is not None:
                yield attr_str

        if self.__values:
            values_str: list[str] = []
            for name, value in self.__values.items():
                value_str = self.__str_value__(name, value, force_value=True)
                if value_str is not None:
                    values_str.append(value_str)

            yield f'values={{{", ".join(values_str)}}}'

    def __str_value__(
        self,
        name: str,
        value: Any | None,  # noqa: ANN401
        *,
        force_value: bool = False,
    ) -> str | None:
        """
        Helper method for subclasses to represent a member in a "standard" name=value format.

        In addition, if the value is a weakref, it will get the concrete value first.

        - name: Name of the member to represent.
        - value: Value of the member to represent.
        - force_value: If False, if value is None or False, it will not be represented.
                       If True, regardless of member value, it will always be represented.

        Returns a string representation, or None if the member should not be represented.
        """
        if isinstance(value, ReferenceType):
            value = cast('Any', value())
        if (not force_value) and isinstance(value, bool):
            if value:
                return name
            else:
                return None
        elif force_value or (value is not None):
            return f'{name}={value}'
        else:
            return None

    @override  # object
    def __eq__(self, other: object) -> bool:
        """Equal protocol, based on system_name equality."""
        try:
            # We suppose other is of the same type than us to do these comparisons.
            # But if not, then except AttributeError is meant to catch that,
            # instead of explicitly check type (heavy), or even type casting it (useless here)
            if (self.system_name is None) and (other.system_name is None):  # type: ignore  # noqa: PGH003
                return self is other
            else:
                return self.system_name == other.system_name  # type: ignore  # noqa: PGH003
        except AttributeError:
            return False

    @override  # object
    def __hash__(self) -> int:
        """Hashing protocol, based solely on system_name hash."""
        return hash(self.system_name) if self.system_name else id(self)


class Property(FeatureDescriptor, Generic[VT], ABC):
    """Provides property declaration for nodes."""

    listeners: Observable[PropertyChangeProtocol[Self, VT]]

    def __init__(self, value_type: type[VT], **kwargs: Any) -> None:
        """Initialises a Property with defaults from FeatureDescriptor,
        except for system_name which is set to an empty string.

        - value_type: The type for this property value.
        """
        self.__type = value_type

        super().__init__(**kwargs)

        self.system_name = ''

    @override  # FeatureDescriptor
    def __copy_init_kwargs__(self) -> dict[str, Any]:
        kwargs = super().__copy_init_kwargs__()
        kwargs.update(
            dict(
                value_type=self.value_type,
            ),
        )
        return kwargs

    @property
    def value_type(self) -> type[VT]:
        """The type of this property value."""
        return self.__type

    @observable_property
    @abstractmethod
    def value(self) -> VT:
        """The value of this property."""
        raise NotImplementedError  # pragma: no cover

    @value.setter
    @abstractmethod
    def value(self, value: VT) -> None:
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def can_read(self) -> bool:
        """Tells if this property is readable."""
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def can_write(self) -> bool:
        """Tells if this property can be modified."""
        raise NotImplementedError  # pragma: no cover

    @property
    def supports_default_value(self) -> bool:
        """Tells if this property can have a default value."""
        return False

    def restore_default_value(self) -> None:
        """If the property can have a default value, this method restores it."""

    @property
    def is_default_value(self) -> bool:
        """
        Tells if the current value of this property is the default value.

        If this property does not support default value, it still returns True.
        Because that means any value can be considered a default value (and so,
        can be represented in the same way).
        """
        return True

    # TODO
    @property
    def property_editor(self) -> None:
        if self.__type is None:
            return None
        raise NotImplementedError  # TODO

    # TODO: We have the same in PropertySet and Node.
    # Maybe that should move to FeatureDescriptor?
    @property
    def html_display_name(self) -> str | None:
        """
        Returns an HTML-flavoured version of this property display name.

        This HTML will be processed either by Qt (for GUI), or prompt-toolkit (for CLI).

        If an HTML version is not possible, then it should return None (and avoid returning
        a string that does not contain any HTML).
        """
        return None

    @override  # FeatureDescriptor
    def __str_add__(self) -> Iterator[str]:
        yield from super().__str_add__()

        value = self.__str_value__('value_type', self.value_type, force_value=True)
        if value is not None:
            yield value

        value = self.__str_value__('can_read', self.can_read)
        if value is not None:
            yield value

        value = self.__str_value__('can_write', self.can_write)
        if value is not None:
            yield value

        if self.can_read:
            value = self.__str_value__('value', self.value, force_value=True)
            if value is not None:
                yield value

    @override  # object
    def __eq__(self, other: object) -> bool:
        """Equal protocol, based on system_name, and value_type equality."""
        if not super().__eq__(other):
            return False

        try:
            # We suppose other is of the same type than us to do this comparison.
            # But if not, then except AttributeError is meant to catch that,
            # instead of explicitly check type (heavy), or even type casting it (useless here)
            return self.value_type == other.value_type  # type: ignore  # noqa: PGH003
        except AttributeError:
            return False

    @override  # object
    def __hash__(self) -> int:
        """Hashing protocol, based on system_name, and value_type hashes."""
        type_hash = hash(self.value_type) if self.value_type is not None else 1
        return super().__hash__() * type_hash


class IndexedProperty(Property[VT], Generic[VT, KT, IT]):
    """Provides an indexed property for an indexed node."""

    def __init__(self, index_type: type[KT], item_type: type[IT], **kwargs: Any) -> None:
        """Initialises an IndexedProperty with defaults from Property
        (ie. same defaults than FeatureDescriptor, except for system_name
        which is set to an empty string).

        - index_type: The type for this property indexing keys.
        - item_type: The type for this property items (ie. indexed values).
        - value_type: The type for this property value.
        """
        super().__init__(**kwargs)
        self.__index_type = index_type
        self.__item_type = item_type

    @override  # Property
    def __copy_init_kwargs__(self) -> dict[str, Any]:
        kwargs = super().__copy_init_kwargs__()
        kwargs.update(
            dict(
                index_type=self.index_type,
                item_type=self.item_type,
            ),
        )
        return kwargs

    @property
    def index_type(self) -> type[KT]:
        """The type of this property indexing keys."""
        return self.__index_type

    @property
    def item_type(self) -> type[IT]:
        """The type of this property items (ie. indexed values)."""
        return self.__item_type

    @abstractmethod
    def __getitem__(self, index: KT) -> IT:
        """Returns the value of this property at a particular index."""
        raise NotImplementedError  # pragma: no cover

    # @abstractmethod
    # def get_indexed_value(self, index: int) -> IT:
    #     '''Returns the value of this property at a particular index.'''
    #     raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def __setitem__(self, index: KT, value: IT) -> None:
        """Sets the value of this property at a particular index."""
        raise NotImplementedError  # pragma: no cover

    # @abstractmethod
    # def set_indexed_value(self, index: int, value: ET) -> None:
    #     '''Sets the value of this property at a particular index.'''
    #     raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def can_indexed_read(self) -> bool:
        """Tells if this property is readable using an index."""
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def can_indexed_write(self) -> bool:
        """Tells if this property can be modified using an index."""
        raise NotImplementedError  # pragma: no cover

    @property
    def indexed_property_editor(self) -> None:
        raise NotImplementedError

    @override  # Property
    def __str_add__(self) -> Iterator[str]:
        yield from super().__str_add__()

        value = self.__str_value__('index_type', self.index_type, force_value=True)
        if value is not None:
            yield value

        value = self.__str_value__('item_type', self.item_type, force_value=True)
        if value is not None:
            yield value

    @override  # object
    def __eq__(self, other: object) -> bool:
        """Equal protocol, based on system_name, value_type, index_type, and item_type equality."""
        if not super().__eq__(other):
            return False

        try:
            # We suppose other is of the same type than us to do these comparisons.
            # But if not, then except AttributeError is meant to catch that,
            # instead of explicitly check type (heavy), or even type casting it (useless here)
            return (self.index_type == other.index_type) and (self.item_type == other.item_type)  # type: ignore  # noqa: PGH003
        except AttributeError:
            return False

    @override  # object
    def __hash__(self) -> int:
        """Hashing protocol, based on system_name, value_type, index_type, and item_type hashes."""
        index_type_hash = hash(self.index_type) if self.index_type is not None else 1
        item_type_hash = hash(self.item_type) if self.item_type is not None else 1
        return super().__hash__() * index_type_hash * item_type_hash


class PropertySet(FeatureDescriptor, ABC):
    """Represents a set of properties."""

    listeners: Observable[PropertyChangeProtocol[Self, VT]]

    def __init__(
        self,
        system_name: str | None = None,
        display_name: str | None = None,
        short_description: str | None = None,
    ) -> None:
        """Initialises a PropertySet, first using defaults from FeatureDescriptor,
        which is then customised with provided arguments system_name,
        display_name and short_description.
        """
        super().__init__()
        self.system_name = system_name
        self.display_name = display_name
        self.short_description = short_description

    @property
    @abstractmethod
    def properties(self) -> Sequence[Property[Any]]:
        """The properties in this set."""
        raise NotImplementedError  # pragma: no cover

    @override  # object
    def __eq__(self, other: object) -> bool:
        # FeatureDescriptor.__eq__ only check system_name, without regard for class equality.
        # We usually don't care about class equality (because duck-typing). But here it would
        # make a difference between a PropertySet and another FeatureDescriptor with the same
        # system_name.
        if not isinstance(other, PropertySet):
            return False
        return super().__eq__(other)

    @override  # object
    def __hash__(self) -> int:
        # FeatureDescriptor.__hash__ returns a non-zero hash even when system_name is None
        system_name = self.system_name
        return hash(system_name) if system_name is not None else 0

    # TODO: We have the same in Property and Node.
    # Maybe that should move to FeatureDescriptor?
    @property
    def html_display_name(self) -> str | None:
        """
        Returns an HTML-flavoured version of this property display name.

        This HTML will be processed either by Qt (for GUI), or prompt-toolkit (for CLI).

        If an HTML version is not possible, then it should return None (and avoid returning
        a string that does not contain any HTML).
        """
        return None


# class PropertyChangeProtocol(Protocol[VT_contra, ES_contra]):
#     def __call__(
#         self,
#         source: ES_contra,
#         property_name: str,
#         old_value: VT_contra,
#         new_value: VT_contra,
#     ) -> Any: ...  # noqa: ANN401
PropertyChangeProtocol: TypeAlias = PropertyListener[ES_contra, VT_contra]

# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
# from abc import ABC, abstractmethod
from typing import (
    FrozenSet, Generator, Optional,
    MutableMapping, Any,
)
from weakref import ReferenceType

# Third-party imports

# Local imports


class FeatureDescriptor:
    '''
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
    '''

    def __init__(self) -> None:
        '''
        Initialise a FeatureDescriptor with defaults.

        - system_name = None
        - display_name = None
        - is_expert = False
        - is_hidden = False
        - is_preferred = False
        - short_description = None
        - No extra attribute value

        Calls super().__init__() at the end.
        '''
        self.__system_name: Optional[str] = None
        self.__display_name: Optional[str] = None
        self.__is_expert = False
        self.__is_hidden = False
        self.__is_preferred = False
        self.__short_description: Optional[str] = None
        # Lazy instanciation of dynamic attribute dict
        self.__values: Optional[MutableMapping[str, Any]] = None

        super().__init__()

    def __copy__(self) -> FeatureDescriptor:
        '''
        Participate in shallow-copy protocol.

        This method only instanciate a new object, and call self.__copy_super__(new) to get
        all the members copied to the new instance.

        Subclasses that also have a no-arg __init__ don't need to overload this method.
        Instead, they should overload __copy_super__ to set their own members.

        Subclasses that do have args in their __init__ should overload __copy__.
        They should NOT call super().__copy__, but instead instanciate their own object,
        and call self.__copy_super__(new) to get parent, and children, classes copy behaviour.
        '''
        new = type(self)()
        self.__copy_super__(new)
        return new

    def __copy_super__(self, new: FeatureDescriptor) -> None:
        '''
        Does the actual member copying, avoid the object instanciation.

        Subclasses overloading this method should call super().__copy_super__(new).

        In case there is a class further down in the MRO with also a __copy_super__ method,
        this implementation will call it.

        - new: The new object to copy members onto.
        '''
        if hasattr(super(), '__copy_super__'):
            super().__copy_super__(new)  # type: ignore

        new.system_name = self.system_name
        new.__display_name = self.__display_name
        new.is_expert = self.is_expert
        new.is_hidden = self.is_hidden
        new.is_preferred = self.is_preferred
        new.__short_description = self.__short_description

        if self.__values:
            if new.__values is None:
                new.__values = dict()
            new.__values.update(self.__values)

    @classmethod
    def merge(
        cls, first: FeatureDescriptor, second: FeatureDescriptor, *args: Any, **kwargs: Any
    ) -> FeatureDescriptor:
        '''
        Merge two FeatureDescriptor together.

        String properties system_name, display_name and short_description use
        the second FeatureDescriptor values in priority (ie. if they are not None).

        Boolean properties is_expert, is_hidden and is_preferred are ORed
        between first and second FeatureDescriptor.

        Dynamic attribute values are merged (as dict update), with values from
        second FeatureDescriptor taking precedence.
        '''
        new = cls(*args, **kwargs)

        new.system_name = second.system_name
        if second.__display_name is not None:
            new.__display_name = second.__display_name
        else:
            new.__display_name = first.__display_name

        new.is_expert = first.is_expert or second.is_expert
        new.is_hidden = first.is_hidden or second.is_hidden
        new.is_preferred = first.is_preferred or second.is_preferred

        if second.__short_description is not None:
            new.__short_description = second.__short_description
        else:
            new.__short_description = first.__short_description

        for values in (first.__values, second.__values):
            if values:
                if new.__values is None:
                    new.__values = dict()
                new.__values.update(values)

        return new

    @property
    def system_name(self) -> Optional[str]:
        '''Programmatic name for this object.'''
        return self.__system_name

    @system_name.setter
    def system_name(self, value: Optional[str]) -> None:
        '''Sets programmatic name for this object.'''
        self.__system_name = value

    @property
    def display_name(self) -> Optional[str]:
        '''
        Display name for this object.

        If none is set, returns the system_name instead.
        '''
        return self.__display_name if self.__display_name is not None else self.system_name

    @display_name.setter
    def display_name(self, value: Optional[str]) -> None:
        '''Sets display name for this object.'''
        self.__display_name = value

    @property
    def is_expert(self) -> bool:
        '''Tells if this feature is flagged as an expert feature
        (ie. shown to end users only when an expert context is activated).'''
        return self.__is_expert

    @is_expert.setter
    def is_expert(self, value: bool) -> None:
        '''Sets the expert flag for this feature.'''
        self.__is_expert = value

    @property
    def is_hidden(self) -> bool:
        '''Tells if this feature is flagged as an hidden feature
        (ie. for programmatic access only, not shown to end users).'''
        return self.__is_hidden

    @is_hidden.setter
    def is_hidden(self, value: bool) -> None:
        '''Sets the hidden flag for this feature.'''
        self.__is_hidden = value

    @property
    def is_preferred(self) -> bool:
        '''Tells if this feature is flagged as a preferred feature
        (ie. shown with importance (eg. highlighted, first) to end users).'''
        return self.__is_preferred

    @is_preferred.setter
    def is_preferred(self, value: bool) -> None:
        '''Sets the preferred flag for this feature.'''
        self.__is_preferred = value

    @property
    def short_description(self) -> Optional[str]:
        '''
        Short description for this object.

        If none is set, returns the display_name instead.
        '''
        if self.__short_description is not None:
            return self.__short_description
        else:
            return self.display_name

    @short_description.setter
    def short_description(self, value: Optional[str]) -> None:
        '''Sets short description for this object.'''
        self.__short_description = value

    def get_value(self, name: str) -> Optional[Any]:
        '''
        Returns a named dynamic attribute value for this object.

        If the attribute name is unknown, returns None.
        '''
        if self.__values:
            return self.__values.get(name, None)
        else:
            return None

    def set_value(self, name: str, value: Optional[Any]) -> None:
        '''
        Sets a named dynamic attribute value for this object.

        Can also be set to None.
        '''
        if self.__values is None:
            self.__values = dict()

        self.__values[name] = value

    @property
    def attribute_names(self) -> FrozenSet[str]:
        '''Returns set of known dynamic attribute names.'''
        if self.__values is not None:
            return frozenset(self.__values.keys())
        else:
            return frozenset()

    def __str__(self) -> str:
        '''
        Returns a basic string representation of this feature,
        mentioning all its set properties (non-None and non-False),
        and its dynamic values.

        Sublcasses should not overload this method unless they want to customise
        the string format. Instead, they should overload __str_add__ generator
        to represent their own members.
        '''
        return f'{type(self).__name__}({", ".join(self.__str_add__())})'

    def __str_add__(self) -> Generator[str, None, None]:
        '''
        Returns a generator yielding string representation of each members to include
        in the __str__ representation.

        Subclasses should overload this method, calling "yield from super().__str_add__()"
        to get the base classes member representations, and yield their own.
        '''
        names = 'system_name display_name is_preferred is_hidden is_expert short_description'
        for attr_name in names.split():
            attr_value = getattr(self, f'_FeatureDescriptor__{attr_name}')
            attr_str = self.__str_value__(
                attr_name, attr_value, force_value=(attr_name == 'system_name'))
            if attr_str is not None:
                yield attr_str

        if self.__values:
            values_str = []
            for name, value in self.__values.items():
                value_str = self.__str_value__(name, value, force_value=True)
                if value_str is not None:
                    values_str.append(value_str)

            yield f'values={{{", ".join(values_str)}}}'

    def __str_value__(
        self,
        name: str,
        value: Optional[Any],
        force_value: bool = False
    ) -> Optional[str]:
        '''
        Helper method for subclasses to represent a member in a "standard" name=value format.

        In addition, if the value is a weakref, it will get the concrete value first.

        - name: Name of the member to represent.
        - value: Value of the member to represent.
        - force_value: If False, if value is None or False, it will not be represented.
                       If True, regardless of member value, it will always be represented.

        Returns a string representation, or None if the member should not be represented.
        '''
        if isinstance(value, ReferenceType):
            value = value()
        if (not force_value) and isinstance(value, bool):
            if value:
                return name
            else:
                return None
        elif force_value or (value is not None):
            return f'{name}={value}'
        else:
            return None


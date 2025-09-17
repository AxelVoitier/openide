# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore
""""""

from __future__ import annotations

# System imports
from threading import RLock
from typing import TYPE_CHECKING, Any, Self, override

# Third-party imports
from listeners import Listeners, Observable

# Local imports
from .properties import (
    Property,
    PropertySet,
    PropertySetChangeListener,
    PropertySetModificationKind,
    Sheet,
    SheetChangeListener,
    SheetModificationKind,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Final

__all__: Final = (
    'PropertySetSupport',
    'SheetSupport',
)


class PropertySetSupport(PropertySet):
    listeners: Listeners[PropertySetChangeListener]
    """Property change listeners listening on this set"""

    def __init__(self) -> None:
        super().__init__()

        self.__props: list[Property[Any]] = []
        """List of properties"""

        self.__lock = RLock()

        self.listeners = Listeners[PropertySetChangeListener]()
        self._observable = Observable(self.listeners)

    @property
    @override
    def properties(self) -> Iterator[Property[Any]]:
        """Iterate over all properties in this set"""

        with self.__lock:
            yield from self.__props

    def get(self, name: str) -> Property[Any] | None:
        """Get a property by name.

        Returns the first property in the list that has this name, None if not found.
        """

        with self.__lock:
            index = self.__find_index(name)
            return self.__props[index] if index != -1 else None

    def put(self, prop: Property[Any]) -> Property[Any] | None:
        """Add a property to this set, replacing any old one with the same name.

        Returns the property with the same name that was replaced, or None for a fresh insertion.
        """

        with self.__lock:
            name = prop.system_name
            index = self.__find_index(name)
            removed = None
            if index == -1:
                with self._observable.fire(
                    self,
                    PropertySetModificationKind.AddProperty,
                    None,
                    prop,
                ):
                    self.__props.append(prop)
            else:
                removed = self.__props[index]
                with self._observable.fire(
                    self,
                    PropertySetModificationKind.ReplaceProperty,
                    removed,
                    prop,
                ):
                    self.__props[index] = prop

            return removed

    def puts(self, *props: Property[Any]) -> None:
        """Add several properties to this set, replacing old ones with the same names."""

        with self.__lock:
            for prop in props:
                name = prop.system_name
                index = self.__find_index(name)
                if index == -1:
                    self.__props.append(prop)
                else:
                    self.__props[index] = prop

    def remove(self, prop: Property[Any] | str) -> Property[Any] | None:
        """Remove a property from the set.

        Returns the removed property, or None if it was not there to begin with.
        """

        with self.__lock:
            name = prop.system_name if not isinstance(prop, str) else prop
            if (index := self.__find_index(name)) == -1:
                return None

            removed = self.__props[index]
            with self._observable.fire(
                self,
                PropertySetModificationKind.RemoveProperty,
                removed,
                None,
            ):
                return self.__props.pop(index)

    def clear(self) -> None:
        """Remove all properties from the set"""

        with (
            self.__lock,
            self._observable.fire(self, PropertySetModificationKind.ClearAllProperties, None, None),
        ):
            self.__props.clear()

    def __find_index(self, name: str | None) -> int:
        """Finds index for property with specified name,  or -1 if not found"""

        if name is None:
            return -1

        for i, prop in enumerate(self.__props):
            if prop.system_name == name:
                return i

        return -1


class SheetSupport(Sheet):
    """Support for creation of property sets. Allows easy
    addition, modification, and deletion of properties. Also
    permits listening on changes of contained property sets."""

    PROPERTIES = 'properties'
    """Name for regular property set"""

    EXPERT = 'expert'
    """Name for expert property set"""

    listeners: Listeners[SheetChangeListener]
    """Property change listeners"""

    @classmethod
    def create_default(cls) -> Self:
        """Convenience method to create new sheet with only one empty set, named Sheet.PROPERTIES

        Returns a new sheet with default property set.
        """

        new_sheet = cls()
        new_sheet.put(cls.create_properties_set())

        return new_sheet

    @classmethod
    def create_properties_set(cls) -> PropertySetSupport:
        """Convenience method to create new sheet set named Sheet.PROPERTIES"""

        sheet_set = PropertySetSupport()
        sheet_set.system_name = cls.PROPERTIES
        sheet_set.display_name = 'Properties'
        sheet_set.short_description = 'Properties of this object.'

        return sheet_set

    @classmethod
    def create_expert_set(cls) -> PropertySetSupport:
        """Convenience method to create new sheet set named Sheet.PROPERTIES"""

        sheet_set = PropertySetSupport()
        sheet_set.is_expert = True
        sheet_set.system_name = cls.EXPERT
        sheet_set.display_name = 'Expert'
        sheet_set.short_description = 'Expert properties of this object.'

        return sheet_set

    def __init__(self) -> None:
        super().__init__()

        self.__sets: list[PropertySetSupport] = []
        """List of sets"""

        self.__lock = RLock()

        self.listeners = Listeners[SheetChangeListener]()
        self._observable = Observable(self.listeners)

    @property
    @override
    def property_sets(self) -> Iterator[PropertySet]:
        """Iterate over the property sets in this sheet"""

        with self.__lock:
            yield from self.__sets

    def get(self, name: str) -> PropertySetSupport | None:
        """Find the property set with a given name"""

        with self.__lock:
            index = self.__find_index(name)
            return self.__sets[index] if index != -1 else None

    def put(self, sheet_set: PropertySetSupport) -> PropertySetSupport | None:
        """Add a property set. If the set does not yet exist in the sheet,
        inserts a new set with the implied name. Otherwise the old set is replaced
        by the new one.

        Returns the previous set with the same name, or None if this is a fresh insertion.
        """

        with self.__lock:
            name = sheet_set.system_name
            index = self.__find_index(name)
            removed = None
            if index == -1:
                with self._observable.fire(
                    self,
                    SheetModificationKind.AddPropertySet,
                    None,
                    sheet_set,
                ):
                    self.__sets.append(sheet_set)
            else:
                removed = self.__sets[index]
                with self._observable.fire(
                    self,
                    SheetModificationKind.ReplacePropertySet,
                    removed,
                    sheet_set,
                ):
                    self.__sets[index] = sheet_set

            return removed

    def remove(self, sheet_set: PropertySetSupport | str) -> PropertySetSupport | None:
        """Remove a property set from the sheet.

        Returns removed set, or None if the set could not be found.
        """

        with self.__lock:
            name = sheet_set.system_name if not isinstance(sheet_set, str) else sheet_set
            if (index := self.__find_index(name)) == -1:
                return None

            removed = self.__sets[index]
            with self._observable.fire(
                self, SheetModificationKind.RemovePropertySet, removed, None
            ):
                return self.__sets.pop(index)

    def clear(self) -> None:
        """Remove all property sets from the sheet"""

        with (
            self.__lock,
            self._observable.fire(self, SheetModificationKind.ClearAllPropertySet, None, None),
        ):
            self.__sets.clear()

    def __find_index(self, name: str | None) -> int:
        """Finds index for property set for given name, or -1 if not found"""

        if name is None:
            return -1

        for i, sheet_set in enumerate(self.__sets):
            if sheet_set.system_name == name:
                return i

        return -1

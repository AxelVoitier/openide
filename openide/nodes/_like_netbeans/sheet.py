from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from threading import RLock
from typing import TYPE_CHECKING, Any

from listeners import Observable
from typing_extensions import Self, override

from openide.nodes._like_netbeans.properties import Property, PropertyChangeProtocol, PropertySet

if TYPE_CHECKING:
    from collections.abc import Sequence


class Sheet:
    """Support for creation of property sets. Allows easy
    addition, modification, and deletion of properties. Also
    permits listening on changes of contained properties."""

    PROPERTIES = 'properties'
    """Name for regular property set"""

    EXPERT = 'expert'
    """Name for expert property set"""

    listeners: Observable[PropertyChangeProtocol[Any, Any]]
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
    def create_properties_set(cls) -> SheetSet:
        """Convenience method to create new sheet set named Sheet.PROPERTIES"""

        sheet_set = SheetSet()
        sheet_set.system_name = cls.PROPERTIES
        sheet_set.display_name = 'Properties'
        sheet_set.short_description = 'Properties of this object.'

        return sheet_set

    @classmethod
    def create_expert_set(cls) -> SheetSet:
        """Convenience method to create new sheet set named Sheet.PROPERTIES"""

        sheet_set = SheetSet()
        sheet_set.is_expert = True
        sheet_set.system_name = cls.EXPERT
        sheet_set.display_name = 'Expert'
        sheet_set.short_description = 'Expert properties of this object.'

        return sheet_set

    def __init__(self) -> None:
        super().__init__()

        self.__sets: list[SheetSet] = []
        """List of sets"""

        self.__array: list[PropertySet] | None = None
        """Cached list of PropertySet"""

        self.__lock = RLock()

        self.listeners = Observable[PropertyChangeProtocol[Any, Any]]()

    def to_list(self) -> list[PropertySet]:
        """Obtain the array of property sets"""

        while True:
            with self.__lock:
                if (array := self.__array) is not None:
                    return array

            array = list(self.__sets)  # Clone
            with self.__lock:
                if self.__array is None:
                    self.__array = array

    # Addition to Netbeans for a simpler interface
    def iter_property_sets(self) -> Iterator[PropertySet]:
        yield from self.__sets

    def clone_sheet(self) -> Self:
        """Create a deep copy of the sheet. Listeners are not copied."""

        new_sheet = type(self)()
        with self.__lock:
            for sheet_set in self.__sets:
                new_sheet.__sets.append(sheet_set.clone_set())

        return new_sheet

    def get(self, name: str) -> SheetSet | None:
        """Find the property set with a given name"""

        with self.__lock:
            index = self.__find_index(name)
            return self.__sets[index] if index != -1 else None

    def put(self, sheet_set: SheetSet) -> SheetSet | None:
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
                self.__sets.append(sheet_set)
                # sheet_set.listeners += self.__forward_event
            else:
                removed = self.__sets[index]
                # removed.listeners -= self.__forward_event
                self.__sets[index] = sheet_set
                # sheet_set.listeners += self.__forward_event
                removed.listeners -= self.__property_change_listener

            sheet_set.listeners += self.__property_change_listener
            self.__refresh(hint=name if name is not None else '')

            return removed

    def remove(self, name: str) -> SheetSet | None:
        """Remove a property set from the sheet.

        Returns removed set, or None if the set could not be found.
        """

        with self.__lock:
            if (index := self.__find_index(name)) == -1:
                return None

            try:
                removed = self.__sets.pop(index)
                # removed.listeners -= self.__forward_event
                removed.listeners -= self.__property_change_listener

                return removed
            finally:
                # Clears computed array and fire property change listeners
                self.__refresh(hint=name)

    def __find_index(self, name: str | None) -> int:
        """Finds index for property set for given name, or -1 if not found"""

        if name is None:
            return -1

        for i, sheet_set in enumerate(self.__sets):
            if sheet_set.system_name == name:
                return i

        return -1

    def __refresh(self, hint: str = '') -> None:
        with self.__lock:
            self.__array = None

        self.listeners.fire_no_veto(self, hint, None, None)

    def __property_change_listener(
        self,
        source: Any,  # noqa: ANN401
        property_name: str,
        old_value: Any,  # noqa: ANN401
        new_value: Any,  # noqa: ANN401
    ) -> None:
        self.listeners.fire_no_veto(source, property_name, old_value, new_value)

    # @contextmanager
    # def __forward_event(
    #     self,
    #     owner: Any,  # noqa: ANN401
    #     attr_name: str,
    #     old_value: Any | None,  # noqa: ANN401
    #     new_value: Any,  # noqa: ANN401
    # ) -> Iterator[None]:
    #     with self.listeners.fire(owner, attr_name, old_value, new_value):
    #         yield


class SheetSet(PropertySet):
    listeners: Observable[PropertyChangeProtocol[Any, Any]]
    """Property change listeners listening on this set"""

    def __init__(self) -> None:
        super().__init__()

        self.__props: list[Property[Any]] = []
        """List of properties"""
        self.__array: list[Property[Any]] | None = None
        """Cached array of properties"""

        self.__lock = RLock()

        self.listeners = Observable[PropertyChangeProtocol[Any, Any]]()

    def clone_set(self) -> Self:
        """Clone the property set"""

        new_set = type(self)()
        with self.__lock:
            new_set.__props = list(self.__props)
        return new_set

    def get(self, name: str) -> Property[Any] | None:
        """Get a property by name.

        Returns the first property in the list that has this name, None if not found.
        """

        with self.__lock:
            index = self.__find_index(name)
            return self.__props[index] if index != -1 else None

    @property
    @override
    def properties(self) -> Sequence[Property[Any]]:
        """Get all properties in this set"""

        with self.__lock:
            if (array := self.__array) is None:
                self.__array = array = list(self.__props)

            return array

    def put(self, prop: Property[Any]) -> Property[Any] | None:
        """Add a property to this set, replacing any old one with the same name.

        Returns the property with the same name that was replaced, or None for a fresh insertion.
        """

        with self.__lock:
            name = prop.system_name
            index = self.__find_index(name)
            removed = None
            if index == -1:
                self.__props.append(prop)
                # prop.listeners += self.__forward_event
            else:
                removed = self.__props[index]
                # removed.listeners -= self.__forward_event
                self.__props[index] = prop
                # prop.listeners += self.__forward_event

            self.__refresh(hint=name if name is not None else '')

            return removed

    def puts(self, *props: Property[Any]) -> None:
        """Add several properties to this set, replacing old ones with the same names."""

        with self.__lock:
            for prop in props:
                name = prop.system_name
                index = self.__find_index(name)
                if index == -1:
                    self.__props.append(prop)
                    # prop.listeners += self.__forward_event
                else:
                    # self.__props[index].listeners -= self.__forward_event
                    self.__props[index] = prop
                    # prop.listeners += self.__forward_event

            self.__refresh()

    def remove(self, name: str) -> Property[Any] | None:
        """Remove a property from the set.

        Returns the removed property, or None if it was not there to begin with.
        """

        with self.__lock:
            if (index := self.__find_index(name)) == -1:
                return None

            try:
                # self.__props[index].listeners -= self.__forward_event
                return self.__props.pop(index)
            finally:
                # Clears computed array and fire property change listeners
                self.__refresh(hint=name)

    def __find_index(self, name: str | None) -> int:
        """Finds index for property with specified name,  or -1 if not found"""

        if name is None:
            return -1

        for i, prop in enumerate(self.__props):
            if prop.system_name == name:
                return i

        return -1

    def __refresh(self, hint: str = '') -> None:
        """Notifies change of properties."""

        self.__array = None
        self.listeners.fire_no_veto(self, hint, None, None)

    # @contextmanager
    # def __forward_event(
    #     self,
    #     owner: Any,  # noqa: ANN401
    #     attr_name: str,
    #     old_value: Any | None,  # noqa: ANN401
    #     new_value: Any,  # noqa: ANN401
    # ) -> Iterator[None]:
    #     print(f'!!! Firing in forward agent {owner=} {attr_name=} {old_value=} {new_value=}')
    #     with self.listeners.fire(owner, attr_name, old_value, new_value):
    #         print('!!!! Entered in forward agent')
    #         yield
    #         print('!!! Actually executed in forward agent')

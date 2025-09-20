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
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generic, TypeVar

# Third-party imports
# Local imports
from .properties import PropertySetModificationKind, SheetModificationKind

PropertySetItem = TypeVar('PropertySetItem')
PropertyItem = TypeVar('PropertyItem')
if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Final

    from .properties import Property, PropertySet, Sheet

__all__: Final = ('AbstractSheetUser',)

_logger = logging.getLogger(__name__)


class AbstractSheetUser(ABC, Generic[PropertySetItem, PropertyItem]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__sheet: Sheet | None = None
        self.__prop_set_to_item: dict[PropertySet, PropertySetItem] = {}
        self.__prop_to_item: dict[Property[Any], PropertyItem] = {}
        self.__show_expert = False
        self.__show_hidden = False

    @property
    def show_expert(self) -> bool:
        return self.__show_expert

    @show_expert.setter
    def show_expert(self, value: bool) -> None:
        self.__show_expert = value

        # Crude. Maybe there is a way to do a refresh by insertions/deletions?
        self.set_sheet(self.__sheet)

    @property
    def show_hidden(self) -> bool:
        return self.__show_hidden

    @show_hidden.setter
    def show_hidden(self, value: bool) -> None:
        self.__show_hidden = value

        # Crude. Maybe there is a way to do a refresh by insertions/deletions?
        self.set_sheet(self.__sheet)

    #
    # Sheets
    #

    def set_sheet(self, sheet: Sheet | None) -> None:
        if self.__sheet is not None:
            self.__clear_sheet()
            self.__sheet.listeners -= self.__sheet_event

        if sheet is None:
            return

        for prop_set in sheet.property_sets:
            self.__add_property_set(prop_set)

        sheet.listeners += self.__sheet_event
        self.__sheet = sheet

    def __clear_sheet(self) -> None:
        # NB: Capture it in tuple because it is going to change size during operation
        for prop_set in tuple(self.__prop_set_to_item):
            self.__remove_property_set(prop_set)

        assert not self.__prop_set_to_item
        assert not self.__prop_to_item

    @contextmanager
    def __sheet_event(
        self,
        sheet: Sheet,
        kind: SheetModificationKind,
        old_prop_set: PropertySet | None,
        new_prop_set: PropertySet | None,
    ) -> Iterator[None]:
        match kind:
            case SheetModificationKind.RemovePropertySet | SheetModificationKind.ReplacePropertySet:
                assert old_prop_set is not None, 'Cannot remove a None property set'
                self.__remove_property_set(old_prop_set)
            case SheetModificationKind.ClearAllPropertySet:
                for prop_set in sheet.property_sets:
                    self.__remove_property_set(prop_set)
            case _:
                pass

        yield

        match kind:
            case SheetModificationKind.AddPropertySet | SheetModificationKind.ReplacePropertySet:
                assert new_prop_set is not None, 'Cannot add a None property'
                self.__add_property_set(new_prop_set)
            case _:
                pass

    #
    # Property Sets
    #

    def __add_property_set(self, prop_set: PropertySet) -> None:
        if prop_set.is_hidden and not self.__show_hidden:
            return
        if prop_set.is_expert and not self.__show_expert:
            return
        if not self._accept_property_set(prop_set):
            return

        with self._on_adding_property_set(prop_set) as item:
            for prop in prop_set.properties:
                self.__add_property(prop, item)

            self.__prop_set_to_item[prop_set] = item
            prop_set.listeners += self.__property_set_event

    def _accept_property_set(self, prop: PropertySet) -> bool:
        return True

    @contextmanager
    @abstractmethod
    def _on_adding_property_set(self, prop_set: PropertySet) -> Iterator[PropertySetItem]:
        raise NotImplementedError

    def __remove_property_set(self, prop_set: PropertySet) -> None:
        if prop_set not in self.__prop_set_to_item:
            return

        with self._on_removing_property_set(prop_set, self.__prop_set_to_item[prop_set]):
            prop_set.listeners -= self.__property_set_event
            for prop in prop_set.properties:
                self.__remove_property(prop)
            del self.__prop_set_to_item[prop_set]

    @contextmanager
    @abstractmethod
    def _on_removing_property_set(
        self,
        prop_set: PropertySet,
        item: PropertySetItem,
    ) -> Iterator[None]:
        raise NotImplementedError

    def _get_property_set_item(self, prop_set: PropertySet) -> PropertySetItem:
        return self.__prop_set_to_item[prop_set]

    @contextmanager
    def __property_set_event(
        self,
        prop_set: PropertySet,
        kind: PropertySetModificationKind,
        old_prop: Property[Any] | None,
        new_prop: Property[Any] | None,
    ) -> Iterator[None]:
        match kind:
            case (
                PropertySetModificationKind.RemoveProperty
                | PropertySetModificationKind.ReplaceProperty
            ):
                assert old_prop is not None, 'Cannot remove a None property'
                self.__remove_property(old_prop)
            case PropertySetModificationKind.ClearAllProperties:
                for prop in prop_set.properties:
                    self.__remove_property(prop)
            case _:
                pass

        yield

        match kind:
            case (
                PropertySetModificationKind.AddProperty
                | PropertySetModificationKind.ReplaceProperty
            ):
                assert new_prop is not None, 'Cannot add a None property'
                parent_item = self.__prop_set_to_item[prop_set]
                self.__add_property(new_prop, parent_item)
            case _:
                pass

    #
    # Properties
    #

    def __add_property(self, prop: Property[Any], parent_item: PropertySetItem) -> None:
        if prop.is_hidden and not self.__show_hidden:
            return
        if prop.is_expert and not self.__show_expert:
            return
        if not self._accept_property(prop):
            return

        with self._on_adding_property(prop, parent_item) as item:
            self.__prop_to_item[prop] = item
            prop.listeners += self.__prop_event

    def _accept_property(self, prop: Property[Any]) -> bool:
        return True

    @contextmanager
    @abstractmethod
    def _on_adding_property(
        self,
        prop: Property[Any],
        parent_item: PropertySetItem,
    ) -> Iterator[PropertyItem]:
        raise NotImplementedError

    def __remove_property(self, prop: Property[Any]) -> None:
        if prop not in self.__prop_to_item:
            return

        with self._on_removing_property(prop, self.__prop_to_item[prop]):
            prop.listeners -= self.__prop_event
            del self.__prop_to_item[prop]

    @contextmanager
    @abstractmethod
    def _on_removing_property(self, prop: Property[Any], item: PropertyItem) -> Iterator[None]:
        raise NotImplementedError

    def _get_property_item(self, prop: Property[Any]) -> PropertyItem:
        return self.__prop_to_item[prop]

    def __prop_event(
        self,
        prop: Property[Any],
        attr_name: str,
        old_value: Any | None,  # noqa: ANN401
        new_value: Any,  # noqa: ANN401
    ) -> None:
        item = self.__prop_to_item[prop]
        self._on_property_event(prop, attr_name, old_value, new_value, item)

    @abstractmethod
    def _on_property_event(
        self,
        prop: Property[Any],
        attr_name: str,
        old_value: Any | None,  # noqa: ANN401
        new_value: Any,  # noqa: ANN401
        item: PropertyItem,
    ) -> None:
        raise NotImplementedError

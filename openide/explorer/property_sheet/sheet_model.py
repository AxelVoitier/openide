# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore pset descr
""""""

from __future__ import annotations

import logging

# System imports
from contextlib import contextmanager
from enum import Enum
from typing import TYPE_CHECKING, cast, override

# Third-party imports
from PySide6.QtCore import QModelIndex, QPersistentModelIndex, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel

from openide.nodes import PropertySetModificationKind, SheetModificationKind

# Local imports


if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    from openide.nodes import Property, PropertySet, Sheet


_logger = logging.getLogger(__name__)


class SheetModel(QStandardItemModel):
    section_span = Signal(int, QModelIndex, bool, arguments=['row', 'parent', 'span'])
    expand = Signal(QModelIndex, bool, arguments=['index', 'expanded'])

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.setColumnCount(2)
        self.__sheet: Sheet | None = None
        self.__prop_set_to_item: dict[PropertySet, QStandardItem] = {}
        self.__prop_to_item: dict[Property[Any], QStandardItem] = {}
        self.__currently_setting: set[Property[Any]] = set()

    def set_sheet(self, sheet: Sheet | None) -> None:
        if self.__sheet is not None:
            self._clear_sheet()
            self.__sheet.listeners -= self.__sheet_event

        if sheet is None:
            return

        for prop_set in sheet.property_sets:
            self._add_property_set(prop_set)

        sheet.listeners += self.__sheet_event
        self.__sheet = sheet

    def _clear_sheet(self) -> None:
        for prop_set in tuple(self.__prop_set_to_item):
            self._remove_property_set(prop_set)

        assert not self.__prop_set_to_item
        assert not self.__prop_to_item

    def _add_property_set(self, prop_set: PropertySet) -> None:
        item = QStandardItem(prop_set.display_name or '')
        item.setEditable(False)
        if descr := prop_set.short_description:
            item.setData(descr, Qt.ItemDataRole.ToolTipRole)

        for prop in prop_set.properties:
            self._add_property(prop, item)

        self.__prop_set_to_item[prop_set] = item
        prop_set.listeners += self.__property_set_event

        self.appendRow(item)
        self.section_span.emit(item.row(), QModelIndex(), True)  # noqa: FBT003
        self.expand.emit(item.index(), True)  # noqa: FBT003

    def _remove_property_set(self, prop_set: PropertySet) -> None:
        prop_set.listeners -= self.__property_set_event

        for prop in prop_set.properties:
            self._remove_property(prop)

        item = self.__prop_set_to_item.pop(prop_set)
        self.removeRow(item.row())

    def _add_property(self, prop: Property[Any], parent_item: QStandardItem) -> None:
        if prop.is_hidden:
            return

        descr = prop.short_description

        name_item = QStandardItem(prop.display_name or '')
        name_item.setEditable(False)
        if descr:
            name_item.setData(descr, Qt.ItemDataRole.ToolTipRole)

        value_item = QStandardItem()
        value_item.setData(prop, role=Qt.ItemDataRole.UserRole)
        if prop.can_read:
            if prop.value_type is bool:
                value_item.setCheckable(True)
                value_item.setCheckState(self._get_display_value(prop))
            else:
                value_item.setData(self._get_display_value(prop), role=Qt.ItemDataRole.DisplayRole)
        if descr:
            name_item.setData(descr, Qt.ItemDataRole.ToolTipRole)
        value_item.setEditable(prop.can_write)

        self.__prop_to_item[prop] = value_item
        prop.listeners += self.__prop_event

        parent_item.appendRow([name_item, value_item])

    def _remove_property(self, prop: Property[Any]) -> None:
        prop.listeners -= self.__prop_event
        value_item = self.__prop_to_item.pop(prop)
        value_item.parent().removeRow(value_item.row())

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
                self._remove_property_set(old_prop_set)
            case SheetModificationKind.ClearAllPropertySet:
                for prop_set in sheet.property_sets:
                    self._remove_property_set(prop_set)
            case _:
                pass

        yield

        match kind:
            case SheetModificationKind.AddPropertySet | SheetModificationKind.ReplacePropertySet:
                assert new_prop_set is not None, 'Cannot add a None property'
                self._add_property_set(new_prop_set)
            case _:
                pass

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
                self._remove_property(old_prop)
            case PropertySetModificationKind.ClearAllProperties:
                for prop in prop_set.properties:
                    self._remove_property(prop)
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
                self._add_property(new_prop, parent_item)
            case _:
                pass

    def __prop_event(
        self,
        owner: Any,  # noqa: ANN401
        attr_name: str,
        old_value: Any | None,  # noqa: ANN401
        new_value: Any,  # noqa: ANN401
    ) -> None:
        if owner in self.__currently_setting:
            return

        item = self.__prop_to_item[owner]
        item.setData(new_value, Qt.ItemDataRole.DisplayRole)

    def _get_display_value(self, prop: Property[Any]) -> Any:  # noqa: ANN401
        value = prop.value
        if value is None:
            return ''
        if isinstance(value, Enum):
            return value.name
        elif isinstance(value, bool):
            return Qt.CheckState.Checked if value else Qt.CheckState.Unchecked
        else:
            return value

    @override
    def setData(
        self,
        index: QModelIndex | QPersistentModelIndex,
        value: Any,
        /,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        # print(
        #     f'>>>>> setData {index = }, {value = } ({type(value)}), role={Qt.ItemDataRole(role).name}'
        # )
        if role not in (
            Qt.ItemDataRole.EditRole,
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.CheckStateRole,
        ):
            return super().setData(index, value, role)

        item = self.itemFromIndex(index)
        prop = cast('Property[Any]', item.data(Qt.ItemDataRole.UserRole))

        if role == Qt.ItemDataRole.CheckStateRole:
            match Qt.CheckState(value):
                case Qt.CheckState.Checked:
                    value = True
                case Qt.CheckState.Unchecked:
                    value = False
                case other:
                    _logger.error(
                        'Invalid check state value %s for boolean property %s',
                        other.name,
                        prop.display_name,
                    )
                    return False

        if (prop.value_type in (int, float)) and not isinstance(value, prop.value_type):
            value = prop.value_type(value)

        if value == prop.value:
            return False

        self.__currently_setting.add(prop)
        try:
            prop.value = value
        except Exception:
            _logger.exception('Error while attempting to set property %s', prop)
            return False
        else:
            return super().setData(index, self._get_display_value(prop), role)
        finally:
            self.__currently_setting.remove(prop)

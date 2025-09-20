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

from openide.nodes import AbstractSheetUser
from openide.utils_qt import QABC

# Local imports


if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    from openide.nodes import Property, PropertySet


_logger = logging.getLogger(__name__)


class SheetModel(AbstractSheetUser[QStandardItem, QStandardItem], QABC, QStandardItemModel):
    section_span = Signal(int, QModelIndex, bool, arguments=['row', 'parent', 'span'])
    expand = Signal(QModelIndex, bool, arguments=['index', 'expanded'])

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.setColumnCount(2)
        self.__currently_setting: set[Property[Any]] = set()

    @contextmanager
    @override  # AbstractSheetUser
    def _on_adding_property_set(self, prop_set: PropertySet) -> Iterator[QStandardItem]:
        item = QStandardItem(prop_set.display_name or '')
        item.setEditable(False)
        if descr := prop_set.short_description:
            item.setData(descr, Qt.ItemDataRole.ToolTipRole)

        yield item

        self.appendRow(item)
        self.section_span.emit(item.row(), QModelIndex(), True)  # noqa: FBT003
        self.expand.emit(item.index(), True)  # noqa: FBT003

    @contextmanager
    @override  # AbstractSheetUser
    def _on_removing_property_set(
        self,
        prop_set: PropertySet,
        item: QStandardItem,
    ) -> Iterator[None]:
        yield
        self.removeRow(item.row())

    @contextmanager
    @override  # AbstractSheetUser
    def _on_adding_property(
        self,
        prop: Property[Any],
        parent_item: QStandardItem,
    ) -> Iterator[QStandardItem]:
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

        yield value_item

        parent_item.appendRow([name_item, value_item])

    @contextmanager
    @override  # AbstractSheetUser
    def _on_removing_property(self, prop: Property[Any], item: QStandardItem) -> Iterator[None]:
        yield
        item.parent().removeRow(item.row())

    @override  # AbstractSheetUser
    def _on_property_event(
        self,
        prop: Property[Any],
        attr_name: str,
        old_value: Any | None,
        new_value: Any,
        item: QStandardItem,
    ) -> None:
        if prop in self.__currently_setting:
            return

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
        #     f'>>>>> setData {index = }, {value = } '
        #     f'({type(value)}), role={Qt.ItemDataRole(role).name}',
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

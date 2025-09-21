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

import logging

# System imports
from enum import Enum
from types import NoneType, UnionType
from typing import TYPE_CHECKING, TypedDict, cast, override

# Third-party imports
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QStyledItemDelegate

# Local imports

if TYPE_CHECKING:
    from typing import Any, Final, Literal

    from PySide6.QtCore import QAbstractItemModel, QModelIndex, QPersistentModelIndex
    from PySide6.QtWidgets import QStyleOptionViewItem, QWidget

    from openide.nodes import Property

__all__: Final = (
    'PropertyValueDelegate',
    'TypeInfo',
)

_logger = logging.getLogger(__name__)


class TypeInfo(TypedDict):
    is_nullable: bool
    is_enum: Literal[False] | type[Enum]


class PropertyValueDelegate(QStyledItemDelegate):
    # def __init__(self, *args: Any, **kwargs: Any) -> None:
    #     super().__init__(*args, **kwargs)

    def _get_type_info(self, prop: Property[Any]) -> TypeInfo:
        value_type: Any = prop.value_type
        info = TypeInfo(is_nullable=False, is_enum=False)
        if isinstance(value_type, UnionType):
            for subtype in value_type.__args__:
                # print(f'{subtype} ({type(subtype)})')
                if subtype is NoneType:
                    info['is_nullable'] = True
                elif issubclass(subtype, Enum):
                    info['is_enum'] = subtype
        elif issubclass(value_type, Enum):
            info['is_enum'] = value_type

        return info

    @override
    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QWidget:
        assert index.column() == 1, (
            f'Requested index is not for column 1, but {index.column()} instead'
        )

        prop = cast('Property[Any]', index.data(Qt.ItemDataRole.UserRole))
        type_info = self._get_type_info(prop)

        if (enum_type := type_info['is_enum']) is not False:
            editor = QComboBox(parent)

            if type_info['is_nullable']:
                editor.addItem('', None)
            for value in enum_type:
                editor.addItem(value.name, value)

            return editor
        else:
            return super().createEditor(parent, option, index)

    @override
    def setEditorData(self, editor: QWidget, index: QModelIndex | QPersistentModelIndex) -> None:
        if isinstance(editor, QComboBox):
            value = index.data(Qt.ItemDataRole.EditRole)
            ix = editor.findText(value)
            if ix >= 0:
                editor.setCurrentIndex(ix)
        else:
            super().setEditorData(editor, index)

    @override
    def setModelData(
        self,
        editor: QWidget,
        model: QAbstractItemModel,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        if isinstance(editor, QComboBox):
            value = editor.itemData(editor.currentIndex())
            model.setData(index, value, Qt.ItemDataRole.EditRole)
        else:
            super().setModelData(editor, model, index)

    @override
    def updateEditorGeometry(
        self,
        editor: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        editor.setGeometry(option.rect)

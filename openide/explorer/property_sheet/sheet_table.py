# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore

from __future__ import annotations

# System imports
import logging
from typing import TYPE_CHECKING, Any, cast

# Third-party imports
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTreeView
from typing_extensions import override

# Local imports
from openide.explorer.property_sheet.editor_support import PropertyValueDelegate
from openide.explorer.property_sheet.sheet_model import SheetModel

if TYPE_CHECKING:
    from typing import Final

    from PySide6.QtCore import QAbstractItemModel
    from PySide6.QtWidgets import QAbstractItemDelegate

__all__: Final = ('SheetTable',)

_logger = logging.getLogger(__name__)


class SheetTable(QTreeView):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__value_delegate: QAbstractItemDelegate | None = None
        _ = self.value_delegate

        self.setHeaderHidden(True)
        self.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.AnyKeyPressed
            | QAbstractItemView.EditTrigger.CurrentChanged,  # This one might be controversial
        )

    @override  # QTreeView
    def model(self) -> SheetModel | None:  # pyright: ignore[reportIncompatibleMethodOverride]
        return cast('SheetModel', super().model())

    @override  # QTreeView
    def setModel(self, model: QAbstractItemModel | SheetModel | None) -> None:
        if (model is not None) and (not isinstance(model, SheetModel)):
            msg = f'Model must be a subclass of SheetModel, got {type(model).__name__}'
            raise TypeError(msg)

        if (current_model := self.model()) is not None:
            current_model.expand.disconnect(self.setExpanded)
            current_model.section_span.disconnect(self.setFirstColumnSpanned)

        super().setModel(model)

        if model is not None:
            model.section_span.connect(self.setFirstColumnSpanned)
            model.expand.connect(self.setExpanded)

    @property
    def value_delegate(self) -> QAbstractItemDelegate:
        if (delegate := self.__value_delegate) is None:
            self.value_delegate = delegate = PropertyValueDelegate(parent=self)

        return delegate

    @value_delegate.setter
    def value_delegate(self, delegate: QAbstractItemDelegate) -> None:
        self.__value_delegate = delegate
        self.setItemDelegateForColumn(1, delegate)

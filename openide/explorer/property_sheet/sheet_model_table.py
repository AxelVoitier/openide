# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore pset

from __future__ import annotations

# System imports
import logging
from contextlib import ExitStack, contextmanager
from typing import TYPE_CHECKING, cast, override

# Third-party imports
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt, Signal

# Local imports
from openide.explorer.property_sheet import PropertySetModelChangeType

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any, Final, TypeAlias

    from openide.explorer.property_sheet import PropertySetModel
    from openide.nodes import Property

    ModelIndex: TypeAlias = QModelIndex | QPersistentModelIndex

__all__: Final = ()

_logger = logging.getLogger(__name__)


class SheetModel(QAbstractTableModel):
    section_span = Signal(int, int, int, int, arguments=['row', 'column', 'rowSpam', 'columnSpan'])

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.__pset_model: PropertySetModel | None = None

    @property
    def property_set_model(self) -> PropertySetModel | None:
        """Get the property set model this table is using"""

        return self.__pset_model

    @property_set_model.setter
    def property_set_model(self, model: PropertySetModel) -> None:
        """The property set model is a model-within-a-model which
        manages the expanded/unexpanded state of expandable
        property sets and handles the sorting of properties
        within a property set
        """

        if (old_model := self.__pset_model) == model:
            return

        if old_model is not None:
            old_model.listeners -= self.__property_set_model_changed

        self.__pset_model = model
        self.__pset_model.listeners += self.__property_set_model_changed

        # TODO: Notify (who?) table change

    @contextmanager
    def __property_set_model_changed(
        self,
        source: PropertySetModel,
        type: PropertySetModelChangeType,
        start: int,
        end: int,
        *,
        reordering: bool,
    ) -> Iterator[None]:
        print(
            f'>!>!>!> property set model changed: {type = }, {start = }, {end = }, {reordering = }',
        )

        with ExitStack() as on_exit:
            match type:
                case PropertySetModelChangeType.WholesaleChange:
                    self.beginResetModel()
                    on_exit.callback(self.endResetModel)
                    yield

                    for i in range(source.count):
                        if not source.is_property(i):
                            self.section_span.emit(i, 0, 1, 2)

                case PropertySetModelChangeType.Insert:
                    pass

                case PropertySetModelChangeType.Remove:
                    pass

    # Qt interface

    @override  # QAbstractTableModel
    def rowCount(self, parent: ModelIndex | None = None) -> int:
        if (pset_model := self.__pset_model) is None:
            return 0

        return pset_model.count

    @override  # QAbstractTableModel
    def columnCount(self, parent: ModelIndex | None = None) -> int:
        # assert parent is not None
        return 2

    # @override  # QAbstractTableModel
    # def headerData(
    #     self,
    #     section: int,
    #     orientation: Qt.Orientation,
    #     role: int = Qt.ItemDataRole.DisplayRole,
    # ) -> Any:
    #     print(f'headerData {section=}, {orientation=}, role={Qt.ItemDataRole(role)=}')

    #     return None

    #     # if role != Qt.ItemDataRole.DisplayRole:
    #     #     return None

    #     # if section == 0:
    #     #     return 'Names'
    #     # elif section == 1:
    #     #     return 'Values'
    #     # else:
    #     #     return None

    @override  # QAbstractTableModel
    def data(self, proxyIndex: ModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        print(f'data {proxyIndex=}, role={Qt.ItemDataRole(role)=}')

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            pset_model = self.__pset_model
            assert pset_model is not None
            row = proxyIndex.row()
            fd = pset_model.get_feature_descriptor(row)
            assert fd is not None

            if proxyIndex.column() == 0:
                return fd.display_name
            elif pset_model.is_property(row):
                return cast('Property[Any]', fd).value
            else:
                return None

        return None

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
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

# Third-party imports
from lookups import Lookup
from typing_extensions import Self, override

# Local imports
from openide.nodes._refactor1 import ChildNode, Children, Node, NodeHandle, ParentNode

if TYPE_CHECKING:
    from PySide6.QtGui import QAction, QColor, QIcon, QPixmap

    from openide.nodes import PropertySet, Sheet


class MinimalNode(Node[ParentNode, ChildNode]):
    def __init__(
        self,
        children: Children[Self, ChildNode],
        lookup: Lookup | None = None,
        *,
        name: str | None = None,
    ) -> None:
        super().__init__(children=children, lookup=lookup)

        if name is not None:
            self.display_name = name

    @override
    def clone(self) -> Self:
        raise NotImplementedError

    @property
    @override
    def can_rename(self) -> bool:
        raise NotImplementedError

    @property
    @override
    def property_sets(self) -> Sequence[PropertySet]:
        raise NotImplementedError

    @property
    @override
    def sheet(self) -> Sheet:
        raise NotImplementedError

    @property
    @override
    def icon(self) -> QIcon | QPixmap | QColor:
        raise NotImplementedError

    @property
    @override
    def opened_icon(self) -> QIcon | QPixmap | QColor:
        raise NotImplementedError

    @property
    @override
    def help_context(self) -> Any:
        raise NotImplementedError

    @property
    @override
    def can_copy(self) -> bool:
        raise NotImplementedError

    @property
    @override
    def clipboard_copy(self) -> Any:
        raise NotImplementedError

    @property
    @override
    def can_cut(self) -> bool:
        raise NotImplementedError

    @property
    @override
    def clipboard_cut(self) -> Any:
        raise NotImplementedError

    @property
    @override
    def drag(self) -> Any:
        raise NotImplementedError

    @override
    def get_paste_types(self, transferable: Any) -> Any:
        raise NotImplementedError

    @override
    def get_drop_type(self, transferable: Any, action: QAction, index: int) -> Any:
        raise NotImplementedError

    @property
    @override
    def new_types(self) -> Any:
        raise NotImplementedError

    @property
    @override
    def has_customiser(self) -> bool:
        raise NotImplementedError

    @property
    @override
    def customiser(self) -> Any | None:
        raise NotImplementedError

    @property
    @override
    def handle(self) -> NodeHandle[Self] | None:
        raise NotImplementedError

    @property
    @override
    def can_destroy(self) -> bool:
        raise NotImplementedError

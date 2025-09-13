# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# From:   # noqa: E501

from __future__ import annotations

# System imports
from threading import RLock
from typing import TYPE_CHECKING, Any, Generic, Self, TypeAlias, TypeVar, final

# Third-party imports
from typing_extensions import override

# Local imports
from openide.lookup.cookie_set import Cookie, CookieSet
from openide.nodes._like_netbeans.children import Children
from openide.nodes._like_netbeans.node import AnyNode, Node
from openide.nodes.properties import Sheet

# from openide.nodes.sheet import Sheet
# from openide.nodes.default_handle import DefaultHandle


T = TypeVar('T')
if TYPE_CHECKING:
    from collections.abc import Sequence

    from lookups import Lookup
    from PySide6.QtGui import QAction, QColor, QIcon, QPixmap

    from openide.lookup.cookie_set import CookieSetChangeProtocol
    from openide.nodes._like_netbeans.properties import PropertySet

    Ck = TypeVar('Ck', bound=Cookie)

PN = TypeVar('PN', bound=AnyNode)
CN = TypeVar('CN', bound=AnyNode)
AnyGenericNode: TypeAlias = 'GenericNode[AnyNode, AnyNode]'


class GenericNode(Node[PN, CN]):
    # TODO: private static final
    # - icons
    # - ICON_BASE
    # - OPENED_ICON_BASE
    # - NO_PASTE_TYPES
    # - NO_NEW_TYPES
    # - DEFAULT_ICON_BASE
    # - DEFAULT_ICON_EXTENSION
    # - DEFAULT_ICON
    # - overridesGetDefaultAction

    @classmethod
    def with_cookie_set(cls, cookie_set: CookieSet) -> Self:
        node = cls(Children.LEAF)
        node.__cookie_set = cookie_set

        return node

    # TODO: AbstractNode(CookieSet set) constructor
    def __init__(self, children: Children[Self, CN], lookup: Lookup | None = None) -> None:
        self._lock = RLock()

        self._display_format: str | None = None

        # TODO:
        # self.__preferred_action: Optional[Action] = None
        # self.__icon_base = GenericNode.__DEFAULT_ICON_BASE
        self.__icon_extension = '.png'

        self.__cookie_set: CookieSet | None = None
        self.__sheet: Sheet | None = None

        # TODO:
        # self._system_actions: Optional[Sequence[SystemAction]] = None  # deprecated

        self.__sheet_cookie_listener: _SheetAndCookieListener[PN, CN] | None = None

        super().__init__(children, lookup)

        super(GenericNode, type(self)).system_name.fset(self, '')

    # TODO: Cloning stuff

    # Needed as it is abstract in Node
    @override  # Node
    def clone(self) -> Self:
        raise NotImplementedError  # TODO

    @Node.system_name.setter  # type: ignore[attr-defined]  # mypy bug #5936
    @override  # Node
    def system_name(self, value: str | None) -> None:
        super(GenericNode, type(self)).system_name.fset(self, value)

        if (disp_format := self._display_format) is not None:
            # TODO: Review teh whole display format thing to be more user-friendly:
            # - Should have a setter that automatically change display_name with the new formatter
            # - Should be able to take either more named parameters (but taken from where),
            #   or maybe just be a user-controlled callback all by itself
            self.display_name = disp_format.format(value)
        else:
            self._fire_own_property_change('display_name', None, None)

    # TODO (or not, deprecated): setIconBase

    # TODO: Use pathlib instead
    @final
    def set_icon_base_with_extension(
        self,
        base: str,
        extension: str | None = None,
    ) -> None:
        if extension is None:
            try:
                last_dot = base.rindex('.')
            except ValueError:
                last_dot = -1

            try:
                last_slash = base.rindex('/')
            except ValueError:
                last_slash = -1

            if (last_slash > last_dot) or (last_dot == -1):
                extension = ''
            else:
                base, extension = base[:last_dot], base[last_dot:]

        if (base == self.__icon_base) and (extension == self.__icon_extension):
            return

        self.__icon_base = base
        self.__icon_extension = extension
        self._fire_own_property_change('icon', None, None)
        self._fire_own_property_change('opened_icon', None, None)

    # TODO: Input type parameter
    @property
    @override  # Node
    def icon(self) -> QIcon | QPixmap | QColor:
        from PySide6.QtGui import QIcon  # noqa: PLC0415

        icon = QIcon()
        icon.addPixmap(QIcon.fromTheme('folder').pixmap(256), QIcon.Mode.Normal, QIcon.State.Off)
        icon.addPixmap(
            QIcon.fromTheme('folder-open').pixmap(256),
            QIcon.Mode.Normal,
            QIcon.State.On,
        )
        return icon
        # return self.__find_icon(GenericNode.ICON_BASE)

    # TODO: Input type parameter
    @property
    @override  # Node
    def opened_icon(self) -> QIcon | QPixmap | QColor:
        return self.__find_icon(GenericNode.OPENED_ICON_BASE)

    # TODO: Implement
    # TODO: Define return type
    @property
    @override  # Node
    def help_context(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    # TODO: Input type parameter
    # TODO: Type of input ib parameter
    # TODO: Implement
    def __find_icon(self, type, ib) -> QIcon | QPixmap | QColor:
        raise NotImplementedError

    # TODO: Implement
    # TODO: Define return type
    @property
    def _default_icon(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    @property
    @override  # Node
    def can_rename(self) -> bool:
        return False

    @property
    @override  # Node
    def can_destroy(self) -> bool:
        return False

    def _create_sheet(self) -> Sheet:
        from openide.nodes import SheetSupport  # noqa: PLC0415

        return SheetSupport()

    @final
    def __set_sheet_implementation(self, sheet: Sheet) -> None:
        with self._lock:
            # TODO: Figure out listeners of sheet
            # if (listener := self.__sheet_cookie_listener) is None:
            #     listener = self.__sheet_cookie_listener = _SheetAndCookieListener(self)

            # if sheet is not None:
            #     sheet.remove_property_change_listener(listener)

            # sheet.add_property_change_listener(listener)
            self.__sheet = sheet

    @property
    def _sheet(self) -> Sheet:
        if (sheet := self.__sheet) is not None:
            return sheet

        sheet = self._create_sheet()
        if sheet is None:
            msg = f'create_sheet returns None in {type(self).__name__}'
            raise RuntimeError(msg)

        self.__set_sheet_implementation(sheet)

        return sheet

    @_sheet.setter
    def _sheet(self, sheet: Sheet) -> None:
        with self._lock:
            self.__set_sheet_implementation(sheet)
            self._fire_own_property_change('property_sets', None, None)

    # TODO: Maybe define an iterator in Sheet
    # and let caller (eg. the following function) use a list, or a tuple, or whatever.
    @property
    @override  # Node
    def property_sets(self) -> Sequence[PropertySet]:
        return self._sheet.to_list()

    # Temp. addition not in Netbeans to directly access the Sheet, because this "public should
    # only access a list of PropertySet and not the Sheet itself" just seems like
    # some whatever Java-trust-issue madness...
    @property
    def sheet(self) -> Sheet:
        return self._sheet

    @property
    @override  # Node
    def _property_sets_are_known(self) -> bool:
        return self.__sheet is not None

    # TODO: Implement
    # TODO: Define return type
    @property
    @override  # Node
    def clipboard_copy(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    # TODO: Implement
    # TODO: Define return type
    @property
    @override  # Node
    def clipboard_cut(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    # TODO: Define return type
    @property
    @override  # Node
    def drag(self):  # type: ignore[no-untyped-def]
        return self.clipboard_copy()

    @property
    @override  # Node
    def can_copy(self) -> bool:
        return True

    @property
    @override  # Node
    def can_cut(self) -> bool:
        return False

    # TODO: createPasteTypes (protected)

    # TODO: Implement
    # TODO: Define return type
    @final
    @override  # Node
    def get_paste_types(self, transferable):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    # TODO: Implement
    # TODO: Define return type
    @override  # Node
    def get_drop_type(self, transferable, action, index: int):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    # TODO: Implement
    # TODO: Define return type
    @property
    @override  # Node
    def new_types(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    # # TODO: Implement
    # # TODO: Define return type
    # @property
    # @override  # Node
    # def preferred_action(self) -> QAction | None:
    #     raise NotImplementedError

    # # TODO: Implement
    # # TODO: Define return type
    # # TODO: Actually deprecated
    # @property
    # @override  # Node
    # def default_action(self):  # type: ignore[no-untyped-def]
    #     raise NotImplementedError

    # # TODO: Actually deprecated
    # @default_action.setter
    # def default_action(self, action) -> None:  # type: ignore[no-untyped-def]
    #     self.__preferred_action = action

    # # TODO: Implement
    # # TODO: Define return type
    # # TODO: Actually deprecated
    # @property
    # @override  # Node
    # def actions(self) -> Iterable[QAction | str | None]:
    #     raise NotImplementedError

    # TODO: createActions (deprecated) (protected)

    @property
    @override  # Node
    def has_customiser(self) -> bool:
        return False

    # TODO: Define return type
    @property
    @override  # Node
    def customiser(self):  # type: ignore[no-untyped-def]
        return None

    @override  # Node
    def get_cookie(self, cls: type[Ck]) -> Ck | None:
        if (cookie_set := self.__cookie_set) is not None:
            return cookie_set.get_cookie(cls)
        else:
            return super().get_cookie(cls)

    @property
    @override  # Node
    def _supports_cookie_set(self) -> bool:
        return self.__cookie_set is not None

    # TODO: Review
    @property
    @override  # Node
    def _cookie_set(self) -> CookieSet:
        if self._internal_lookup is not None:
            msg = 'CookieSet cannot be used when lookup is associated with a node'
            raise RuntimeError(msg)

        # Optimistic check to avoid lock
        if (cookie_set := self.__cookie_set) is not None:
            return cookie_set

        with self._lock:
            # Re-check after lock
            if (cookie_set := self.__cookie_set) is None:
                # Use the setter has it does more things
                cookie_set = self._cookie_set = CookieSet()

            return cookie_set

    # TODO: Review
    # TODO: Actually deprecated (but used by _cookie_set getter)
    @_cookie_set.setter
    @override  # Node
    def _cookie_set(self, value: CookieSet) -> None:
        with self._lock:
            if self._internal_lookup is not None:
                msg = 'CookieSet cannot be used when lookup is associated with a node'
                raise RuntimeError(msg)

            if (listener := self.__sheet_cookie_listener) is None:
                listener = self.__sheet_cookie_listener = _SheetAndCookieListener(self)

            if (cookie_set := self.__cookie_set) is not None:
                cookie_set.listeners -= listener.state_changed

            value.listeners += listener.state_changed
            self.__cookie_set = value

            self._fire_cookie_change()

    @property
    @override  # Node
    def handle(self) -> Node.Handle:
        return DefaultHandle.create_handle(self)


# TODO: Extends java.beans.PropertyChangeListener
# TODO: Extends javax.swing.event.ChangeListener
@final
class _SheetAndCookieListener(Generic[PN, CN]):
    def __init__(self, node: GenericNode[PN, CN]) -> None:
        super().__init__()

        self.__node = node

    def property_change(self, event) -> None:  # type: ignore[no-untyped-def]
        self.__node._fire_own_property_change('property_sets', None, None)

    def state_changed(self, kind: CookieSetChangeProtocol.ChangeKind, cookie: object) -> None:
        self.__node._fire_cookie_change()


Node.EMPTY = GenericNode(Children.LEAF)

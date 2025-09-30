# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore disp nuitka javax
""""""

from __future__ import annotations

# System imports
import logging
from threading import RLock
from typing import TYPE_CHECKING, Generic, final

# Third-party imports
from typing_extensions import override

from openide.lookup.cookie_set import CookieSet, CookieSetChangeProtocol

# Local imports
from .children import Children
from .node import (
    ChildNode,
    Node,
    ParentNode,
    _NodeActionsInterface,
    _NodeBase,
    _NodeCopyMixin,
    _NodeCopyPasteDnDInterface,
    _NodeLookupAndCookieMixin,
    _NodePropertiesInterface,
    _NodeRepresentationInterface,
)

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence
    from typing import Any, ClassVar, Final

    from lookups import Lookup
    from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
    from typing_extensions import Self

    from openide.lookup.cookie_set import Ck
    from openide.nodes import PropertySet
    from openide.nodes.properties import Sheet

    from .node import NodeHandle

__all__: Final = (
    'GenericNode',
    'GenericNodeActions',
    'GenericNodeCopy',
    'GenericNodeCopyPasteDnD',
    'GenericNodeLookupAndCookie',
    'GenericNodeProperties',
    'GenericNodeRepresentation',
)

_logger = logging.getLogger(__name__)


class _GenericNodeLock:
    def __init__(self, **kwargs: Any) -> None:
        self._lock = RLock()

        super().__init__(**kwargs)


class GenericNodeActions(_NodeActionsInterface[ChildNode]):
    def __init__(self, **kwargs: Any) -> None:
        # TODO:
        self.__preferred_action: QAction | None = None
        # self._system_actions: Optional[Sequence[SystemAction]] = None  # deprecated

        super().__init__(**kwargs)

    # # TODO: Implement
    # def __overrides_a_method(self, name: str, arguments: Iterable[type[Any]]) -> bool:
    #     '''Checks whether subclass overrides a method.'''
    #     raise NotImplementedError

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


class GenericNodeCopy(_NodeCopyMixin):
    # Needed as it is abstract in Node
    @override  # Node
    def clone(self) -> Self:
        raise NotImplementedError  # TODO


class GenericNodeCopyPasteDnD(_NodeCopyPasteDnDInterface):
    #
    # Copy
    #
    @property
    @override  # _NodeCopyPasteDnDInterface
    def can_copy(self) -> bool:
        return True

    # TODO: Implement
    @property
    @override  # _NodeCopyPasteDnDInterface
    def clipboard_copy(self) -> Any:
        raise NotImplementedError

    #
    # Cut
    #

    @property
    @override  # _NodeCopyPasteDnDInterface
    def can_cut(self) -> bool:
        return False

    # TODO: Implement
    @property
    @override  # _NodeCopyPasteDnDInterface
    def clipboard_cut(self) -> Any:
        raise NotImplementedError

    #
    # Drag'n'Drop
    #

    @property
    @override  # _NodeCopyPasteDnDInterface
    def drag(self) -> Any:
        """This implementation only calls `clipboard_copy()`, supposing that copy
        to clipboard and copy by DnD are similar."""

        return self.clipboard_copy()

    def _create_paste_types(self, transferable: Any, types: list[Any]) -> None:
        """Accumulate the paste types that this node can handle for a given transferable.

        The default implementation simply tests whether the transferable supports
        intelligent pasting via `NodeTransfer.find_paste()`, and if so, it obtains
        the paste types from the NodeTransfer.Paste transfer data, and inserts
        them into the set.

        Subclass implementations should typically call super (first or last), so
        that they add to, rather tha replace, a superclass' available paste types.
        Especially as the default implementation in GenericNode is generally
        desirable to retain.

        Args:
            transferable: A transferable containing clipboard data.
            types: A list of PastTypes that will have added to it all types valid
                   for this node (ordered as they will be presented to the user).
        """
        raise NotImplementedError

    @override  # _NodeCopyPasteDnDInterface
    def get_paste_types(self, transferable: Any) -> Any:
        raise NotImplementedError

    @override  # _NodeCopyPasteDnDInterface
    def get_drop_type(self, transferable: Any, action: QAction, index: int) -> Any:
        raise NotImplementedError

    @property
    @override  # _NodeCopyPasteDnDInterface
    def new_types(self) -> Any:
        raise NotImplementedError


class GenericNodeLookupAndCookie(
    _GenericNodeLock,
    _NodeLookupAndCookieMixin[ChildNode],
    Generic[ParentNode, ChildNode],
):
    def __init__(self, **kwargs: Any) -> None:
        self.__cookie_set: CookieSet | None = None
        """Array of cookies for this node."""
        self.__sheet_cookie_listener: _SheetAndCookieListener[ParentNode, ChildNode] | None = None

        super().__init__(**kwargs)

    @override  # _NodeLookupAndCookieMixin
    def get_cookie(self, cls: type[Ck]) -> Ck | None:
        if (cookie_set := self.__cookie_set) is not None:
            return cookie_set.get_cookie(cls)
        else:
            return super().get_cookie(cls)

    @property
    @override  # _NodeLookupAndCookieMixin
    def _supports_cookie_set(self) -> bool:
        return self.__cookie_set is not None

    @property
    @override  # _NodeLookupAndCookieMixin
    def _cookie_set(self) -> CookieSet:
        """The cookie set.

        Returns:
            The cookie set set with the setter, or an empty set (never None).
        """

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

    @_cookie_set.setter
    @override  # _NodeLookupAndCookieMixin
    def _cookie_set(self, value: CookieSet) -> None:
        """Set the cookie set.

        A listener is attached to the provided cookie set, and any change of the
        sheet is propagated to the node by firing PROP_COOKIE change events.

        Note: Deprecated. You might as well do `node._cookie_set.add()` instead.
        """
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


class GenericNodeProperties(_GenericNodeLock, _NodePropertiesInterface[ChildNode]):
    def __init__(self, **kwargs: Any) -> None:
        self._display_format: str | None = None
        """Message format to use for creation of the display name.

        It permits conversion of text from `system_name` property to the one sent
        to `display_name` property. The format can take one parameter, which will
        be filled by a value from `system_name`.

        The default format just uses the simple `system_name`. Subclasses may
        change it, though it will not take effect until the next time `system_name`
        property setter is called.

        Can be set to None. The there is no connection between the system name and
        display name; they may be independently modified.
        """

        self.__sheet: Sheet | None = None
        """Set of properties to use."""

        super().__init__(**kwargs)

    @Node.system_name.setter  # type: ignore[attr-defined]  # mypy bug #5936
    @override  # Node
    def system_name(self, value: str | None) -> None:
        self._super_property_setter(GenericNodeProperties, 'system_name', value)

        if (disp_format := self._display_format) is not None:
            # TODO: Review teh whole display format thing to be more user-friendly:
            # - Should have a setter that automatically change display_name with the new formatter
            # - Should be able to take either more named parameters (but taken from where),
            #   or maybe just be a user-controlled callback all by itself
            self.display_name = disp_format.format(value)
        else:
            # Additional hack, because if no display name is set, then it is taken
            # from the `system_name` property. That means calling setter of
            # `system_name` can also change display_name.
            self._fire_own_property_change('display_name', None, None)

    @property
    @override  # Node
    def can_rename(self) -> bool:
        return False

    def _create_sheet(self) -> Sheet:
        """Initialise a default property sheet.

        Commonly overridden. If `sheet` property is called, and there is not yet
        a sheet, this method is called to allow a subclass to specify its properties.

        WARNING: Do not call `sheet` property getter in this method.

        The default implementation returns an empty sheet.

        Returns:
            The sheet with initialised values (and should never return None).
        """

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
        if sheet is None:  # pyright: ignore[reportUnnecessaryComparison]
            msg = f'create_sheet returns None in {type(self).__name__}'
            raise RuntimeError(msg)

        self.__set_sheet_implementation(sheet)

        return sheet

    @_sheet.setter
    def _sheet(self, sheet: Sheet) -> None:
        """Sets the set of properties.

        A listener is attached to the provided sheet, and any change of the sheet
        is propagated to the node by firing a PROP_PROPERTY_SETS change event.
        """

        with self._lock:
            self.__set_sheet_implementation(sheet)
            self._fire_own_property_change('property_sets', None, None)

    # TODO: Maybe define an iterator in Sheet
    # and let caller (eg. the following function) use a list, or a tuple, or whatever.
    @property
    @override  # Node
    def property_sets(self) -> Sequence[PropertySet]:
        return list(self._sheet.property_sets)

    @property
    @override  # Node
    def _property_sets_are_known(self) -> bool:
        return self.__sheet is not None

    @property
    @override  # _NodePropertiesInterface
    def sheet(self) -> Sheet:
        return self._sheet


class GenericNodeRepresentation(
    _GenericNodeLock,
    _NodeRepresentationInterface,
    _NodeBase[ChildNode],
):
    # TODO: Actually implement the real stuffs. These are just stubs to get a
    # basic default behaviour. That does not even match the docstrings.
    # Would need to figure out:
    # - How Qt can handle the various cases of icons: user provided, as well as
    #   the default packs it can access itself using specific mnemonics.
    # - How to properly load user provided ones as either importlib.resources
    #   ones, or Qt own resource system.
    # - How all of that would play with application packagers (Nuitka, pyinstaller).
    # - Qt embedded the notion of various flavours of icons directly in QIcon itself
    #   using "State". This can replace the weird array (here a tuple) used as a
    #   map with int indices. This would at least be an enum with proper member
    #   names. And at best replace with something that can map to Qt's icon states.

    # __DEFAULT_ICON_BASE: ClassVar = 'openide.nodes.default_node'
    __DEFAULT_ICON_BASE: ClassVar = ''
    __DEFAULT_ICON_EXTENSION: ClassVar = '.gif'
    __DEFAULT_ICON: ClassVar = f'{__DEFAULT_ICON_BASE}.png'

    __icons: ClassVar = (
        '',  # Color 16x16
        '32',  # Color 32x32
        '',  # Mono 16x16
        '32',  # Mono 32x32
        'Open',  # Opened color 16x16
        'Open32',  # Opened color 32x32
        'Open',  # Opened mono 16x16
        'Open32',  # Opened mono 32x32
    )
    __ICON_BASE: ClassVar = -1
    __OPENED_ICON_BASE: ClassVar = 3

    def __init__(self, **kwargs: Any) -> None:
        self.__icon_base = self.__DEFAULT_ICON_BASE
        """Resource base for icons (without suffix denoting right icon)."""
        self.__icon_extension = '.png'
        """Resource extension for icons."""

        super().__init__(**kwargs)

    # TODO (or not, deprecated): setIconBase

    # TODO: Use pathlib instead
    @final
    def set_icon_base_with_extension(
        self,
        base: str,
        extension: str | None = None,
    ) -> None:
        """Change the icon.

        One need only specify the base resource name without extension. The real
        name of the icon is obtained by inserting proper infixes into the resource
        name.

        For example, for the base "foo.resource.MyIcon.png", the following images
        may be used according to the icon state:
        - "foo.resource.MyIcon.png"
        - "foo.resource.MyIconOpen.png"
        - "foo.resource.MyIcon32.png"
        - "foo.resource.MyIconOpen32.png"

        This method may be used to dynamically switch between different sets of
        icons for different configurations. If the set is changed, an icon property
        change event is fired.
        """

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

    def get_icon(self, type: int) -> QIcon | QPixmap | QColor:
        return self.__find_icon(type, self.__ICON_BASE)

    # TODO: Input type parameter
    @property
    @override  # Node
    def opened_icon(self) -> QIcon | QPixmap | QColor:
        raise NotImplementedError

    def get_opened_icon(self, type: int) -> QIcon | QPixmap | QColor:
        return self.__find_icon(type, self.__OPENED_ICON_BASE)

    # TODO: Input type parameter
    # TODO: Type of input ib parameter
    # TODO: Implement
    def __find_icon(self, type: int, ib: int) -> QIcon | QPixmap | QColor:
        """Tries to find the right icon for the iconbase.

        Args:
            type: Type of icon.
            ib: Base where to scan in the array.
        """
        _ = self.__icon_base + self.__icons[type + ib] + self.__icon_extension
        raise NotImplementedError

    # TODO: Implement
    # TODO: Define return type
    @property
    def _default_icon(self) -> QIcon | QPixmap | QColor:
        raise NotImplementedError

    # TODO: Implement
    # TODO: Define return type
    @property
    @override  # Node
    def help_context(self) -> Any:
        raise NotImplementedError


class GenericNode(
    GenericNodeCopy,
    GenericNodeActions[ChildNode],
    GenericNodeCopyPasteDnD,
    GenericNodeRepresentation[ChildNode],
    GenericNodeLookupAndCookie[ParentNode, ChildNode],
    GenericNodeProperties[ChildNode],
    _GenericNodeLock,
    Node[ParentNode, ChildNode],
    Generic[ParentNode, ChildNode],
):
    """A basic implementation of a Node.

    It simplifies creation of the display name, based on a message format and the
    system name. It also simplifies working with icons: one need only specify the
    base name and all icons will be loaded when needed. Other common requirements
    are handled as well.

    Args:
        ParentNode: The type of this node parent node.
        ChildNode: The type of child nodes this node have.
    """

    # TODO: private static final
    # - NO_PASTE_TYPES
    # - NO_NEW_TYPES
    # - overridesGetDefaultAction

    # TODO: Cloning stuff

    def __init__(self, children: Children[Self, ChildNode], lookup: Lookup | None = None) -> None:
        super().__init__(children=children, lookup=lookup)

        # Setting the system_name to non-None value for the node to return
        # "reasonable" system_name and display_name.
        # Not using self.system_name to set it because subclasses can override
        # it, and they might assume that it is not called from constructor.
        self._super_property_setter(GenericNodeProperties, 'system_name', '')

    @classmethod
    def with_cookie_set(cls, cookie_set: CookieSet) -> Self:
        """Initialise a node using the given CookieSet.

        The default hierarchy is Children.LEAF.
        """

        node = cls(Children.LEAF)
        node.__cookie_set = cookie_set

        return node

    @property
    @override  # Node
    def can_destroy(self) -> bool:
        return False

    @property
    @override  # Node
    def has_customiser(self) -> bool:
        return False

    # TODO: Define return type
    @property
    @override  # Node
    def customiser(self) -> Any | None:
        return None

    @property
    @override  # Node
    def handle(self) -> NodeHandle[Self] | None:
        raise NotImplementedError
        # return DefaultHandle.create_handle(self)


# TODO: Extends java.beans.PropertyChangeListener
# TODO: Extends javax.swing.event.ChangeListener
@final
class _SheetAndCookieListener(Generic[ParentNode, ChildNode]):
    """Listener for changes in the sheet and the cookie set."""

    def __init__(self, node: GenericNodeLookupAndCookie[ParentNode, ChildNode]) -> None:
        super().__init__()

        self.__node = node

    def property_change(self, event: Any) -> None:
        self.__node._fire_own_property_change('property_sets', None, None)

    def state_changed(self, kind: CookieSetChangeProtocol.ChangeKind, cookie: object) -> None:
        self.__node._fire_cookie_change()


Node.EMPTY = GenericNode(Children.LEAF)

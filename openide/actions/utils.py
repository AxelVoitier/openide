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
from typing import TYPE_CHECKING

# Third-party imports
from PySide6.QtWidgets import QMenu

# Local imports
from openide.actions import ContextAwareAction
from openide.actions.transformers import ContextMenuPresenter

if TYPE_CHECKING:
    from collections.abc import Iterable

    from lookups import Lookup
    from PySide6.QtGui import QAction


_logger = logging.getLogger(__name__)


def actions_to_context_menu(actions: Iterable[QAction | str | None], context: Lookup) -> QMenu:
    """Builds a context menu from actions for a provided context.

    Takes a list of actions, and for actions that are instance of ContextAwareAction
    creates and uses the context aware instance.

    Then, if the action is an instance of ContextMenuPresenter, transform the it
    through the presenter. Otherwise the action will be inserted as is in the menu.

    The list of actions can also contains None, or strings. A None leads to inserting
    a separator in the menu. While a string inserts a section (which is basically
    a separator with a text hint).

    actions: Iterable of actions to build the menu with. Can contain None or strings
             elements, which will be replaced by separator or section.
    context: The context for which the popup is built.

    Returns the constructed context menu.
    """

    added: set[QAction] = set()
    items: list[QAction | str | None] = []

    for action in actions:
        if (action is None) or isinstance(action, str) or (action in added):
            items.append(action)
        else:
            added.add(action)

            if isinstance(action, ContextAwareAction):
                action = action.create_context_aware_instance(context)  # noqa: PLW2901

            if isinstance(action, ContextMenuPresenter):
                action = action.get_context_menu_presenter()  # noqa: PLW2901

            items.append(action)

    # TODO: Netbeans is having a "convoluted" way to let users customise the class used
    # to build a menu. We might consider it at some point, if need be.
    # Basically, there is an ActionPresenterProvider abstract class, for which a getDefault()
    # method search on the default Lookup an implementation of ActionPresenterProvider
    # (and only care about the first one returned), and if None, returns a default implementation.
    # That default implementation would then just return a standard QMenu.
    # And other implementations would customise that by registering them on the default lookup.
    # Note that ActionPresenterProvider also have methods to get menu/popup/toolbar presenters,
    # or to convert "components". However, that's because Java swing Actions are not actually,
    # directly usable in a JMenu, and require an intermediate JMenuItem. But in Qt there
    # is not such intermediate item/"presenter" object existing, and it's the QMenu
    # that decides how to present actions. Hence, here we would only need to cover the need
    # to customise QMenu, and none of these intermediate presenter items.
    # Also, Qt does not differentiate between a context menu and a window menu, unlike
    # Java Swing JMenu and JPopupMenu.
    menu = QMenu()
    for item in items:
        if item is None:
            menu.addSeparator()

        elif isinstance(item, str):
            # TODO: Find a way to support a section with an icon?
            # Or just let callee provide a QAction with isSeparator, text hint, and icon.
            menu.addSection(item)

        else:
            menu.addAction(item)

    return menu

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
from typing import TYPE_CHECKING

# Third-party imports
from PySide6.QtGui import QAction

# Local imports
from openide.utils import MetaClassResolver

if TYPE_CHECKING:
    from lookups import Lookup

_logger = logging.getLogger(__name__)


class ContextAwareAction(MetaClassResolver(QAction, ABC)):
    """Interface to be implemented by an action whose behaviour is dependent on some context.

    The action created by create_context_aware_instance() is bound to the provided context:
    isEnabled(), activate(), etc. may be specific to that context.

    For example, the action representing a context menu item will usually implement
    this interface. When the actual context menu is created, rather than making a
    presenter for the generic action, the menu will contain a presenter for the
    context-aware instance. The context will then be taken from the GUI environment
    where the context menu was shown; for example, it may be a TopComponent's context
    (using TopComponent.get_lookup()) ofthen taken from an activated node selection.
    The context action might be enabled only if a certain "cookie" is present in
    that selection. When invoked, the action need not search for an object to act on,
    since it can use the context.
    """

    @abstractmethod
    def create_context_aware_instance(self, context: Lookup) -> QAction:
        """Creates action instance for provided context.

        context: An arbitrary context (ie. lookup).

        Returns a transient action whose behaviour applies only to that context."""
        raise NotImplementedError


class MenuPresenter(MetaClassResolver(QAction, ABC)):
    """Presenter interface for presenting an action in a windown menu"""

    @abstractmethod
    def get_menu_presenter(self) -> QAction:
        """Get an action that can present this action in a QMenu used as a window menu"""
        raise NotImplementedError


class ContextMenuPresenter(MetaClassResolver(QAction, ABC)):
    """Presenter interface for presenting an action in a popup menu"""

    @abstractmethod
    def get_context_menu_presenter(self) -> QAction:
        """Get an action that can present this action in a QMenu used as a context menu"""
        raise NotImplementedError


class ToolbarPresenter(MetaClassResolver(QAction, ABC)):
    """Presenter interface for presenting an action in a toolbar"""

    @abstractmethod
    def get_toolbar_presenter(self) -> QAction:
        """Get an action that can present this action in a toolbar"""
        raise NotImplementedError

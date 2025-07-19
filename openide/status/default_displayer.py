# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore qmain
""""""

from __future__ import annotations

# System imports
import logging
import time
from math import inf, isinf
from typing import TYPE_CHECKING, cast

# Third-party imports
from PySide6.QtCore import QObject, Signal, Slot
from typing_extensions import override

# Local imports
from openide.services import ServiceProvider, StatusDisplayer, WindowManager
from openide.utils import MetaClassResolver

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow, QStatusBar

_logger = logging.getLogger(__name__)


@ServiceProvider(service=StatusDisplayer)
class DefaultStatusDisplayer(MetaClassResolver(StatusDisplayer, QObject)):
    def __init__(self) -> None:
        super().__init__()

        self.__current_messages: dict[str, tuple[StatusDisplayer.Importance, float]] = {}
        """Our queue of pending messages.

        Dict of message string to tuple of (importance, timeout_at),
        with timeout_at being "absolute" (ie. relative to the 0 of time.monotonic()).
        For message with no timeout, timeout_at is +inf.
        """

        self.__current_message: str | None = None
        """The currently displayed message.

        Used to keep track of which message to delete from our pending list when
        a message gets cleared.
        """

        self.__show_message_signal.connect(self.__show_message)
        self._status_bar.messageChanged.connect(self.__message_changed)

    def __message_changed(self, message: str) -> None:
        """Callback for messageChanged signal of the status bar.

        If the message have been cleared, we remove it from the list of pending messages.
        """

        if not message:
            if self.__current_message in self.__current_messages:
                del self.__current_messages[self.__current_message]
                self.__current_message = None

            self.__pick_and_show_message()

        else:
            self.__current_message = message

    def __purge_outdated(self) -> None:
        """Go through the list of pending messages, and trim all the outdated ones."""

        now = time.monotonic()
        self.__current_messages = {
            message: details
            for message, details in self.__current_messages.items()
            if details[1] > now
        }

    def __pick_a_message(self) -> tuple[str | None, StatusDisplayer.Importance | int, float]:
        """Pick the next message to be displayed, if any.

        Priority ordering is given by the importance value (the lower the more important),
        then the timeout_at value (message set to expire earlier are more important),
        and finally the lexicographic order of the messages themselves.

        Will purge outdated message beforehand.

        Returns the message, its importance, and its timeout_at value if any.
        Otherwise returns a (None, 0, 0) tuple.
        """

        self.__purge_outdated()
        for message, (importance, timeout_at) in sorted(
            self.__current_messages.items(),
            key=lambda item: (*item[1], item[0]),
        ):
            if message == self.__current_message:
                return None, 0, 0
            else:
                return message, importance, timeout_at

        return None, 0, 0

    def __pick_and_show_message(self) -> None:
        """Pock and show the next message to be displayed, if any.

        Priority ordering is given by the importance value (the lower the more important),
        then the timeout_at value (message set to expire earlier are more important),
        and finally the lexicographic order of the messages themselves.

        Will purge outdated message beforehand.

        Also handle painting the message differently based on its importance.
        """

        message, importance, timeout_at = self.__pick_a_message()
        if message is None:
            return
        timeout = 0 if isinf(timeout_at) else timeout_at - time.monotonic()

        # TODO: How to not hardcode that and somehow comply with a future app-wide
        # stylesheet/theme?
        if importance == StatusDisplayer.Importance.ERROR:
            self._status_bar.setStyleSheet('QStatusBar {color: red}')
        elif importance == StatusDisplayer.Importance.WARNING:
            self._status_bar.setStyleSheet('QStatusBar {color: yellow}')
        elif importance == StatusDisplayer.Importance.DEBUG:
            self._status_bar.setStyleSheet('QStatusBar {color: gray}')
        else:
            self._status_bar.setStyleSheet('')

        self._status_bar.showMessage(message, timeout=round(timeout * 1000))

    def __add_message(
        self,
        message: str,
        importance: StatusDisplayer.Importance,
        timeout: float,
    ) -> None:
        """Adds a message to the queue.

        Handles computing the absolute timeout_at time from the given relative timeout.
        """

        timeout_at = time.monotonic() + timeout if timeout else +inf
        self.__current_messages[message] = (importance, timeout_at)

    @property
    def _status_bar(self) -> QStatusBar:
        """Returns the status bar from the current main window"""

        return cast('QMainWindow', WindowManager()).statusBar()

    @override
    def show_message(
        self,
        message: str,
        importance: StatusDisplayer.Importance = StatusDisplayer.Importance.NORMAL,
        timeout: float | None = None,
    ) -> None:
        # Need to emit an actual float value for timeout as Qt does not seem to like a None
        if timeout is None:
            timeout = importance.default_timeout

        self.__show_message_signal.emit(message, importance, timeout)

    __show_message_signal = Signal(
        str,
        StatusDisplayer.Importance,
        float,
        arguments=['message', 'importance', 'timeout'],
    )

    @Slot()
    def __show_message(
        self,
        message: str,
        importance: StatusDisplayer.Importance,
        timeout: float,
    ) -> None:
        if importance == StatusDisplayer.Importance.ERROR:
            _logger.error(message)
        elif importance == StatusDisplayer.Importance.WARNING:
            _logger.warning(message)
        elif importance == StatusDisplayer.Importance.DEBUG:
            _logger.debug(message)
        else:
            _logger.info(message)

        timeout = max(0, timeout)  # Cap negative values to 0

        self.__add_message(message, importance, timeout)
        self.__pick_and_show_message()

    @override
    def clear_message(self, message: str | None = None) -> None:
        if message is not None:
            self.__current_messages.pop(message, None)
            if self.__current_message != message:
                return

        self._status_bar.clearMessage()  # Will trigger displaying another message, if any

    @override
    def clear_all_messages(self) -> None:
        self.__current_messages.clear()
        self._status_bar.clearMessage()

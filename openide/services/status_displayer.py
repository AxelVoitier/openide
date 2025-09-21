# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from abc import abstractmethod
from enum import IntEnum
from typing import TYPE_CHECKING

# Third-party imports
# Local imports
from openide.services.registration import ServiceSingletonABCMeta

if TYPE_CHECKING:
    from typing import Final

__all__: Final = ('StatusDisplayer',)


class StatusDisplayer(metaclass=ServiceSingletonABCMeta):
    class Importance(IntEnum):
        """Importance of a status message.

        Lower number = higher priority.
        """

        DEBUG = 10000
        NORMAL = 1000
        WARNING = 500
        ERROR = 100

        @property
        def default_timeout(self) -> float:
            cls = type(self)
            if self in (cls.ERROR, cls.WARNING):
                return 10
            else:
                return 5

    @abstractmethod
    def show_message(
        self,
        message: str,
        importance: StatusDisplayer.Importance = Importance.NORMAL,
        timeout: float | None = None,
    ) -> None:
        """Show a message in the status area.

        importance: Message with higher importance (lower number) will be displayed before
        less important ones, until removed.
        timeout: How long in seconds should the message stay. If 0, stays until manually cleared.
                 If None, automatically set a default one based on importance.
        """
        raise NotImplementedError

    @abstractmethod
    def clear_message(self, message: str | None = None) -> None:
        """Remove the current message.

        If other messages are waiting to be displayed, another message will be shown.

        message: If a message is given, it first checks it corresponds to the currently
                 displayed one before clearing it. If not, does nothing.
        """
        raise NotImplementedError

    @abstractmethod
    def clear_all_messages(self) -> None:
        """Remove all current and pending messages."""
        raise NotImplementedError

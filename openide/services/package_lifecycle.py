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
# Third-party imports
from typing_extensions import override

# Local imports
from openide.services import ServiceSingletonABCMeta


class PackageLifecycle(metaclass=ServiceSingletonABCMeta):
    NAME: str

    # Currently we don't even manage directly what is loaded (ie. on Python PATH).
    # So, that one is pointless for now.
    # def validate(self) -> bool:
    #     return True

    def restored(self) -> None:
        pass

    def closing(self) -> bool:
        return True

    def close(self) -> None:
        pass

    @override  # object
    def __str__(self) -> str:
        return self.NAME

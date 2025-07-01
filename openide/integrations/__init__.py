# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# /!\ Be careful of what is included here (in terms of third-party dependencies),
# as this gets imported during the integration/setup hooks.

from __future__ import annotations

# System imports
from typing import TYPE_CHECKING

# Third-party imports
# Local imports

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, Protocol, TypeVar

    from openide.utils import RecursiveDict
    from openide.utils.classes import ClassDecorator

    C = TypeVar('C', bound=type)

    class SetupDecorator(Protocol):
        # openide_setup: str

        def __call__(self, *args: Any, **kwargs: Any) -> ClassDecorator: ...

    class ConfigDecorator(Protocol):
        def __call__(
            self,
            *args: Any,
            _config: RecursiveDict | None = None,
            **kwargs: Any,
        ) -> ClassDecorator: ...


def mark_setup(
    mark: str,
    # *,
    # is_static: bool = True,
) -> Callable[[SetupDecorator], SetupDecorator]:
    """Function decorator intended to mark the decorated function as one that participate in
    OpenIDE setup system."""

    def _inner(
        # func: SetupDecorator | staticmethod[..., ClassDecorator],
        func: SetupDecorator,
    ) -> SetupDecorator:  # | staticmethod[..., ClassDecorator]:
        func.openide_setup = mark
        # if is_static:
        #     return staticmethod(func)
        # else:
        #     return func
        return func

    return _inner

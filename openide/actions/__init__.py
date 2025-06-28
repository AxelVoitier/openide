# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
import dataclasses
from typing import TYPE_CHECKING

# Third-party imports
# Local imports
from openide.integration import mark_setup
from openide.utils import class_decorator

if TYPE_CHECKING:
    from openide.utils.classes import ClassDecorator
    from openide.utils.datastructures import RecursiveDict


@dataclasses.dataclass
class ActionReference:
    path: str
    position: int = -1
    separator_before: bool = False
    separator_after: bool = False


class Actions:
    @staticmethod
    @mark_setup('config')
    def Registration(  # noqa: N802
        references: list[ActionReference],
        _config: RecursiveDict | None = None,
    ) -> ClassDecorator:
        if _config is not None:
            _config.merge(
                dict(
                    actions=[
                        dict(
                            cls=_config['_fqname'],
                            references=[dataclasses.asdict(ref) for ref in references],
                        ),
                    ],
                ),
            )

        return class_decorator

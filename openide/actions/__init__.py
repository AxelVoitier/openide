# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
import dataclasses
from typing import TYPE_CHECKING, TypedDict

# Third-party imports
from typing_extensions import NotRequired

# Local imports
from openide.integrations import mark_setup
from openide.utils import class_decorator

if TYPE_CHECKING:
    from typing import Any, TypeVar

    from openide.utils.classes import ClassDecorator
    from openide.utils.datastructures import RecursiveDict

    AC = TypeVar('AC', bound=type['Actions'])


@dataclasses.dataclass
class ActionReference:
    path: str
    position: int = -1
    separator_before: bool = False
    separator_after: bool = False


class _ActionReferenceAsDict(TypedDict):
    path: str
    position: int
    separator_before: NotRequired[bool]
    separator_after: NotRequired[bool]


class ActionConfig(TypedDict):
    cls: str
    references: list[_ActionReferenceAsDict]
    kwargs: NotRequired[dict[str, Any]]
    target_apps: NotRequired[list[str] | None]


class Actions:
    @staticmethod
    @mark_setup('config')
    def Registration(  # noqa: N802
        references: list[ActionReference],
        target_apps: str | list[str] | None = None,
        _config: RecursiveDict | None = None,
    ) -> ClassDecorator[AC]:
        if _config is not None:
            if not target_apps:
                target_apps = None
            elif isinstance(target_apps, str):
                target_apps = [target_apps]

            _config.merge(
                dict(
                    actions=[
                        ActionConfig(
                            cls=_config['_fqname'],
                            references=[
                                _ActionReferenceAsDict(**dataclasses.asdict(ref))
                                for ref in references
                            ],
                            target_apps=target_apps,
                        ),
                    ],
                ),
            )

        return class_decorator

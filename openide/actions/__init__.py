# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# System imports
import dataclasses

# Third-party imports

# Local imports
from openide.integration import mark_setup
from openide.utils import class_decorator


@dataclasses.dataclass
class ActionReference:

    path: str
    position: int = -1
    separator_before: bool = False
    separator_after: bool = False


class Actions:

    @mark_setup('config')
    def Registration(references=None, _config=None):
        if _config is not None:
            _config.merge(dict(
                actions=[
                    dict(
                        cls=_config['_fqname'],
                        references=[dataclasses.asdict(ref) for ref in references]
                    )
                ],
            ))

        return class_decorator

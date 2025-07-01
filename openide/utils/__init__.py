# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# /!\ Be careful of what is included here (in terms of third-party dependencies),
# as this gets imported during the integration/setup hooks.

from .classes import (  # noqa: F401
    MetaClassResolver,
    SingletonMeta,
    class_decorator,
    class_decorator_ext,
    class_loader,
    dig_wrapped,
)
from .datastructures import RecursiveDict  # noqa: F401

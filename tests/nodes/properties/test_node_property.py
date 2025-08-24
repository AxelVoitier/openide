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
# Local imports
from openide.nodes import DescriptorProperty, node_property


class RWProperty:
    def __init__(self) -> None:
        super().__init__()

        self.__attr = 0

    @node_property(display_name='Attr', force_no_setter=True)
    def attr(self) -> int:
        return self.__attr

    @attr.setter
    def attr(self, value: int) -> None:
        self.__attr = value


def test_a() -> None:
    rw = RWProperty()
    print(rw.attr)
    assert rw.attr == 0
    rw.attr = 12
    print(rw.attr)
    assert rw.attr == 12

    for class_name, props in DescriptorProperty.all_properties(rw):
        for name, prop in props:
            print(name, prop)

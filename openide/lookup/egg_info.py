# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
import logging
from typing import TYPE_CHECKING, TypeVar

# Third-party imports
from lookups import Convertor, Lookup
from lookups.instance_content import ConvertingItem
from lookups.simple import SimpleResult

# Local imports
from openide import IDEApplication
from openide.utils import class_loader

T = TypeVar('T')
if TYPE_CHECKING:
    from collections.abc import Sequence

    from lookups.lookup import Item


_logger = logging.getLogger(__name__)


class EggInfoLookup(Lookup):
    class _FQNameConvertor(Convertor):
        def convert(self, element: object) -> object:
            fqname = element[0]
            cls = class_loader(fqname)
            return cls()

            # kwargs = element[1].get('kwargs', {})
            # return cls(**kwargs)

        def type(self, element: object) -> type:
            fqname = element[1].get('service', element[0])
            module_path, qualname = fqname.split(':')
            name = qualname.split('.')[-1]
            return type(name, (object,), dict(__module__=module_path, __qualname__=qualname))

        def id(self, element: object) -> str:
            return element[0]

        def display_name(self, element: object) -> str:
            return element[0]

    class _FQNameConvertingItem(ConvertingItem):
        def issubclass(self, cls: type) -> bool:
            """The special resolution based on full qualifed name requires
            overloading issubclass(). Unfortunately, it cannot be done with
            __subclasscheck__ as this dunder gets called only if defined on
            the comparison class(es) (ie. 2nd arg of issubclass).
            Here we don't support cls argument to be a tuple of classes.
            """

            item_type = self.get_type()
            result = issubclass(item_type, cls)
            if result:
                return result

            same_module = cls.__module__ == item_type.__module__
            same_qualname = cls.__qualname__ == item_type.__qualname__
            return same_module and same_qualname

    def __init__(self, section: str) -> None:
        registry = IDEApplication().config.get(section, {})
        self._convertor = self._FQNameConvertor()

        self._content = tuple(
            self._FQNameConvertingItem(element, self._convertor) for element in registry.items()
        )

    def lookup(self, cls: type[T]) -> T | None:
        for item in self._content:
            if item.issubclass(cls):
                return item.get_instance()

        return None

    def lookup_result(self, cls: type[T]) -> EggInfoServiceResult:  # [T]:
        return EggInfoServiceResult(self, cls)


class EggInfoServiceResult(SimpleResult):  # [T]):
    def all_items(self) -> Sequence[Item]:
        if self._items is None:
            self._items = tuple(item for item in self.lookup._content if item.issubclass(self.cls))

        return self._items

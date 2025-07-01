# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from abc import ABCMeta
from typing import Self

# Third-party imports
from qtpy.QtCore import QObject

# Needed to make Generics work on user classes, despite all the "error" here...
_QObjectType: type[type[QObject]] = type(QObject)  # type: ignore[valid-type]


class _QObjectTypeFence(_QObjectType):  # type: ignore[valid-type,misc]
    ...


class _QABCMeta(_QObjectTypeFence, ABCMeta, _QObjectType):  # type: ignore[valid-type,misc]
    ...


class QABC(metaclass=_QABCMeta):
    """A simpler variant of what MetaClassResolver does, but just for
    the very common case of QObject + ABC.

    This one has the advantage of keeping mypy and pylance happy,
    compared to MetaClassResolver that cannot even be nicely done
    using a mypy plugin...

    Usage:
    class MyClass(APythonABC, QABC, AQtSubclass)):
        ...

    Note: Put it _before_ the first Qt class in the subclasses declaration.
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        obj = super().__new__(cls, *args, **kwargs)
        if obj.__abstractmethods__:
            s = 's' if len(obj.__abstractmethods__) > 1 else ''
            msg = (
                f"Can't instantiate abstract class {cls.__name__} "
                f'with abstract method{s} {", ".join(obj.__abstractmethods__)}'
            )
            raise TypeError(msg)

        return obj

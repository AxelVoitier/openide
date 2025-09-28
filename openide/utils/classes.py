# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:words metaclasses metas uniquify metatypes fqname passthrough
# spell-checker:ignore shiboken pyside abstractmethods typeobject staticbase mcls

from __future__ import annotations

# System imports
import functools
import importlib
import logging
import time
from abc import ABCMeta
from contextlib import contextmanager
from typing import TYPE_CHECKING, ClassVar, ParamSpec, TypeVar
from weakref import ReferenceType

# Third-party imports
from lookups import Lookup
from typing_extensions import Self

# Local imports

C = TypeVar('C', bound=type)
P = ParamSpec('P')
if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from typing import Any, Final, TypeAlias

    ClassDecorator: TypeAlias = Callable[[C], C]
    ParametrisedClassDecorator: TypeAlias = Callable[P, ClassDecorator[C]]

__all__: Final = (
    'Debug',
    'MetaClassResolver',
    'SingletonABCMeta',
    'SingletonMeta',
    'class_decorator',
    'class_decorator_ext',
    'class_loader',
    'dig_wrapped',
)

_logger = logging.getLogger(__name__)


class SingletonMeta(type):
    """
    Uses like this:
    > class YourClass(metaclass=SingletonMeta):
    >     ...
    """

    _instances: ClassVar = dict[type['SingletonMeta'], 'SingletonMeta']()

    def __call__(cls, *args: Any, **kwargs: Any) -> SingletonMeta:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)

        return cls._instances[cls]


class SingletonABCMeta(SingletonMeta, ABCMeta):
    pass


def MetaClassResolver(*subclasses: C, extra_metas: Iterable[type] | None = None) -> type[C]:  # noqa: N802
    """Function to be called as a subclass definition, passing it all the subclasses you actually
    want, plus some extra metaclasses if you need.
    It will create a composite metaclass made of the metaclasses of all subclasses.

    Usage:
    class MyClass(MetaClassResolver(APythonSubClass, AQtSubclass)):
        ...

    Useful to fix the following error when you mix up Python and Qt subclasses:
      > TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict)
      > subclass of the metaclasses of all its bases
    Or:
      > TypeError: Shiboken.ObjectType.__new__(_ResolverMeta) is not safe,
      > use type.__new__()

    Can also be used to quickly declare several metaclasses:
    class MyClass(MetaClassResolver(extra_metas=[ABCMeta, SingletonMeta])):
        ...
    """
    # Main principle of a metaclass resolver is to generate a dynamic metaclass
    # subclassing all metaclasses of the subclasses we are interested to have.
    #
    # class _ResolverMeta(metaclass1, metaclass2, ...): ...
    # class _Resolver(subclass1, subclass2, ..., metaclass=_ResolverMeta): ...

    if extra_metas is None:
        extra_metas = []
    extra_metas = list(extra_metas)

    all_metas = [type(subclass) for subclass in subclasses] + extra_metas
    all_metas = list(dict.fromkeys(all_metas))  # Uniquify, keeping order

    # Ensure type is last
    if type in all_metas:
        all_metas.remove(type)
    all_metas.append(type)

    # Fix for PySide6 QObject inheritance (would probably also work for other "C base metatype"))
    # That one was very tricky to figure out...
    #
    # If you do a simple "class _ResolverMeta(ABCMeta, type(QObject))", you will have an error like
    # "TypeError: Shiboken.ObjectType.__new__(_ResolverMeta) is not safe, use type.__new__()" when
    # trying to construct a class with this metaclass. See PYSIDE-1434 and PYSIDE-1767.
    #
    # In a glimpse, it looks like if you revert the order of the subclasses of _ResolverMeta, it
    # seems to be working. But actually, because ATM PySide does not support cooperative multiple
    # inheritance (ie. won't call super), ABCMeta.__new__ is never called, and the
    # __abstractmethods__ attribute on the class is never set. And if that was another metaclass
    # than ABCMeta, it would be the same, its __new__ would never be executed.
    # And in that case, we cannot make _ResolverMeta.__new__ explicitly call each subclass __new__,
    # like you would in an __init__ in a diamond inheritance. Because each __new__ will return you a
    # different instance, when you want a unique one.
    #
    # The (cryptic) "is not safe" error comes from a check on Python side, from Objects/typeobject.c
    # in tp_new_wrapper function. It tries to check that the tp_new of a type is the same than the
    # tp_new of the "most derived base that's not a heap type". Also very cryptic...
    # Note that PySide "recently" switched to use Python Limited API, meaning using heap types.
    # That might be why it used to work easily on PySide2.
    #
    # Another thing that does not help at first (but was actually key to lead me to the solution),
    # is if you make the code of that function correspond to the error message it generates, it
    # looks like "the most derived base that's not a heap type" it finds (ie. "staticbase") seems
    # to be "type" itself. But it is not. If you experiment a bit with the MRO of _ResolverMeta,
    # you can find with this:
    # > class IntermediateType(type): ...
    # > class _ResolverMeta(IntermediateType, ABCMeta, type(QObject)): ...
    # You will get:
    # Shiboken.ObjectType.__new__(_ResolverMeta) is not safe, use IntermediateType.__new__()
    # Note how "type" became "IntermediateType" in the error message.
    #
    # However, if you just add a passthrough __new__ method to IntermediateType:
    # > class IntermediateType(type):
    # >     def __new__(mcls, name, bases, namespace, /, **kwargs):
    # >         return super().__new__(mcls, name, bases, namespace, **kwargs)
    # > class _ResolverMeta(IntermediateType, ABCMeta, type(QObject)): ...
    # Then you get the error message mentioning "type" again:
    # Shiboken.ObjectType.__new__(_ResolverMeta) is not safe, use type.__new__()
    #
    # The reasons why when you reimplement __new__ you get an incorrect class name when it finds the
    # "staticbase" are still unclear. But at least that test confirms it actually choke on the
    # "meta-type" of the first "meta-subclass".
    #
    # And so, to bypass that "safe" check, we want to trick it to think the first meta-subclass is
    # of the same meta-type than the one we will end up calling when we reach the type(QObject) one
    # down the MRO of _ResolverMeta.
    # And one way to do that is to have that IntermediateType class above actually "subclass"
    # type(QObject) instead of type. As we have another type(QObject) further down in the MRO, on
    # one side, during normal processing (think executing the chain of __new__ through the MRO) it
    # will just "passthrough" that do-nothing IntermediateType, and correctly execute
    # ABCMeta.__new__ before "terminating" in that non-cooperative type(QObject).__new__.
    # And on the other side, when we get to execute type(QObject).__new__, the "safe" check will
    # think "the most derived base that's not a heap type" is IntermediateType, which now happens to
    # have the same tp_new than type(QObject).
    #
    # To make that a bit more generic (the same issue and solution would apply for any other C-based
    # metatype that is a heap type), we can actually collect all types of the metatypes we intend
    # to have. And if we have something else than just "type", then add that IntermediateType (that
    # we call _MetaTypeFence below), making it subclass those other metatype types.
    # Actually, in case we find more than one "exotic" metatype type (Qt stuffs + some other C-based
    # objects), the behaviour is yet to be defined...
    all_meta_types = list({type(meta): meta for meta in all_metas if type(meta) is not type}.keys())
    if all_meta_types:

        class _MetaTypeFence(*all_meta_types):
            pass

        all_metas.insert(0, _MetaTypeFence)

    # Generate a metaclass that mixes all metaclasses, and will fix the typical error
    # "TypeError: metaclass conflict: the metaclass of a derived class
    #  must be a (non-strict) subclass of the metaclasses of all its bases"
    class _ResolverMeta(*all_metas):
        pass

    # Generate a class that can be simply inherited to:
    # - Subclass all given subclasses
    # - Mix and fix their metaclasses
    class _Resolver(*subclasses, metaclass=_ResolverMeta):
        def __new__(cls, *args: Any, **kwargs: Any) -> Self:
            obj = super().__new__(cls, *args, **kwargs)
            if (ABCMeta in all_metas) and obj.__abstractmethods__:
                # In case an ABC is used along a QObject (for instance), it turns out
                # the new of QObject type is not checking for abstract methods.
                # Therefore, even if ABCMeta.__new__ has properly run and
                # inited its internal states, the actual check for abstraction
                # is not enforced.
                # We replicate it here, raising the TypeError ourselves.
                # In the event we are an ABC but not a QObject, and we
                # do have abstract methods, the normal abstraction check will happen
                # before we reach this one.
                s = 's' if len(obj.__abstractmethods__) > 1 else ''
                msg = (
                    f"Can't instantiate abstract class {cls.__name__} "
                    f'with abstract method{s} {", ".join(obj.__abstractmethods__)}'
                )
                raise TypeError(msg)
            return obj

    return _Resolver


def dig_wrapped(cls: C) -> C:
    while hasattr(cls, '__wrapped__'):
        cls = cls.__wrapped__
    return cls


def class_decorator(cls: C) -> C:
    """A utility to act as a class decorator. To be returned by a callable decorator."""
    return cls


# TODO: Not sure of the type signatures here...
def class_decorator_ext(callback: Callable[[C], Any]) -> ClassDecorator[C]:
    """Another helper for callable decorator, this time allowing to specify a callback to which we
    will pass the actual decorated class."""

    def class_decorator(cls: C) -> C:
        callback(dig_wrapped(cls))

        @functools.wraps(cls)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            return cls(*args, **kwargs)

        return wrapper

    return class_decorator


@functools.cache
def class_loader(fqname: str) -> type:
    _logger.info('Loading class %s', fqname)
    module_path, qualname = fqname.split(':')
    module = importlib.import_module(module_path)
    attr = module
    for attr_name in qualname.split('.'):
        attr = getattr(dig_wrapped(attr), attr_name)
    return attr


# To be tested
# Do we need to set as well? If so, it is more complicated...
# TODO: Review type signatures
class classproperty:  # noqa: N801
    def __init__(self, func: Callable[[Any], Any]) -> None:
        self.func = func

    def __get__(self, obj: Any, owner: Any) -> Any:  # noqa: ANN401
        return self.func(owner)


class _DebugReturn:
    _GUARD = object()

    def __init__(self) -> None:
        self._value = _DebugReturn._GUARD

    @property
    def value(self) -> Any:  # noqa: ANN401
        if self._value is _DebugReturn._GUARD:
            return 'FAIL'
        else:
            return self._value

    @value.setter
    def value(self, value: Any) -> None:  # noqa: ANN401
        self._value = value


class _Debug_Dummy: ...  # noqa: N801


class _Debug_Real:  # noqa: N801
    # TODO:
    # - __init__
    # - __del__
    # - set
    # - qualname on instance attributes, not just the ones defined at class level (ie. mostly methods)

    _INDENT = 0
    _SILENT = False

    @classmethod
    @contextmanager
    def _SILENCE(cls) -> Iterator[None]:  # noqa: N802
        Debug._SILENT, was_silent = True, Debug._SILENT
        yield
        Debug._SILENT = was_silent

    def __getattribute__(self, /, __name: str) -> Any:  # noqa: ANN401, PLR0915
        attr = None

        def _attr_name() -> str:
            cls_qn = type(self).__qualname__
            attr_qn = getattr(getattr(type(self), __name, None), '__qualname__', None)
            if attr_qn:
                if not attr_qn.startswith(cls_qn):
                    return f'{cls_qn}.{attr_qn}'
                else:
                    return f'{attr_qn}'
            else:
                return f'{cls_qn}.{__name}'

        # print(f'{Debug._INDENT * " "}" _get_ {_attr_name()}')

        @contextmanager
        def _wrapper(params: str | None = None, *, is_prop: bool = False) -> Iterator[_DebugReturn]:
            if Debug._SILENT:
                yield _DebugReturn()
                return

            indent = Debug._INDENT
            attr_name = _attr_name()
            if is_prop:
                print(f'{indent * " "}> {attr_name}')
            else:
                print(f'{indent * " "}> {attr_name}({params})')
                attr_name += '()'

            Debug._INDENT += 2
            ret = _DebugReturn()
            try:
                t1 = time.monotonic_ns()
                yield ret
            finally:
                t2 = time.monotonic_ns()
                dt = t2 - t1
                Debug._INDENT = indent
                with Debug._SILENCE():
                    if dt >= 1e9:
                        print(f'{indent * " "}< {attr_name} => {ret.value} ({dt / 1e9:.02f} s)')
                    elif dt >= 1e6:
                        print(f'{indent * " "}< {attr_name} => {ret.value} ({dt / 1e6:.02f} ms)')
                    elif dt >= 1e3:
                        print(f'{indent * " "}< {attr_name} => {ret.value} ({dt / 1e3:.02f} us)')
                    else:
                        print(f'{indent * " "}< {attr_name} => {ret.value} ({dt} ns)')

        if isinstance(getattr(type(self), __name, None), property):
            # print(f'{Debug._INDENT * " "}" _get_ {_attr_name()} is a property')
            with _wrapper(is_prop=True) as ret:
                ret.value = super().__getattribute__(__name)
                return ret.value
        else:
            attr = super().__getattribute__(__name)

            if callable(attr) and not isinstance(attr, (type, Lookup, ReferenceType)):
                # print(f'{Debug._INDENT * " "}" _get_ {_attr_name()} is callable')

                def _callable_wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
                    with Debug._SILENCE():
                        params = ', '.join(
                            [str(arg) for arg in args] + [f'{k}={v}' for k, v in kwargs.items()],
                        )

                    with _wrapper(params) as ret:
                        ret.value = attr(*args, **kwargs)
                        return ret.value

                return _callable_wrapper

            else:
                if not Debug._SILENT:
                    with Debug._SILENCE():
                        print(f'{Debug._INDENT * " "}- {_attr_name()} => {attr}')
                return attr


_DEBUG_MAP = {
    'openide.explorer.node_model.NodeModel': _Debug_Real,
}


def Debug(name: str | None = None) -> type:  # noqa: N802
    if name not in _DEBUG_MAP:
        return _Debug_Dummy  # TODO: Change to a configurable default
    else:
        return _DEBUG_MAP[name]


# TODO: def debug_method()

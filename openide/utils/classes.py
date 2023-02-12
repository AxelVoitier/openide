# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# System imports
import functools
import importlib
import logging
from abc import ABCMeta
from functools import lru_cache

# Third-party imports

# Local imports


_logger = logging.getLogger(__name__)


class SingletonMeta(type):
    '''
    Uses like this:
    > class YourClass(metaclass=SingletonMeta):
    >     ...
    '''

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)

        return cls._instances[cls]


def MetaClassResolver(*subclasses, extra_metas=None):
    '''Function to be called as a subclass definition, passing it all the subclasses you actually
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
    '''
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
    # inheritence (ie. won't call super), ABCMeta.__new__ is never called, and the
    # __abstractmethods__ attribute on the class is never set. And if that was another metaclass
    # than ABCMeta, it would be the same, its __new__ would never be executed.
    # And in that case, we cannot make _ResolverMeta.__new__ explicitly call each subclass __new__,
    # like you would in an __init__ in a diamond inheritence. Because each __new__ will return you a
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

        def __new__(cls, *args, **kwargs):
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
                raise TypeError(
                    f'Can\'t instantiate abstract class {cls.__name__} '
                    f'with abstract method{s} {", ".join(obj.__abstractmethods__)}'
                )
            return obj

    return _Resolver


def dig_wrapped(cls):
    while hasattr(cls, '__wrapped__'):
        cls = cls.__wrapped__
    return cls


def class_decorator(cls):
    '''A utility to act as a class decorator. To be returned by a callable decorator.'''
    return cls


def class_decorator_ext(callback):
    '''Another helper for callable decorator, this time allowing to specify a callback to which we
    will pass the actual decorated class.'''
    def class_decorator(cls):
        callback(dig_wrapped(cls))

        @functools.wraps(cls)
        def wrapper(*args, **kwargs):
            return cls(*args, **kwargs)
        return wrapper

    return class_decorator


@lru_cache(maxsize=None)
def class_loader(fqname):
    _logger.info('Loading class %s', fqname)
    module_path, qualname = fqname.split(':')
    module = importlib.import_module(module_path)
    attr = module
    for attr_name in qualname.split('.'):
        attr = getattr(dig_wrapped(attr), attr_name)
    return attr

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

    Can also be used to quickly declare several metaclasses:
    class MyClass(MetaClassResolver(extra_metas=[ABCMeta, SingletonMeta])):
        ...
    '''

    if extra_metas is None:
        extra_metas = []
    extra_metas = list(extra_metas)
    extra_metas.append(type)

    all_metas = [type(subclass) for subclass in subclasses] + extra_metas
    all_metas = list(dict.fromkeys(all_metas))  # Uniquify, keeping order

    class _ResolverMeta(*all_metas):
        pass

    class _Resolver(*subclasses, metaclass=_ResolverMeta):
        pass

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

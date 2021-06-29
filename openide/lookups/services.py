# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# System imports
import logging
from abc import ABCMeta

# Third-party imports
from lookups import Lookup

# Local imports
from openide.integration import mark_setup
from openide.utils import class_decorator


_logger = logging.getLogger(__name__)


@mark_setup('config', is_static=False)
def ServiceProvider(service, position=None, supersedes=None, _config=None):
    if _config is not None:
        _config.merge(dict(
            services={
                _config['_fqname']: dict(
                    service=f'{service.__module__}:{service.__qualname__}',
                    position=position,
                    supersedes=supersedes,
                )
            },
        ))

    return class_decorator


class ServiceSingletonMeta(type):
    '''Metaclass that does two things:
    - Ensures the concrete class implementing this service is instantiated only once (singleton)
    - When trying to instantiate the base service class (most likely an abstract class),
      it will actually search in the default lookup for a provider of this service. And cache the
      resulting instance as if it was its own singleton instance

    See also: ServiceSingletonABCMeta for a metaclass already inheriting from abc.ABCMeta.

    Usage:
    # First declare your service class
    class MyService(metaclass=ServiceSingletonMeta):
        pass

    # Then define a concrete class implementing this service
    @ServiceProvider(service=MyService)
    class MyServiceImpl(MyService):
        pass

    # And when you need a MyService, just do:
    my_service1 = MyService()
    my_service2 = MyService()
    assert my_service1 is my_service2
    assert isinstance(my_service1, MyServiceImpl)
    '''

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            # First search for which parent class is actually the one that defined the
            # ServiceSingleton metaclass first
            for subclass in reversed(cls.__mro__):
                if issubclass(type(subclass), ServiceSingletonMeta):
                    root_service_abc = subclass
                    break
            else:
                raise RuntimeError(f'Could not find root service abstract class for {cls}')

            if root_service_abc is not cls:
                # Here we are actually trying to instantiate an actual concrete class
                # for this service.
                instance = super().__call__(*args, **kwargs)

                cls._instances[cls] = instance  # Ensure we are a singleton
                return instance

            else:
                # Here we have been invoked on the abstract service class.
                # we need to find one concrete implementation to return.

                provider = Lookup.get_default().lookup(root_service_abc)

                cls._instances[cls] = provider  # Cache the singleton value
                return provider

        # Return (cached) singleton instance
        return cls._instances[cls]


class ServiceSingletonABCMeta(ABCMeta, ServiceSingletonMeta):
    '''Mix both metaclasses needed to make a typical abstract service singleton class'''
    pass

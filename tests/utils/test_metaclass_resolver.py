# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from abc import ABCMeta, ABC, abstractmethod
from collections.abc import Generator, Iterable
from typing import Type

# Third-party imports
import pytest
from qtpy.QtWidgets import QWidget, QApplication

# Local imports
from openide.utils.classes import MetaClassResolver, SingletonMeta


class Interface(ABC):

    @abstractmethod
    def method1(self) -> bool:
        '''method1 is meant to be implemented by one of the given subclasses'''
        raise NotImplementedError()

    @abstractmethod
    def method2(self) -> bool:
        '''method2 is meant to be implemented by the class using MetaClassResolver directly'''
        raise NotImplementedError()

    @abstractmethod
    def method3(self) -> bool:
        '''method3 is meant to be implemented by a subclass of the class using MetaClassResolver'''
        raise NotImplementedError()


class Normal1:
    '''A bog-standard class'''

    def method1(self) -> bool:
        return True


class Normal2:
    '''A second bog-standard class, to combine with another bog-standard'''

    def method1(self) -> bool:
        return True


class ASingleton(metaclass=SingletonMeta):
    ...


class AWidget(QWidget):
    ...


@pytest.fixture(autouse=True, scope='module')
def qapp() -> Generator[None, None, None]:
    '''Create QApplication needed to instantiate QObjects'''
    qapp = QApplication()
    yield
    del qapp


def check(cls: Type, subclasses: Iterable[Type], check_method3=False) -> None:
    '''Reusable checking function'''
    # You would think checking some of these stuffs are superfluous.
    # But I have seen very weird behaviours during development,
    # as we manipulate some fundamental stuffs about class and object creation.
    # So, don't dare optimizing these checks...

    # An abstract class should not even instantiate
    obj = cls()
    assert obj

    # If we are supposed to have a method1, check we are not hitting the abstract one
    if hasattr(obj, 'method1'):
        assert obj.method1() is True

    # Method2 should always be here, and should not hit an abstract one
    assert obj.method2() is True

    # Method3 is like method2, but for a subclass test
    if check_method3:
        assert obj.method3() is True

    # Checking some meta behaviours have run properly.
    metas = {type(subclass) for subclass in subclasses}

    # An ABC should have __abstractmethods__ (even if empty).
    if ABCMeta in metas:
        assert hasattr(cls, '__abstractmethods__') is True, 'It seems ABCMeta.__new__ did not run'
        assert hasattr(obj, '__abstractmethods__') is True, 'It seems ABCMeta.__new__ did not run'

    # A Singleton should be registered in the instances dict
    if SingletonMeta in metas:
        assert cls in SingletonMeta._instances
        assert SingletonMeta._instances[cls] is obj

    # Checking MRO of both the class and metaclass behave sanely
    mro_iter = iter(cls.__mro__)
    meta_mro = type(cls).__mro__
    for subclass in subclasses:
        # Typing tests should still work
        assert issubclass(cls, subclass)
        assert isinstance(obj, subclass)

        # Check we do find the subclass in the MRO, in the expected order
        for mro_class in mro_iter:
            if mro_class is subclass:
                break
        else:
            raise AssertionError(f'Subclass {subclass} not in MRO: {cls.__mro__}')

        # Check the metaclass of a subclass is in the metaclass MRO
        assert type(subclass) in meta_mro, f'{type(subclass)} not in metaclass MRO: {meta_mro}'


SUBCLASSES_TESTS = [
    # Single
    (Normal1, ),
    (ASingleton, ),
    pytest.param((Interface, ), marks=pytest.mark.xfail(raises=TypeError, strict=True)),
    (AWidget, ),

    # Combined
    (Normal1, Normal2),
    (Normal1, ASingleton),
    (ASingleton, Normal1),
    (Normal1, Interface),
    (Normal1, AWidget),
    (AWidget, Normal1),
    pytest.param((Interface, ASingleton), marks=pytest.mark.xfail(
        raises=TypeError, strict=True)),
    pytest.param((ASingleton, Interface), marks=pytest.mark.xfail(
        raises=TypeError, strict=True)),
    pytest.param((Interface, AWidget), marks=pytest.mark.xfail(raises=TypeError, strict=True)),
    pytest.param((AWidget, Interface), marks=pytest.mark.xfail(raises=TypeError, strict=True)),

    (Normal1, ASingleton, Interface),
    (Normal1, Interface, ASingleton),
    (ASingleton, Normal1, Interface),

    pytest.param((Normal1, AWidget, Interface),
                 marks=pytest.mark.xfail(raises=TypeError, strict=True)),
    (Normal1, Interface, AWidget),
    pytest.param((AWidget, Normal1, Interface),
                 marks=pytest.mark.xfail(raises=TypeError, strict=True)),

    (Normal1, ASingleton, AWidget),
    (Normal1, AWidget, ASingleton),
    (ASingleton, Normal1, AWidget),
    (ASingleton, AWidget, Normal1),
    (AWidget, Normal1, ASingleton),
    (AWidget, ASingleton, Normal1),

    (Normal1, Interface, ASingleton, AWidget),
    (Normal1, Interface, AWidget, ASingleton),
    (ASingleton, Normal1, Interface, AWidget),
    pytest.param((AWidget, Normal1, Interface, ASingleton),
                 marks=pytest.mark.xfail(raises=TypeError, strict=True)),
    pytest.param((ASingleton, AWidget, Normal1, Interface),
                 marks=pytest.mark.xfail(raises=TypeError, strict=True)),
    pytest.param((AWidget, ASingleton, Normal1, Interface),
                 marks=pytest.mark.xfail(raises=TypeError, strict=True)),
    (Normal1, ASingleton, Interface, AWidget),
    pytest.param((Normal1, AWidget, Interface, ASingleton),
                 marks=pytest.mark.xfail(raises=TypeError, strict=True)),
    pytest.param((ASingleton, Normal1, AWidget, Interface),
                 marks=pytest.mark.xfail(raises=TypeError, strict=True)),
    pytest.param((AWidget, Normal1, ASingleton, Interface),
                 marks=pytest.mark.xfail(raises=TypeError, strict=True)),
]


@pytest.mark.parametrize('subclasses', SUBCLASSES_TESTS)
def test_subclasses_direct(subclasses: Iterable[Type]) -> None:
    class ToTest(MetaClassResolver(*subclasses)):  # type: ignore[misc]

        def method2(self) -> bool:
            return True

        def method3(self) -> bool:
            '''
            Even method3 is supposed to be implemented by a subclass,
            for tests to work properly we still need to implement it.
            Otherwise some tests would fail because the class is still abstract.
            '''
            return True

    check(ToTest, subclasses)


@pytest.mark.parametrize('subclasses', SUBCLASSES_TESTS)
def test_subclasses_subclass(subclasses: Iterable[Type]) -> None:
    '''Separate subclass tests such that the xfail ones also run for the subclass case'''

    class ToTest(MetaClassResolver(*subclasses)):  # type: ignore[misc]

        def method2(self) -> bool:
            return True

    class SubclassToTest(ToTest):

        def method3(self) -> bool:
            return True

    check(SubclassToTest, subclasses, check_method3=True)

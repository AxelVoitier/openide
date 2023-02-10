# Copyright (c) 2023 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable
from typing import Type

# Third-party imports
import pytest
from qtpy.QtWidgets import QWidget, QApplication

# Local imports
from openide.utils.classes import MetaClassResolver, SingletonMeta


class Normal1:

    def method(self) -> bool:
        return True


class Normal2:

    def method(self) -> bool:
        return True


class ASingleton(metaclass=SingletonMeta):
    ...


class Interface(ABC):

    @abstractmethod
    def method(self) -> bool:
        raise NotImplementedError()


class AWidget(QWidget):
    ...


@pytest.fixture(autouse=True, scope='module')
def qapp() -> Generator[None, None, None]:
    '''Create QApplication needed to instantiate QObjects'''
    qapp = QApplication()
    yield
    del qapp


@pytest.mark.parametrize(
    'subclasses', [
        # Single
        (Normal1, ),
        (ASingleton, ),
        pytest.param((Interface, ), marks=pytest.mark.xfail(raises=TypeError)),
        (AWidget, ),

        # Combined
        (Normal1, Normal2),
        (Normal1, ASingleton),
        (ASingleton, Normal1),
        (Normal1, Interface),
        (Normal1, AWidget),
        (AWidget, Normal1),
        pytest.param((Interface, ASingleton), marks=pytest.mark.xfail(raises=TypeError)),
        pytest.param((ASingleton, Interface), marks=pytest.mark.xfail(raises=TypeError)),
        pytest.param((Interface, AWidget), marks=pytest.mark.xfail(raises=TypeError)),
        pytest.param((AWidget, Interface), marks=pytest.mark.xfail(raises=TypeError)),

        (Normal1, ASingleton, Interface),
        (Normal1, Interface, ASingleton),
        (ASingleton, Normal1, Interface),

        (Normal1, AWidget, Interface),
        (Normal1, Interface, AWidget),
        (AWidget, Normal1, Interface),

        (Normal1, ASingleton, AWidget),
        (Normal1, AWidget, ASingleton),
        (ASingleton, Normal1, AWidget),
        (ASingleton, AWidget, Normal1),
        (AWidget, Normal1, ASingleton),
        (AWidget, ASingleton, Normal1),

        (Normal1, Interface, ASingleton, AWidget),
        (Normal1, Interface, AWidget, ASingleton),
        (ASingleton, Normal1, Interface, AWidget),
        (AWidget, Normal1, Interface, ASingleton),
        (ASingleton, AWidget, Normal1, Interface),
        (AWidget, ASingleton, Normal1, Interface),
        (Normal1, ASingleton, Interface, AWidget),
        (Normal1, AWidget, Interface, ASingleton),
        (ASingleton, Normal1, AWidget, Interface),
        (AWidget, Normal1, ASingleton, Interface),
    ]
)
def test_only_subclasses(subclasses: Iterable[Type]) -> None:
    class ToTest(MetaClassResolver(*subclasses)):  # type: ignore[misc]
        ...

    print(ToTest.__mro__)

    obj = ToTest()
    assert obj
    if hasattr(obj, 'method'):
        assert obj.method() is True

    mro_iter = iter(ToTest.__mro__)
    meta_mro = type(ToTest).__mro__
    for subclass in subclasses:
        assert issubclass(ToTest, subclass)
        assert isinstance(obj, subclass)

        for mro_class in mro_iter:
            if mro_class is subclass:
                break
        else:
            raise AssertionError(f'Subclass {subclass} not in MRO: {ToTest.__mro__}')

        assert type(subclass) in meta_mro, f'{type(subclass)} not in metaclass MRO: {meta_mro}'

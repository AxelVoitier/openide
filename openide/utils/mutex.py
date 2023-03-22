# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# From: https://github.com/apache/netbeans/blob/master/platform/openide.util/src/org/openide/util/Mutex.java  # noqa: E501

from __future__ import annotations

# System imports
import logging
import queue
import sys
import time
import threading
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable, MutableMapping, MutableSequence
from contextlib import contextmanager, AbstractContextManager
from dataclasses import dataclass, field
from enum import Enum
from functools import partial
from math import inf
from threading import Condition, RLock, Thread
from typing import TYPE_CHECKING

# Third-party imports

# Local imports
from openide.utils.classes import Debug


if TYPE_CHECKING:
    from collections.abc import Generator
    from types import TracebackType
    from typing import Optional, Union, Any


_logger = logging.getLogger(__name__)

_DEBUG_ACCESS = False
_DBG_PRINT_LOCK = RLock()


def _debug(*args: Any, **kwargs: Any) -> None:
    if not _DEBUG_ACCESS:
        return

    with _DBG_PRINT_LOCK:
        print(*args, **kwargs)
        if 'end' in kwargs and not kwargs['end']:
            sys.stdout.flush()


class _TimeMeasure(AbstractContextManager):

    def __init__(
        self,
        message: str,
        time_fn: Optional[Callable[[], Union[float, int]]] = None
    ) -> None:
        if not _DEBUG_ACCESS:
            return

        self._message = message + '... '
        self._time_fn = time_fn or time.monotonic
        self._t1: Union[float, int]

    def __enter__(self) -> _TimeMeasure:
        if not _DEBUG_ACCESS:
            return self

        with _DBG_PRINT_LOCK:
            print(self._message, end='')
            sys.stdout.flush()
        self._t1 = self._time_fn()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> bool:
        if not _DEBUG_ACCESS:
            return False

        t2 = self._time_fn()
        if exc_type is None:
            with _DBG_PRINT_LOCK:
                print(f'OK in {t2 - self._t1:.03f}')
        else:
            with _DBG_PRINT_LOCK:
                print(f'FAIL in {t2 - self._t1:.03f}')

        return False


class MutexImplementation(ABC):

    @property
    @abstractmethod
    def is_read_access(self) -> bool:
        raise NotImplementedError()  # pragma: no cover

    @contextmanager
    @abstractmethod
    def read_access(self) -> Generator[None, None, None]:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def post_read_request(self, run: Callable[[], None]) -> None:
        raise NotImplementedError()  # pragma: no cover

    @property
    @abstractmethod
    def is_write_access(self) -> bool:
        raise NotImplementedError()  # pragma: no cover

    @contextmanager
    @abstractmethod
    def write_access(self) -> Generator[None, None, None]:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def post_write_request(self, run: Callable[[], None]) -> None:
        raise NotImplementedError()  # pragma: no cover


class Mutex(Debug(f'{__name__}.Mutex')):

    def __init__(
        self, implementation: Optional[MutexImplementation] = None,
        lock: Optional[RLock] = None
    ) -> None:
        super().__init__()

        if implementation is not None:
            self._implementation = implementation

        else:
            self._implementation = DefaultMutexImplementation(lock=lock)

    @property
    def is_read_access(self) -> bool:
        return self._implementation.is_read_access

    @contextmanager
    def read_access(self) -> Generator[None, None, None]:
        with self._implementation.read_access():
            yield

    def post_read_request(self, run: Callable[[], None]) -> None:
        self._implementation.post_read_request(run)

    @property
    def is_write_access(self) -> bool:
        return self._implementation.is_write_access

    @contextmanager
    def write_access(self) -> Generator[None, None, None]:
        with self._implementation.write_access():
            yield

    def post_write_request(self, run: Callable[[], None]) -> None:
        self._implementation.post_write_request(run)


class DefaultMutexImplementation(MutexImplementation):

    class _Modes(Enum):
        NONE = 0
        CHAIN = 1
        EXCL = 2
        SHARED = 3

    _CMATRIX = [  # [requested][granted]
        None,  # NONE
        None,  # CHAIN
        [True, False, False, False],  # EXCL
        [True, False, False, True],  # SHARED
    ]

    class _ThreadInfo:

        def __init__(self, thread: Thread, mode: DefaultMutexImplementation._Modes) -> None:
            self.thread = thread
            self.mode = mode
            n_modes = len(DefaultMutexImplementation._Modes)
            self.counts = [0] * n_modes
            self.counts[mode.value] = 1
            self.post_requests: tuple[
                MutableSequence[Callable[[], None]], ...
            ] = tuple([] for _ in range(n_modes))

            self.forced = False
            self.rsnapshot = 0

        def __str__(self) -> str:
            n_excl = self.counts[DefaultMutexImplementation._Modes.EXCL.value]
            n_shared = self.counts[DefaultMutexImplementation._Modes.SHARED.value]

            return f'ThreadInfo(thread={self.thread} ; mode={self.mode} ; ' \
                   f'EXCL={n_excl} ; SHARED={n_shared})'

    @dataclass(order=True)
    class _QueueCell(Condition):
        priority: float
        mode: DefaultMutexImplementation._Modes = field(compare=False)
        thread: Thread = field(compare=False)

        def __post_init__(self) -> None:
            super().__init__()

            self.left = False
            self._signal = False

        def sleep(self, timeout: Optional[float] = None) -> None:
            with self:
                self.wait_for(
                    partial(getattr, self, '_signal'),
                    timeout
                )

        def wake_me_up(self) -> None:
            with self:
                self._signal = True
                self.notify_all()

    def __init__(self, lock: Optional[RLock] = None) -> None:
        super().__init__()

        if lock is None:
            lock = RLock()
        self._LOCK = lock

        self.__granted_mode = self._Modes.NONE
        self.__original_mode = self._Modes.NONE
        self.__registered_threads: MutableMapping[
            Thread, DefaultMutexImplementation._ThreadInfo] = {}
        self._readers_num = 0
        self._waiters: queue.Queue = queue.PriorityQueue()

    @property
    def is_read_access(self) -> bool:
        thread = threading.current_thread()

        with self._LOCK:
            info = self._get_thread_info(thread)
            if info is not None:
                if info.counts[self._Modes.SHARED.value] > 0:
                    return True

        return False

    @contextmanager
    def read_access(self, timeout: Optional[float] = None) -> Generator[None, None, None]:
        thread = threading.current_thread()

        if _DEBUG_ACCESS:
            with _TimeMeasure(f'Requesting read access {thread=} {timeout=}'):
                self._enter(self._Modes.SHARED, thread, timeout)

            try:
                with _TimeMeasure('Processing read access'):
                    yield
            finally:
                with _TimeMeasure('Leaving read access'):
                    self._leave(thread)

        else:
            self._enter(self._Modes.SHARED, thread, timeout)
            try:
                yield
            finally:
                self._leave(thread)

    def post_read_request(self, run: Callable[[], None]) -> None:
        if _DEBUG_ACCESS:
            self._post_request_debug(self._Modes.SHARED, run)
        else:
            self._post_request(self._Modes.SHARED, run)

    @property
    def is_write_access(self) -> bool:
        thread = threading.current_thread()

        with self._LOCK:
            info = self._get_thread_info(thread)
            if info is not None:
                if info.counts[self._Modes.EXCL.value] > 0:
                    return True

        return False

    @contextmanager
    def write_access(self, timeout: Optional[float] = None) -> Generator[None, None, None]:
        thread = threading.current_thread()

        if _DEBUG_ACCESS:
            with _TimeMeasure(f'Requesting write access {thread=} {timeout=}'):
                self._enter(self._Modes.EXCL, thread, timeout)

            try:
                with _TimeMeasure('Processing write access'):
                    yield
            finally:
                with _TimeMeasure('Leaving write access'):
                    self._leave(thread)

        else:
            self._enter(self._Modes.EXCL, thread, timeout)
            try:
                yield
            finally:
                self._leave(thread)

    def post_write_request(self, run: Callable[[], None]) -> None:
        if self._LOCK._is_owned():
            raise RuntimeError('Cannot post write request while we are doing some mutex operation')

        if _DEBUG_ACCESS:
            self._post_request_debug(self._Modes.EXCL, run)
        else:
            self._post_request(self._Modes.EXCL, run)

    def _enter(
        self, requested: DefaultMutexImplementation._Modes,
        thread: Thread, timeout: Optional[float],
    ) -> bool:
        cell = None
        loop_counter = 0

        EXCL = self._Modes.EXCL
        SHARED = self._Modes.SHARED

        while True:
            loop_counter += 1
            with self._LOCK:
                _debug(f'Getting thread info {thread=}')
                info = self._get_thread_info(thread)
                _debug(f'Thread info: {info}')

                if info is not None:
                    if self._granted_mode == self._Modes.NONE:
                        raise RuntimeError('Thread already entered, but has no mode?! ')

                    if any((
                        (info.mode == SHARED) and (self._granted_mode == EXCL),
                        (info.mode == EXCL) and (self._granted_mode == SHARED),
                    )):
                        raise RuntimeError('Discrepency between thread mode and granted mode')

                    if (info.mode == EXCL) or (info.mode == requested):
                        if info.forced:
                            info.forced = False
                        else:
                            if (requested == EXCL) and (info.counts[SHARED.value] > 0):
                                warnings.warn(
                                    'Going from read_access to write_access', RuntimeWarning)
                            info.counts[requested.value] += 1
                            if (requested == SHARED) and (info.counts[requested.value] == 1):
                                self._readers_num += 1

                        return True

                    elif self._can_upgrade(info.mode, requested):
                        warnings.warn(
                            'Going from read_access to write_access', RuntimeWarning)
                        info.mode = EXCL
                        info.counts[requested.value] += 1
                        info.rsnapshot = info.counts[SHARED.value]
                        if self._granted_mode == SHARED:
                            self._granted_mode = EXCL
                        elif self._granted_mode == EXCL:
                            raise RuntimeError('Cannot go to write mode, we alread are in it?!')

                        return True

                    else:
                        warnings.warn(
                            'Going from read_access to write_access', RuntimeWarning)

                else:
                    if self._is_compatible(requested):
                        _debug(f'We are compatible ({requested=}), registering')
                        self._granted_mode = requested
                        self._registered_threads[thread] = self._ThreadInfo(thread, requested)

                        if requested == SHARED:
                            self._readers_num += 1

                        return True

                if (timeout is not None) and (timeout == 0):
                    return False

                self._granted_mode = self._Modes.CHAIN
                cell = self._chain(requested, thread, +inf)

            _debug(f'Cell waiting for {timeout}')
            cell.sleep(timeout)
            if (timeout is not None) and (timeout > 0):
                timeout = 0

    def _reenter(self, thread: Thread, mode: DefaultMutexImplementation._Modes) -> bool:
        Modes = self._Modes
        granted_mode = self._granted_mode

        if mode == Modes.SHARED:
            if (self._granted_mode != Modes.NONE) and (self._granted_mode != Modes.SHARED):
                raise RuntimeError(f'Cannot enter shared mode as we are in {self._granted_mode}')

            self._enter(mode, thread, None)
            return False

        info = self._get_thread_info(thread)
        if any((
            granted_mode in (Modes.EXCL, Modes.NONE),
            all((
                self._granted_mode == Modes.CHAIN,
                (info is not None) and (info.counts[Modes.EXCL.value] > 0),
            ))
        )):
            self._enter(mode, thread, None)
            return False

        if self._readers_num == 0:
            raise RuntimeError('No readers?!')

        info = self._ThreadInfo(thread, mode)
        self._registered_threads[thread] = info

        self._readers_num += 2

        self._granted_mode = Modes.CHAIN

        return True

    def _privileged_enter(self, thread: Thread, mode: DefaultMutexImplementation._Modes) -> None:
        decrease = True

        with self._LOCK:
            self._get_thread_info(thread)

        while True:
            with self._LOCK:
                if decrease:
                    decrease = False
                    self._readers_num -= 2

                self._granted_mode = self._Modes.CHAIN
                cell = self._chain(mode, thread, 0)

                if self._readers_num == 0:
                    try:
                        highest_cell = self._waiters.get_nowait()
                    except queue.Empty:
                        raise RuntimeError('No cell waiting, not even our own?!')

                    if highest_cell == cell:
                        self._waiters.task_done()
                        self._granted_mode = mode
                        return
                    else:
                        self._waiters.put(highest_cell)
                        self._granted_mode = self._Modes.NONE
                        self._wake_up_others()

            cell.sleep()

    def _leave(self, thread: Thread) -> None:
        Modes = self._Modes
        posted_mode = Modes.NONE
        need_lock = False

        with self._LOCK:
            info = self._get_thread_info(thread)
            if info is None:
                raise RuntimeError('No info on thread in a leave?!')

            granted_mode = self._granted_mode
            if granted_mode == Modes.NONE:
                raise RuntimeError('Cannot leave from None mode')

            elif granted_mode == Modes.CHAIN:
                if info.counts[Modes.EXCL.value] > 0:
                    posted_mode = self._leave_excl(info)
                elif info.counts[Modes.SHARED.value] > 0:
                    posted_mode = self._leave_shared(info)
                else:
                    raise RuntimeError(
                        'Cannot leave chain mode without any exclusive or shared users')

            elif granted_mode == Modes.EXCL:
                posted_mode = self._leave_excl(info)

            elif granted_mode == Modes.SHARED:
                posted_mode = self._leave_shared(info)

            if (posted_mode != Modes.NONE) and info.post_requests[posted_mode.value]:
                need_lock = self._reenter(thread, posted_mode)

        if (posted_mode != Modes.NONE) and info.post_requests[posted_mode.value]:
            try:
                if need_lock:
                    self._privileged_enter(thread, posted_mode)

                post_requests = info.post_requests[posted_mode.value]
                while post_requests:
                    post_request = post_requests.pop(0)
                    try:
                        post_request()
                    except Exception:
                        _logger.exception('Exception in a post request')

            finally:
                self._leave(thread)

    def _leave_excl(
        self, info: DefaultMutexImplementation._ThreadInfo
    ) -> DefaultMutexImplementation._Modes:
        Modes = self._Modes
        if any((
            info.counts[Modes.EXCL.value] <= 0,
            info.rsnapshot > info.counts[Modes.SHARED.value]
        )):
            raise RuntimeError('Cannot leave exclusive, thread is not in exclusive mode...')

        if info.rsnapshot == info.counts[Modes.SHARED.value]:
            info.counts[Modes.EXCL.value] -= 1

            if info.counts[Modes.EXCL.value] == 0:
                info.rsnapshot = 0

                if info.counts[Modes.SHARED.value] > 0:
                    info.mode = Modes.SHARED
                    self._granted_mode = Modes.SHARED
                else:
                    info.mode = Modes.NONE
                    self._granted_mode = Modes.NONE
                    del self._registered_threads[info.thread]

                if info.post_requests[Modes.SHARED.value]:
                    self._wake_up_readers()

                    return Modes.SHARED

                self._wake_up_others()

        else:
            if info.counts[Modes.SHARED.value] <= 0:
                raise RuntimeError('Is rsnapshot negative?!')

            info.counts[Modes.SHARED.value] -= 1
            if info.counts[Modes.SHARED.value] == 0:
                if self._readers_num <= 0:
                    raise RuntimeError('No more readers?!')
                self._readers_num -= 1

                return Modes.EXCL

        return Modes.NONE

    def _leave_shared(
        self, info: DefaultMutexImplementation._ThreadInfo
    ) -> DefaultMutexImplementation._Modes:
        Modes = self._Modes
        if (info.counts[Modes.SHARED.value] <= 0) or (info.counts[Modes.EXCL.value] > 0):
            raise RuntimeError('Cannot leave shared, conditions are not met')

        info.counts[Modes.SHARED.value] -= 1

        if info.counts[Modes.SHARED.value] == 0:
            info.mode = Modes.NONE
            del self._registered_threads[info.thread]

            if self._readers_num <= 0:
                raise RuntimeError('No more readers?!')
            self._readers_num -= 1

            if self._readers_num == 0:
                self._granted_mode = Modes.NONE

                if info.post_requests[Modes.EXCL.value]:
                    return Modes.EXCL

                self._wake_up_others()

            elif info.post_requests[Modes.EXCL.value]:
                return Modes.EXCL

            elif (self._granted_mode == Modes.CHAIN) and (self._readers_num == 1):
                while self._waiters.qsize():
                    try:
                        cell = self._waiters.get_nowait()
                    except queue.Empty:
                        raise RuntimeError('Hum, non-empty queue is... empty?!')

                    with cell:
                        if cell.left:
                            self._waiters.task_done()
                            continue

                        cell_info = self._get_thread_info(cell.thread)
                        if cell_info is not None:
                            if cell_info.mode == Modes.SHARED:
                                if cell.mode != Modes.EXCL:
                                    self._waiters.put(cell)
                                    raise RuntimeError('Cell in wrong mode to be awaken')

                                if self._waiters.qsize() == 0:
                                    self._granted_mode = Modes.EXCL

                                cell_info.mode = Modes.EXCL
                                cell.wake_me_up()

                            else:
                                self._waiters.put(cell)
                        else:
                            self._waiters.put(cell)

                        break

        return Modes.NONE

    def _chain(
        self, requested: DefaultMutexImplementation._Modes,
        thread: Thread, priority: float
    ) -> DefaultMutexImplementation._QueueCell:
        cell = self._QueueCell(priority=priority, mode=requested, thread=thread)
        self._waiters.put(cell)
        return cell

    def _wake_up_others(self) -> None:
        if self._granted_mode in (self._Modes.EXCL, self._Modes.CHAIN):
            raise RuntimeError('Wrong mode to wake up others')

        while self._waiters.qsize():
            try:
                cell = self._waiters.get_nowait()
            except queue.Empty:
                raise RuntimeError('Hum, non-empty queue is... empty?!')

            with cell:
                if cell.left:
                    self._waiters.task_done()
                    continue

                if self._is_compatible(cell.mode):
                    self._waiters.task_done()
                    cell.wake_me_up()
                    self._granted_mode = cell.mode

                    if self._get_thread_info(cell.thread) is None:
                        info = self._ThreadInfo(cell.thread, cell.mode)
                        info.forced = True

                        if cell.mode == self._Modes.SHARED:
                            self._readers_num += 1

                        self._registered_threads[cell.thread] = info

                else:
                    self._waiters.put(cell)
                    self._granted_mode = self._Modes.CHAIN
                    break

    def _wake_up_readers(self) -> None:
        assert self._granted_mode in (self._Modes.NONE, self._Modes.SHARED)

        put_back = []
        while self._waiters.qsize():
            try:
                cell = self._waiters.get_nowait()
            except queue.Empty:
                raise RuntimeError('Hum, non-empty queue is... empty?!')

            with cell:
                if cell.left:
                    self._waiters.task_done()
                    continue

                if cell.mode == self._Modes.SHARED:
                    self._waiters.task_done()
                    cell.wake_me_up()
                    self._granted_mode = cell.mode

                    if self._get_thread_info(cell.thread) is None:
                        info = self._ThreadInfo(cell.thread, cell.mode)
                        info.forced = True

                        self._readers_num += 1
                        self._registered_threads[cell.thread] = info

                else:
                    put_back.append(cell)

        for cell in put_back:
            self._waiters.put(cell)

    def _post_request(
        self, mutex_mode: DefaultMutexImplementation._Modes,
        run: Callable[[], None]
    ) -> None:
        Modes = self._Modes
        thread = threading.current_thread()

        with self._LOCK:
            info = self._get_thread_info(thread)

            if info is not None:
                idx = (Modes.SHARED.value + Modes.EXCL.value) - mutex_mode.value
                if (mutex_mode == info.mode) and (info.counts[idx] == 0):
                    self._enter(mutex_mode, thread, None)
                else:
                    info.post_requests[mutex_mode.value].append(run)
                    return

        if info is None:
            self._enter(mutex_mode, thread, None)

        try:
            run()
        finally:
            self._leave(thread)

    def _post_request_debug(
        self, mutex_mode: DefaultMutexImplementation._Modes,
        run: Callable[[], None]
    ) -> None:
        Modes = self._Modes
        thread = threading.current_thread()

        with self._LOCK:
            info = self._get_thread_info(thread)

            if info is not None:
                idx = (Modes.SHARED.value + Modes.EXCL.value) - mutex_mode.value
                if (mutex_mode == info.mode) and (info.counts[idx] == 0):
                    with _TimeMeasure(f'Post entering {mutex_mode.name} access {thread=}'):
                        self._enter(mutex_mode, thread, None)
                else:
                    _debug(f'Posting {mutex_mode.name} access for {run=}')
                    info.post_requests[mutex_mode.value].append(run)
                    return

        if info is None:
            with _TimeMeasure(f'Post entering {mutex_mode.name} access {thread=}'):
                self._enter(mutex_mode, thread, None)

        try:
            with _TimeMeasure(f'Post processing {mutex_mode.name} access for {run=}'):
                run()
        finally:
            with _TimeMeasure(f'Post leaving {mutex_mode.name} access'):
                self._leave(thread)

    def _is_compatible(self, requested: DefaultMutexImplementation._Modes) -> bool:
        if all((
            requested == self._Modes.SHARED,
            self._granted_mode == self._Modes.CHAIN,
            self._original_mode == self._Modes.SHARED,
        )):
            return True
        else:
            return self._CMATRIX[requested.value][self._granted_mode.value]

    def _get_thread_info(
        self, thread: Thread
    ) -> Optional[DefaultMutexImplementation._ThreadInfo]:
        return self._registered_threads.get(thread)

    def _can_upgrade(
        self, thread_mode: DefaultMutexImplementation._Modes,
        requested: DefaultMutexImplementation._Modes
    ) -> bool:
        return all((
            thread_mode == self._Modes.SHARED,
            requested == self._Modes.EXCL,
            self._readers_num == 1
        ))

    @property
    def _granted_mode(self) -> DefaultMutexImplementation._Modes:
        assert self._LOCK._is_owned()  # type: ignore[attr-defined]
        return self.__granted_mode

    @_granted_mode.setter
    def _granted_mode(self, mode: DefaultMutexImplementation._Modes) -> None:
        assert self._LOCK._is_owned()  # type: ignore[attr-defined]

        if (self.__granted_mode != self._Modes.CHAIN) and (mode == self._Modes.CHAIN):
            self.__original_mode = self.__granted_mode

        self.__granted_mode = mode

    @property
    def _original_mode(self) -> DefaultMutexImplementation._Modes:
        assert self._LOCK._is_owned()  # type: ignore[attr-defined]
        return self.__original_mode

    @property
    def _registered_threads(
        self
    ) -> MutableMapping[Thread, DefaultMutexImplementation._ThreadInfo]:
        assert self._LOCK._is_owned()  # type: ignore[attr-defined]
        return self.__registered_threads

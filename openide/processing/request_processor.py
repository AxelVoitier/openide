# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:words klass
# spell-checker:ignore

# From: https://github.com/apache/netbeans/blob/master/platform/openide.util/src/org/openide/util/RequestProcessor.java  # noqa: E501

from __future__ import annotations

# System imports
import enum
import logging
from collections.abc import Callable, Iterator
from concurrent.futures import Executor, Future, ThreadPoolExecutor, wait
from concurrent.futures.thread import BrokenThreadPool, _global_shutdown_lock, _shutdown
from contextlib import contextmanager
from itertools import count
from queue import PriorityQueue
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    NamedTuple,
    ParamSpec,
    Self,
    TypeVar,
)

# Third-party imports
from listeners import KeyedListeners, KeyedObservable, VetoError
from typing_extensions import override

# Local imports

P = ParamSpec('P')
R_co = TypeVar('R_co', covariant=True)
if TYPE_CHECKING:
    from typing import Final

__all__: Final = (
    'RequestProcessor',
    'Task',
)

_logger = logging.getLogger(__name__)


class Task(Generic[P, R_co]):
    class Events(enum.Enum):
        Scheduled = enum.auto()
        """Called when a delayed task has been register in the scheduler for future execution.
        No veto possible."""

        Submitted = enum.auto()
        """Called when a task is submitted to an executor."""

        Started = enum.auto()
        """Called just when the task is starting. No veto possible."""

        Processing = enum.auto()
        """Event entered when the task is about to start, and exited when it has terminated.
        Suitable for context listeners. Veto is possible during the entering part.
        Note that the task may also have been cancelled through the Future."""

        Finished = enum.auto()
        """Called just when the task has terminated. No veto possible."""

        Cancelled = enum.auto()
        """Called when upon running we discover the task is cancelled,
        or when a veto is raised by a context listener."""

    def __init__(self, target: Callable[P, R_co], *args: P.args, **kwargs: P.kwargs) -> None:
        super().__init__()

        self._target = target
        self._args = args
        self._kwargs = kwargs

        # TODO: Find a way to be able to call immediately on Finished listeners whenever the task is already finished upon watching
        self.listeners = KeyedListeners[
            Task.Events,
            Callable[[Self, Future[R_co], Task.Events], Any],
        ](keys=Task.Events)
        self._observables = KeyedObservable(self.listeners)

    def run(self, future: Future[R_co]) -> None:
        # We don't want to inadvertently declare the future as running in case
        # later on we have a listener vetoing (because a future is no longer
        # cancellable if it is already declared as running).
        if future.cancelled():
            future.set_running_or_notify_cancel()
            self._observables[Task.Events.Cancelled](self, future, Task.Events.Cancelled)
            return

        try:
            with self._observables[Task.Events.Processing].fire(
                self, future, Task.Events.Processing
            ):
                if not future.set_running_or_notify_cancel():
                    self._observables[Task.Events.Cancelled](self, future, Task.Events.Cancelled)
                    return

                self._observables[Task.Events.Started](self, future, Task.Events.Started)

                try:
                    result = self._target(*self._args, **self._kwargs)
                except BaseException as exc:  # noqa: BLE001
                    future.set_exception(exc)
                else:
                    future.set_result(result)

            self._observables[Task.Events.Finished](self, future, Task.Events.Finished)

        except VetoError:
            _logger.info('Task %s has been vetoed from running', self)
            future.cancel()
            future.set_running_or_notify_cancel()
            self._observables[Task.Events.Cancelled](self, future, Task.Events.Cancelled)

        finally:
            # Break a reference cycle with the exception 'exc'
            self = None  # noqa: PLW0642

    # def schedule(self, delay: float) -> None:
    #     pass

    @override  # object
    def __str__(self) -> str:
        return 'RequestProcessor.Task [ ]'


class WorkItem(NamedTuple, Generic[P, R_co]):
    priority: int
    counter: int
    # delay: float
    task: Task[P, R_co]
    future: Future[R_co]

    def run(self) -> None:
        self.task.run(self.future)


class ThreadPoolProcessor(ThreadPoolExecutor):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self._work_queue = PriorityQueue[WorkItem[Any, Any]]()  # pyright: ignore[reportAttributeAccessIssue]
        self._task_counter = count()

    def create_item(
        self,
        task: Task[P, R_co],
        priority: int = 1000,
        # delay: float = 0,
    ) -> WorkItem[P, R_co]:
        """Creates a work item ready for submitting.

        Suitable for when you need to access the Future before it is even submitted.
        Otherwise, just use submit() or submit_task()."""

        return WorkItem(
            max(0, priority),
            next(self._task_counter),
            # delay,
            task,
            Future[R_co](),
        )

    def submit_item(self, item: WorkItem[P, R_co]) -> Future[R_co]:
        """Submits a work item to the pool, and returns an associated Future.

        Suitable for when you need to access the Future before it is even submitted.
        Otherwise, just use submit() or submit_task()."""

        with self._shutdown_lock, _global_shutdown_lock:
            if self._broken:
                raise BrokenThreadPool(self._broken)

            if self._shutdown:
                msg = 'cannot schedule new futures after shutdown'
                raise RuntimeError(msg)
            if _shutdown:
                msg = 'cannot schedule new futures after interpreter shutdown'
                raise RuntimeError(msg)

            task = item.task
            future = item.future

            try:
                with task._observables[Task.Events.Submitted].fire(  # pyright: ignore[reportPrivateUsage]
                    task,
                    future,
                    Task.Events.Submitted,
                ):
                    self._work_queue.put(item)  # pyright: ignore[reportArgumentType]
                    self._adjust_thread_count()
                    return future

            except VetoError:
                _logger.info('Item %s has been vetoed from submitting', item)
                future.cancel()
                future.set_running_or_notify_cancel()
                task._observables[Task.Events.Cancelled](task, future, Task.Events.Cancelled)  # pyright: ignore[reportPrivateUsage]
                raise

    def submit_task(
        self,
        task: Task[P, R_co],
        priority: int = 1000,
        # delay: float = 0,
    ) -> Future[R_co]:
        """Submits a task to the pool, and returns an associated Future.

        Suitable for when you need to specify the priority of this submission,
        or when you need to keep a hand on the Task itself
        Otherwise, just use submit()"""

        return self.submit_item(self.create_item(task, priority=priority))  # , delay=delay))

    @override  # ThreadPoolExecutor
    def submit(self, fn: Callable[P, R_co], /, *args: P.args, **kwargs: P.kwargs) -> Future[R_co]:
        """Submits a task to the pool, and returns an associated Future."""

        return self.submit_task(Task(fn, *args, **kwargs))


class RequestProcessor(Executor):
    """RequestProcessor is a concurrent.futures.Executor capable of performing
    asynchronous requests in a dedicated pool.
    """

    _COUNTER = count()
    """The counter for automatic naming of unnamed RequestProcessor"""

    _DEFAULT: RequestProcessor | None = None
    """A unique shared instance for users that do not want to have to own a RequestProcessor"""

    @classmethod
    def get_default(cls) -> RequestProcessor:
        """Getter for the shared instance of RequestProcessor.

        This instance is shared with anybody who needs a way of performing
        sporadic asynchronous work.

        Returns:
            Returns an instance of RequestProcessor that is capable of performing
            a relatively large number of requests in parallel.
        """

        if cls._DEFAULT is None:
            cls._DEFAULT = RequestProcessor(
                name='OpenIDE-RequestProcessor-Default',
                throughput=None,
            )
        return cls._DEFAULT

    @classmethod
    def __shutdown_default(cls, *, wait: bool = True, cancel_futures: bool = False) -> None:  # pyright: ignore[reportUnusedFunction]
        """Special class-method to bypass the no default shutdown check in RequestProcessor.shutdown().

        Only to be called by IDEApplication on exit cleanup.
        """
        if cls._DEFAULT is None:
            return

        cls._DEFAULT._processor.shutdown(wait=wait, cancel_futures=cancel_futures)

    @classmethod
    def for_class(cls, klass: type[Any], throughput: int = 1) -> Self:
        """A convenience constructor for a new RequestProcessor named after the provided class"""

        return cls(klass.__name__, throughput=throughput)

    def __init__(
        self,
        name: str | None = None,
        throughput: int | None = 1,
        *,
        enable_stack_traces: bool = True,
        pool_type: Literal['thread', 'process'] = 'thread',
    ) -> None:
        """Create a new RequestProcessor.

        _extended_summary_

        Args:
            name: The name to use for the request processor thread or process.
                  Defaults to None, meaning auto-assigned.
            throughput: The maximal amount of requests allowed to run in parallel.
                        A None means auto-detection of a high value sensible for this machine.
                        Defaults to 1.
            enable_stack_traces: If True, captures a stack trace when the task is submitted.
                                 When an exception is later thrown from the task, this stack trace
                                 can be used to complement the exception information.
                                 Defaults to True.
            pool_type: Whether this request processor use a thread pool (typically
                       for IO bounded tasks), or a process pool (typically for CPU bounded tasks).
                       Defaults to thread.
        """
        super().__init__()

        if name is not None:
            self._name = name
        else:
            self._name = f'OpenIDE-RequestProcessor-{next(RequestProcessor._COUNTER)}'

        # TODO: See if it makes sense to either make these super-private, or on the contrary, provides getter and setter
        self._throughput = throughput
        self._enable_stack_traces = enable_stack_traces

        if pool_type == 'thread':
            self._processor = ThreadPoolProcessor(
                max_workers=throughput,
                thread_name_prefix=self._name,
            )
        elif pool_type == 'process':
            msg = 'pool_type=process is not implemented yet'
            raise NotImplementedError(msg)

    def create_item(
        self,
        task: Task[P, R_co],
        priority: int = 1000,
        # delay: float = 0,
    ) -> WorkItem[P, R_co]:
        """Creates a work item ready for submitting.

        Suitable for when you need to access the Future before it is even submitted.
        Otherwise, just use submit() or submit_task()."""

        return self._processor.create_item(task, priority=priority)  # , delay=delay)

    def submit_item(self, item: WorkItem[P, R_co]) -> Future[R_co]:
        """Submits a work item to the pool, and returns an associated Future.

        Suitable for when you need to access the Future before it is even submitted.
        Otherwise, just use submit() or submit_task()."""

        return self._processor.submit_item(item)

    def submit_task(
        self,
        task: Task[P, R_co],
        priority: int = 1000,
        # delay: float = 0,
    ) -> Future[R_co]:
        """Submits a task to the pool, and returns an associated Future.

        Suitable for when you need to specify the priority of this submission,
        or when you need to keep a hand on the Task itself
        Otherwise, just use submit()"""

        return self._processor.submit_task(task, priority=priority)  # , delay=delay)

    @override  # Executor
    def submit(self, fn: Callable[P, R_co], *args: P.args, **kwargs: P.kwargs) -> Future[R_co]:
        """Submits a task to the pool, and returns an associated Future."""

        return self._processor.submit(fn, *args, **kwargs)

    @override  # Executor
    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        if self is self._DEFAULT:
            msg = 'Cannot stop default RequestProcessor'
            raise ValueError(msg)

        self._processor.shutdown(wait=wait, cancel_futures=cancel_futures)


RequestProcessor.get_default()


if __name__ == '__main__':

    def work(a: int, b: float) -> float:
        print('Hardly working')
        return a * b

    def listener(
        task: Task[[int, float], float],
        future: Future[float],
        event: Task.Events,
    ) -> None:
        print(f'Task {task} has {event.name}')
        if event == Task.Events.Finished:
            print(f'Result is {future.result()}')

    @contextmanager
    def ctx_listener(
        task: Task[[int, float], float],
        future: Future[float],
        event: Task.Events,
    ) -> Iterator[None]:
        print(f'Task {task} is {event.name}')
        # raise VetoError('Nope')
        yield
        print(f'Task {task} is done {event.name}, result is {future.result()}')

    task = Task(work, 12, 42.0)
    for event in Task.Events:
        if event == Task.Events.Processing:
            task.listeners[event].add(ctx_listener)
        else:
            task.listeners[event].add(listener)

    RP = RequestProcessor.get_default()
    future = RP.submit_task(task)

    wait((future,))

    if not future.cancelled():
        print(f'Done, result is {future.result()}')
    else:
        print('Cancelled')

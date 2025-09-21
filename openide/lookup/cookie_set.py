# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore
""""""

from __future__ import annotations

# System imports
import enum
import logging
import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Literal, Protocol, Self, TypeVar, overload
from weakref import ReferenceType, ref

# Third-party imports
from listeners import Listeners, Observable
from lookups import GenericLookup, InstanceContent, Lookup, LookupProvider
from lookups.generic_lookup import Pair
from lookups.instance_content import Convertor, SimpleItem
from typing_extensions import override

# Local imports
from openide.utils import SingletonABCMeta

_logger = logging.getLogger(__name__)

T = TypeVar('T')
Ck = TypeVar('Ck', bound='Cookie')
if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from typing import Final

    from lookups import Item

__all__: Final = (
    'CookieFactory',
    'CookieSet',
    'CookieSetChangeProtocol',
)


class Cookie:
    """Marker interface for all cookies"""


class CookieSetChangeProtocol(Protocol):
    class ChangeKind(enum.Enum):
        Add = enum.auto()
        Remove = enum.auto()
        Assign = enum.auto()
        Replace = enum.auto()

    @overload
    def __call__(
        self,
        kind: Literal[ChangeKind.Add, ChangeKind.Remove],
        cookie: Cookie,
    ) -> Any: ...  # noqa: ANN401
    @overload
    def __call__(
        self,
        kind: Literal[ChangeKind.Replace],
        cookie: Collection[Pair[Cookie]],
    ) -> Any: ...  # noqa: ANN401


class CookieFactory(Protocol[Ck]):
    """Factory for creating cookies of given class on demand"""

    @abstractmethod
    def create_cookie(self, cls: type[Ck]) -> Ck:
        """Creates a cookie instance for the given class.

        The method may be called more than once.

        Args:
            cls: The cookie class to create

        Returns:
            New cookie instance
        """


# class __QueryMode(threading.local):
#     value: Any | None = None
#     lock: threading.RLock

#     def __init__(self) -> None:
#         super().__init__()
#         self.lock = threading.RLock()


class __CookieEntry(Generic[Ck]):
    """Entry for one cookie convertible with a factory"""

    __slots__ = ('__cookie_ref', '__lock', '_cls', '_factory')

    def __init__(self, factory: CookieFactory[Ck], cls: type[Ck]) -> None:
        super().__init__()

        self._factory = factory
        self._cls = cls
        self.__cookie_ref: ReferenceType[Ck] | None = None
        self.__lock = threading.RLock()

    @overload
    def get_cookie(self, *, create: Literal[True]) -> Ck: ...
    @overload
    def get_cookie(self, *, create: Literal[False]) -> Ck | None: ...
    def get_cookie(self, *, create: bool) -> Ck | None:
        with self.__lock:
            cookie_ref = self.__cookie_ref
            cookie = None if cookie_ref is None else cookie_ref()

            if create and (cookie is None):
                cookie = self._factory.create_cookie(self._cls)
                # NB: Original code allowed null/None. We don't.
                self.__cookie_ref = ref(cookie)

            return cookie


class __CookieEntryPair(Pair[Ck]):
    __slots__ = ('__entry',)

    def __init__(self, entry: __CookieEntry[Ck]) -> None:
        super().__init__()

        self.__entry = entry

    @override  # Item
    def get_display_name(self) -> str:
        return self.__entry._cls.__name__

    @override  # Item
    def get_id(self) -> str:
        return self.__entry._cls.__qualname__

    @override  # Item
    def get_instance(self) -> Ck | None:
        return self.__entry.get_cookie(create=True)

    @override  # Item
    def get_type(self) -> type[Ck]:
        return self.__entry._cls

    @override  # Pair
    def instance_of(self, cls: type[Any]) -> bool:
        return issubclass(self.__entry._cls, cls)

    @override  # Pair
    def creator_of(self, obj: object) -> bool:
        return obj is self.__entry.get_cookie(create=False)

    @override  # object
    def __eq__(self, other: object) -> bool:
        if isinstance(other, type(self)):
            return self.__entry == other.__entry
        else:
            return False

    @override  # object
    def __hash__(self) -> int:
        return hash(self.__entry) + 5


class __CookieConvertor(Convertor[__CookieEntry[Ck], Ck], metaclass=SingletonABCMeta):
    @override  # Convertor
    def convert(self, obj: __CookieEntry[Ck]) -> Ck:
        return obj.get_cookie(create=True)

    @override  # Convertor
    def type(self, obj: __CookieEntry[Ck]) -> type[Ck]:
        return obj._cls

    @override  # Convertor
    def id(self, obj: __CookieEntry[Ck]) -> str:
        return obj._cls.__qualname__

    @override  # Convertor
    def display_name(self, obj: __CookieEntry[Ck]) -> str:
        return obj._cls.__name__


def __cookie_type(cookie: Ck | __CookieEntry[Ck]) -> type[Ck]:
    if isinstance(cookie, __CookieEntry):
        return cookie._cls
    else:
        return type(cookie)


class __Result(Generic[Ck]):
    __slots__ = ('base', 'cookies')

    def __init__(self) -> None:
        super().__init__()

        self.cookies: list[Ck | __CookieEntry[Ck]] | None = None
        self.base: type[Any] | None = None

    @property
    def cookie(self) -> Ck | __CookieEntry[Ck] | None:
        return self.cookies[0] if self.cookies else None

    def add(self, cookie: Ck | __CookieEntry[Ck]) -> None:
        if (cookies := self.cookies) is None:
            self.cookies = [cookie]
            self.base = __cookie_type(cookie)
            return

        new_base = __cookie_type(cookie)
        if (self.base is None) or issubclass(self.base, new_base):
            cookies[0] = cookie
            self.base = new_base
        else:
            cookies.append(cookie)

    def remove(self, cookie: Ck | __CookieEntry[Ck]) -> bool:
        if (cookies := self.cookies) is None:
            return True

        def _list_remove(lst: list[Any], obj: Any) -> bool:  # noqa: ANN401
            try:
                lst.remove(obj)
            except ValueError:
                return False
            else:
                return True

        if _list_remove(cookies, cookie) and not cookies:
            self.base = None
            self.cookies = None
            return True

        self.base = __cookie_type(cookies[0])

        return False


class _PairWrap(Pair[T]):
    def __init__(self, item: Item[T]) -> None:
        super().__init__()

        self.__item = item
        self.__created = False

    @override  # Item
    def get_display_name(self) -> str:
        return self.__item.get_display_name()

    @override  # Item
    def get_id(self) -> str:
        return self.__item.get_id()

    @override  # Item
    def get_instance(self) -> T | None:
        self.__created = True
        return self.__item.get_instance()

    @override  # Item
    def get_type(self) -> type[T]:
        return self.__item.get_type()

    @override  # Pair
    def instance_of(self, cls: type[Any]) -> bool:
        return issubclass(self.get_type(), cls)

    @override  # Pair
    def creator_of(self, obj: object) -> bool:
        return self.__created and (self.get_instance() == obj)

    @override  # object
    def __eq__(self, other: object) -> bool:
        if isinstance(other, type(self)):
            return self.__item == other.__item
        else:
            return False

    @override  # object
    def __hash__(self) -> int:
        return 777 + hash(self.__item)


class CookieSet(LookupProvider):
    __slots__ = ('__content', '__lock', '__lookup', '__map', 'listeners')

    class Before(ABC):
        """Allows to update content of the cookie set just before a query
        for a given class is made."""

        @abstractmethod
        def before_lookup(self, cls: type[Ck]) -> None:
            raise NotImplementedError

    @classmethod
    def create_generic(cls, before: Before) -> Self:
        """Factory method to create a new general purpose cookie set.

        It is possible to store any object into the cookie set, and then obtain
        it using get_lookup() and queries on the returned Lookup.

        The before object can be passed in if one wants to do a lazy initialisation
        of the CookieSet content.

        Args:
            before: The interface to support lazy initialisation

        Returns :
            A new cookie set that can contain any object.
        """

        jar = cls()
        jar.__content = CookieSetContent()
        jar.__lookup = CookieSetLookup(jar.__content, before)

        return jar

    def __init__(self) -> None:
        """Initialise an empty cookie set"""

        super().__init__()

        self.__content: CookieSetContent | None = None
        self.__lookup: CookieSetLookup | None = None
        # self.__query_mode = __QueryMode()
        self.__map: dict[type[Cookie], __Result[Cookie]] = {}
        self.__lock = threading.RLock()

        self.listeners = Listeners[CookieSetChangeProtocol]()
        self._observable = Observable(self.listeners)

    @override  # LookupProvider
    def get_lookup(self) -> Lookup:
        """The lookup associated with this cookie set.

        Keeps track of the same things that are in the cookie set, but presents
        them as being inside the lookup.

        Returns:
            Lookup interface providing access to all cookies.
        """

        return self.__lookup

    def add(self, cookie: Cookie) -> None:
        """Adds a cookie instance to the set.

        Registers the cookie for its actual class and all superclasses.
        Replaces any existing cookie of the same type.

        Insertion order is maintained such that queries for one representation
        class matching several cookie instances will return the first one added.

        Args:
            cookie: Cookie instance to add.
        """

        if cookie is None:  # pyright: ignore[reportUnnecessaryComparison]
            msg = 'Cannot add a None cookie'
            raise ValueError(msg)

        with self._observable.fire(CookieSetChangeProtocol.ChangeKind.Add, cookie):
            self.__add(cookie)

    def __add(self, cookie: Cookie) -> None:
        with self.__lock:
            self.__register_cookie(type(cookie), cookie)

        if (content := self.__content) is not None:
            content.add(cookie)

    def remove(self, cookie: Cookie) -> None:
        """Remove a specific cookie instance from the set.

        Args:
            cookie: Cookie instance to remove
        """

        if cookie is None:  # pyright: ignore[reportUnnecessaryComparison]
            msg = 'Cannot remove a None cookie'
            raise ValueError(msg)

        with self._observable.fire(CookieSetChangeProtocol.ChangeKind.Remove, cookie):
            self.__remove(cookie)

    def __remove(self, cookie: Cookie) -> None:
        with self.__lock:
            self.__unregister_cookie(type(cookie), cookie)

        if (content := self.__content) is not None:
            content.remove(cookie)

    def get_cookie(self, cls: type[Ck]) -> Ck | None:
        """Get a cookie.

        cls: The representation class.

        Returns a cookie assignable to the representation class, or None if there are none.
        """

        if (lookup := self.__lookup) is not None:
            lookup._before_lookup(cls)

        return self.__lookup_cookie(cls)

    def __lookup_cookie(self, cls: type[Ck]) -> Ck | None:
        with self.__lock:
            if (result := self.__find_result(cls)) is None:
                return None

            cookie = result.cookie

        if isinstance(cookie, __CookieEntry):
            cookie = cookie.get_cookie(create=True)

        return cookie

        # to_return = None
        # # query_mode = self.__query_mode.value

        # with self.__lock:
        #     if (result := self.__find_result(cls)) is None:
        #         # if (query_mode is None) or (self.__content is None):
        #         if self.__content is None:
        #             return None
        #     else:
        #         to_return = result.cookie
        #         # if isinstance(query_mode, set):
        #         #     query_mode |= self.__map.keys()

        # if isinstance(to_return, __CookieEntry):
        #     # if query_mode == cls:
        #     #     self.__query_mode.value = to_return
        #     #     to_return = None
        #     # else:
        #     to_return = cast('__CookieEntry[Ck]', to_return).get_cookie(create=True)

        # elif (to_return is None) and (self.__content is not None):
        #     # self.__enhanced_query_mode(self.__lookup, cls)
        #     to_return = None

        # return to_return

    def _lookup_cookie_or_pairs(
        self,
        cls: type[Ck | T],
    ) -> tuple[Ck | None, list[Pair[Ck] | Pair[T]] | None]:
        cookie = None
        with self.__lock:
            if (result := self.__find_result(cls)) is not None:
                cookie = result.cookie

        if (result is None) and ((lookup := self.__lookup) is not None):
            if (not issubclass(cls, Cookie)) or (cls is Cookie):
                return None, self._wrap_pairs_from_lookup(lookup, cls)

            else:
                return None, None

        elif isinstance(cookie, __CookieEntry):
            return None, [__CookieEntryPair(cookie)]

        else:
            return cookie, None

    # NB: In original code this was more or less enhancedQueryMode()
    @staticmethod
    def _wrap_pairs_from_lookup(lookup: Lookup, cls: type[T]) -> list[Pair[T]] | None:
        items = lookup.lookup_result(cls).all_items()
        if not items:
            return None

        return [item if isinstance(item, Pair) else _PairWrap(item) for item in items]

    # def __enhanced_query_mode(self, lookup: Lookup, cls: type[T]) -> None:
    #     clzz = self.__query_mode.value
    #     if clzz != cls:
    #         return

    #     items = lookup.lookup_result(cls).all_items()
    #     if not items:
    #         return

    #     arr = [__PairWrap(item) for item in items]
    #     self.__query_mode.value = arr

    # @contextmanager
    # def _enter_query_mode(self, cls: type[T]) -> Iterator[Collection[Pair[Any]]]:
    #     prev = self.__query_mode.value
    #     self.__query_mode.value = cls

    #     pairs: list[Pair[Any]] = []
    #     try:
    #         yield pairs

    #     finally:
    #         cookie = self.__query_mode.value
    #         self.__query_mode.value = prev

    #         if isinstance(cookie, __CookieEntry):
    #             pairs.append(__CookieEntryPair(cookie))
    #         elif isinstance(cookie, Pair):
    #             pairs.append(cookie)

    # def _entry_query_mode(self, cls: type[T]) -> Any:  # noqa: ANN401
    #     prev = self.__query_mode.value
    #     self.__query_mode.value = cls

    #     return prev

    # def _exit_query_mode(self, prev: Any) -> Collection[Pair[Any]] | None:  # noqa: ANN401
    #     cookie = self.__query_mode.value
    #     self.__query_mode.value = prev

    #     if isinstance(cookie, __CookieEntry):
    #         return (__CookieEntryPair(cookie),)
    #     elif isinstance(cookie, Pair):
    #         return (cookie,)
    #     else:
    #         return None

    # @contextmanager
    # def _enter_all_classes_mode(self) -> Iterator[set[Any]]:
    #     prev = self.__query_mode.value
    #     self.__query_mode.value = set()

    #     a_set = set()
    #     try:
    #         yield a_set
    #     finally:
    #         cookie = self.__query_mode.value
    #         self.__query_mode.value = prev

    #         if isinstance(cookie, set):

    #             return cookie
    #         else:
    #             return None

    # def _entry_all_classes_mode(self) -> Any:  # noqa: ANN401
    #     prev = self.__query_mode.value
    #     self.__query_mode.value = set()

    #     return prev

    # def _exit_all_classes_mode(self, prev: Any) -> set[Any] | None:  # noqa: ANN401
    #     cookie = self.__query_mode.value
    #     self.__query_mode.value = prev

    #     if isinstance(cookie, set):
    #         return cookie
    #     else:
    #         return None

    def __register_cookie(self, cls: type[Ck], cookie: __CookieEntry[Ck] | Ck) -> None:
        """Attaches cookie to given class and all its superclasses"""

        if (result := self.__find_result(cls)) is None:
            self.__map[cls] = result = __Result[Ck]()

        result.add(cookie)

        if len(mro := cls.__mro__) >= 2:
            self.__register_cookie(mro[1], cookie)

    def __unregister_cookie(self, cls: type[Ck], cookie: __CookieEntry[Ck] | Ck) -> None:
        """Removes cookie from the class and all its superclasses"""

        if (result := self.__find_result(cls)) is not None:
            result.remove(cookie)

        if len(mro := cls.__mro__) >= 2:
            self.__unregister_cookie(mro[1], cookie)

    def add_with_factory(self, factory: CookieFactory[Ck], *classes: type[Ck]) -> None:
        """Registers a factory for a given cookie class or set of cookie classes"""

        with self._observable.fire(CookieSetChangeProtocol.ChangeKind.Add, factory):
            entries = [__CookieEntry(factory, cls) for cls in classes]
            with self.__lock:
                for cls, entry in zip(classes, entries, strict=True):
                    self.__register_cookie(cls, entry)

            if (content := self.__content) is not None:
                for entry in entries:
                    content.add(entry, __CookieConvertor())

    def remove_with_factory(self, factory: CookieFactory[Ck], *classes: type[Ck]) -> None:
        """Unregisters a factory for a given cookie class or set of cookie classes"""

        with self._observable.fire(CookieSetChangeProtocol.ChangeKind.Remove, factory):
            with self.__lock:
                entries: list[__CookieEntry[Ck]] = []
                for cls in classes:
                    if (result := self.__find_result(cls)) is None:
                        continue

                    cookie = result.cookie
                    if isinstance(cookie, __CookieEntry):
                        entries.append(cookie)
                        if cookie._factory == factory:
                            self.__unregister_cookie(cls, cookie)

            if (content := self.__content) is not None:
                for entry in entries:
                    content.remove(entry, __CookieConvertor())

    def assign(self, cls: type[Ck], *instances: Ck) -> None:
        """Removes all instances of cls from the set and replaces them with
        the newly provided instances.

        cls: The root class for cookies to remove.
        instances: The one, or more, or none, instances to put into the lookup.
        """

        with self._observable.fire(CookieSetChangeProtocol.ChangeKind.Replace, instances):
            while True:
                if (cookie := self.__lookup_cookie(cls)) is not None:
                    with self.__lock:
                        result = self.__find_result(type(cookie))
                        if (result is not None) and ((arr := result.cookies) is not None):
                            result.base = None
                            result.cookies = None
                            for ckie in arr:
                                self.__unregister_cookie(type(cookie), ckie)

                    self.__unregister_cookie(type(cookie), cookie)
                    if (content := self.__content) is not None:
                        content.remove(cookie)
                else:
                    break

            for instance in instances:
                self.__add(instance)

    def __find_result(self, cls: type[Ck | T]) -> __Result[Ck] | None:
        return self.__map.get(cls)


class CookieSetContent(InstanceContent):
    class IsInReplaceInstances(threading.local):
        value: CookieSetContent | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.is_in_replace_instances = CookieSetContent.IsInReplaceInstances()

    def replace_instances(self, cls: type[Ck], instances: Sequence[Ck], jar: CookieSet) -> None:
        prev = self.is_in_replace_instances.value
        try:
            self.is_in_replace_instances.value = self

            if (lookup := self._generic_lookup) is None:
                msg = 'Content does not seem to be attached to a GenericLookup yet'
                raise RuntimeError(msg)

            pairs: list[Pair[Any]] = []
            changed = False
            index = 0
            for item in lookup.lookup_result(object).all_items():
                if issubclass(item.get_type(), cls):
                    if index < len(instances):
                        if isinstance(item, SimpleItem) and (
                            item.get_instance() == instances[index]
                        ):
                            index += 1
                            pairs.append(item)
                            continue

                        changed = True
                        pairs.append(SimpleItem(instances[index]))
                        index += 1
                    else:
                        changed = True
                else:
                    pairs.append(item)

            for instance in instances[index:]:
                changed = True
                pairs.append(SimpleItem(instance))

            if changed:
                with jar._observable.fire(CookieSetChangeProtocol.ChangeKind.Replace, pairs):
                    self._set_pairs(pairs)

        finally:
            self.is_in_replace_instances.value = prev


class CookieSetLookup(GenericLookup):
    def __init__(self, content: CookieSetContent, before: CookieSet.Before) -> None:
        super().__init__(content)

        self.__before = before
        self.__content = content

    @override  # GenericLookup
    def _before_lookup(self, cls: type[object]) -> None:
        if self.__before and (self.__content.is_in_replace_instances.value is None):
            self.__before.before_lookup(cls)

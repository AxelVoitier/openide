# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:words netbeans
# spell-checker:ignore

# From: https://github.com/apache/netbeans/blob/master/platform/openide.nodes/src/org/openide/nodes/Node.java  # noqa: E501

from __future__ import annotations

import logging
import threading
import warnings
from abc import ABC, abstractmethod

# System imports
from contextlib import contextmanager
from copy import deepcopy
from threading import RLock
from typing import TYPE_CHECKING, Generic, Self, TypeVar, final
from weakref import ReferenceType, ref

# Third-party imports
from lookups import LookupProvider
from typing_extensions import override

# from observable import Observable
# Local imports
from openide.lookup.cookie_set import Cookie
from openide.nodes._like_netbeans.node_listener import NodeEvent, NodeMemberEvent, NodeReorderEvent
from openide.nodes.properties import (
    FeatureDescriptor,
    IndexedProperty,
    Property,
    PropertySet,
    Sheet,
)
from openide.utils.classes import Debug

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Iterator, MutableSequence, Sequence
    from typing import Any, TypeAlias

    from lookups import Lookup, Result
    from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
    from PySide6.QtWidgets import QMenu

    from openide.lookup.cookie_set import CookieSet
    from openide.nodes._like_netbeans.children import Children  # noqa: TC004  # No it's not
    from openide.nodes._like_netbeans.children_storage import ChildrenStorage
    from openide.nodes._like_netbeans.node_listener import NodeListener
    from openide.nodes._like_netbeans.node_lookup import NodeLookup

    Ck = TypeVar('Ck', bound=Cookie)

T = TypeVar('T')
E = TypeVar('E')
AnyNode: TypeAlias = 'Node[Any, Any]'
PN = TypeVar('PN', bound=AnyNode)
N = TypeVar('N', bound=AnyNode)
CN = TypeVar('CN', bound=AnyNode)

_logger = logging.getLogger(__name__)


class _Handle(ABC):
    # Note: That's fore serialisation
    # TODO: Check if we could do differently. Smells like Java-specific construct

    @abstractmethod
    def get_node(self) -> Node:
        raise NotImplementedError  # pragma: no cover


class __BlockEvents(threading.local, Generic[N]):
    value: set[N] | None = None


# TODO: LookupEventList class (private final)


# TODO: Subclasses HelpCtx.Provider
# class Node(Debug(f'{__name__}.Node'), FeatureDescriptor, LookupProvider, ABC):
class Node(FeatureDescriptor, LookupProvider, Generic[PN, CN], ABC):
    # TODO: Review lookups and cookies
    # TODO: Review listeners (node and properties)
    # TODO: Review property changed firing events
    # TODO: FilterNode special treatments (dormant stuffs, and equals/__eq__)
    # TODO: Complete all the "graphical" extra parts (eg. help context, action, icon)
    # TODO: Complete the copy/paste and Drag'n'Drop parts

    # Set in generic_node.py
    EMPTY: Node = None  # type: ignore[assignment]

    Handle: TypeAlias = _Handle
    PropertySet: TypeAlias = PropertySet
    Property: TypeAlias = Property
    IndexedProperty: TypeAlias = IndexedProperty

    # TODO: All property names?
    # TODO: lookups?
    # TODO: TEMPL_COOKIE

    # TODO: INIT_LOCK?
    _LOCK = RLock()

    # TODO: Review
    def __init__(self, children: Children[Self, CN], lookup: Lookup | None = None) -> None:
        super().__init__()

        self._parent: Children[PN, Self] | ChildrenStorage[PN, Self] | None = None
        self._hiearchy = children

        # TODO: transient  # TODO: Actually,
        self._node_listeners: list[NodeListener[Self, CN]] = []
        # it is not a simple list, but seems to be like a list of tuples (listener-class, listener).
        # (It's actually like a list of stride 2...). Could it be even more efficient/usable as a
        # Mapping of listener-class to listeners? Could it be then easily replaced with observable?
        # Note: We seems to be adding only 2 kinds of listener classes: NodeListener,
        # and PropertyChangeListener. Though, it seems as it is right now we just splitted
        # the "listeners" into one for NodeListener, and one for PropertyChangeListener:
        self._property_listeners: MutableSequence[Callable[[Self, str, Any, Any], None]] = []
        self.__delegating_lookup: NodeLookup[Self] | None = None
        self._internal_lookup = self._replace_provided_lookup(
            lookup,
        )  # TODO: Rename _provided_lookup
        if self._internal_lookup is not None:
            self.__result = self._internal_lookup.lookup_result(Cookie)
            self.__result.listeners += self.__lookup_changed
            self.__result.all_items()

        # self.__block_events = __BlockEvents[AnyNode]()

        self._hiearchy._attach_to(self)

    def _replace_provided_lookup(self, lookup: Lookup | None) -> Lookup | None:
        """Subclasses that want to swap the provided lookup based on certain conditions
        (eg. FilterNode) can override this method.

        Will be called only during __init__().
        """

        return lookup

    # TODO: internalLookup (final)

    # TODO: Review
    def __lookup_changed(self, result: Result[Cookie]) -> None:
        self._fire_cookie_change()

    # TODO: Review
    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        """
        Subclasses should first call super().__deepcopy__() to get
        an instance. And then call their own SubClass.__init__(instance, ...)
        (or do the initialisation in __deepcopy__ as they see fit).
        """
        raise NotImplementedError()  # pragma: no cover
        new = Node.__new__(type(self))
        memo[id(self)] = new
        new_hiearchy = deepcopy(self._hiearchy, memo)

        Node.__init__(new, new_hiearchy, self._internal_lookup)

        return new

    # TODO: Review (pythonic?)
    @abstractmethod
    def clone(self) -> Self:
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @property
    def _parent_children(self) -> Children[PN, Self] | None:
        from openide.nodes._like_netbeans.children_storage import ChildrenStorage  # noqa: PLC0415

        if isinstance(self._parent, ChildrenStorage):
            return self._parent.children
        else:
            return self._parent

    # OK, Match
    @final
    def _assign_to(self, parent: Children[PN, Self], index: int) -> None:
        with Node._LOCK:
            p_children = self._parent_children
            if (p_children is not None) and (p_children != parent):
                msg = (
                    f'Cannot initialise {index}th child of node {parent.node} ; '
                    f'It already belongs to node {p_children.node} '
                    '(did you forgot to use Node.clone()?)'
                )
                raise ValueError(msg)

            from openide.nodes._like_netbeans.children_storage import ChildrenStorage  # noqa: I001, PLC0415

            if not isinstance(self._parent, ChildrenStorage):
                self._parent = parent

    # OK, Match
    @final
    def _reassign_to(
        self,
        current_parent: Children[PN, Self],
        children_array: ChildrenStorage[PN, Self],
    ) -> None:
        with Node._LOCK:
            if self._parent not in (current_parent, children_array):
                msg = (
                    f'Unauthorised call to change parent: {current_parent} '
                    f'when it should be {self._parent}'
                )
                raise ValueError(msg)

            self._parent = children_array

    # OK, Match
    @final
    def _deassign_from(self, parent: Children[PN, Self]) -> None:
        with Node._LOCK:
            p_children = self._parent_children
            if parent != p_children:
                msg = f'Deassign from wrong parent: {parent} when it should be {p_children}'
                raise ValueError(msg)

            self._parent = None

    def __set_property(self, name: str, value: str | None) -> None:
        old = getattr(super(), name)

        if old != value:
            # getattr(FeatureDescriptor, name).fset(self, value)  # super().name = value
            getattr(super(Node, type(self)), name).fset(self, value)

            # getattr(self, f'_fire_{name}_change')(old, value)
            self._fire_own_property_change(name, old, value)

    # OK, Match
    @FeatureDescriptor.system_name.setter  # type: ignore[attr-defined]  # mypy bug #5936
    @override  # FeatureDescriptor
    def system_name(self, value: str | None) -> None:
        self.__set_property('system_name', value)

    # OK, Match
    @FeatureDescriptor.display_name.setter  # type: ignore[attr-defined]  # mypy bug #5936
    @override  # FeatureDescriptor
    def display_name(self, value: str | None) -> None:
        self.__set_property('display_name', value)

    # OK, Match
    @FeatureDescriptor.short_description.setter  # type: ignore[attr-defined]  # mypy bug #5936
    @override  # FeatureDescriptor
    def short_description(self, value: str | None) -> None:
        self.__set_property('short_description', value)

    # OK, Match
    @FeatureDescriptor.is_hidden.setter  # type: ignore[attr-defined]  # mypy bug #5936
    @override  # FeatureDescriptor
    def is_hidden(self, value: bool) -> None:
        warnings.warn(
            RuntimeWarning(
                'Setting Node.is_hidden does not do what you think it does. '
                'To hide a node you should remove it from the children of its parent. '
                'For instance, with Children.Keys._set_keys(keys_set) and a smaller keys_set.',
            ),
            stacklevel=2,
        )
        super(Node, type(self)).is_hidden.fset(self, value)  # type: ignore[attr-defined]  # bug5936

    # TODO: Input type parameter
    @property
    @abstractmethod
    def icon(self) -> QIcon | QPixmap | QColor:
        raise NotImplementedError  # pragma: no cover

    # TODO: Input type parameter
    @property
    @abstractmethod
    def opened_icon(self) -> QIcon | QPixmap | QColor:
        # Actually useless thanks to Qt who can embed that info directly in a QIcon (On state)
        raise NotImplementedError  # pragma: no cover

    # TODO: Define return type
    @property
    @abstractmethod
    def help_context(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    # TODO: Resolve Children.LazyChildren
    def _update_children(self) -> None:
        from openide.nodes._like_netbeans.children import _LazyChildren  # noqa: PLC0415

        if isinstance(self._hiearchy, _LazyChildren):
            self._children = self._hiearchy._original

    # OK, Match
    @property  # Also final (set on setter)
    def _children(self) -> Children[Self, CN]:
        self._update_children()
        return self._hiearchy

    # OK, Match
    @_children.setter
    @final
    def _children(self, value: Children[Self, CN]) -> None:
        from openide.nodes._like_netbeans.children import Children  # noqa: PLC0415

        def implementation() -> None:
            snapshot: Sequence[CN] | None = None
            was_initialised = self._hiearchy._is_initialised
            was_leaf = self._hiearchy is Children[Self, CN].LEAF
            if was_initialised and not was_leaf:
                snapshot = self._hiearchy.snapshot()

            self._hiearchy._detach_from()

            if snapshot:
                self._hiearchy = Children[Self, CN].LEAF
                indexes = list(range(len(snapshot)))
                self._fire_sub_nodes_change_idx(False, indexes, None, [], snapshot)  # noqa: FBT003

            self._hiearchy = value
            self._hiearchy._attach_to(self)

            is_leaf = self._hiearchy is Children[Self, CN].LEAF
            if was_initialised and (not was_leaf) and (not is_leaf):
                self._hiearchy.get_nodes_count()
                if snapshot := self._hiearchy.snapshot():
                    indexes = list(range(len(snapshot)))
                    self._fire_sub_nodes_change_idx(True, indexes, None, snapshot, [])  # noqa: FBT003

            if was_leaf != is_leaf:
                self._fire_own_property_change('leaf', was_leaf, is_leaf)

        Children.MUTEX.post_write_request(implementation)

    # OK, Match
    @final
    @property
    def is_leaf(self) -> bool:
        from openide.nodes._like_netbeans.children import Children  # noqa: PLC0415

        self._update_children()
        return self._hiearchy is Children[Self, CN].LEAF

    # OK, Match
    @final
    @property
    def parent_node(self) -> PN | None:
        p_children = self._parent_children
        return p_children.node if p_children is not None else None

    # OK, Match
    @property
    @abstractmethod
    def can_rename(self) -> bool:
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @property
    @abstractmethod
    def can_destroy(self) -> bool:
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    def destroy(self) -> None:
        from openide.nodes._like_netbeans.children import Children  # noqa: PLC0415

        def implementation() -> None:
            p_children = self._parent_children
            if p_children is not None:
                p_children.remove((self,))

            self._fire_node_destroyed()

        Children.MUTEX.post_write_request(implementation)

    @property
    @abstractmethod
    def property_sets(self) -> Sequence[PropertySet]:
        raise NotImplementedError  # pragma: no cover

    # Temp. addition not in Netbeans to directly access the Sheet, because this "public should
    # only access a list of PropertySet and not the Sheet itself" just seems like
    # some whatever Java-trust-issue madness...
    @property
    @abstractmethod
    def sheet(self) -> Sheet:
        raise NotImplementedError  # pragma: no cover

    # TODO: Define return type
    @property
    @abstractmethod
    def clipboard_copy(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError  # pragma: no cover

    # TODO: Define return type
    @property
    @abstractmethod
    def clipboard_cut(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError  # pragma: no cover

    # TODO: Define return type
    @property
    @abstractmethod
    def drag(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @property
    @abstractmethod
    def can_copy(self) -> bool:
        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @property
    @abstractmethod
    def can_cut(self) -> bool:
        raise NotImplementedError  # pragma: no cover

    # TODO: Define return type
    @abstractmethod
    def get_paste_types(self, transferable):  # type: ignore[no-untyped-def]
        raise NotImplementedError  # pragma: no cover

    # TODO: Define return type
    @abstractmethod
    def get_drop_type(self, transferable, action, index: int):  # type: ignore[no-untyped-def]
        raise NotImplementedError  # pragma: no cover

    # TODO: Define return type
    @property
    @abstractmethod
    def new_types(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError  # pragma: no cover

    # TODO: getActions(boolean context)

    # TODO: NodeOp
    # TODO: Actually deprecated, but only in favour of the boolean-arg signature
    #       which redirect to either no-arg getAction, or getContextAction.
    @property
    def actions(self) -> Iterable[QAction | str | None]:
        """Get the set of actions associated with this node.

        This set is used to construct the context menu for the node.

        Returns a list of actions (you may include None or strings for separators).
        """

        from .node_operations import get_default_actions  # noqa: PLC0415

        return get_default_actions()

    @property
    def context_actions(self) -> Iterable[QAction | str | None]:
        """Get a special set of actions for situations when this node is displayed as a context.

        For example, right-clicking on a parent node in a hierarchical view (such as
        a node explorer) should use the actions property. However, if this node
        is serving as the parent of (for instance) a window tab full of icons (e.g., an icon view),
        and the users right-clicks on the empty space in this pane,
        then this method should be used to get the appropriate actions for a context menu.

        Returns by default the same set of actions than the actions property.
        """

        return self.actions

    # TODO: Actually deprecated
    @property
    def default_action(self) -> QAction | None:
        """Gets the default action for this node.

        Returns an action, or None indicating there should be no default action for this node.
        """

        msg = 'Is actually deprecated, try to use preferred_action instead'
        raise NotImplementedError(msg)
        # return None

    @property
    def preferred_action(self) -> QAction | None:
        """Gets the preferred action for this node.

        This action can, but need not be one from the action array returned from
        the actions property.
        In case it is, the context menu created from those actions is encouraged
        to highlight the preferred action.

        Override in subclasses accordingly.

        Returns an action, or None indicating there should be no preferred action for this node.
        """

        return None

    # TODO: NodeOp
    @property
    @final
    def context_menu(self) -> QMenu | None:
        """Makes a context menu for this node."""

        from .node_operations import find_context_menu  # noqa: PLC0415

        menu = find_context_menu((self,))
        if menu is None:
            return None

        preferred_action = self.preferred_action
        if preferred_action is None:
            return menu

        menu.setDefaultAction(preferred_action)
        return menu

    # OK, Match
    @property
    @abstractmethod
    def has_customiser(self) -> bool:
        raise NotImplementedError  # pragma: no cover

    # TODO: Define return type
    @property
    @abstractmethod
    def customiser(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError  # pragma: no cover

    # TODO: Review
    def get_cookie(self, cls: type[Ck]) -> Ck | None:
        if (lookup := self._internal_lookup) is None:
            return None

        obj = lookup(cls)
        # NB: Remove check if it causes performance overhead, and instead rely only on typing.
        # However, it might be implicitly used by NodeLookup.__add_cookie()
        if isinstance(obj, Cookie):
            return obj
        else:
            return None

    @property
    def _supports_cookie_set(self) -> bool:
        return False

    @property
    def _cookie_set(self) -> CookieSet:
        msg = 'CookieSet are not supported on this node'
        raise NotImplementedError(msg)

    @_cookie_set.setter
    def _cookie_set(self, value: CookieSet) -> None:
        msg = 'CookieSet are not supported on this node'
        raise NotImplementedError(msg)

    # TODO: Review
    @final
    @override  # LookupProvider
    def get_lookup(self) -> Lookup:
        if (lookup := self._internal_lookup) is not None:
            return lookup

        if (lookup := self.__delegating_lookup) is None:
            from . import NodeLookup  # noqa: PLC0415

            lookup = self.__delegating_lookup = NodeLookup(self)

        return lookup

    # OK, Match
    # TODO: We have the same in Property and PropertySet.
    # Maybe that should move to FeatureDescriptor?
    @property
    def html_display_name(self) -> str | None:
        """
        Returns an HTML-flavoured version of this property display name.

        This HTML will be processed either by Qt (for GUI), or prompt-toolkit (for CLI).

        If an HTML version is not possible, then it should return None (and avoid returning
        a string that does not contain any HTML).
        """
        return None

    # Not doing: registerDelegatingLookup (final)
    # Not doing: findDelegatingLookup (final)

    # OK, Match
    @property
    @abstractmethod
    def handle(self) -> Handle:
        raise NotImplementedError  # pragma: no cover

    # OK, Match, but
    # TODO: Review the listeners thingies
    @final
    def add_node_listener(self, listener: NodeListener[Self, CN]) -> None:
        self._node_listeners.append(listener)
        self._node_listener_added()

    # OK, Match, but
    # TODO: Compared to _property_change_listener_added,
    # this one do not receive the listener as parameter
    def _node_listener_added(self) -> None:
        pass

    # OK, Match, but
    # TODO: Review the listeners thingies
    @final
    @property
    def _node_listener_count(self) -> int:
        return len(self._node_listeners)

    # OK, Match, but
    # TODO: Review the listeners thingies
    @final
    def remove_node_listener(self, listener: NodeListener[Self, CN]) -> None:
        try:  # noqa: SIM105
            self._node_listeners.remove(listener)
        except ValueError:  # TODO: Case should be handled by listener list implementation
            pass

    # OK, Match, but
    # TODO: Review the listeners thingies
    # TODO: More proper definition of a PropertyChangeListener?
    @final
    def add_property_change_listener(self, listener: Callable[[Self, str, Any, Any], None]) -> None:
        self._property_listeners.append(listener)
        self._property_change_listener_added(listener)

    # OK, Match, but
    # TODO: More proper definition of a PropertyChangeListener?
    def _property_change_listener_added(
        self,
        listener: Callable[[Self, str, Any, Any], None],
    ) -> None:
        pass

    # OK, Match, but
    # TODO: Review the listeners thingies
    @property
    def _property_change_listener_count(self) -> int:
        return len(self._property_listeners)

    # OK, Match, but
    # TODO: Review the listeners thingies
    @final
    @property
    def _has_property_change_listener(self) -> bool:
        return bool(self._property_listeners)

    # OK, Match, but
    # TODO: Review the listeners thingies
    # TODO: More proper definition of a PropertyChangeListener?
    @final
    def remove_property_change_listener(
        self,
        listener: Callable[[Self, str, Any, Any], None],
    ) -> None:
        self._property_listeners.remove(listener)
        self._notify_property_change_listener_removed(listener)

    # OK, Match, but
    # TODO: More proper definition of a PropertyChangeListener?
    def _notify_property_change_listener_removed(
        self,
        listener: Callable[[Self, str, Any, Any], None],
    ) -> None:
        pass

    # OK, Match, except for the dormant part
    # TODO: Originally, all fire names were static string members of the class,
    # plus dedicated firing functions.
    # Maybe that was to be sure one would not fire an unknown/typo event (which
    # would also explain the name check done here).
    # Could that be covered with an enum instead? That would remove the need for
    # the name check, and the _property_sets_are_known thingy.
    @final
    def _fire_property_change(self, name: str, old: Any, new: Any) -> None:  # noqa: ANN401
        if (name is not None) and self._property_sets_are_known:
            for pset in self.property_sets:
                for prop in pset.properties:
                    if prop.system_name == name:
                        break
            else:
                # NB: Originaly it was just a warning
                msg = (
                    f'Node {self.display_name} is trying to trigger on an unknown property, {name}'
                )
                raise ValueError(msg)

        if old == new:
            return

        # TODO: Dormant stuff
        for listener in reversed(self._property_listeners):
            listener(self, name, old, new)

    # OK, Match
    # TODO: See if still needed in case fire-event names are replaced by an enum?
    @property
    def _property_sets_are_known(self) -> bool:
        return False

    # Note: Ignoring all fire*Change as they don't bring much
    # - fireNameChange (protected final)
    # - fireDisplayNameChange (protected final)
    # - fireShortDescriptionChange (protected final)
    # - fireIconChange (protected final)
    # - fireOpenedIconChange (protected final)

    # OK, Match, but
    # TODO: Dormant stuffs
    @final
    def _fire_sub_nodes_change(
        self,
        add_action: bool,  # noqa: FBT001
        nodes_delta: Collection[CN],
        nodes_from: Sequence[CN] | None,
    ) -> None:
        if not self._node_listeners:
            return

        attr = 'children_added' if add_action else 'children_removed'

        from openide.nodes._like_netbeans.children import Children  # noqa: PLC0415

        with Children.MUTEX.read_access():
            event = NodeMemberEvent(self, add=add_action, delta=nodes_delta, from_=nodes_from)

            for listener in reversed(self._node_listeners):
                # TODO: Redo, calling same method (than below) with different args...
                getattr(listener, attr)(event)

    # OK, Match, but
    # TODO: Dormant stuffs
    @final
    def _fire_sub_nodes_change_idx(
        self,
        added: bool,  # noqa: FBT001
        indexes: Sequence[int],
        source_entry: Children.Entry | None,
        current: Sequence[CN],
        previous: Sequence[CN],
    ) -> None:
        if not self._node_listeners:
            return

        attr = 'children_added' if added else 'children_removed'

        with Children.MUTEX.read_access():
            event = NodeMemberEvent(
                self,
                add=added,
                indices=indexes,
                current=current,
                previous=previous,
            )
            event._source_entry = source_entry

            for listener in reversed(self._node_listeners):
                # TODO: Redo, calling same method (than above) with different args...
                getattr(listener, attr)(event)

    # OK, Match, but
    # TODO: Dormant stuffs
    @final
    def _fire_reorder_change(self, indices: Sequence[int]) -> None:
        if not self._node_listeners:
            return

        event = NodeReorderEvent[Self, CN](self, indices)
        for listener in reversed(self._node_listeners):
            listener.children_reordered(event)

    # OK, Match, but
    # TODO: Dormant stuffs
    @final
    def _fire_node_destroyed(self) -> None:
        if not self._node_listeners:
            return

        event = NodeEvent(self)
        for listener in reversed(self._node_listeners):
            listener.node_destroyed(event)

    @final
    def _fire_cookie_change(self) -> None:
        from . import NodeLookup  # noqa: PLC0415

        lookup = self.__delegating_lookup

        if isinstance(lookup, NodeLookup):  # and self.__update_now(self):
            # with self._block_events():
            lookup.update_lookup_as_cookies_are_changed(None)

        self._fire_own_property_change('cookie', None, None)

    # @contextmanager
    # def _block_events(self) -> Iterator[None]:
    #     from . import NodeLookup  # noqa: PLC0415

    #     prev = self.__block_events.value
    #     if prev is None:
    #         self.__block_events.value = set()

    #     try:
    #         yield

    #     finally:
    #         a_set = self.__block_events.value
    #         if prev is None:
    #             while a_set:
    #                 copy = set(a_set)
    #                 for node in copy:
    #                     lookup = node.__delegating_lookup
    #                     if isinstance(lookup, NodeLookup):
    #                         lookup.update_lookup_as_cookies_are_changed(None)

    #                 a_set -= copy

    #         self.__block_events.value = prev

    # def __update_now(self, node: AnyNode) -> bool:
    #     if (a_set := self.__block_events.value) is None:
    #         return True
    #     else:
    #         a_set.add(node)
    #         return False

    # Note: Ignoring all fire*Change as they don't bring much
    # - fireParentNodeChange (protected final)
    # - firePropertySetsChange (protected final)
    # - fireCookieChange (protected final)
    #   - blockEvents (static protected)
    #   - updateNow (static private)
    #   - unblockEvents (static protected)

    # OK, Match, but
    # TODO: Dormant stuffs
    # TODO: There used to be two dedicated functions, fireParentNodeChange and
    # firePropertySetsChange, calling this own, using a static string class member.
    # Like for _fire_property_change, use an enum?
    @final
    def _fire_own_property_change(self, name: str, old: Any, new: Any) -> None:  # noqa: ANN401
        if old == new:
            return

        for listener in reversed(self._node_listeners):
            listener.property_change(self, name, old, new)

    # TODO: equals/__eq__ (FilterNode special treatment)

    # Note: __hash__ relies on super()/FeatureDescriptor __hash__
    # Note: __str__ relies on super()/FeatureDescriptor __str__ (orignally only showing
    # system_name and display name)

    # TODO: removeDormant (private)

# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words deserialisation
# spell-checker:ignore pset
""""""

from __future__ import annotations

# System imports
import logging
import warnings
from abc import ABC, abstractmethod
from copy import deepcopy
from threading import RLock
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    TypeAlias,
    TypeVar,
    cast,
    final,
)

# Third-party imports
from lookups import Lookup, LookupProvider, Result
from typing_extensions import Self, override

# Local imports
from openide.lookup.cookie_set import Cookie
from openide.nodes.properties import FeatureDescriptor

# from .node_listener import NodeEvent, NodeListenersProtocol

T = TypeVar('T')
E = TypeVar('E')
AnyNode: TypeAlias = 'Node[Any, Any]'
NoNode: TypeAlias = 'Node[Any, Any]'

ParentNode = TypeVar('ParentNode', bound='Node[AnyNode, AnyNode]')
ANode = TypeVar('ANode', bound=AnyNode)
ANode_co = TypeVar('ANode_co', bound=AnyNode, covariant=True)
ChildNode = TypeVar('ChildNode', bound='Node[AnyNode, AnyNode]')

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, MutableSequence, Sequence
    from typing import Final

    from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
    from PySide6.QtWidgets import QMenu

    from openide.lookup import Ck, CookieSet
    from openide.nodes import PropertySet
    from openide.nodes.properties import Sheet

    from .children import ChildrenEntry
    from .children import _ChildrenParentNodeInterface as Children
    from .children_storage import ChildrenStorage
    from .node_listener import NodeListener
    from .node_lookup import NodeLookup

__all__: Final = (
    'ANode',
    'AnyNode',
    'ChildNode',
    'NoNode',
    'Node',
    'NodeHandle',
    'ParentNode',
)

_logger = logging.getLogger(__name__)


class NodeHandle(ABC, Generic[ANode_co]):
    """Serialisable node reference.

    The node should not be serialised directly but via this handle. One can obtain
    a handle by a call to `Node.handle` property.

    If that methods returns a non-None value, one can serialise it, and after
    deserialisation use `get_node()` to obtain the original node.
    """

    # Note: That's for serialisation
    # TODO: Check if we could do differently. Smells like Java-specific construct

    @abstractmethod
    def get_node(self) -> ANode_co:
        """Reconstitutes the node for this handle."""

        raise NotImplementedError  # pragma: no cover


# class __BlockEvents(threading.local, Generic[ANode]):
#     value: set[ANode] | None = None


class _NodeBase(FeatureDescriptor, LookupProvider, Generic[ChildNode]):
    if TYPE_CHECKING:
        # Following methods are defined in _NodeListenersMixins
        def _fire_sub_nodes_change(
            self,
            add_action: bool,  # noqa: FBT001
            nodes_delta: Collection[ChildNode],
            nodes_from: Sequence[ChildNode] | None,
        ) -> None: ...  # Used in EntrySupportDefault._notify_remove()
        def _fire_sub_nodes_change_idx(
            self,
            added: bool,  # noqa: FBT001
            indexes: Sequence[int],
            source_entry: ChildrenEntry[ChildNode] | None,
            current: Sequence[ChildNode],
            previous: Sequence[ChildNode],
        ) -> None: ...
        def _fire_reorder_change(
            self,
            indices: Sequence[int],
        ) -> None: ...  # Used by EntrySupportDefault.__update_order()
        def _fire_node_destroyed(self) -> None: ...  # Used by ChildrenKeys._destroy_nodes()
        def _fire_cookie_change(self) -> None: ...
        def _fire_own_property_change(self, name: str, old: Any, new: Any) -> None: ...  # noqa: ANN401

        # Following method is defined in _NodeLookupAndCookieMixin
        def _find_delegating_lookup(self) -> Lookup | None: ...


class _NodePropertiesInterface(_NodeBase[ChildNode], FeatureDescriptor, ABC):
    def _super_property_setter(self, cls: type[Any], name: str, value: Any) -> None:  # noqa: ANN401
        """Sets a property using the setter defined in a super class.

        Useful when you don't want to trigger your descendent, or your own
        property setter, in case it is overridden.

        Args:
            cls: The current class level. The property will be searched below it.
                 This is similar to the first parameter you could give to a super() call.
            name: The name of the property.
            value: The value to set on the property.
        """

        super_cls = cast('type', super(cls, type(self)))
        prop = cast('property', getattr(super_cls, name))
        super_setter = prop.fset
        if super_setter is None:
            msg = f'The property {name} has no setter'
            raise TypeError(msg)
        super_setter(self, value)

    def __set_property(self, name: str, value: str | None) -> None:
        old = getattr(super(), name)

        if old != value:
            self._super_property_setter(_NodePropertiesInterface, name, value)

            # getattr(self, f'_fire_{name}_change')(old, value)
            self._fire_own_property_change(name, old, value)

    # OK, Match
    @FeatureDescriptor.system_name.setter  # type: ignore[attr-defined]  # mypy bug #5936
    @override  # FeatureDescriptor
    def system_name(self, value: str | None) -> None:
        self.__set_property('system_name', value)

    # OK, Match
    @property
    @abstractmethod
    def can_rename(self) -> bool:
        """Test whether this node can be renamed.

        If True, one can use `system_name` property to obtain the current name,
        and use its setter to change it.
        """

        raise NotImplementedError  # pragma: no cover

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

    # TODO: Should be observable
    @property
    @abstractmethod
    def property_sets(self) -> Sequence[PropertySet]:
        """The list of property sets for this node.

        Eg. typically there may be one for normal properties, one for expert properties,
        and one for hidden properties.
        """

        raise NotImplementedError  # pragma: no cover

    # OK, Match
    # TODO: See if still needed in case fire-event names are replaced by an enum?
    @property
    def _property_sets_are_known(self) -> bool:
        """If True, property sets have definitely been computed, and it is fine
        to call `property_sets` property without fear of killing laziness.

        Used from `_fire_property_change()` to only check for bad properties if
        the set of properties has already been computed. Otherwise, don't bother.

        Subclasses may override; GenericNode does.
        """
        return False

    # Temp. addition not in Netbeans to directly access the Sheet, because this "public should
    # only access a list of PropertySet and not the Sheet itself" just seems like
    # some whatever Java-trust-issue madness...
    # TODO: Should be observable
    @property
    @abstractmethod
    def sheet(self) -> Sheet:
        """The sheet of properties (ie. multiple property sets) for this node.

        Eg. typically there may be one for normal properties, one for expert properties,
        and one for hidden properties.
        """

        raise NotImplementedError  # pragma: no cover


class _NodeActionsInterface(_NodeBase[ChildNode]):
    # TODO: getActions(boolean context)

    # TODO: NodeOp
    # TODO: Actually deprecated, but only in favour of the boolean-arg signature
    #       which redirect to either no-arg getAction, or getContextAction.
    @property
    def actions(self) -> Iterable[QAction | str | None]:
        """The set of actions associated with this node.

        This set is used to construct the context menu for the node.

        Returns:
            A list of actions (you may include None or strings for separators).
        """

        from .node_operations import get_default_actions  # noqa: PLC0415

        return get_default_actions()

    @property
    def context_actions(self) -> Iterable[QAction | str | None]:
        """Get a special set of actions for situations when this node is displayed as a context.

        For example, right-clicking on a parent node in a hierarchical view (such
        as a normal explorer) should use the `actions` property. However, if this
        node is serving as the parent of (for instance) a window tab full of icons
        (e.g., an icon view), and the users right-clicks on the empty space in
        this pane, then this method should be used to get the appropriate actions
        for a context menu.

        Returns:
            By default the same set of actions than the actions property.
        """

        return self.actions

    @property
    def preferred_action(self) -> QAction | None:
        """Gets the preferred action for this node.

        This action can, but need not be one from the action array returned from
        the actions property.
        In case it is, the context menu created from those actions is encouraged
        to highlight the preferred action.

        Override in subclasses accordingly.

        Returns:
            An action, or None indicating there should be no preferred action for
            this node.
        """

        return None

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


class _NodeChildrenInterface(_NodeBase[ChildNode], Generic[ParentNode, ChildNode]):
    # TODO: INIT_LOCK?
    _LOCK: ClassVar = RLock()

    def __init__(self, *, children: Children[Self, ChildNode], **kwargs: Any) -> None:
        self._parent: Children[ParentNode, Self] | ChildrenStorage[ParentNode, Self] | None = None
        """Children representing parent node.

        For synchronisation reasons it must be changed only under the Children.MUTEX lock.
        """
        self._hierarchy = children
        """Children "list" (only to be changed under Children.MUTEX)"""

        super().__init__(**kwargs)

        # Attaches children to this node
        self._hierarchy._attach_to(self)

    # OK, Match
    @property
    def _parent_children(self) -> Children[ParentNode, Self] | None:
        """Finds the children we are attached to."""

        from .children_storage import ChildrenStorage  # noqa: PLC0415

        if isinstance(self._parent, ChildrenStorage):
            return self._parent.children
        else:
            return self._parent

    # OK, Match
    @final
    def _assign_to(self, parent: Children[ParentNode, Self], index: int) -> None:
        """Method that allows Children to change the parent children of the node
        when the node is added to a children.

        Args:
            parent: The Children that wants to contain this node.
            index: That will be assigned to this node.

        Raises:
            ValueError: If this node already belongs to a children.
        """

        with Node._LOCK:
            p_children = self._parent_children
            if (p_children is not None) and (p_children != parent):
                msg = (
                    f'Cannot initialise {index}th child of node {parent.node} ; '
                    f'It already belongs to node {p_children.node} '
                    '(did you forgot to use Node.clone()?)'
                )
                raise ValueError(msg)

            from .children_storage import ChildrenStorage  # noqa: PLC0415

            if not isinstance(self._parent, ChildrenStorage):
                self._parent = parent

    # OK, Match
    @final
    def _reassign_to(
        self,
        current_parent: Children[ParentNode, Self],
        children_storage: ChildrenStorage[ParentNode, Self],
    ) -> None:
        """Reassigns the reference to parent from its Children to its ChildrenStorage."""

        with Node._LOCK:
            if self._parent not in (current_parent, children_storage):
                msg = (
                    f'Unauthorised call to change parent: {current_parent} '
                    f'when it should be {self._parent}'
                )
                raise ValueError(msg)

            self._parent = children_storage

    # OK, Match
    @final
    def _deassign_from(self, parent: Children[ParentNode, Self]) -> None:
        """Deassigns the node from a children, when it is removed from a children."""

        with Node._LOCK:
            p_children = self._parent_children
            if parent != p_children:
                msg = f'Deassign from wrong parent: {parent} when it should be {p_children}'
                raise ValueError(msg)

            self._parent = None

    # OK, Match
    # TODO: Resolve Children.LazyChildren
    def _update_children(self) -> None:
        """Can be overridden in subclasses (probably in FilterNode) to check whether
        children are of the right subclass."""

        from .children_implementations import _LazyChildren  # noqa: PLC0415

        if isinstance(self._hierarchy, _LazyChildren):
            self._children = self._hierarchy._original

    # OK, Match
    @property  # Also final (set on setter)
    def _children(self) -> Children[Self, ChildNode]:
        """The list of children."""

        self._update_children()
        return self._hierarchy

    # OK, Match
    @_children.setter
    @final
    def _children(self, value: Children[Self, ChildNode]) -> None:
        """Allows to change Children of the node.

        Call to this setter acquires write lock on the nodes hierarchy. Take care
        not to call this method under read lock.
        """

        from .children import Children  # noqa: PLC0415

        def implementation() -> None:
            snapshot: Sequence[ChildNode] | None = None
            was_initialised = self._hierarchy._is_initialised
            was_leaf = self._hierarchy is Children[Self, ChildNode].LEAF
            if was_initialised and not was_leaf:
                snapshot = self._hierarchy.snapshot()

            self._hierarchy._detach_from()

            if snapshot:
                # Set children to LEAF during firing
                # (cur. snapshot is empty and we should be consistent with children)
                self._hierarchy = Children[Self, ChildNode].LEAF
                indexes = list(range(len(snapshot)))
                # Fire remove event
                self._fire_sub_nodes_change_idx(False, indexes, None, [], snapshot)  # noqa: FBT003

            self._hierarchy = value
            self._hierarchy._attach_to(self)

            is_leaf = self._hierarchy is Children[Self, ChildNode].LEAF
            if was_initialised and (not was_leaf) and (not is_leaf):
                # Init new children if old was inited
                self._hierarchy.get_nodes_count()
                # Fire add event
                if snapshot := self._hierarchy.snapshot():
                    indexes = list(range(len(snapshot)))
                    self._fire_sub_nodes_change_idx(True, indexes, None, snapshot, [])  # noqa: FBT003

            if was_leaf != is_leaf:
                self._fire_own_property_change('leaf', was_leaf, is_leaf)

        Children.MUTEX.post_write_request(implementation)

    # OK, Match
    # TODO: Should be observable?
    @final
    @property
    def is_leaf(self) -> bool:
        """Test whether the node is a leaf, or may contain children."""

        from .children import Children  # noqa: PLC0415

        self._update_children()
        return self._hierarchy is Children[Self, ChildNode].LEAF

    # OK, Match
    # TODO: Should be observable
    @final
    @property
    def parent_node(self) -> ParentNode | None:
        """The parent node, or None if this node is the root of a hierarchy."""

        p_children = self._parent_children
        return p_children.node if p_children is not None else None


class _NodeCopyMixin:
    # TODO: Review
    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        """
        Subclasses should first call super().__deepcopy__() to get
        an instance. And then call their own SubClass.__init__(instance, ...)
        (or do the initialisation in __deepcopy__ as they see fit).
        """
        raise NotImplementedError
        new = Node.__new__(type(self))
        memo[id(self)] = new
        new_hierarchy = deepcopy(self._hierarchy, memo)

        Node.__init__(new, new_hierarchy, self._internal_lookup)

        return new

    # TODO: Review (pythonic?)
    @abstractmethod
    def clone(self) -> Self:
        """Clone the node.

        The newly created node should reference the same object as this node does,
        but it may be added as a child to a different parent node. Also it should
        have an empty set of listeners.
        In all other respects, the node should behave exactly as the original one does.
        """

        raise NotImplementedError  # pragma: no cover


class _NodeCopyPasteDnDInterface(ABC):
    #
    # Copy
    #

    @property
    @abstractmethod
    def can_copy(self) -> bool:
        """Test whether this node premits copying"""

        raise NotImplementedError

    # TODO: Define return type
    @property
    @abstractmethod
    def clipboard_copy(self) -> Any:
        """Called when a node is to be copied to the clipboard.

        Returns:
            The transferable object representing the content of the clipboard.
        """

        raise NotImplementedError

    #
    # Cut
    #

    @property
    @abstractmethod
    def can_cut(self) -> bool:
        """Test whether this node premits cutting"""

        raise NotImplementedError

    # TODO: Define return type
    @property
    @abstractmethod
    def clipboard_cut(self) -> Any:
        """Called when a node is to be cut to the clipboard.

        Returns:
            The transferable object representing the content of the clipboard.
        """

        raise NotImplementedError

    #
    # Drag'n'Drop
    #

    # TODO: Define return type
    @property
    @abstractmethod
    def drag(self) -> Any:
        """Called when a drag is started with this node.

        The node can attach a transfer listener to ExTransferable and will be then
        notified about progress of the drag (accept/reject).

        Returns:
            The transferable to represent this node during a drag.
        """

        raise NotImplementedError

    # TODO: Define types
    @abstractmethod
    def get_paste_types(self, transferable: Any) -> Any:
        """Determines which paste operations are allowed when a given transferable
        is in the clipboard.

        For example, a node representing a Python package will permit modules to
        be pasted into it.

        Args:
            transferable: The transferable in the clipboard.

        Returns:
            Array of operations that are allowed.
        """

        raise NotImplementedError

    # TODO: Define return type
    @abstractmethod
    def get_drop_type(self, transferable: Any, action: QAction, index: int) -> Any:
        """Determines if there is a paste operation that can be performed on provided transferable.

        Used by drag'n'drop code to check whether the drop is possible.

        Args:
            transferable: The transferable.
            action: The drag'n'drop action to do DnDConstants.ACTION_MOVE,
                    ACTION_COPY, or ACTION_LINK.
            index: Index between children the drop occurred at or -1 if not specified.

        Returns:
            None if the transferable cannot be accepted or the paste type to execute
            when the drop occurs.
        """

        raise NotImplementedError

    # TODO: Define return type
    @property
    @abstractmethod
    def new_types(self) -> Any:
        """The new types that can be created in this node.

        For example, a node representing a Python package will permit modules to
        be added.

        Returns:
            Array of new type operations that are allowed.
        """

        raise NotImplementedError


class _NodeListenersMixins(_NodePropertiesInterface[ChildNode], Generic[ChildNode]):
    # listeners: KeyedListeners[NodeEvent, NodeListenersProtocol]
    # properties_listeners: Listeners[PropertyListener[Self, Any]]

    def __init__(self, **kwargs: Any) -> None:
        # self.listeners = KeyedListeners(NodeEvent)
        # self._observable = KeyedObservable(self.listeners)

        # self.properties_listeners = Listeners[PropertyListener[Self, Any]]()

        # TODO: transient  # TODO: Actually,
        self._node_listeners: list[NodeListener[Self, ChildNode]] = []
        """Listeners for changes in hierarchy."""
        # it is not a simple list, but seems to be like a list of tuples (listener-class, listener).
        # (It's actually like a list of stride 2...). Could it be even more efficient/usable as a
        # Mapping of listener-class to listeners? Could it be then easily replaced with observable?
        # Note: We seems to be adding only 2 kinds of listener classes: NodeListener,
        # and PropertyChangeListener. Though, it seems as it is right now we just splitted
        # the "listeners" into one for NodeListener, and one for PropertyChangeListener:
        self._property_listeners: MutableSequence[Callable[[Self, str | None, Any, Any], None]] = []

        # self.__block_events = __BlockEvents[AnyNode]()

        super().__init__(**kwargs)

    # OK, Match, but
    # TODO: Review the listeners thingies
    @final
    def add_node_listener(self, listener: NodeListener[Self, ChildNode]) -> None:
        """Adds a listener to changes in the node's intrinsic properties (name, cookies, etc.).

        The listener is not notified about changes in subnodes until the method
        `children.get_nodes()` is called.
        """

        self._node_listeners.append(listener)
        self._node_listener_added()

    # OK, Match, but
    # TODO: Compared to _property_change_listener_added,
    # this one do not receive the listener as parameter
    def _node_listener_added(self) -> None:
        """A method to notify FilterNode that a listener has been added."""

    # OK, Match, but
    # TODO: Review the listeners thingies
    @final
    @property
    def _node_listener_count(self) -> int:
        return len(self._node_listeners)

    # OK, Match, but
    # TODO: Review the listeners thingies
    @final
    def remove_node_listener(self, listener: NodeListener[Self, ChildNode]) -> None:
        """Removes a node listener."""

        try:  # noqa: SIM105
            self._node_listeners.remove(listener)
        except ValueError:  # TODO: Case should be handled by listener list implementation
            pass

    # OK, Match, but
    # TODO: Review the listeners thingies
    # TODO: More proper definition of a PropertyChangeListener?
    @final
    def add_property_change_listener(
        self,
        listener: Callable[[Self, str | None, Any, Any], None],
    ) -> None:
        """Adds a listener to the node's computed properties."""

        self._property_listeners.append(listener)
        self._notify_property_change_listener_added(listener)

    # OK, Match, but
    # TODO: More proper definition of a PropertyChangeListener?
    def _notify_property_change_listener_added(
        self,
        listener: Callable[[Self, str, Any, Any], None],
    ) -> None:
        """Called to notify subclasses (FilterNode) about addition of PropertyChangeListener."""

    # OK, Match, but
    # TODO: Review the listeners thingies
    @property
    def _property_change_listener_count(self) -> int:
        """The number of property change listeners attached to this node."""

        return len(self._property_listeners)

    # OK, Match, but
    # TODO: Review the listeners thingies
    @final
    @property
    def _has_property_change_listener(self) -> bool:
        """Tells whether the node has any PropertyChangeListeners attached."""

        return bool(self._property_listeners)

    # OK, Match, but
    # TODO: Review the listeners thingies
    # TODO: More proper definition of a PropertyChangeListener?
    @final
    def remove_property_change_listener(
        self,
        listener: Callable[[Self, str | None, Any, Any], None],
    ) -> None:
        """Removes a property change listener."""

        self._property_listeners.remove(listener)
        self._notify_property_change_listener_removed(listener)

    # OK, Match, but
    # TODO: More proper definition of a PropertyChangeListener?
    def _notify_property_change_listener_removed(
        self,
        listener: Callable[[Self, str, Any, Any], None],
    ) -> None:
        """Called to notify subclasses (FilterNode) about removal of PropertyChangeListener."""

    # OK, Match, except for the dormant part
    # TODO: Originally, all fire names were static string members of the class,
    # plus dedicated firing functions.
    # Maybe that was to be sure one would not fire an unknown/typo event (which
    # would also explain the name check done here).
    # Could that be covered with an enum instead? That would remove the need for
    # the name check, and the _property_sets_are_known thingy.
    @final
    def _fire_property_change(self, name: str | None, old: Any | None, new: Any | None) -> None:  # noqa: ANN401
        """Fire a property change event.

        Args:
            name: Name of the changed property (from `property_sets` property);
                  may be None.
            old: Old value. May be None.
            new: New value. May be None.
        """

        if (name is not None) and self._property_sets_are_known:
            for pset in self.property_sets:
                for prop in pset.properties:
                    if prop.system_name == name:
                        break
            else:
                # NB: Originally it was just a warning
                msg = (
                    f'Node {self.display_name} is trying to trigger on an unknown property, {name}'
                )
                raise ValueError(msg)

        if old == new:
            return

        # TODO: Dormant stuff
        for listener in reversed(self._property_listeners):
            listener(self, name, old, new)

    # Note: Ignoring all fire*Change as they don't bring much
    # - fireNameChange (protected final)
    # - fireDisplayNameChange (protected final)
    # - fireShortDescriptionChange (protected final)
    # - fireIconChange (protected final)
    # - fireOpenedIconChange (protected final)

    # OK, Match, but
    # TODO: Dormant stuffs
    @final
    @override
    def _fire_sub_nodes_change(
        self,
        add_action: bool,  # noqa: FBT001
        nodes_delta: Collection[ChildNode],
        nodes_from: Sequence[ChildNode] | None,
    ) -> None:
        """Fires info about some structural change in children.

        Providing type of operation and set of children changed generates event
        describing the change.

        Args:
            add_action: True if the set of children has been added. False if it
                        has been removed.
            nodes_delta: The array with the changed children.
            nodes_from: The array of nodes to take indices from. Can be None if
                        one should find indices from current set of nodes.
        """

        if not self._node_listeners:
            return

        attr = 'children_added' if add_action else 'children_removed'

        from .children import Children  # noqa: PLC0415
        from .node_listener import NodeMemberEvent  # noqa: PLC0415

        # Enter read_access to prevent firing another event before all listeners
        # receive current event.
        with Children.MUTEX.read_access():
            event = NodeMemberEvent(self, add=add_action, delta=nodes_delta, from_=nodes_from)

            for listener in reversed(self._node_listeners):
                # TODO: Redo, calling same method (than below) with different args...
                getattr(listener, attr)(event)

    # OK, Match, but
    # TODO: Dormant stuffs
    @final
    @override
    def _fire_sub_nodes_change_idx(
        self,
        added: bool,
        indexes: Sequence[int],
        source_entry: ChildrenEntry[ChildNode] | None,
        current: Sequence[ChildNode],
        previous: Sequence[ChildNode],
    ) -> None:
        """Fires that some indexes have been removed."""

        if not self._node_listeners:
            return

        attr = 'children_added' if added else 'children_removed'

        from .children import Children  # noqa: PLC0415
        from .node_listener import NodeMemberEvent  # noqa: PLC0415

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
    @override
    def _fire_reorder_change(self, indices: Sequence[int]) -> None:
        """Fires info about reordering of some children.

        Args:
            indices: Array of integers describing the permutation.
        """
        if not self._node_listeners:
            return

        from .node_listener import NodeReorderEvent  # noqa: PLC0415

        event = NodeReorderEvent[Self, ChildNode](self, indices)
        for listener in reversed(self._node_listeners):
            listener.children_reordered(event)

    # OK, Match, but
    # TODO: Dormant stuffs
    @final
    @override
    def _fire_node_destroyed(self) -> None:
        """Fires node destroyed notifications."""

        if not self._node_listeners:
            return

        from .node_listener import NodeEvent  # noqa: PLC0415

        event = NodeEvent(self)
        for listener in reversed(self._node_listeners):
            listener.node_destroyed(event)

    @final
    @override
    def _fire_cookie_change(self) -> None:
        """Fires a change event for PROP_COOKIE.

        The old and new values are set to None.
        """

        from .node_lookup import NodeLookup  # noqa: PLC0415

        lookup = self._find_delegating_lookup()

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
    @override
    def _fire_own_property_change(self, name: str, old: Any, new: Any) -> None:
        """Fires info about change of own property."""

        if old == new:
            return

        for listener in reversed(self._node_listeners):
            listener.property_change(self, name, old, new)

    # TODO: removeDormant (private)


class _NodeLookupAndCookieMixin(_NodeBase[ChildNode], LookupProvider):
    def __init__(self, *, lookup: Lookup | None, **kwargs: Any) -> None:
        self.__delegating_lookup: NodeLookup[Self] | None = None

        super().__init__(**kwargs)

        # Allow subclasses (eg. FilterNode) to update the lookup
        self._internal_lookup = self._replace_provided_lookup(
            lookup,
        )  # TODO: Rename self._provided_lookup
        if self._internal_lookup is not None:
            self.__result = self._internal_lookup.lookup_result(Cookie)
            self.__result.listeners += self.__lookup_changed
            self.__result.all_items()

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
    def get_cookie(self, cls: type[Ck]) -> Ck | None:
        """Get a cookie for this node.

        The set of cookies can change. If a node changes its set of cookies, it
        fires a property change event with PROP_COOKIE.

        If the node was constructed with a Lookup, then this method delegates to
        the provided lookup object.

        Args:
            cls: The representation class of the cookie.

        Returns:
            A cookie assignable to that class, or None if this node has no such
            cookie.
        """

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

    # TODO: Should be observable
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
        """Obtains a Lookup representingadditional content of this Node.

        If the lookup was provided in a constructor, it is returned here.
        If not, a lookup based on the content of `get_cookie()` method is provided.
        """

        if (lookup := self._internal_lookup) is not None:
            return lookup

        if (lookup := self.__delegating_lookup) is None:
            from .node_lookup import NodeLookup  # noqa: PLC0415

            lookup = self.__delegating_lookup = NodeLookup(self)

        return lookup

    # Not doing: registerDelegatingLookup (final)

    # Not doing: findDelegatingLookup (final)
    # But actually, _fire_cookie_change() needs to access it, and otherwise
    # we have it as a __ private...
    @override
    def _find_delegating_lookup(self) -> Lookup | None:
        return self.__delegating_lookup


class _NodeRepresentationInterface(ABC):
    # TODO: Input type parameter
    # TODO: Should be observable
    @property
    @abstractmethod
    def icon(self) -> QIcon | QPixmap | QColor:
        """Find an icon for this node."""

        raise NotImplementedError  # pragma: no cover

    # TODO: Input type parameter
    # TODO: Should be observable
    @property
    @abstractmethod
    def opened_icon(self) -> QIcon | QPixmap | QColor:
        """Find an icon fo this node in the open state.

        This icon should represent the node only when it is opened (when it can
        have children).
        """

        # Actually useless thanks to Qt who can embed that info directly in a QIcon (On state)
        raise NotImplementedError  # pragma: no cover

    # TODO: Define return type
    @property
    @abstractmethod
    def help_context(self) -> Any:
        """Get the context help associated with this node."""

        raise NotImplementedError  # pragma: no cover

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


class _NodeUnknown:
    # OK, Match
    @property
    @abstractmethod
    def has_customiser(self) -> bool:
        """Test whether there is a customiser for this node.

        If True, the customiser can be obtained via the `customiser` property.
        """

        raise NotImplementedError  # pragma: no cover

    # TODO: Define return type
    @property
    @abstractmethod
    def customiser(self) -> Any | None:
        """The customiser widget."""

        raise NotImplementedError  # pragma: no cover


class Node(
    _NodeUnknown,
    _NodeActionsInterface[ChildNode],
    _NodeCopyPasteDnDInterface,
    _NodeRepresentationInterface,
    _NodeListenersMixins[ChildNode],
    _NodeChildrenInterface[ParentNode, ChildNode],
    _NodeLookupAndCookieMixin[ChildNode],
    _NodePropertiesInterface[ChildNode],
    _NodeCopyMixin,
    _NodeBase[ChildNode],
    Generic[ParentNode, ChildNode],
):
    """A node represents one element in a hierarchy of object.

    It provides all methods that are needed for communication between an explorer
    view and the object.

    The node has three purposes:
    - Visually represents the object in the tree hierarchy (ie. Explorer).
    - Provide sets of properties for that object (eg. Property Sheet).
    - Offer actions to perform on itself.

    Frequently nodes are created to represent Data objects. But they may also
    represent anything to be displayed to the user, or manipulated programatically,
    even if they have no data directly stored behind them. For example, a control
    panel, or debugger breakpoint.

    There are two listeners in this class: PropertyChangeListener, and NodeListener
    (which extents PropertyChangeListener). The first is designed to listen on
    properties that can be returned from the `sheet` property. The later for listening
    on changes in the node itself (including name, children, parent, set of properties,
    icons, etc.). Be sure to distinguish between these two.

    The node is cloneable. When a node is cloned, it is initialised with an empty
    set of listeners and no parent. The display name and short description are
    copied to the new node. The set of properties is shared.

    Args:
        ParentNode: The type of this node parent node.
        ChildNode: The type of child nodes this node have.
    """

    # Set in generic_node.py
    EMPTY: Node[Any, NoNode]
    """An empty leaf node"""

    Handle: TypeAlias = NodeHandle[Self]

    def __init__(self, children: Children[Self, ChildNode], lookup: Lookup | None = None) -> None:
        """Initialises a new Node with a given hierarchy, and optionally a lookup.

        Args:
            children: The Children to use for this node
            lookup: The Lookup to provide content of `get_lookup()` and `get_cookie()`.

        Raises:
            RuntimeError: When the children object is already used by a different node.
        """

        super().__init__(children=children, lookup=lookup)

    # TODO: equals/__eq__ (FilterNode special treatment)
    # Note: __hash__ relies on super()/FeatureDescriptor __hash__
    # Note: __str__ relies on super()/FeatureDescriptor __str__ (originally only showing
    # system_name and display name)

    # OK, Match
    @property
    @abstractmethod
    def handle(self) -> NodeHandle[Self] | None:
        """An handle for this node (for serialisation).

        The handle can be serialised and `Handle.get_node()` used after
        deserialisation to obtain the original node.

        Returns:
            The handle, or None if this node is not persistable.
        """

        raise NotImplementedError  # pragma: no cover

    # OK, Match
    @property
    @abstractmethod
    def can_destroy(self) -> bool:
        """Test whether this node can be deleted."""

        raise NotImplementedError  # pragma: no cover

    # OK, Match
    def destroy(self) -> None:
        """Called when a node is deleted.

        Generally you would never call this method yourself (only override it).
        You should perform modifications on the underlying model itself instead.

        The default implementation obtains write access to `Children.MUTEX`, and
        removes the node from its parent (if any). Also fires a property change.

        Subclasses which return True from `can_destroy` property should override
        this method to remove the associated model object from its parent. There
        is no need to call the super method in this case.

        There is no guarantee that after this method has been called, other methods
        such as the `icon` property will not also be called for a little while.
        """

        from .children import Children  # noqa: PLC0415

        def implementation() -> None:
            p_children = self._parent_children
            if p_children is not None:
                # Remove itself from parent
                p_children.remove((self,))

            # Sets the valid flag to false and fires prop. change.
            self._fire_node_destroyed()

        Children.MUTEX.post_write_request(implementation)

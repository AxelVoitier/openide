# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore qapp

from __future__ import annotations

# System imports
import logging
from collections.abc import Callable, Iterable, Sequence
from pprint import pformat as pf
from typing import TYPE_CHECKING, Any, ClassVar

# Third-party imports
import pytest
from PySide6.QtGui import QAction
from typing_extensions import override

# Local imports
from openide.nodes._refactor1 import (
    ANode,
    AnyNode,
    ChildNode,
    Children,
    ChildrenArray,
    Node,
    NodeMemberEvent,
    NoNode,
    ParentNode,
)
from openide.nodes._refactor1.children_implementations import _EmptyChildren

from .minimal_node import MinimalNode
from .node_listener import Listener

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)
_logger = logging.getLogger(__name__)


def test_instantiate_minimal_node() -> None:
    assert MinimalNode(Children.LEAF)


#
# Properties
#


@pytest.mark.parametrize(
    ('name', 'init_value', 'set_value'),
    [
        ('system_name', None, 'test'),
        ('display_name', None, 'test'),
        ('short_description', None, 'test'),
    ],
)
def test_set_property(name: str, init_value: Any, set_value: Any) -> None:  # noqa: ANN401
    node = MinimalNode(Children.LEAF)
    listener = Listener[NoNode, NoNode]()
    node.add_node_listener(listener)

    assert getattr(node, name) == init_value

    setattr(node, name, set_value)

    assert getattr(node, name) == set_value

    assert listener.called == dict(
        property_change=[dict(node=node, name=name, old=init_value, new=set_value)],
    )


def test_properties_is_hidden() -> None:
    node = MinimalNode(Children.LEAF)
    listener = Listener[NoNode, NoNode]()
    node.add_node_listener(listener)

    assert node.is_hidden is False

    with pytest.warns(RuntimeWarning):
        node.is_hidden = True

    assert node.is_hidden is True
    assert not listener.called  # Not called in case of is_hidden


def test_property_sets_are_known() -> None:
    node = MinimalNode(Children.LEAF)
    assert node._property_sets_are_known is False


def test_html_display_name() -> None:
    node = MinimalNode(Children.LEAF)
    assert node.html_display_name is None


#
# Actions
#


class MinimalWithActionsNode(MinimalNode[ParentNode, ChildNode]):
    _REF_ACTIONS: ClassVar[tuple[QAction | str | None, ...] | None] = None

    @classmethod
    def ref_actions(cls) -> tuple[QAction | str | None, ...]:
        if (actions := cls._REF_ACTIONS) is None:
            actions = cls._REF_ACTIONS = (  # pyright: ignore[reportConstantRedefinition]
                QAction(text='action1'),
                QAction(text='action2'),
                None,
                QAction(text='action3'),
                '',
                QAction(text='action4'),
                'Section',
                QAction(text='action5'),
                # TODO: Should we also test with ContextAwareAction and ContextMenuPresenter?
                #       Or leave that to tests for openide.actions?
            )
        return actions

    @property
    @override
    def actions(self) -> Iterable[QAction | str | None]:
        return self.ref_actions()


class MinimalWithActionsWithPreferredNode(MinimalWithActionsNode[ParentNode, ChildNode]):
    @property
    @override
    def preferred_action(self) -> QAction | None:
        action = self.ref_actions()[1]
        assert isinstance(action, QAction)
        return action


@pytest.mark.parametrize(
    ('node_cls', 'fixture_actions_cb'),
    [
        (MinimalNode, lambda: ()),
        (MinimalWithActionsNode, MinimalWithActionsNode.ref_actions),
        (MinimalWithActionsWithPreferredNode, MinimalWithActionsWithPreferredNode.ref_actions),
    ],
)
def test_actions(
    qapp: QApplication,
    node_cls: type[AnyNode],
    fixture_actions_cb: Callable[[], tuple[QAction | str | None, ...]],
) -> None:
    node = node_cls(Children.LEAF)
    assert node.actions == fixture_actions_cb()


@pytest.mark.parametrize(
    ('node_cls', 'fixture_actions_cb'),
    [
        (MinimalNode, lambda: ()),
        (MinimalWithActionsNode, MinimalWithActionsNode.ref_actions),
        (MinimalWithActionsWithPreferredNode, MinimalWithActionsWithPreferredNode.ref_actions),
    ],
)
def test_context_actions(
    qapp: QApplication,
    node_cls: type[AnyNode],
    fixture_actions_cb: Callable[[], tuple[QAction | str | None, ...]],
) -> None:
    node = node_cls(Children.LEAF)
    assert node.context_actions == fixture_actions_cb()


@pytest.mark.parametrize(
    ('node_cls', 'fixture_pref_action_cb'),
    [
        (MinimalNode, lambda: None),
        (MinimalWithActionsNode, lambda: None),
        (
            MinimalWithActionsWithPreferredNode,
            lambda: MinimalWithActionsWithPreferredNode.ref_actions()[1],
        ),
    ],
)
def test_preferred_actions_default(
    qapp: QApplication,
    node_cls: type[AnyNode],
    fixture_pref_action_cb: Callable[[], QAction | None],
) -> None:
    node = node_cls(Children.LEAF)
    assert node.preferred_action == fixture_pref_action_cb()


@pytest.mark.parametrize(
    ('node_cls', 'fixture_actions_cb'),
    [
        (MinimalNode, lambda: ()),
        (MinimalWithActionsNode, MinimalWithActionsNode.ref_actions),
        (MinimalWithActionsWithPreferredNode, MinimalWithActionsWithPreferredNode.ref_actions),
    ],
)
def test_context_menu(
    qapp: QApplication,
    node_cls: type[AnyNode],
    fixture_actions_cb: Callable[[], tuple[QAction | str | None, ...]],
) -> None:
    node = node_cls(Children.LEAF)
    fixture_actions = fixture_actions_cb()

    menu = node.context_menu
    if not fixture_actions:
        assert menu is None
    else:
        assert menu
        menu_actions = menu.actions()
        if not fixture_actions:
            assert not menu_actions
        else:
            for menu_action, fixture_action in zip(menu_actions, fixture_actions, strict=True):
                if isinstance(fixture_action, QAction):
                    assert menu_action == fixture_action
                elif fixture_action is None:
                    assert menu_action.isSeparator()
                else:
                    assert menu_action.isSeparator()
                    assert menu_action.text() == fixture_action

        assert menu.defaultAction() == node.preferred_action


#
# Children
#


class MinimalChildren(Children[ANode, ChildNode]):
    @override
    def add(self, nodes: Sequence[NoNode]) -> bool:
        raise NotImplementedError

    @override
    def remove(self, nodes: Sequence[NoNode]) -> bool:
        raise NotImplementedError


def test_children_attach() -> None:
    children = MinimalChildren[MinimalNode[NoNode, NoNode], NoNode]()
    node = MinimalNode(children)
    assert children._parent is node


def test_children_attach_once() -> None:
    children = MinimalChildren[MinimalNode[NoNode, NoNode], NoNode]()
    MinimalNode(children)

    with pytest.raises(ValueError):  # noqa: PT011
        MinimalNode(children)


def test_children_cannot_change_parent() -> None:
    child_node = MinimalNode(Children.LEAF, name='child_node')
    parent_node1 = MinimalNode[NoNode, MinimalNode[AnyNode, NoNode]](
        ChildrenArray([child_node]),
        name='parent_node1',
    )
    # Force initialisation of supports, which does the actual parenting of child_node
    # (that's a quirk/bug of ChildrenArray).
    parent_node1._children.get_nodes()

    parent_node2 = MinimalNode[NoNode, MinimalNode[AnyNode, NoNode]](
        ChildrenArray([child_node]),
        name='parent_node2',
    )
    with pytest.raises(ValueError):  # noqa: PT011
        parent_node2._children.get_nodes()


@pytest.mark.parametrize(
    ('children', 'expected'),
    [
        (Children.LEAF, True),
        (ChildrenArray(), False),
        (_EmptyChildren(), False),
    ],
)
def test_is_leaf(children: Children[AnyNode, AnyNode], *, expected: bool) -> None:
    parent_node = MinimalNode(children, name='parent_node')
    assert parent_node.is_leaf is expected


def test_swap_children() -> None:
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()
    listener_child = Listener[AnyNode, NoNode]()

    child_node1 = MinimalNode(Children.LEAF, name='child_node1')
    child_node1.add_node_listener(listener_child)
    children1 = ChildrenArray[MinimalNode[NoNode, AnyNode], AnyNode]([child_node1])
    children1.get_nodes()  # Force initialisation of entry support

    child_node2 = MinimalNode(Children.LEAF, name='child_node2')
    child_node2.add_node_listener(listener_child)
    children2 = ChildrenArray[MinimalNode[NoNode, AnyNode], AnyNode]([child_node2])
    children2.get_nodes()  # Force initialisation of entry support

    parent_node = MinimalNode[NoNode, AnyNode](children1, name='parent_node')
    parent_node.add_node_listener(listener_parent)
    assert parent_node._children.get_nodes() == [child_node1]
    assert child_node1.parent_node == parent_node
    assert child_node2.parent_node is None
    listener_parent.called.clear()
    listener_child.called.clear()

    # Testing swap of parent/children
    _logger.info('Swapping parent...')
    parent_node._children = children2
    _logger.info('Swapping done')
    assert parent_node._children.get_nodes() == [child_node2]
    assert child_node1.parent_node is None
    assert child_node2.parent_node == parent_node

    # Listener parent
    _logger.info('listener_parent.called=%s', listener_parent.called)
    assert len(listener_parent.called['children_removed']) == 1
    removed_event = listener_parent.called['children_removed'][0]['event']
    assert isinstance(removed_event, NodeMemberEvent)
    assert removed_event.node == parent_node
    assert removed_event.is_add_event is False
    assert removed_event.delta_indices == [0]
    assert removed_event.prev_snapshot == (child_node1,)
    assert removed_event.snapshot == []
    del listener_parent.called['children_removed']

    assert len(listener_parent.called['children_added']) == 1
    added_event = listener_parent.called['children_added'][0]['event']
    assert isinstance(added_event, NodeMemberEvent)
    assert added_event.node == parent_node
    assert added_event.is_add_event is True
    assert added_event.delta_indices == [0]
    assert added_event.prev_snapshot == []
    assert added_event.snapshot == (child_node2,)
    del listener_parent.called['children_added']

    assert not listener_parent.called

    # Listener child
    _logger.info('listener_child.called=%s', pf(listener_child.called))
    assert listener_child.called['property_change'] == [
        dict(node=child_node1, name='parentNode', old=parent_node, new=None),
        dict(node=child_node2, name='parentNode', old=None, new=parent_node),
    ]

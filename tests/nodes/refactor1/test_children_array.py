# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore

from __future__ import annotations

# System imports
import contextlib
import logging
from collections import defaultdict
from typing import Any, cast

# Third-party imports
import pytest

# Local imports
from openide.nodes._refactor1 import AnyNode, Children, ChildrenArray, Node, NodeMemberEvent, NoNode

from .minimal_node import MinimalNode
from .node_listener import Listener

logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)
_logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    'lazy',
    [
        False,
        pytest.param(True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
    ],
)
def test_initialisation_blank(*, lazy: bool) -> None:
    children = ChildrenArray[NoNode, NoNode](_lazy=lazy)
    assert children.node is None
    assert children.get_nodes() == []
    assert children._is_lazy is lazy


@pytest.mark.parametrize('lazy', [False, True])
def test_initialisation_empty(*, lazy: bool) -> None:
    backed: list[NoNode] = []
    children = ChildrenArray[NoNode, NoNode](_nodes=backed, _lazy=lazy)
    assert children.node is None
    assert children.get_nodes() == []
    assert children._is_lazy is False  # When backed it is forced to not-lazy


@pytest.mark.parametrize('lazy', [False, True])
def test_initialisation_populated(*, lazy: bool) -> None:
    backed: list[MinimalNode[NoNode, NoNode]] = [
        MinimalNode[NoNode, NoNode](Children.LEAF, name='node1'),
        MinimalNode[NoNode, NoNode](Children.LEAF, name='node2'),
        MinimalNode[NoNode, NoNode](Children.LEAF, name='node3'),
    ]
    children = ChildrenArray[NoNode, MinimalNode[NoNode, NoNode]](_nodes=backed, _lazy=lazy)
    assert children.node is None
    assert children.get_nodes() == backed
    assert children._is_lazy is False  # When backed it is forced to not-lazy


@pytest.mark.parametrize(
    ('parent_node', 'lazy'),
    [
        (None, False),
        (MinimalNode(Children.LEAF), False),
        pytest.param(None, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(MinimalNode(Children.LEAF), True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
    ],
)
def test_add_empty(parent_node: Node[NoNode, AnyNode] | None, *, lazy: bool) -> None:
    # Setup
    children = ChildrenArray[Node[NoNode, AnyNode], AnyNode](_lazy=lazy)
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()

    if parent_node is not None:
        parent_node._children = children
        parent_node.system_name = 'parent_node'
        parent_node.add_node_listener(listener_parent)

    # Test empty add when there are no node already
    assert not children.add(()), 'Children.add() added something from nothing'
    # Check children see no nodes
    assert children._is_initialised is False, 'Children has initialised entry support too early'
    assert children.get_nodes() == [], children.get_nodes()
    assert children._is_initialised is True, 'Children did not initialised entry support'
    # Check listener was never notified of anything
    assert not listener_parent.called


def check_children_added_event(
    called: dict[str, list[dict[str, Any]]],
    parent_node: AnyNode,
    snapshot: tuple[AnyNode, ...],
    added_nodes: list[AnyNode],
    indices: list[int],
) -> None:
    assert 'children_added' in called
    assert len(called['children_added']) == 1
    assert len(called['children_added'][0]) == 1
    assert 'event' in called['children_added'][0]
    event = cast(
        'NodeMemberEvent[MinimalNode[NoNode, AnyNode], NoNode]',
        called['children_added'][0]['event'],
    )
    assert event.node == parent_node
    assert event.is_add_event is True
    assert event.snapshot == snapshot

    prev_snapshot = list(snapshot)
    for idx in reversed(indices):
        prev_snapshot.pop(idx)

    with pytest.raises(AssertionError):  # BUG #5
        assert event.prev_snapshot == prev_snapshot

    assert event.delta == added_nodes
    assert event.delta_indices == indices


@pytest.mark.parametrize(
    ('parent_node', 'lazy'),
    [
        (None, False),
        (MinimalNode(Children.LEAF), False),
        pytest.param(None, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(MinimalNode(Children.LEAF), True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
    ],
)
def test_add(parent_node: Node[NoNode, AnyNode] | None, *, lazy: bool) -> None:
    def check(
        nodes_to_add: tuple[MinimalNode[Node[NoNode, AnyNode], NoNode], ...],
        all_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        added_nodes_indices: list[int],
    ) -> None:
        nonlocal first_run

        if nodes_to_add:
            assert children.add(nodes_to_add), 'Children.add() did not add'
        else:
            assert not children.add(nodes_to_add), 'Children.add() added something from nothing'

        #
        # Check each node has its parent children set (if any)
        for node in nodes_to_add:
            assert node._parent_children is children, node._parent_children
            assert node.parent_node is parent_node

        #
        # Check children do see the nodes
        assert children.node is parent_node, 'Confused with children parent node'

        if first_run:
            assert children._is_initialised is False, (
                'Children has initialised entry support too early'
            )
        else:
            assert children._is_initialised is True, 'Children resetted entry support'

        assert children.get_nodes() == all_nodes, children.get_nodes()

        if first_run:
            assert children._is_initialised is True, 'Children did not initialised entry support'

        #
        # Listeners
        if parent_node:
            #
            # Check parent listener
            if not first_run and added_nodes_indices:
                # Listener not called on first add because entry support was not created yet (...)
                check_children_added_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=tuple(all_nodes),
                    added_nodes=list(nodes_to_add),
                    indices=added_nodes_indices,
                )
            else:
                assert not listener_parent.called
            listener_parent.called.clear()

            #
            # Check child listener
            events = listener_child.called['property_change']
            notified_for_nodes: dict[AnyNode, int] = defaultdict(int)
            for event in events:
                node = cast('AnyNode', event['node'])
                notified_for_nodes[node] += 1
                assert event == dict(node=node, name='parentNode', old=None, new=parent_node)

            for i in added_nodes_indices:
                node = all_nodes[i]
                assert node in notified_for_nodes, f'Node {node} never notified'
                assert notified_for_nodes[node] == 1, f'Node {node} notified more than once'
                del notified_for_nodes[node]

            assert not notified_for_nodes, (
                'More nodes have been called than they should',
                notified_for_nodes,
            )

            listener_child.called.clear()

        else:  # No parent node
            assert not listener_parent.called

            # In the case of the child nodes, while entry support might call
            # _fire_own_property_change directly, there is further down a check
            # if old == new to not fire (in if there is no actual parent node,
            # then new is None, which corresponds to old).
            assert not listener_child.called

        first_run = False

    # Setup
    first_run = True
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()
    listener_child = Listener[AnyNode, NoNode]()
    children = ChildrenArray[Node[NoNode, AnyNode], AnyNode](_lazy=lazy)

    if parent_node is not None:
        parent_node._children = children
        parent_node.system_name = 'parent_node'
        parent_node.add_node_listener(listener_parent)

    node1 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node1')
    node1.add_node_listener(listener_child)
    node2 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node2')
    node2.add_node_listener(listener_child)
    node3 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node3')
    node3.add_node_listener(listener_child)
    node4 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node4')
    node4.add_node_listener(listener_child)

    # Test single add
    check((node1,), [node1], [0])

    # Test a second node after entry support has been initialised
    check((node2,), [node1, node2], [1])

    # Test the same first node (entry support should deduplicate it)
    check((node1,), [node1, node2], [])

    # Test empty add when there are already nodes
    check((), [node1, node2], [])

    # Test multiple adds
    check((node3, node4), [node1, node2, node3, node4], [2, 3])


def check_children_removed_event(
    called: dict[str, list[dict[str, Any]]],
    parent_node: AnyNode,
    snapshot: tuple[AnyNode, ...],
    removed_nodes: list[AnyNode],
    indices: list[int],
) -> None:
    assert 'children_removed' in called
    assert len(called['children_removed']) == 1
    assert len(called['children_removed'][0]) == 1
    assert 'event' in called['children_removed'][0]
    event = cast(
        'NodeMemberEvent[MinimalNode[NoNode, AnyNode], NoNode]',
        called['children_removed'][0]['event'],
    )
    assert event.node == parent_node
    assert event.is_add_event is False
    assert event.snapshot == snapshot
    prev_snapshot = list(snapshot)
    for node, idx in zip(removed_nodes, indices, strict=True):
        prev_snapshot.insert(idx, node)
    assert event.prev_snapshot == prev_snapshot
    assert event.delta == set(removed_nodes)
    assert event.delta_indices == indices


@pytest.mark.parametrize(
    ('parent_node', 'lazy'),
    [
        (None, False),
        (MinimalNode(Children.LEAF), False),
        pytest.param(None, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(MinimalNode(Children.LEAF), True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
    ],
)
def test_remove(parent_node: Node[NoNode, AnyNode] | None, *, lazy: bool) -> None:  # noqa: C901
    def check(
        nodes_to_remove: tuple[MinimalNode[Node[NoNode, AnyNode], NoNode], ...]
        | list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        all_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        removed_nodes_indices: list[int],
    ) -> None:
        nonlocal first_run

        if removed_nodes_indices:
            assert children.remove(nodes_to_remove), 'Children.remove() did not remove'
        else:
            assert not children.remove(()), 'Children.remove() removed from nothing'

        #
        # Check node has its parent cleared
        # Filter for various buggy conditions
        if (not parent_node or first_run) and removed_nodes_indices:
            for node in nodes_to_remove:
                with pytest.raises(AssertionError):  # BUG #1 or #2 depending on first_run
                    assert node._parent_children is None
                if parent_node:  # BUG #2 would only appear if there was a parent_node
                    with pytest.raises(AssertionError):  # BUG #1 or #2 depending on first_run
                        assert node.parent_node is None
                else:
                    assert node.parent_node is None
        else:
            for node in nodes_to_remove:
                assert node._parent_children is None
                assert node.parent_node is None

        #
        # Check children still see the right set of nodes
        if first_run:
            assert children._is_initialised is False, (
                'Children has initialised entry support too early'
            )
        else:
            assert children._is_initialised is True, 'Children resetted entry support'

        assert children.get_nodes() == all_nodes, children.get_nodes()

        if first_run:
            assert children._is_initialised is True, 'Children did not initialised entry support'

        #
        # Listeners
        if parent_node:
            #
            # Check parent listener
            if not first_run and removed_nodes_indices:
                # Listener not called on first add because entry support was not created yet (...)
                check_children_removed_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=tuple(all_nodes),
                    removed_nodes=list(nodes_to_remove),
                    indices=removed_nodes_indices,
                )
            else:
                assert not listener_parent.called
            listener_parent.called.clear()

            #
            # Check child listener
            events = listener_child.called['property_change']
            notified_for_nodes: dict[AnyNode, int] = defaultdict(int)
            for event in events:
                node = cast('AnyNode', event['node'])
                notified_for_nodes[node] += 1
                assert event == dict(node=node, name='parentNode', old=parent_node, new=None)

            if not first_run:  # BUG #2
                for node, _ in zip(nodes_to_remove, removed_nodes_indices, strict=False):
                    assert node in notified_for_nodes, f'Node {node} never notified'
                    assert notified_for_nodes[node] == 1, f'Node {node} notified more than once'
                    del notified_for_nodes[node]

            assert not notified_for_nodes, (
                'More nodes have been called than they should',
                notified_for_nodes,
            )

            listener_child.called.clear()
        else:
            assert not listener_parent.called
            assert not listener_child.called

        first_run = False

    # Setup
    first_run = True
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()
    listener_child = Listener[AnyNode, NoNode]()
    children = ChildrenArray[Node[NoNode, AnyNode], AnyNode](_lazy=lazy)

    if parent_node is not None:
        parent_node._children = children
        parent_node.system_name = 'parent_node'
        parent_node.add_node_listener(listener_parent)

    node1 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node1')
    node1.add_node_listener(listener_child)
    node2 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node2')
    node2.add_node_listener(listener_child)
    node3 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node3')
    node3.add_node_listener(listener_child)
    node4 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node4')
    node4.add_node_listener(listener_child)
    node5 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node5')
    node5.add_node_listener(listener_child)
    node6 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node6')  # Not adding it
    node6.add_node_listener(listener_child)

    children.add((node1, node2, node3, node4, node5))
    listener_parent.called.clear()
    listener_child.called.clear()

    # Test remove one
    check((node2,), [node1, node3, node4, node5], [1])

    # Test remove multiple
    check((node3, node4), [node1, node5], [1, 2])

    # Test remove none
    check((), [node1, node5], [])

    # Test remove not present
    check((node6,), [node1, node5], [])

    # Test remove all (needs to be a list and not a tuple to pass equality test)
    check([node1, node5], [], [0, 1])

    # Test remove not present on empty
    check((node6,), [], [])

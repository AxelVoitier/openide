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
import logging
from collections import defaultdict
from collections.abc import MutableMapping
from pprint import pformat as pf
from typing import Any, cast

# Third-party imports
import pytest

# Local imports
from openide.nodes._refactor1 import AnyNode, Children, ChildrenMap, Node, NodeMemberEvent, NoNode

from .minimal_node import MinimalNode
from .node_listener import Listener

logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)
_logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    'map',
    [
        None,
        {},
        dict(
            node1=MinimalNode[NoNode, NoNode](Children.LEAF, name='node1'),
            node2=MinimalNode[NoNode, NoNode](Children.LEAF, name='node2'),
            node3=MinimalNode[NoNode, NoNode](Children.LEAF, name='node3'),
        ),
    ],
)
def test_initialisation(map: MutableMapping[str, NoNode] | None) -> None:
    children = ChildrenMap[str, NoNode, NoNode](_map=map)
    assert children.node is None
    assert children._map == (map or {})
    assert children.get_nodes() == list((map or {}).values())
    assert children._is_lazy is False


@pytest.mark.parametrize('parent_node', [None, MinimalNode(Children.LEAF, name='parent_node')])
def test_put_all_empty(parent_node: Node[NoNode, AnyNode] | None) -> None:
    # Setup
    children = ChildrenMap[str, Node[NoNode, AnyNode], AnyNode]()
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()

    if parent_node is not None:
        parent_node._children = children
        parent_node.add_node_listener(listener_parent)

    # Test empty add when there are no node already
    children._put_all({})
    # Check children see no nodes
    assert children._is_initialised is False, 'Children has initialised entry support too early'
    assert children._map == {}
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
    assert event.prev_snapshot == prev_snapshot

    assert event.delta == added_nodes
    assert event.delta_indices == indices


@pytest.mark.parametrize('parent_node', [None, MinimalNode(Children.LEAF, name='parent_node')])
def test_put(parent_node: Node[NoNode, AnyNode] | None) -> None:
    def check(
        key_to_add: str,
        node_to_add: MinimalNode[Node[NoNode, AnyNode], NoNode],
        all_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        added_nodes_indices: list[int],
        removed_node: MinimalNode[Node[NoNode, AnyNode], NoNode] | None = None,
        removed_nodes_indices: list[int] | None = None,
    ) -> None:
        nonlocal first_run
        assert (removed_node is None) is (removed_nodes_indices is None)

        children._put(key_to_add, node_to_add)

        #
        # Check the node has its parent children set (if any)
        if not first_run:  # Hu, another NB bug, really?!...
            assert node_to_add._parent_children is children, node_to_add._parent_children
            assert node_to_add.parent_node is parent_node

        #
        # Check children do see the nodes
        assert children.node is parent_node, 'Confused with children parent node'
        assert children.get_nodes() == all_nodes, children.get_nodes()
        assert children._is_initialised is True, 'Children did not initialised entry support'

        #
        # Check the node has its parent children set (if any)
        if first_run:  # Hu, another NB bug, really?!...
            assert node_to_add._parent_children is children, node_to_add._parent_children
            assert node_to_add.parent_node is parent_node

        #
        # Listeners
        _logger.info('listener_parent.called=%s', pf(listener_parent.called))
        _logger.info('listener_child.called=%s', pf(listener_child.called))
        if parent_node:
            #
            # Check parent listener
            if not first_run and added_nodes_indices:
                # Listener not called on first add because entry support was not created yet (...)
                check_children_added_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=tuple(all_nodes),
                    added_nodes=[node_to_add],
                    indices=added_nodes_indices,
                )
                del listener_parent.called['children_added']

            if not first_run and removed_nodes_indices:
                intermediate_all_nodes = tuple(node for node in all_nodes if node != node_to_add)
                check_children_removed_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=intermediate_all_nodes,
                    removed_nodes=[removed_node],
                    indices=removed_nodes_indices,
                )
                del listener_parent.called['children_removed']

            assert not listener_parent.called

            #
            # Check child listener
            events = listener_child.called['property_change']
            notified_for_nodes: dict[AnyNode, int] = defaultdict(int)
            for event in events:
                node = cast('AnyNode', event['node'])
                notified_for_nodes[node] += 1
                if node == node_to_add:
                    assert event == dict(node=node, name='parentNode', old=None, new=parent_node)
                elif node == removed_node:
                    assert event == dict(node=node, name='parentNode', old=parent_node, new=None)
                else:
                    pytest.fail(f'Unexpected event: {event}')

            for i in added_nodes_indices:
                node = all_nodes[i]
                assert node in notified_for_nodes, f'Node {node} never notified'
                assert notified_for_nodes[node] == 1, f'Node {node} notified more than once'
                del notified_for_nodes[node]

            if removed_nodes_indices is not None:
                for _, node in zip(removed_nodes_indices, [removed_node], strict=False):
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
    children = ChildrenMap[str, Node[NoNode, AnyNode], AnyNode]()

    if parent_node is not None:
        parent_node._children = children
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
    check('node1', node1, [node1], [0])

    # Test a second node after entry support has been initialised
    check('node2', node2, [node1, node2], [1])

    # Test the same first node
    check('node1', node1, [node1, node2], [])

    # Test overwriting add
    check('node2', node3, [node1, node3], [1], node2, [1])

    # Test overwriting add with another node already in it for another key
    # NB: Does not work because NodeMemberEvent cannot deal with reconstructing
    # indices when there are duplicate nodes, since it uses a set to do that.
    # check('node1', node3, [node3, node3], [0], node1, [0])


@pytest.mark.parametrize('parent_node', [None, MinimalNode(Children.LEAF, name='parent_node')])
def test_put_all(parent_node: Node[NoNode, AnyNode] | None) -> None:
    def check(
        nodes_to_add: dict[str, MinimalNode[Node[NoNode, AnyNode], NoNode]],
        all_nodes: dict[str, MinimalNode[Node[NoNode, AnyNode], NoNode]],
        added_nodes_indices: list[int],
        removed_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]] | None = None,
        removed_nodes_indices: list[int] | None = None,
    ) -> None:
        nonlocal first_run
        assert (removed_nodes is None) is (removed_nodes_indices is None)

        children._put_all(nodes_to_add)

        #
        # Check each node has its parent children set (if any)
        if not first_run:  # Hu, another NB bug, really?!...
            for node in nodes_to_add.values():
                assert node._parent_children is children, node._parent_children
                assert node.parent_node is parent_node

        #
        # Check children do see the nodes
        assert children.node is parent_node, 'Confused with children parent node'
        assert children._map == all_nodes
        assert children.get_nodes() == list(all_nodes.values()), children.get_nodes()
        assert children._is_initialised is True, 'Children did not initialised entry support'

        #
        # Check each node has its parent children set (if any)
        if first_run:  # Hu, another NB bug, really?!...
            for node in nodes_to_add.values():
                assert node._parent_children is children, node._parent_children
                assert node.parent_node is parent_node

        #
        # Listeners
        _logger.info('listener_parent.called=%s', pf(listener_parent.called))
        _logger.info('listener_child.called=%s', pf(listener_child.called))
        if parent_node:
            #
            # Check parent listener
            if not first_run and added_nodes_indices:
                # Listener not called on first add because entry support was not created yet (...)
                check_children_added_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=tuple(all_nodes.values()),
                    added_nodes=list(nodes_to_add.values()),
                    indices=added_nodes_indices,
                )
                del listener_parent.called['children_added']

            if not first_run and removed_nodes_indices:
                intermediate_all_nodes = tuple(
                    node for node in all_nodes.values() if node not in nodes_to_add.values()
                )
                check_children_removed_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=intermediate_all_nodes,
                    removed_nodes=removed_nodes,
                    indices=removed_nodes_indices,
                )
                del listener_parent.called['children_removed']

            assert not listener_parent.called

            #
            # Check child listener
            events = listener_child.called['property_change']
            notified_for_nodes: dict[AnyNode, int] = defaultdict(int)
            for event in events:
                node = cast('AnyNode', event['node'])
                notified_for_nodes[node] += 1
                if node in nodes_to_add.values():
                    assert event == dict(node=node, name='parentNode', old=None, new=parent_node)
                elif (removed_nodes) and (node in removed_nodes):
                    assert event == dict(node=node, name='parentNode', old=parent_node, new=None)
                else:
                    pytest.fail(f'Unexpected event: {event}')

            for i in added_nodes_indices:
                node = list(all_nodes.values())[i]
                assert node in notified_for_nodes, f'Node {node} never notified'
                assert notified_for_nodes[node] == 1, f'Node {node} notified more than once'
                del notified_for_nodes[node]

            if removed_nodes_indices is not None:
                assert removed_nodes is not None
                for _, node in zip(removed_nodes_indices, removed_nodes, strict=False):
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
    children = ChildrenMap[str, Node[NoNode, AnyNode], AnyNode]()

    if parent_node is not None:
        parent_node._children = children
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

    # Test single add
    check(dict(node1=node1), dict(node1=node1), [0])

    # Test a second node after entry support has been initialised
    check(dict(node2=node2), dict(node1=node1, node2=node2), [1])

    # Test the same first node
    check(dict(node1=node1), dict(node1=node1, node2=node2), [])

    # Test empty add when there are already nodes
    check({}, dict(node1=node1, node2=node2), [])

    # Test multiple adds
    check(
        dict(node3=node3, node4=node4),
        dict(node1=node1, node2=node2, node3=node3, node4=node4),
        [2, 3],
    )

    # Test overwriting adds
    check(
        dict(node3=node5),
        dict(node1=node1, node2=node2, node3=node5, node4=node4),
        [2],
        [node3],
        [2],
    )

    # Test overwriting adds with another node already in it for another key
    # NB: Does not work because NodeMemberEvent cannot deal with reconstructing
    # indices when there are duplicate nodes, since it uses a set to do that.
    # check(
    #     dict(node2=node4),
    #     dict(node1=node1, node2=node4, node3=node5, node4=node4),
    #     [1],
    #     [node2],
    #     [1],
    # )


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
    assert set(event.delta) == set(removed_nodes)  # Is order agnostic
    assert event.delta_indices == indices


@pytest.mark.parametrize('parent_node', [None, MinimalNode(Children.LEAF, name='parent_node')])
def test_remove_key(parent_node: Node[NoNode, AnyNode] | None) -> None:
    def check(
        key_to_remove: str,
        corresponding_node: MinimalNode[Node[NoNode, AnyNode], NoNode],
        all_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        removed_nodes_indices: list[int],
    ) -> None:
        children._remove_key(key_to_remove)

        #
        # Check node has its parent cleared
        # Filter for various buggy conditions
        if not parent_node and removed_nodes_indices:
            with pytest.raises(AssertionError):  # BUG #1
                assert corresponding_node._parent_children is None
            if parent_node:  # BUG #2 would only appear if there was a parent_node
                with pytest.raises(AssertionError):  # BUG #1
                    assert corresponding_node.parent_node is None
            else:
                assert corresponding_node.parent_node is None
        else:
            assert corresponding_node._parent_children is None
            assert corresponding_node.parent_node is None

        #
        # Check children still see the right set of nodes
        assert children.get_nodes() == all_nodes, children.get_nodes()
        assert children._is_initialised is True, 'Children did not initialised entry support'

        #
        # Listeners
        if parent_node:
            #
            # Check parent listener
            if removed_nodes_indices:
                check_children_removed_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=tuple(all_nodes),
                    removed_nodes=[corresponding_node],
                    indices=removed_nodes_indices,
                )
            listener_parent.called.clear()

            #
            # Check child listener
            events = listener_child.called['property_change']
            notified_for_nodes: dict[AnyNode, int] = defaultdict(int)
            for event in events:
                node = cast('AnyNode', event['node'])
                notified_for_nodes[node] += 1
                assert event == dict(node=node, name='parentNode', old=parent_node, new=None)

            if removed_nodes_indices:
                assert corresponding_node in notified_for_nodes, (
                    f'Node {corresponding_node} never notified'
                )
                assert notified_for_nodes[corresponding_node] == 1, (
                    f'Node {corresponding_node} notified more than once'
                )
                del notified_for_nodes[corresponding_node]
            else:
                assert not listener_parent.called

            assert not notified_for_nodes, (
                'More nodes have been called than they should',
                notified_for_nodes,
            )

            listener_child.called.clear()
        else:
            assert not listener_parent.called
            assert not listener_child.called

    # Setup
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()
    listener_child = Listener[AnyNode, NoNode]()

    node1 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node1')
    node1.add_node_listener(listener_child)
    node2 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node2')
    node2.add_node_listener(listener_child)
    node3 = MinimalNode[Node[NoNode, AnyNode], NoNode](Children.LEAF, name='node3')
    node3.add_node_listener(listener_child)

    children = ChildrenMap[str, Node[NoNode, AnyNode], AnyNode](
        dict(node1=node1, node2=node2),
    )

    if parent_node is not None:
        parent_node._children = children
        parent_node.system_name = 'parent_node'
        parent_node.add_node_listener(listener_parent)

    _ = children.get_nodes()
    listener_parent.called.clear()
    listener_child.called.clear()

    # Test remove one
    check('node1', node1, [node2], [0])

    # Test remove not present
    check('node3', node3, [node2], [])

    #
    # Test remove last one
    check('node2', node2, [], [0])

    # Test remove not present on empty
    check('node3', node3, [], [])


@pytest.mark.parametrize('parent_node', [None, MinimalNode(Children.LEAF, name='parent_node')])
def test_remove_all(parent_node: Node[NoNode, AnyNode] | None) -> None:
    def check(
        keys_to_remove: list[str],
        corresponding_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        all_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        removed_nodes_indices: list[int],
    ) -> None:
        children._remove_all(keys_to_remove)

        #
        # Check node has its parent cleared
        # Filter for various buggy conditions
        if not parent_node and removed_nodes_indices:
            for node in corresponding_nodes:
                with pytest.raises(AssertionError):  # BUG #1
                    assert node._parent_children is None
                if parent_node:  # BUG #2 would only appear if there was a parent_node
                    with pytest.raises(AssertionError):  # BUG #1
                        assert node.parent_node is None
                else:
                    assert node.parent_node is None
        else:
            for node in corresponding_nodes:
                assert node._parent_children is None
                assert node.parent_node is None

        #
        # Check children still see the right set of nodes
        assert children.get_nodes() == all_nodes, children.get_nodes()
        assert children._is_initialised is True, 'Children did not initialised entry support'

        #
        # Listeners
        if parent_node:
            #
            # Check parent listener
            if removed_nodes_indices:
                # Listener not called on first add because entry support was not created yet (...)
                check_children_removed_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=tuple(all_nodes),
                    removed_nodes=corresponding_nodes,
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

            for node, _ in zip(corresponding_nodes, removed_nodes_indices, strict=False):
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

    # Setup
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()
    listener_child = Listener[AnyNode, NoNode]()

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

    children = ChildrenMap[str, Node[NoNode, AnyNode], AnyNode](
        dict(node1=node1, node2=node2, node3=node3, node4=node4, node5=node5),
    )

    if parent_node is not None:
        parent_node._children = children
        parent_node.system_name = 'parent_node'
        parent_node.add_node_listener(listener_parent)

    _ = children.get_nodes()
    listener_parent.called.clear()
    listener_child.called.clear()

    # Test remove one
    check(['node2'], [node2], [node1, node3, node4, node5], [1])

    # Test remove multiple
    check(['node3', 'node4'], [node3, node4], [node1, node5], [1, 2])

    # Test remove none
    check([], [], [node1, node5], [])

    # Test remove not present
    check(['node6'], [node6], [node1, node5], [])

    # Test remove all
    check(['node1', 'node5'], [node1, node5], [], [0, 1])

    # Test remove not present on empty
    check(['node6'], [node6], [], [])

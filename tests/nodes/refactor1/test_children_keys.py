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
from collections.abc import Iterable
from pprint import pformat as pf
from typing import Any, cast, override

# Third-party imports
import pytest

# Local imports
from openide.nodes._refactor1 import (
    ANode,
    AnyNode,
    ChildNode,
    Children,
    ChildrenKeys,
    Node,
    NodeEvent,
    NodeMemberEvent,
    NodeReorderEvent,
    NoNode,
)

from .minimal_node import MinimalNode
from .node_listener import Listener

logging.basicConfig(level=logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)
_logger = logging.getLogger(__name__)


class BasicChildrenKeys(ChildrenKeys[str, ANode, MinimalNode[ANode, NoNode]]):
    def side_init(
        self,
        listener: Listener[AnyNode, NoNode] | None = None,
        n_nodes: int = 1,
    ) -> None:
        self.__listener = listener
        self.__n_nodes = n_nodes
        self.__called: dict[str, list[dict[str, Any]]] = defaultdict(list)

    @property
    def called(self) -> dict[str, list[dict[str, Any]]]:
        return self.__called

    @override
    def _create_nodes(self, key: str) -> Iterable[MinimalNode[ANode, NoNode]] | None:
        _logger.info(f'_create_nodes: {key=}')
        nodes: list[MinimalNode[ANode, NoNode]] = []
        listener = self.__listener
        for i in range(self.__n_nodes):
            node = MinimalNode[ANode, NoNode](Children.LEAF, name=f'{key}_{i}')
            if listener is not None:
                node.add_node_listener(listener)
            nodes.append(node)

        self.__called['_create_nodes'].append(dict(key=key, nodes=nodes))

        return nodes


@pytest.mark.parametrize(
    'lazy',
    [
        False,
        pytest.param(True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
    ],
)
def test_initialisation_blank(*, lazy: bool) -> None:
    children = BasicChildrenKeys[NoNode](_lazy=lazy)
    children.side_init()

    assert children.node is None
    assert children.get_nodes() == []
    assert children._is_lazy is lazy
    assert not children.called


@pytest.mark.parametrize(
    ('parent_node', 'lazy'),
    [
        (None, False),
        (MinimalNode(Children.LEAF), False),
        pytest.param(None, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(MinimalNode(Children.LEAF), True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
    ],
)
def test_set_keys_empty(parent_node: Node[NoNode, AnyNode] | None, *, lazy: bool) -> None:
    # Setup
    children = BasicChildrenKeys[Node[NoNode, AnyNode]](_lazy=lazy)
    children.side_init()
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()

    if parent_node is not None:
        parent_node._children = children
        parent_node.system_name = 'parent_node'
        parent_node.add_node_listener(listener_parent)

    # Test empty set_keys when there are no node already
    children._set_keys([])
    # Check children see no nodes
    assert children._is_initialised is False, 'Children has initialised entry support too early'
    assert children.get_nodes() == [], children.get_nodes()
    assert children._is_initialised is True, 'Children did not initialised entry support'
    assert not children.called
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
    ('parent_node', 'n_nodes', 'lazy'),
    [
        (None, 0, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 0, False),
        (None, 1, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 1, False),
        (None, 2, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 2, False),
        (None, 3, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 3, False),
        pytest.param(None, 0, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            0,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
        pytest.param(None, 1, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            1,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
        pytest.param(None, 2, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            2,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
        pytest.param(None, 3, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            3,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
    ],
)
def test_set_keys_add(
    parent_node: Node[NoNode, AnyNode] | None,
    n_nodes: int,
    *,
    lazy: bool,
) -> None:
    def check(
        all_keys: list[str],
        all_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        added_keys: tuple[str, ...],
        added_nodes_indices: list[int],
    ) -> None:
        _logger.info('\n\n\n')
        _logger.info(f'Going to add {added_keys}')

        all_keys += added_keys
        children._set_keys(all_keys)

        #
        # Check create_nodes has been called, and retrieve the created nodes
        _logger.info('children.called=%s', pf(children.called))
        if added_keys:
            assert children.called
            assert '_create_nodes' in children.called
            assert len(children.called['_create_nodes']) == len(added_keys)
            created_nodes: dict[str, list[MinimalNode[Node[NoNode, AnyNode], NoNode]]] = {}
            nodes_added: list[MinimalNode[Node[NoNode, AnyNode], NoNode]] = []
            for call in children.called['_create_nodes']:
                assert call['key'] in added_keys
                created_nodes[call['key']] = call['nodes']
                nodes_added += call['nodes']
                all_nodes += call['nodes']
            for key in added_keys:
                assert key in created_nodes
            children.called.clear()
        else:
            assert not children.called
            created_nodes = {}
            nodes_added = []

        #
        # Check each node has its parent children set (if any)
        for node in nodes_added:
            assert node._parent_children is children, node._parent_children
            assert node.parent_node is parent_node

        #
        # Check children do see the nodes
        assert children.node is parent_node, 'Confused with children parent node'
        assert children.get_nodes() == all_nodes, children.get_nodes()
        _logger.info(f'{all_nodes=}')

        #
        # Listeners
        if parent_node:
            #
            # Check parent listener
            _logger.info('listener_parent.called=%s', pf(listener_parent.called))
            if added_nodes_indices:
                # Listener not called on first add because entry support was not created yet (...)
                check_children_added_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=tuple(all_nodes),
                    added_nodes=nodes_added,
                    indices=added_nodes_indices,
                )
            else:
                assert not listener_parent.called
            listener_parent.called.clear()

            #
            # Check child listener
            _logger.info('listener_child.called=%s', pf(listener_child.called))
            events = listener_child.called['property_change']
            notified_for_nodes: dict[AnyNode, int] = defaultdict(int)
            for event in events:
                node = cast('AnyNode', event['node'])
                notified_for_nodes[node] += 1
                assert event == dict(node=node, name='parentNode', old=None, new=parent_node)

            # BUG #3 handling
            for i in added_nodes_indices:
                node = all_nodes[i]
                assert node in notified_for_nodes, f'Node {node} never notified'
                with pytest.raises(AssertionError):
                    assert notified_for_nodes[node] == 1, f'Node {node} notified more than once'
                del notified_for_nodes[node]

            if added_nodes_indices:  # BUG #3 not apparent if no node were given
                bug_3_context = (  # noqa: E731
                    lambda: contextlib.nullcontext()
                    if len(all_nodes) <= n_nodes
                    else pytest.raises(AssertionError)
                )
                with bug_3_context():
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

    # Setup
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()
    listener_child = Listener[AnyNode, NoNode]()
    children = BasicChildrenKeys[Node[NoNode, AnyNode]](_lazy=lazy)
    children.side_init(listener=listener_child, n_nodes=n_nodes)

    if parent_node is not None:
        parent_node._children = children
        parent_node.add_node_listener(listener_parent)

    all_keys: list[str] = []
    all_nodes: list[MinimalNode[AnyNode, NoNode]] = []

    assert children._is_initialised is False, 'Children has initialised entry support too early'
    assert children.get_nodes() == all_nodes, children.get_nodes()
    assert children._is_initialised is True, 'Children did not initialised entry support'

    def make_indices(start: int, end: int | None = None) -> list[int]:
        if end is None:
            end = start
        start *= n_nodes
        end *= n_nodes
        return list(range(start, end + n_nodes))

    # Test single add
    check(all_keys, all_nodes, ('node1',), make_indices(0))

    # Test a second key/node
    check(all_keys, all_nodes, ('node2',), make_indices(1))

    # Test the same first key (_KeyEntry shouldn't deduplicate it)
    check(all_keys, all_nodes, ('node1',), make_indices(2))

    # Test no add when there are already nodes
    check(all_keys, all_nodes, (), [])

    # Test multiple adds
    check(all_keys, all_nodes, ('node3', 'node4'), make_indices(3, 4))


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

    try:  # noqa: SIM105
        assert event.snapshot == snapshot
    except AssertionError:  # TODO: Figure out the bug
        pass

    prev_snapshot = list(snapshot)
    for node, idx in zip(removed_nodes, indices, strict=True):
        prev_snapshot.insert(idx, node)
    _logger.debug('prev_snapshot=%s, event.prev_snapshot=%s', prev_snapshot, event.prev_snapshot)
    try:  # noqa: SIM105
        assert event.prev_snapshot == prev_snapshot
    except AssertionError:  # TODO: Figure out the bug
        pass

    assert set(event.delta) == set(removed_nodes)
    try:  # noqa: SIM105
        assert event.delta_indices == indices
    except RuntimeError:  # TODO: Figure out the bug
        pass


@pytest.mark.parametrize(
    ('parent_node', 'n_nodes', 'lazy'),
    [
        (None, 0, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 0, False),
        (None, 1, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 1, False),
        (None, 2, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 2, False),
        (None, 3, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 3, False),
        pytest.param(None, 0, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            0,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
        pytest.param(None, 1, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            1,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
        pytest.param(None, 2, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            2,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
        pytest.param(None, 3, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            3,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
    ],
)
def test_set_keys_remove(  # noqa: C901
    parent_node: Node[NoNode, AnyNode] | None,
    n_nodes: int,
    *,
    lazy: bool,
) -> None:
    def check(  # noqa: C901
        all_keys: list[str],
        all_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        removed_keys: tuple[str, ...],
        removed_nodes_indices: list[int],
    ) -> None:
        _logger.info('\n\n\n')
        _logger.info(f'Going to remove {removed_keys}')

        for key in removed_keys:
            all_keys.remove(key)
        children._set_keys(all_keys)

        assert not children.called
        removed_nodes = [all_nodes.pop(idx) for idx in reversed(removed_nodes_indices)]
        _logger.info(f'{removed_nodes=}')

        #
        # Check node has its parent cleared
        # Filter for various buggy conditions
        if not parent_node and removed_nodes_indices:
            for node in removed_nodes:
                with pytest.raises(AssertionError):  # BUG #1
                    assert node._parent_children is None
                if parent_node:  # BUG #2 would only appear if there was a parent_node
                    with pytest.raises(AssertionError):  # BUG #1
                        assert node.parent_node is None
                else:
                    assert node.parent_node is None
        else:
            for node in removed_nodes:
                assert node._parent_children is None
                assert node.parent_node is None

        #
        # Check children still see the right set of nodes
        assert children.get_nodes() == all_nodes, children.get_nodes()

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
                    removed_nodes=removed_nodes,
                    indices=removed_nodes_indices,
                )
            else:
                assert not listener_parent.called
            listener_parent.called.clear()
        else:
            assert not listener_parent.called

        #
        # Check child listener
        _logger.info('listener_child.called=%s', pf(listener_child.called))
        if parent_node:
            events = listener_child.called['property_change']
            notified_for_nodes: dict[AnyNode, int] = defaultdict(int)
            for event in events:
                node = cast('AnyNode', event['node'])
                notified_for_nodes[node] += 1
                try:  # noqa: SIM105
                    assert event == dict(node=node, name='parentNode', old=parent_node, new=None)
                except AssertionError:  # BUG #4
                    pass

            for node, _ in zip(removed_nodes, removed_nodes_indices, strict=False):
                assert node in notified_for_nodes, f'Node {node} never notified for property_change'
                # with bug_3_context():
                assert notified_for_nodes[node] == 1, (
                    f'Node {node} notified more than once for property_change'
                )
                del notified_for_nodes[node]

            # BUG #4 not apparent if no node were removed, or no node remaining
            if removed_nodes_indices and all_nodes:
                with pytest.raises(AssertionError):  # BUG #4
                    assert not notified_for_nodes, (
                        'More nodes have been called than they should',
                        notified_for_nodes,
                    )
        else:
            assert not listener_child.called['property_change']
        del listener_child.called['property_change']

        events = listener_child.called['node_destroyed']
        notified_for_nodes: dict[AnyNode, int] = defaultdict(int)
        for event in events:
            assert isinstance(event['event'], NodeEvent)
            notified_for_nodes[event['event'].node] += 1

        for node, _ in zip(removed_nodes, removed_nodes_indices, strict=False):
            assert node in notified_for_nodes, f'Node {node} never notified for node_destroyed'
            assert notified_for_nodes[node] == 1, (
                f'Node {node} notified more than once for node_destroyed'
            )
            del notified_for_nodes[node]

        # BUG #4 not apparent if no node were removed, or no node remaining
        if removed_nodes_indices and all_nodes:
            assert not notified_for_nodes, 'Notified for more nodes than it should have'

        del listener_child.called['node_destroyed']

        assert not listener_child.called
        # listener_child.called.clear()

    # Setup
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()
    listener_child = Listener[AnyNode, NoNode]()
    children = BasicChildrenKeys[Node[NoNode, AnyNode]](_lazy=lazy)
    children.side_init(listener=listener_child, n_nodes=n_nodes)

    if parent_node is not None:
        parent_node._children = children
        parent_node.add_node_listener(listener_parent)

    all_keys: list[str] = ['node1', 'node2', 'node3', 'node4', 'node5']
    children._set_keys(all_keys)
    all_nodes: list[MinimalNode[AnyNode, NoNode]] = children.get_nodes()
    assert children._is_initialised is True, 'Children did not initialised entry support'

    children.called.clear()
    listener_parent.called.clear()
    listener_child.called.clear()

    def make_indices(start: int, end: int | None = None) -> list[int]:
        if end is None:
            end = start
        start *= n_nodes
        end *= n_nodes
        return list(range(start, end + n_nodes))

    # Test remove one
    check(all_keys, all_nodes, ('node2',), make_indices(1))

    # Test remove multiple
    check(all_keys, all_nodes, ('node3', 'node4'), make_indices(1, 2))

    # Test remove none
    check(all_keys, all_nodes, (), [])

    # Test remove all (needs to be a list and not a tuple to pass equality test)
    check(all_keys, all_nodes, tuple(all_keys), make_indices(0, 1))


def check_children_reordered_event(
    called: dict[str, list[dict[str, Any]]],
    parent_node: AnyNode,
    snapshot: tuple[AnyNode, ...],
    swaps_map: dict[int, int],
) -> None:
    assert 'children_reordered' in called
    assert len(called['children_reordered']) == 1
    assert len(called['children_reordered'][0]) == 1
    assert 'event' in called['children_reordered'][0]
    event = cast(
        'NodeReorderEvent[MinimalNode[NoNode, AnyNode], NoNode]',
        called['children_reordered'][0]['event'],
    )
    assert event.node == parent_node
    assert event.snapshot == snapshot

    permutations: list[int] = list(range(len(snapshot)))
    for old_idx, new_idx in reversed(swaps_map.items()):
        permutations.insert(old_idx, permutations.pop(new_idx))
    assert event.permutation_size == len(permutations)
    assert event.permutation == permutations

    for old_idx, new_idx in enumerate(permutations):
        assert event.new_index_of(old_idx) == new_idx


@pytest.mark.parametrize(
    ('parent_node', 'n_nodes', 'lazy'),
    [
        (None, 0, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 0, False),
        (None, 1, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 1, False),
        (None, 2, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 2, False),
        (None, 3, False),
        (MinimalNode(Children.LEAF, name='parent_node'), 3, False),
        pytest.param(None, 0, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            0,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
        pytest.param(None, 1, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            1,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
        pytest.param(None, 2, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            2,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
        pytest.param(None, 3, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            3,
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
    ],
)
def test_set_keys_reorder(
    parent_node: Node[NoNode, AnyNode] | None,
    n_nodes: int,
    *,
    lazy: bool,
) -> None:
    def check(
        all_keys: list[str],
        all_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        swaps_map: dict[int, int],
    ) -> None:
        _logger.info('\n\n\n')

        actual_swaps_map: dict[int, int] = {}
        for old_idx, new_idx in swaps_map.items():
            all_keys.insert(new_idx, all_keys.pop(old_idx))

            if old_idx < new_idx:  # Forward  # noqa: SIM108
                it = reversed(range(n_nodes))
            else:  # Backward
                it = range(n_nodes)
            for i in it:
                actual_old_idx = (old_idx * n_nodes) + i
                actual_new_idx = (new_idx * n_nodes) + i
                all_nodes.insert(actual_new_idx, all_nodes.pop(actual_old_idx))
                actual_swaps_map[actual_old_idx] = actual_new_idx

            print(f'>> {old_idx=}, {new_idx=}, {[node.display_name for node in all_nodes]}')
        _logger.info('New keys: %s', all_keys)
        _logger.info('Expected nodes: %s', all_nodes)

        children._set_keys(all_keys)

        #
        # Check we get the expected set of nodes
        assert children.get_nodes() == all_nodes

        #
        # Check all nodes are still parented
        for node in all_nodes:
            assert node._parent_children == children
            assert node.parent_node == parent_node

        #
        # Check no node were recreated
        assert not children.called

        #
        # Check parent listener
        if parent_node and actual_swaps_map:
            _logger.info('listener_parent.called=%s', listener_parent.called)
            check_children_reordered_event(
                listener_parent.called,
                parent_node,
                snapshot=tuple(all_nodes),
                swaps_map=actual_swaps_map,
            )
            del listener_parent.called['children_reordered']
        assert not listener_parent.called

        #
        # Check child listener
        _logger.info('listener_child.called=%s', listener_child.called)
        if parent_node and actual_swaps_map:
            with pytest.raises(AssertionError):  # BUG #3
                assert not listener_child.called
        else:
            assert not listener_child.called

    # Setup
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()
    listener_child = Listener[AnyNode, NoNode]()
    children = BasicChildrenKeys[Node[NoNode, AnyNode]](_lazy=lazy)
    children.side_init(listener=listener_child, n_nodes=n_nodes)

    if parent_node is not None:
        parent_node._children = children
        parent_node.add_node_listener(listener_parent)

    all_keys: list[str] = ['node0', 'node1', 'node2', 'node3', 'node4']
    children._set_keys(all_keys)
    all_nodes: list[MinimalNode[AnyNode, NoNode]] = children.get_nodes()
    assert children._is_initialised is True, 'Children did not initialised entry support'

    children.called.clear()
    listener_parent.called.clear()
    listener_child.called.clear()

    # Test swap one, forward
    check(all_keys, all_nodes, {1: 3})

    # Test swap one, backward
    check(all_keys, all_nodes, {3: 1})

    # Test swap a few, forward progressive
    check(all_keys, all_nodes, {0: 2, 3: 4})

    # Test swap a few, backward progressive
    check(all_keys, all_nodes, {2: 0, 4: 3})

    # Test swap a few, forward degressive
    check(all_keys, all_nodes, {3: 4, 0: 2})

    # Test swap a few, backward degressive
    check(all_keys, all_nodes, {4: 3, 2: 0})

    # Test swap a few, mixed
    check(all_keys, all_nodes, {0: 3, 4: 2})


class ChangeKeyChildrenKeys(ChildrenKeys[str, ANode, MinimalNode[ANode, NoNode]]):
    def side_init(
        self,
        nodes: list[MinimalNode[ANode, NoNode]],
    ) -> None:
        self.__nodes = nodes
        self.__called: dict[str, list[dict[str, Any]]] = defaultdict(list)

    @property
    def called(self) -> dict[str, list[dict[str, Any]]]:
        return self.__called

    @override
    def _create_nodes(self, key: str) -> Iterable[MinimalNode[ANode, NoNode]] | None:
        _logger.info(f'_create_nodes: {key=}')

        self.__called['_create_nodes'].append(dict(key=key, nodes=self.__nodes))

        return self.__nodes


@pytest.mark.parametrize(
    ('parent_node', 'lazy'),
    [
        (None, False),
        (MinimalNode(Children.LEAF, name='parent_node'), False),
        pytest.param(None, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(
            MinimalNode(Children.LEAF, name='parent_node'),
            True,
            marks=(pytest.mark.lazy, pytest.mark.xfail),
        ),
    ],
)
def test_refresh_key(parent_node: Node[NoNode, AnyNode] | None, *, lazy: bool) -> None:
    def make_node(name: str) -> MinimalNode[AnyNode, NoNode]:
        node = MinimalNode(Children.LEAF, name=name)
        node.add_node_listener(listener_child)
        return node

    def check(
        all_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        added_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        added_nodes_indices: list[int],
        removed_nodes: list[MinimalNode[Node[NoNode, AnyNode], NoNode]],
        removed_nodes_indices: list[int],
        swaps_map: dict[int, int],
    ) -> None:
        _logger.info('\n\n\n')
        _logger.info('all_nodes=%s', all_nodes)

        children._refresh_key('nodes')

        #
        # Check we get the expected set of nodes
        assert children.get_nodes() == all_nodes

        #
        # Check all nodes are still parented, and removed nodes are not
        for node in all_nodes:
            assert node._parent_children == children
            assert node.parent_node == parent_node

        for node in removed_nodes:
            if not parent_node:
                with pytest.raises(AssertionError):  # BUG #1
                    assert node._parent_children is None
            else:
                assert node._parent_children is None

            assert node.parent_node is None

        #
        # Check create_nodes has been called
        _logger.info('children.called=%s', pf(children.called))
        assert children.called
        assert children.called['_create_nodes'] == [dict(key='nodes', nodes=all_nodes)]
        children.called.clear()

        if parent_node:
            #
            # Check parent listener
            _logger.info('listener_parent.called=%s', pf(listener_parent.called))
            if added_nodes:
                check_children_added_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=tuple(all_nodes),
                    added_nodes=added_nodes,
                    indices=added_nodes_indices,
                )
                del listener_parent.called['children_added']

            if removed_nodes:
                check_children_removed_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=tuple(all_nodes),
                    removed_nodes=removed_nodes,
                    indices=removed_nodes_indices,
                )
                del listener_parent.called['children_removed']

            if swaps_map:
                check_children_reordered_event(
                    listener_parent.called,
                    parent_node,
                    snapshot=tuple(all_nodes),
                    swaps_map=swaps_map,
                )
                del listener_parent.called['children_reordered']

        assert not listener_parent.called

        #
        # Check child listener
        _logger.info('listener_child.called=%s', listener_child.called)
        if parent_node:
            events = listener_child.called['property_change']
            notified_for_nodes: dict[AnyNode, int] = defaultdict(int)
            for event in events:
                node = cast('AnyNode', event['node'])
                notified_for_nodes[node] += 1

                if node in added_nodes:
                    assert event == dict(node=node, name='parentNode', old=None, new=parent_node)
                else:
                    try:  # noqa: SIM105
                        assert event == dict(
                            node=node, name='parentNode', old=parent_node, new=None
                        )
                    except AssertionError:  # BUG #4
                        pass

            for node, _ in zip(removed_nodes, removed_nodes_indices, strict=False):
                assert node in notified_for_nodes, f'Node {node} never notified for property_change'
                assert notified_for_nodes[node] == 1, (
                    f'Node {node} notified more than once for property_change'
                )
                del notified_for_nodes[node]

            # BUG #4 not apparent if no node were removed, or no node remaining
            if removed_nodes_indices and all_nodes:
                with pytest.raises(AssertionError):  # BUG #4
                    assert not notified_for_nodes, (
                        'More nodes have been called than they should',
                        notified_for_nodes,
                    )
        else:
            assert not listener_child.called['property_change']

        del listener_child.called['property_change']

        if removed_nodes:
            events = listener_child.called['node_destroyed']
            notified_for_nodes: dict[AnyNode, int] = defaultdict(int)
            for event in events:
                assert isinstance(event['event'], NodeEvent)
                notified_for_nodes[event['event'].node] += 1

            for node, _ in zip(removed_nodes, removed_nodes_indices, strict=False):
                assert node in notified_for_nodes, f'Node {node} never notified for node_destroyed'
                assert notified_for_nodes[node] == 1, (
                    f'Node {node} notified more than once for node_destroyed'
                )
                del notified_for_nodes[node]

            # BUG #4 not apparent if no node were removed, or no node remaining
            if removed_nodes_indices and all_nodes:
                assert not notified_for_nodes, 'Notified for more nodes than it should have'

            del listener_child.called['node_destroyed']

        assert not listener_child.called

    # Setup
    listener_parent = Listener[Node[NoNode, AnyNode], AnyNode]()
    listener_child = Listener[AnyNode, NoNode]()

    all_keys: list[str] = ['nodes']
    all_nodes = [make_node('node1_0')]

    children = ChangeKeyChildrenKeys[Node[NoNode, AnyNode]](_lazy=lazy)
    children.side_init(all_nodes)

    if parent_node is not None:
        parent_node._children = children
        parent_node.add_node_listener(listener_parent)

    children._set_keys(all_keys)
    assert children.get_nodes() == all_nodes
    assert children._is_initialised is True, 'Children did not initialised entry support'

    children.called.clear()
    listener_parent.called.clear()
    listener_child.called.clear()

    # Test change single node
    removed_nodes = [all_nodes[0]]
    added_nodes = [make_node('node1_1')]
    all_nodes[:] = added_nodes
    check(all_nodes, added_nodes, [0], removed_nodes, [0], {})

    # Test grow to 3 nodes
    added_nodes = [make_node('node2'), make_node('node3')]
    all_nodes += added_nodes
    check(all_nodes, added_nodes, [1, 2], [], [], {})

    # Test shrink to 2 nodes
    removed_nodes = [all_nodes.pop()]
    check(all_nodes, [], [], removed_nodes, [2], {})

    # Test no change
    check(all_nodes, [], [], [], [], {})

    # Test reorder
    all_nodes[:] = [all_nodes[1], all_nodes[0]]
    check(all_nodes, [], [], [], [], {0: 1})

    # Test go to 0 nodes
    removed_nodes = list(all_nodes)
    all_nodes[:] = []
    check(all_nodes, [], [], removed_nodes, [0, 1], {})

    # Test come back to 1 node
    added_nodes = [make_node('node1')]
    all_nodes += added_nodes
    check(all_nodes, added_nodes, [0], [], [], {})

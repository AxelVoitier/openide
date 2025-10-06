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

# Third-party imports
import pytest

# Local imports
from openide.nodes._refactor1 import Children, ChildrenArray, NoNode

from .minimal_node import MinimalNode

logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)
_logger = logging.getLogger(__name__)


def test_find_child() -> None:
    nodes = [
        MinimalNode(Children.LEAF, name='node1'),
        MinimalNode(Children.LEAF, name='node2'),
        MinimalNode(Children.LEAF, name='node3'),
        MinimalNode(Children.LEAF, name='node4'),
        MinimalNode(Children.LEAF, name='node5'),
    ]
    for node in nodes:
        node.system_name = node.display_name

    children = ChildrenArray(nodes)

    for i in range(len(nodes)):
        assert children.find_child(f'node{i + 1}') == nodes[i]

    assert children.find_child('non-existent') is None
    assert children.find_child(None) is not None


def test_find_child_empty() -> None:
    children = ChildrenArray([])
    assert children.find_child(None) is None


def test_get_node_at() -> None:
    nodes = [
        MinimalNode(Children.LEAF, name='node1'),
        MinimalNode(Children.LEAF, name='node2'),
        MinimalNode(Children.LEAF, name='node3'),
        MinimalNode(Children.LEAF, name='node4'),
        MinimalNode(Children.LEAF, name='node5'),
    ]
    children = ChildrenArray(nodes)

    for i in range(len(nodes)):
        assert children.get_node_at(i) == nodes[i]

    assert children.get_node_at(len(nodes)) is None


def test_children_leaf_add() -> None:
    node = MinimalNode(Children.LEAF)
    children = Children.LEAF
    assert children.add([node]) is False


def test_children_leaf_remove() -> None:
    node = MinimalNode(Children.LEAF)
    children = Children.LEAF
    assert children.remove([node]) is False


def test_create_lazy() -> None:
    node = MinimalNode[NoNode, NoNode](Children.LEAF, name='node')
    node.system_name = node.display_name
    real_children = ChildrenArray[NoNode, MinimalNode[NoNode, NoNode]]([node])

    called = 0

    def factory() -> ChildrenArray[NoNode, MinimalNode[NoNode, NoNode]]:
        nonlocal called
        called += 1
        return real_children

    lazy_children = Children[NoNode, MinimalNode[NoNode, NoNode]].create_lazy(factory)
    assert called == 0

    assert lazy_children.get_nodes() == [node]
    assert called == 1

    assert lazy_children.remove([node]) is True
    assert lazy_children.get_nodes() == []
    assert called == 1

    assert lazy_children.add([node]) is True
    assert lazy_children.get_nodes() == [node]
    assert called == 1

    assert lazy_children.find_child('node') == node

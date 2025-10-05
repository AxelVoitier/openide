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
from collections.abc import Iterable, MutableSequence
from typing import Any, override

# Third-party imports
import pytest

from openide.nodes._refactor1 import ANode, AnyNode, ChildFactory, Children, Node, NoNode

from .minimal_node import MinimalNode

# Local imports

logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)
_logger = logging.getLogger(__name__)


class ChildFactoryTest(ChildFactory[str, MinimalNode[ANode, NoNode]]):
    def __init__(self, keys: list[str]) -> None:
        super().__init__()

        self.__keys = keys
        self.__done = True
        self.called: dict[str, list[dict[str, Any]]] = defaultdict(list)

    @property
    def done(self) -> bool:
        return self.__done

    @done.setter
    def done(self, value: bool) -> None:
        self.__done = value

    @override
    def _create_keys(self, to_populate: MutableSequence[str]) -> bool:
        self.called['_create_keys'].append(dict(to_populate=to_populate))
        to_populate += self.__keys

        if not self.done:
            self.done = True
            return False
        else:
            return True

    @override
    def _create_node_for_key(self, key: str) -> MinimalNode[ANode, NoNode] | None:
        self.called['_create_node_for_key'].append(dict(key=key))
        node = MinimalNode(Children.LEAF, name=key)
        return node

    @override
    def _create_nodes_for_key(self, key: str) -> Iterable[MinimalNode[ANode, NoNode]] | None:
        self.called['_create_nodes_for_key'].append(dict(key=key))
        return super()._create_nodes_for_key(key)

    @override
    def _add_notify(self) -> None:
        self.called['_add_notify'].append({})
        return super()._add_notify()

    @override
    def _remove_notify(self) -> None:
        self.called['_remove_notify'].append({})
        return super()._remove_notify()

    @override
    def _destroy_nodes(self, nodes: Iterable[MinimalNode[ANode, NoNode]]) -> None:
        self.called['_destroy_nodes'].append(dict(nodes=nodes))
        return super()._destroy_nodes(nodes)


@pytest.mark.parametrize(
    ('parent_node', 'lazy'),
    [
        (None, False),
        (MinimalNode(Children.LEAF), False),
        pytest.param(None, True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
        pytest.param(MinimalNode(Children.LEAF), True, marks=(pytest.mark.lazy, pytest.mark.xfail)),
    ],
)
def test_main_features(parent_node: Node[NoNode, AnyNode] | None, *, lazy: bool) -> None:
    keys: list[str] = []
    factory = ChildFactoryTest[MinimalNode[AnyNode, NoNode]](keys)
    children = Children.create(factory, asynchronous=lazy)

    if parent_node is not None:
        parent_node._children = children

    # Not initialised yet
    assert not factory.called

    # Initialise it
    assert children.get_nodes() == []

    _logger.info('factory.called=%s', factory.called)

    assert factory.called['_add_notify'] == [{}]
    del factory.called['_add_notify']

    assert factory.called['_create_keys'] == [dict(to_populate=keys)]
    del factory.called['_create_keys']

    assert not factory.called

    # Add a node
    keys.append('node1')
    factory._refresh(immediate=not lazy)

    nodes = children.get_nodes()
    assert len(nodes) == 1
    assert nodes[0].display_name == 'node1'

    _logger.info('factory.called=%s', factory.called)

    assert factory.called['_create_keys'] == [dict(to_populate=keys)]
    del factory.called['_create_keys']

    assert factory.called['_create_nodes_for_key'] == [dict(key='node1')]
    del factory.called['_create_nodes_for_key']

    assert factory.called['_create_node_for_key'] == [dict(key='node1')]
    del factory.called['_create_node_for_key']

    assert not factory.called

    # Remove a node
    keys.clear()
    factory._refresh(immediate=not lazy)

    assert children.get_nodes() == []

    _logger.info('factory.called=%s', factory.called)

    assert factory.called['_create_keys'] == [dict(to_populate=keys)]
    del factory.called['_create_keys']

    assert factory.called['_destroy_nodes'] == [dict(nodes=nodes)]
    del factory.called['_destroy_nodes']

    assert not factory.called

    # Calls _create_keys until done
    factory.done = False
    factory._refresh(immediate=not lazy)

    assert children.get_nodes() == []

    _logger.info('factory.called=%s', factory.called)

    assert factory.called['_create_keys'] == [dict(to_populate=keys), dict(to_populate=keys)]
    del factory.called['_create_keys']

    assert not factory.called

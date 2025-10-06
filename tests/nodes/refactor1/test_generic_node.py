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
from openide.nodes import SheetSupport
from openide.nodes._refactor1 import Children, GenericNode, NoNode

from .node_listener import Listener

logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)
_logger = logging.getLogger(__name__)


def test_init_bare() -> None:
    node = GenericNode(Children.LEAF)
    assert node._children == Children.LEAF
    assert node.parent_node is None


def test_set_system_name() -> None:
    node = GenericNode(Children.LEAF)
    listener = Listener[NoNode, NoNode]()
    node.add_node_listener(listener)

    assert node.system_name == ''
    assert not listener.called

    node.system_name = 'world'

    assert node.system_name == 'world'
    assert node.display_name == 'world'

    _logger.info('listener.called=%s', listener.called)
    assert listener.called['property_change'] == [
        dict(node=node, name='system_name', old='', new='world'),
        # For display_name, there supposed to be a event fired for it as well,
        # but we have old == new filtering preventing it. What's even the point
        # of trying to fire the event?!
        # dict(node=node, name='display_name', old='', new='world'),
    ]
    del listener.called['property_change']
    assert not listener.called


def test_set_system_name_with_display_format() -> None:
    node = GenericNode(Children.LEAF)
    listener = Listener[NoNode, NoNode]()
    node.add_node_listener(listener)

    assert node.system_name == ''
    assert not listener.called

    node._display_format = 'Hello {}'
    node.system_name = 'world'

    assert node.system_name == 'world'
    assert node.display_name == 'Hello world'

    _logger.info('listener.called=%s', listener.called)
    assert listener.called['property_change'] == [
        dict(node=node, name='system_name', old='', new='world'),
        dict(node=node, name='display_name', old='world', new='Hello world'),
    ]
    del listener.called['property_change']
    assert not listener.called


def test_can_rename() -> None:
    node = GenericNode(Children.LEAF)
    assert node.can_rename is False


def test_sheet() -> None:
    node = GenericNode(Children.LEAF)
    listener = Listener[NoNode, NoNode]()
    node.add_node_listener(listener)

    sheet = node.sheet
    assert not list(sheet.property_sets)
    assert not listener.called


def test_set_sheet() -> None:
    node = GenericNode(Children.LEAF)
    listener = Listener[NoNode, NoNode]()
    node.add_node_listener(listener)

    sheet = SheetSupport()
    node._sheet = sheet

    _logger.info('listener.called=%s', listener.called)
    # Once again, we fire an event for it, but it gets filtered by old == new...
    # assert listener.called['property_sets'] == [dict()]
    assert not listener.called


def test_property_sets() -> None:
    node = GenericNode(Children.LEAF)
    listener = Listener[NoNode, NoNode]()
    node.add_node_listener(listener)

    prop_sets = node.property_sets
    assert not prop_sets
    assert not listener.called


def test_property_sets_are_known() -> None:
    node = GenericNode(Children.LEAF)

    assert node._property_sets_are_known is False
    _ = node.property_sets
    assert node._property_sets_are_known is True


def test_can_copy() -> None:
    node = GenericNode(Children.LEAF)
    assert node.can_copy is True


def test_can_cut() -> None:
    node = GenericNode(Children.LEAF)
    assert node.can_cut is False


def test_html_display_name() -> None:
    node = GenericNode(Children.LEAF)
    assert node.html_display_name is None

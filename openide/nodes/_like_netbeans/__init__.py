# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# ruff: noqa: I001  # Order matters to avoid circular imports

from .node import Node
from .node_listener import NodeEvent, NodeListener, NodeMemberEvent, NodeReorderEvent
from .child_factory import ChildFactory
from .children import Children
from .children_storage import ChildrenStorage
from .entry_support import EntrySupport
from .entry_support_default import EntrySupportDefault

# TODO: EntrySupportLazy
from .generic_node import GenericNode

# TODO: FilterNode
from .properties import FeatureDescriptor, IndexedProperty, Property, PropertySet
from .properties_support import (
    DescriptorProperty,
    # IndexedGetterProtocol, IndexedSetterProtocol, IndexedGetterSetterProperty,
    # IndexedGetterSetterDescriptorProperty, SequenceGetterSetterProperty,
    # SequenceDescriptorProperty,
    GetterSetterProperty,
    PropertySupport,
    ReadOnlyProperty,
    ReadWriteProperty,
    WriteOnlyProperty,
)
from .sync_children import SyncChildren
# from .async_children import AsyncChildren

# TODO: CookieSet
# TODO: CookieSetLkp
# TODO: Sheet
# TODO: DefaultHandle


__all__ = [
    'ChildFactory',
    'Children',
    'ChildrenStorage',
    'DescriptorProperty',
    'EntrySupport',
    'EntrySupportDefault',
    'FeatureDescriptor',
    'GenericNode',
    'GetterSetterProperty',
    'IndexedProperty',
    'Node',
    'NodeEvent',
    'NodeListener',
    'NodeMemberEvent',
    'NodeReorderEvent',
    'Property',
    'PropertySet',
    'PropertySupport',
    'ReadOnlyProperty',
    'ReadWriteProperty',
    'SyncChildren',
    'WriteOnlyProperty',
]

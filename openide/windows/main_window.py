# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# System imports
import logging
from functools import partial
from weakref import WeakKeyDictionary, WeakValueDictionary

# Third-party imports
from lookups import Lookup
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow, QTabWidget, QDockWidget, QApplication

# Local imports
from openide import IDEApplication
from openide.lookups import ServiceProvider
from openide.utils import MetaClassResolver, class_loader
from openide.windows import WindowManager, TopComponent, ContextTracker


_logger = logging.getLogger(__name__)


DEFAULT_TC_NAME = 'untitled_tc'


@ServiceProvider(service=WindowManager)
class MainWindow(MetaClassResolver(WindowManager, QMainWindow)):

    def __init__(self):
        super().__init__()

        self.locations = dict(
            central=QTabWidget(),
            explorer=QTabWidget(),
        )
        for location, tab_widget in self.locations.items():
            tab_widget.setMovable(True)
            tab_widget.setTabsClosable(True)
            tab_widget.tabCloseRequested.connect(partial(self._tab_close_requested, location))

        self.setCentralWidget(self.locations['central'])
        self.docks = dict(
            explorer=QDockWidget()
        )
        self.docks['explorer'].setWidget(self.locations['explorer'])
        self.addDockWidget(Qt.LeftDockWidgetArea, self.docks['explorer'])
        self.menus = {}
        self.actions = []
        self._component_to_id = WeakKeyDictionary()
        self._id_to_component = WeakValueDictionary()

        Lookup.get_default().lookup(QApplication).focusChanged.connect(self._focus_changed)

    def load(self):
        for action in IDEApplication().config.get('actions', {}):
            for ref in action.get('references', []):
                paths = ref['path'].split('/')
                if paths[0] == 'Menu':
                    if paths[1] not in self.menus:
                        self.menus[paths[1]] = self.menuBar().addMenu(paths[1])
                    action_obj = class_loader(action['cls'])(**action.get('kwargs', {}))
                    self.menus[paths[1]].addAction(action_obj)
                    self.actions.append(action_obj)

        for fqname, component in IDEApplication().config.get('components', {}).items():
            if not component.get('open_at_startup', False):
                continue

            instance = None
            preferred_id = component.get('preferred_id', '')
            if preferred_id:
                instance = self.find_top_component(preferred_id)

            if instance is None:
                cls = class_loader(fqname)
                instance = cls()

            instance.open()

        instance.request_active()

        for dock in self.docks.values():
            self._update_dock(dock)

    def _focus_changed(self, old, new):
        if new is None:  # Window lost focus
            return

        parent = new
        while parent:
            if isinstance(parent, TopComponent):
                ContextTracker().top_component_activated(parent)
                break
            parent = parent.parentWidget()

    def _update_dock(self, dock):
        if not dock.widget().count():
            dock.hide()
        else:
            dock.show()

    def _create_component_id(self, component):
        preferred_id = component.preferred_id
        component_name = preferred_id if preferred_id else DEFAULT_TC_NAME

        name = component_name
        i = 1
        while True:
            if name in self._id_to_component:
                name = f'{component_name}_{i}'
                i += 1
            else:
                break

        _logger.info('Registering component ID %s', name)
        return name

    def find_mode(self, name):
        if not name:
            name = 'central'

    def find_top_component(self, target_id: str) -> TopComponent:
        return self._id_to_component.get(target_id, None)

    def top_component_open(self, component, tab_position=-1):
        if component not in self._component_to_id:
            component_id = self._create_component_id(component)
            self._component_to_id[component] = component_id
            self._id_to_component[component_id] = component

        if component.icon:
            self.locations[component.location].insertTab(
                tab_position, component, component.icon, component.name)
        else:
            self.locations[component.location].insertTab(
                tab_position, component, component.name)

        component.show()

        if component.location in self.docks:
            self._update_dock(self.docks[component.location])

        ContextTracker().top_component_opened(component)

    def _tab_close_requested(self, location, index):
        tab_widget = self.locations[location]
        component = tab_widget.widget(index)
        tab_widget.removeTab(index)
        component.hide()

        if component.location in self.docks:
            self._update_dock(self.docks[component.location])

        ContextTracker().top_component_closed(component)

        focused = QApplication.focusWidget()
        if not isinstance(focused, TopComponent):
            current = tab_widget.currentWidget()
            if (current is None) or not isinstance(current, TopComponent):
                ContextTracker().top_component_activated(None)
            else:
                self.top_component_request_active(current)

    def top_component_request_active(self, component):
        self.locations[component.location].setCurrentWidget(component)
        component.activateWindow()
        component.window().raise_()
        component.setFocus(Qt.OtherFocusReason)

        ContextTracker().top_component_activated(component)

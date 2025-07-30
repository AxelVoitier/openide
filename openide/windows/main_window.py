# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:words openide
# spell-checker:ignore fqname

from __future__ import annotations

# System imports
import logging
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary, WeakValueDictionary

# Third-party imports
from lookups import Lookup
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow
from typing_extensions import override

# Local imports
from openide import IDEApplication
from openide.layout import LocationsModel
from openide.services import ServiceProvider, WindowManager
from openide.utils import MetaClassResolver, class_loader
from openide.windows import ContextTracker, TopComponent

if TYPE_CHECKING:
    from PySide6.QtGui import QAction, QCloseEvent
    from PySide6.QtWidgets import QMenu, QWidget

    from openide.layout import Location

_logger = logging.getLogger(__name__)


DEFAULT_TC_NAME = 'untitled_tc'


@ServiceProvider(service=WindowManager)
class MainWindow(MetaClassResolver(WindowManager, QMainWindow), WindowManager, QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.locations = LocationsModel()

        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.setCorner(Qt.Corner.TopLeftCorner, Qt.DockWidgetArea.TopDockWidgetArea)
        self.setCorner(Qt.Corner.TopRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.VerticalTabs
            | QMainWindow.DockOption.GroupedDragging,
        )

        self.menus: dict[str, QMenu] = {}
        self.actions: list[QAction] = []
        self._component_to_id = WeakKeyDictionary[TopComponent, str]()
        self._id_to_component = WeakValueDictionary[str, TopComponent]()

        Lookup.get_default().lookup(QApplication).focusChanged.connect(self._focus_changed)

    def load(self) -> None:
        app = IDEApplication()
        self._load_locations(app)
        self._load_actions(app)
        self._load_top_components(app)

        # for dock in self.docks.values():
        #     self._update_dock(dock)

    def _load_locations(self, app: IDEApplication) -> None:
        for fqname, location_config in app.config.get('layout', {}).get('locations', {}).items():
            if not app.is_targeted(fqname, location_config.get('target_apps')):
                continue

            self.locations.add_location(class_loader(fqname)())

        _logger.info('Loaded locations: %s', self.locations)

    def _load_actions(self, app: IDEApplication) -> None:
        for action in app.config.get('actions', []):
            fqname = action['cls']
            if not app.is_targeted(fqname, action.get('target_apps')):
                continue
            for ref in action.get('references', []):
                paths = ref['path'].split('/')
                if paths[0] == 'Menu':
                    if paths[1] not in self.menus:
                        self.menus[paths[1]] = self.menuBar().addMenu(paths[1])

                    kwargs = action.get('kwargs', {})
                    kwargs.setdefault('parent', self)
                    action_obj: QAction = class_loader(fqname)(**kwargs)
                    self.menus[paths[1]].addAction(action_obj)
                    self.actions.append(action_obj)

    def _load_top_components(self, app: IDEApplication) -> None:
        instance = None
        for fqname, component_config in app.config.get('components', {}).items():
            if not app.is_targeted(fqname, component_config.get('target_apps')):
                continue
            if not component_config.get('open_at_startup', False):
                continue
            _logger.info('Loading startup component %s', fqname)

            preferred_id = component_config.get('preferred_id', '')
            if preferred_id:
                instance = self.find_top_component(preferred_id)

            if instance is None:
                cls = class_loader(fqname)
                instance = cls()

            instance.open()

        if instance:
            instance.request_active()

    def _focus_changed(self, old: QWidget, new: QWidget | None) -> None:
        if new is None:  # Window lost focus
            return

        parent = new
        while parent:
            if isinstance(parent, TopComponent):
                ContextTracker().top_component_activated(parent)
                break
            parent = parent.parentWidget()

    # def _update_dock(self, dock: QDockWidget) -> None:
    #     if not dock.widget().count():
    #         dock.hide()
    #     else:
    #         dock.show()

    def _create_component_id(self, component: TopComponent) -> str:
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
        component.assigned_id = name
        return name

    @override  # WindowManager
    def find_mode(self, name: str) -> None:
        if not name:
            name = 'central'

    @override  # WindowManager
    def find_top_component(self, target_id: str) -> TopComponent | None:
        return self._id_to_component.get(target_id, None)

    @override  # WindowManager
    def top_component_open(self, component: TopComponent, tab_position: int = -1) -> None:
        component_id = component.assigned_id
        if component not in self._component_to_id:
            component_id = self._create_component_id(component)
            self._component_to_id[component] = component_id
            self._id_to_component[component_id] = component

        _logger.info(f'Opening {component_id} at location {component.location}')
        self.locations[component.location].add_top_component(component, self, tab_position)

        component.show()

        # if component.location in self.docks:
        #     self._update_dock(self.docks[component.location])

        ContextTracker().top_component_opened(component)

    @override  # WindowManager
    def central_top_component_close_requested(
        self,
        location: Location,
        component: TopComponent,
    ) -> None:
        component.hide()
        location.component_closed(component)

        ContextTracker().top_component_closed(component)

        focused = QApplication.focusWidget()
        if not isinstance(focused, TopComponent):
            current = location.current_component()
            if (current is None) or not isinstance(current, TopComponent):
                ContextTracker().top_component_activated(None)
            else:
                self.top_component_request_active(current)

    @override  # WindowManager
    def top_component_request_active(self, component: TopComponent) -> None:
        # self.locations[component.location].setCurrentWidget(component)
        component.activateWindow()
        component.window().raise_()
        component.setFocus(Qt.FocusReason.OtherFocusReason)

        ContextTracker().top_component_activated(component)

    @override  # QMainWindow
    def closeEvent(self, event: QCloseEvent) -> None:
        if not IDEApplication().accepts_close():
            event.ignore()
            return

        super().closeEvent(event)

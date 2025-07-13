# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore fqname
""""""

from __future__ import annotations

# System imports
import logging
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from functools import partial
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Literal,
    NotRequired,
    TypeAlias,
    TypedDict,
    cast,
)

# Third-party imports
from typing_extensions import override

# Local imports
from openide.config import Config
from openide.integrations import mark_setup
from openide.layout import LayoutConfig
from openide.utils import class_decorator_ext

if TYPE_CHECKING:
    from typing import TypeVar

    # Qt and QDockWidget will be imported at runtime within specific functions to avoid
    # import issue during the setup process
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDockWidget, QMainWindow, QTabWidget, QWidget

    from openide.services.window_manager import WindowManager
    from openide.utils.classes import ClassDecorator
    from openide.utils.datastructures import RecursiveDict
    from openide.windows.top_component import TopComponent

    LC = TypeVar('LC', bound=type['Location'])

_logger = logging.getLogger(__name__)


LocationKind: TypeAlias = Literal['central', 'dock', 'float']
LocationPathOrientation: TypeAlias = Literal['horizontal', 'vertical']


class LocationPathConfig(TypedDict):
    orientation: LocationPathOrientation
    index: int


# @dataclass(frozen=True)
# class LocationPath:
#     orientation: LocationPathOrientation
#     index: int

#     def __getitem__(self, key: str) -> object:
#         return getattr(self, key)


class LocationConfig(TypedDict):
    """Specifies the content that a location definition have"""

    name: str
    """Unique identifier of location. Used by TopComponents when they register"""

    kind: LocationKind
    """Kind of this location.

    - central: In the principal element area of a main window.
    - dock: An element around the central element area within the main window.
    - float: An element floating outside the main window.
    """

    paths: NotRequired[list[LocationPathConfig]]

    target_apps: NotRequired[list[str] | None]


class LocationsModel(Mapping[str, 'Location']):
    def __init__(self) -> None:
        super().__init__()

        self._storage: dict[str, Location] = {}

    def add_location(self, location: Location) -> None:
        self._storage[location.NAME] = location

    # def _get_same_side(
    #     self,
    #     path: LocationPathConfig,
    #     locations: Iterable[Location],
    #     level: int,
    # ) -> Iterator[Location]:
    #     path_sign = path['index'] > 0
    #     for location in locations:
    #         if not location.PATHS:
    #             continue
    #         if len(location.PATHS) < level:
    #             continue
    #         loc_path = location.PATHS[level - 1]
    #         if loc_path['orientation'] != path['orientation']:
    #             continue
    #         if (loc_path['index'] > 0) is not path_sign:
    #             continue

    #         yield location

    # def get_split_path(
    #     self,
    #     target: Location,
    # ) -> Iterator[tuple[Location, Location, Qt.Orientation]]:
    #     from PySide6.QtCore import Qt  # noqa: PLC0415

    #     if not target.PATHS:
    #         return

    #     ORIENTATION = dict(
    #         horizontal=Qt.Orientation.Horizontal,
    #         vertical=Qt.Orientation.Vertical,
    #     )

    #     locations = self._storage.values()
    #     for level in range(1, len(target.PATHS) + 1):
    #         locations = list(self._get_same_side(target.PATHS[level - 1], locations, level))
    #         sorted_paths = sorted(
    #             # {loc.PATHS[level - 1] for loc in locations if loc.PATHS},
    #             locations,
    #             # key=lambda pth: pth['index'],
    #             key=lambda loc: loc.PATHS[level - 1]['index'],
    #         )
    #         # idx_target = sorted_paths.index(target.PATHS[level - 1])
    #         idx_target = sorted_paths.index(target)
    #         if (idx_target + 1) == len(locations):  # Target is rightmost
    #             if idx_target == 0:  # Target is also leftmost
    #                 continue  # Single, no neighbour to split with
    #             else:
    #                 yield (
    #                     sorted_paths[idx_target - 1],
    #                     target,
    #                     ORIENTATION[target.PATHS[level - 1]['orientation']],
    #                 )
    #         else:
    #             yield (
    #                 target,
    #                 sorted_paths[idx_target + 1],
    #                 ORIENTATION[target.PATHS[level - 1]['orientation']],
    #             )

    @override  # Mapping
    def __getitem__(self, name: str) -> Location:
        return self._storage[name]

    @override  # Mapping (Iterable)
    def __iter__(self) -> Iterator[str]:
        return iter(self._storage)

    @override  # Mapping (Collection/Sized)
    def __len__(self) -> int:
        return len(self._storage)


class Location:
    NAME: ClassVar[str]
    KIND: ClassVar[LocationKind]
    PATHS: ClassVar[list[LocationPathConfig] | None]

    components: dict[str, TopComponent]
    _containers: dict[str, QDockWidget]
    _central_tabs: QTabWidget | None

    @staticmethod
    @mark_setup('config')
    def Registration(  # noqa: N802
        name: str,
        kind: LocationKind,
        paths: list[LocationPathConfig] | None = None,
        target_apps: str | list[str] | None = None,
        _config: RecursiveDict | None = None,
    ) -> ClassDecorator[LC]:
        if not target_apps:
            target_apps = None
        elif isinstance(target_apps, str):
            target_apps = [target_apps]

        loc_config = LocationConfig(
            name=name,
            kind=kind,
            target_apps=target_apps,
        )

        if paths:
            loc_config['paths'] = paths

        if _config is not None:
            _config.merge(
                Config(
                    layout=LayoutConfig(
                        locations={
                            _config['_fqname']: loc_config,
                        },
                    ),
                ),
            )

        def callback(cls: type[Location]) -> None:
            cls.NAME = name  # pyright: ignore[reportConstantRedefinition]
            cls.KIND = kind  # pyright: ignore[reportConstantRedefinition]
            cls.PATHS = paths  # pyright: ignore[reportConstantRedefinition]
            # if paths:
            #     cls.PATHS = [LocationPath(**path) for path in paths]  # pyright: ignore[reportConstantRedefinition]
            # else:
            #     cls.PATHS = None  # pyright: ignore[reportConstantRedefinition]

        return class_decorator_ext(callback)

    def __init__(self) -> None:
        super().__init__()

        self.components = {}
        self._containers = {}
        self._central_tabs = None

    def add_top_component(
        self,
        component: TopComponent,
        main_window: QMainWindow,
        tab_position: int = -1,
    ) -> None:
        assert component.assigned_id not in self.components, (
            f'Trying to add a component with ID {component.assigned_id} that already exists'
        )

        if self.KIND == 'central':
            self._add_central_top_component(component, main_window)
        elif self.KIND in ('dock', 'float'):
            self._add_dock_top_component(component, main_window)

    def _add_central_top_component(
        self,
        component: TopComponent,
        main_window: QMainWindow,
        tab_position: int = -1,
    ) -> None:
        from PySide6.QtWidgets import QTabWidget  # noqa: PLC0415

        if not self._central_tabs:
            self._central_tabs = tabs = QTabWidget(parent=main_window)
            tabs.setMovable(True)
            tabs.setTabsClosable(True)
            tabs.tabCloseRequested.connect(
                partial(
                    self._central_tab_close_request_cb,
                    cast('WindowManager', main_window),
                ),
            )

            main_window.setCentralWidget(tabs)

        self.components[component.assigned_id] = component
        if component.icon:
            self._central_tabs.insertTab(
                tab_position,
                component,
                component.icon,
                component.display_name,
            )
        else:
            self._central_tabs.insertTab(tab_position, component, component.display_name)

    def _add_dock_top_component(
        self,
        component: TopComponent,
        main_window: QMainWindow,
        tab_position: int = -1,  # TODO: Find a way to use
    ) -> None:
        from PySide6.QtWidgets import QDockWidget  # noqa: PLC0415

        dock = QDockWidget(component.display_name, main_window)
        dock.setWidget(component)
        main_window.addDockWidget(self._dock_area, dock)

        # TODO: Find way to use icon if present

        if self.KIND == 'float':
            dock.setFloating(True)
            dock.show()

        else:  # noqa: PLR5501
            # Handles stacking ("tabifying") when there are more than one component in that location
            if self._containers:
                # Tabifying with first or last of the preexisting ones does not seem
                # to matter.
                # However, what matters is that our new dock comes as the second arg.
                first = next(iter(self._containers.values()))
                main_window.tabifyDockWidget(first, dock)
            # else:
            #     locations_model = cast('WindowManager', main_window).locations
            #     for location1, location2 in locations_model.get_split_path(self):
            #         pass

        self.components[component.assigned_id] = component
        self._containers[component.assigned_id] = dock

    def _central_tab_close_request_cb(self, main_window: WindowManager, index: int) -> None:
        """Trampoline between Qt event to close a tab and WindowManager to handle the close.

        The WindowManager may have the choice to deny the close. Hence why we don't call/do
        self.component_closed() directly ourself.
        """

        assert self._central_tabs
        component = cast('TopComponent', self._central_tabs.widget(index))
        main_window.central_top_component_close_requested(self, component)

    def component_closed(self, component: TopComponent) -> None:
        component_id = component.assigned_id

        if self.KIND == 'central':
            if self._central_tabs is None:
                _logger.warning(
                    'Asked to close a central top component, but we do not have any tab widget?!',
                )
                return

            self._central_tabs.removeTab(self._central_tabs.indexOf(component))
            del self.components[component_id]

        elif self.KIND in ('dock', 'float'):
            self._containers[component_id].hide()
            del self._containers[component_id]
            del self.components[component_id]

    def current_component(self) -> QWidget | None:
        if self.KIND == 'central':
            if self._central_tabs is None:
                return None
            return self._central_tabs.currentWidget()

        elif self.KIND in ('dock', 'float'):
            return None  # TODO

        return None

    @property
    def _dock_area(self) -> Qt.DockWidgetArea:
        from PySide6.QtCore import Qt  # noqa: PLC0415

        if not (paths := self.PATHS):
            return Qt.DockWidgetArea.NoDockWidgetArea

        first_path = paths[0]
        if first_path['index'] < 0:
            if first_path['orientation'] == 'horizontal':
                return Qt.DockWidgetArea.LeftDockWidgetArea
            else:
                return Qt.DockWidgetArea.TopDockWidgetArea

        elif first_path['index'] > 0:
            if first_path['orientation'] == 'horizontal':
                return Qt.DockWidgetArea.RightDockWidgetArea
            else:
                return Qt.DockWidgetArea.BottomDockWidgetArea

        else:
            msg = (
                f'First path of location {self.NAME} cannot have a weight of '
                '0 since that corresponds to the central widget'
            )
            raise ValueError(msg)

    @override  # object
    def __str__(self) -> str:
        return f'Location({self.NAME})'

    __repr__ = __str__


@Location.Registration(
    name='central',
    kind='central',
)
class CentralLocation(Location):
    pass


@Location.Registration(
    name='left-panel',
    kind='dock',
    paths=[LocationPathConfig(orientation='horizontal', index=-50)],
)
class LeftPanelLocation(Location):
    pass


@Location.Registration(
    name='right-panel',
    kind='dock',
    paths=[LocationPathConfig(orientation='horizontal', index=50)],
)
class RightPanelLocation(Location):
    pass


@Location.Registration(
    name='top-panel',
    kind='dock',
    paths=[LocationPathConfig(orientation='vertical', index=-50)],
)
class TopPanelLocation(Location):
    pass


@Location.Registration(
    name='bottom-panel',
    kind='dock',
    paths=[LocationPathConfig(orientation='vertical', index=50)],
)
class BottomPanelLocation(Location):
    pass


@Location.Registration(
    name='float',
    kind='float',
)
class FloatLocation(Location):
    pass

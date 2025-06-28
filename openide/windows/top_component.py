# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
import logging
import warnings
from enum import StrEnum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pkg_resources

# Third-party imports
from lookups import Lookup, LookupProvider
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QAction, QWidget
from qtpy.uic import loadUi

# Local imports
from openide.actions import Actions
from openide.integration import mark_setup
from openide.utils import (
    MetaClassResolver,
    class_decorator,
    class_decorator_ext,
    class_loader,
)
from openide.windows import WindowManager

if TYPE_CHECKING:
    from qtpy.QtCore import QObject
    from qtpy.QtGui import QHideEvent, QShowEvent

    from openide.actions import ActionReference
    from openide.utils.classes import ClassDecorator
    from openide.utils.datastructures import RecursiveDict

_logger = logging.getLogger(__name__)


class Location(StrEnum):
    Central = auto()
    Explorer = auto()


class TopComponent(MetaClassResolver(LookupProvider, QWidget)):
    PREFERRED_ID: str | None = None
    ICON_BASE: str | None = None

    LOCATION: Location = Location.Central
    OPEN_AT_STARTUP: bool = False
    # POSITION: int | None = None
    # PERSPECTIVES: list = None

    @staticmethod
    @mark_setup('config')
    def Description(  # noqa: N802
        preferred_id: str,
        icon_base: str | None = None,
        _config: RecursiveDict | None = None,
    ) -> ClassDecorator:
        if _config is not None:
            _config.merge(
                dict(
                    components={
                        _config['_fqname']: dict(
                            preferred_id=preferred_id,
                            # icon_base=icon_base,  # Not actually loaded from the YAML file
                        ),
                    },
                ),
            )

        def callback(cls: type[TopComponent]) -> None:
            cls.PREFERRED_ID = preferred_id
            if icon_base is not None:
                cls.ICON_BASE = icon_base

        return class_decorator_ext(callback)

    @staticmethod
    @mark_setup('config')
    def Registration(  # noqa: N802
        location: Location,
        open_at_startup: bool,  # noqa: FBT001
        # position: int | None = None,
        # perspectives: list | None = None,
        _config: RecursiveDict | None = None,
    ) -> ClassDecorator:
        if _config is not None:
            _config.merge(
                dict(
                    components={
                        _config['_fqname']: dict(
                            open_at_startup=open_at_startup,
                            # Not actually loaded from the YAML file:
                            # perspectives=perspectives,
                            # location=location.value,
                            # position=position,
                        ),
                    },
                ),
            )

        def callback(cls: type[TopComponent]) -> None:
            cls.LOCATION = location
            cls.OPEN_AT_STARTUP = open_at_startup
            # No use for, yet:
            # if position is not None:
            #     cls.POSITION = position
            # if perspectives is not None:
            #     cls.PERSPECTIVES = perspectives

        return class_decorator_ext(callback)

    class OpenTopComponentAction(QAction):
        def __init__(
            self,
            display_name: str,
            component: TopComponent,
            target_id: str | None = None,
            parent: QObject | None = None,
        ) -> None:
            super().__init__(text=display_name, parent=parent)
            self._component_fqname = component
            self._target_id = target_id
            self.triggered.connect(self.perform_action)

        def perform_action(self) -> None:
            component = None
            if self._target_id is not None:
                component = WindowManager().find_top_component(self._target_id)

            if component is None:
                cls = class_loader(self._component_fqname)
                component = cls()

            component.open()
            component.request_active()

    @staticmethod
    @mark_setup('config')
    def OpenActionRegistration(  # noqa: N802
        display_name: str,
        references: list[ActionReference],
        target_id: str | None = None,
        _config: RecursiveDict | None = None,
    ) -> ClassDecorator:
        if _config is not None:
            component = _config['_fqname']
            _config['_fqname'] = f'{__name__}:TopComponent.OpenTopComponentAction'
            Actions.Registration(references, _config=_config)
            _config['actions'][-1]['kwargs'] = dict(
                display_name=display_name,
                component=component,
                target_id=target_id,
            )

        return class_decorator

    def __init__(self) -> None:
        super().__init__()

        _logger.info(
            f'We, {type(self)}, have been loaded with {self.PREFERRED_ID=}, {self.LOCATION=} ({type(self.LOCATION)})'
        )

        self._lookup: Lookup | None = None
        self._name: str | None = None
        self._tooltip: str | None = None

    def get_lookup(self) -> Lookup:
        return self._lookup

    def set_lookup(self, lookup: Lookup) -> None:
        if self._lookup is not None:
            msg = f'Lookup is already set on component {self}'
            raise RuntimeError(msg)

        self._lookup = lookup

    def load_ui(self, *ui_file: str) -> None:
        if len(ui_file) == 2:
            ui_file = pkg_resources.resource_filename(*ui_file)
        else:
            ui_file, *_ = ui_file
            if isinstance(ui_file, str):
                ui_file = Path(ui_file)
            if isinstance(ui_file, Path) and not ui_file.is_absolute():
                ui_file = pkg_resources.resource_filename(
                    str(ui_file.parent).replace('/', '.'),
                    ui_file.name,
                )

        loadUi(uifile=str(ui_file), baseinstance=self)

    def open(self) -> None:
        WindowManager().top_component_open(self)  # pyright: ignore[reportAbstractUsage]

    def request_active(self) -> None:
        WindowManager().top_component_request_active(self)  # pyright: ignore[reportAbstractUsage]

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        if event.isAccepted():
            # TODO: Redo, should trigger component_opened only when it is the first time it is opened
            # print('shown')
            self.component_opened()

    def component_opened(self) -> None:
        pass

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802
        super().hideEvent(event)
        if event.isAccepted():
            # TODO: Redo, should trigger component_closed only when it is the last time it is closed
            # print('hidden')
            self.component_closed()

    def component_closed(self) -> None:
        pass

    @property
    def preferred_id(self) -> str:
        if self.PREFERRED_ID is not None:
            return self.PREFERRED_ID

        class_name = self.__class__.__name__
        warnings.warn(  # noqa: B028
            f'{class_name} should provide preferred_id through TopComponent.Descrition, '
            'or override preferred_id property',
        )

        if self.name is None:
            return class_name
        else:
            return self.name

    @property
    def icon(self) -> QIcon:
        if self.ICON_BASE is None:
            return None

        if self.ICON_BASE.startswith(':'):
            return QIcon(self.ICON_BASE)
        else:
            return QIcon.fromTheme(self.ICON_BASE)

    @property
    def location(self) -> Location:
        return self.LOCATION

    @property
    def open_at_startup(self) -> bool:
        return self.OPEN_AT_STARTUP

    # @property
    # def position(self) -> int:
    #     return self.POSITION

    # @property
    # def perspectives(self) -> list:
    #     return self.PERSPECTIVES

    @property
    def name(self) -> str | None:
        return self._name

    @name.setter
    def name(self, new_name: str | None) -> None:
        self._name = new_name

    @property
    def tooltip(self) -> str | None:
        return self._tooltip

    @tooltip.setter
    def tooltip(self, new_value: str | None) -> None:
        self._tooltip = new_value

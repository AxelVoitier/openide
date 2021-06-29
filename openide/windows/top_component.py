# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# System imports
import logging
import pkg_resources
import warnings
from pathlib import Path

# Third-party imports
from lookups import Lookup, LookupProvider
from qtpy.uic import loadUi
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QWidget, QAction

# Local imports
from openide.integration import mark_setup
from openide.utils import (
    class_decorator, class_decorator_ext,
    class_loader, MetaClassResolver,
)
from openide.actions import Actions
from openide.windows import WindowManager


_logger = logging.getLogger(__name__)


class TopComponent(MetaClassResolver(LookupProvider, QWidget)):

    PREFERRED_ID: str = None
    ICON_BASE: str = None

    LOCATION: str = None
    OPEN_AT_STARTUP: bool = False
    POSITION: int = None
    PERSPECTIVES: list = None

    @mark_setup('config')
    def Description(preferred_id, icon_base=None, _config=None):
        if _config is not None:
            _config.merge(dict(
                components={
                    _config['_fqname']: dict(
                        preferred_id=preferred_id,
                        icon_base=icon_base
                    )
                }
            ))

        def callback(cls):
            cls.PREFERRED_ID = preferred_id
            if icon_base is not None:
                cls.ICON_BASE = icon_base

        return class_decorator_ext(callback)

    @mark_setup('config')
    def Registration(location, open_at_startup, position=None, perspectives=None, _config=None):
        if _config is not None:
            _config.merge(dict(
                components={
                    _config['_fqname']: dict(
                        open_at_startup=open_at_startup,
                        perspectives=perspectives,
                        location=location,
                        position=position
                    )
                },
            ))

        def callback(cls):
            cls.LOCATION = location
            cls.OPEN_AT_STARTUP = open_at_startup
            if position is not None:
                cls.POSITION = position
            if perspectives is not None:
                cls.PERSPECTIVES = perspectives

        return class_decorator_ext(callback)

    class OpenTopComponentAction(QAction):

        def __init__(self, display_name, component, target_id=None, parent=None):
            super().__init__(text=display_name, parent=parent)
            self._component_fqname = component
            self._target_id = target_id
            self.triggered.connect(self.perform_action)

        def perform_action(self):
            component = None
            if self._target_id is not None:
                component = WindowManager().find_top_component(self._target_id)

            if component is None:
                cls = class_loader(self._component_fqname)
                component = cls()

            component.open()
            component.request_active()

    @mark_setup('config')
    def OpenActionRegistration(display_name, *args, target_id=None, _config=None, **kwargs):
        if _config is not None:
            component = _config['_fqname']
            _config['_fqname'] = f'{__name__}:TopComponent.OpenTopComponentAction'
            Actions.Registration(*args, _config=_config, **kwargs)
            _config['actions'][-1]['kwargs'] = dict(
                display_name=display_name,
                component=component,
                target_id=target_id,
            )

        return class_decorator

    def __init__(self):
        super().__init__()

        self._lookup = None
        self._name = None
        self._tooltip = None

    def get_lookup(self) -> Lookup:
        return self._lookup

    def set_lookup(self, lookup):
        if self._lookup is not None:
            raise RuntimeError(f'Lookup is already set on component {self}')

        self._lookup = lookup

    def load_ui(self, *ui_file):
        if len(ui_file) == 2:
            ui_file = pkg_resources.resource_filename(*ui_file)
        else:
            ui_file, *_ = ui_file
            if isinstance(ui_file, str):
                ui_file = Path(ui_file)
            if isinstance(ui_file, Path) and not ui_file.is_absolute():
                ui_file = pkg_resources.resource_filename(
                    str(ui_file.parent).replace('/', '.'), ui_file.name)

        loadUi(uifile=str(ui_file), baseinstance=self)

    def open(self):
        WindowManager().top_component_open(self)

    def request_active(self):
        WindowManager().top_component_request_active(self)

    def showEvent(self, event):
        super().showEvent(event)
        if event.isAccepted():
            # TODO: Redo, should trigger component_opened only when it is the first time it is opened
            # print('shown')
            self.component_opened()

    def component_opened(self):
        pass

    def hideEvent(self, event):
        super().hideEvent(event)
        if event.isAccepted():
            # TODO: Redo, should trigger component_closed only when it is the last time it is closed
            # print('hidden')
            self.component_closed()

    def component_closed(self):
        pass

    @property
    def preferred_id(self) -> str:
        if self.PREFERRED_ID is not None:
            return self.PREFERRED_ID

        class_name = self.__class__.__name__
        warnings.warn(
            f'{class_name} should provide preferred_id through TopComponent.Descrition, '
            'or override preferred_id property'
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
    def location(self) -> str:
        return self.LOCATION

    @property
    def open_at_startup(self) -> bool:
        return self.OPEN_AT_STARTUP

    @property
    def position(self) -> int:
        return self.POSITION

    @property
    def perspectives(self) -> list:
        return self.PERSPECTIVES

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        self._name = new_name

    @property
    def tooltip(self):
        return self._tooltip

    @tooltip.setter
    def tooltip(self, new_value):
        self._tooltip = new_value

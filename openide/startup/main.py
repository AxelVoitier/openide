# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
import logging
import sys

import pkg_resources

# Third-party imports
import yaml

# Local imports
from openide.utils import RecursiveDict, SingletonMeta

_logger = logging.getLogger(__name__)


class IDEApplication(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._gui_started = False

        self._setup_logger()
        self._load_config()

    def _setup_logger(self) -> None:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        for handler in logger.handlers:
            logger.removeHandler(handler)

        formatter = logging.Formatter(
            fmt='{levelname:<7}: {threadName}: {name}: {message}',
            style='{',
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def _load_config(self) -> None:
        self._config = RecursiveDict()
        for dist in pkg_resources.working_set:
            if not dist.has_metadata('openide.yaml'):
                continue

            _logger.info('Loading config for package %s', dist.project_name)
            self._config.merge(yaml.safe_load(dist.get_metadata('openide.yaml')))

    @property
    def config(self) -> RecursiveDict:
        return self._config

    def start(self) -> None:
        # For now, only supporting GUI mode. CLI mode will come later
        self.gui_start()

    def gui_start(self) -> None:
        from qtpy.QtCore import Qt  # noqa: PLC0415
        from qtpy.QtWidgets import QApplication  # noqa: PLC0415

        from openide.lookup import MainLookup  # noqa: PLC0415
        from openide.windows import WindowManager  # noqa: PLC0415

        if self._gui_started:
            _logger.warning('Attempting to start GUI but it is already started')
            return
        self._gui_started = True

        # TODO: Set Look and feel
        # TODO: Set window size

        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)  # Avoids pesky warning
        self._qt_app = QApplication(sys.argv)
        MainLookup().register(self._qt_app)
        self._main_window = WindowManager()  # pyright: ignore[reportAbstractUsage]
        self._main_window.load()

        # Temporary solution
        geometry = self._main_window.screen().availableGeometry()
        self._main_window.resize(geometry.width() / 3, geometry.height() / 2)

        self._main_window.show()

        self._qt_app.exec_()

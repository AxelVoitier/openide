# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:words
# spell-checker:ignore levelname

from __future__ import annotations

# System imports
import logging
import sys
from pathlib import Path

# Third-party imports
# Local imports
from openide.config import Config, load_config
from openide.utils import SingletonMeta

_logger = logging.getLogger(__name__)


class IDEApplication(metaclass=SingletonMeta):
    def __init__(self, app_name: str | None = None) -> None:
        super().__init__()

        if app_name:
            self.__app_name = app_name
        else:
            self.__app_name = Path(sys.argv[0]).stem

        self.__gui_started = False

        self._setup_logger()

        self._config = load_config(
            lambda package_name, _: _logger.info('Loading config for package %s', package_name),
        )

    @property
    def app_name(self) -> str:
        return self.__app_name

    def is_targeted(self, element_id: str, target_apps: list[str] | None) -> bool:
        """
        Check if an element declared in the config is meant to target this application.

        This is a default implementation only checking if our app_name appears in the
        target_apps of the element.

        An application wishing to change that default behaviour can sub-class us,
        and reimplement this method.
        """
        if not target_apps:
            # If the element did not specify anything, it is for every app.
            return True

        return self.app_name in target_apps

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

    @property
    def config(self) -> Config:
        return self._config

    def start(self) -> None:
        _logger.info('Starting application %s', self.app_name)
        # For now, only supporting GUI mode. CLI mode will come later
        self.gui_start()

    def gui_start(self) -> None:
        from PySide6.QtCore import Qt  # noqa: PLC0415
        from PySide6.QtWidgets import QApplication  # noqa: PLC0415

        from openide.lookup import MainLookup  # noqa: PLC0415
        from openide.services import WindowManager  # noqa: PLC0415

        if self.__gui_started:
            _logger.warning('Attempting to start GUI but it is already started')
            return
        self.__gui_started = True

        # TODO: Set Look and feel
        # TODO: Set window size

        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)  # Avoids pesky warning
        self._qt_app = QApplication(sys.argv)
        MainLookup().register(self._qt_app)
        self._main_window = WindowManager()  # pyright: ignore[reportAbstractUsage]
        if self._main_window is None:
            msg = (
                'No WindowManager found. Are the services, config, and/or lookups setup correctly?'
            )
            raise RuntimeError(msg)
        self._main_window.load()

        # Temporary solution
        geometry = self._main_window.screen().availableGeometry()
        self._main_window.resize(geometry.width() / 3, geometry.height() / 2)

        self._main_window.show()

        self._qt_app.exec()


if __name__ == '__main__':
    app = IDEApplication()
    app.start()

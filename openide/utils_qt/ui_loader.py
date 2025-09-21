# spell-checker:words segfault
# spell-checker:ignore uifile customwidgets

from __future__ import annotations

# System imports
import importlib
import importlib.resources
import logging
from pathlib import Path
from typing import TYPE_CHECKING, cast
from xml.etree.ElementTree import ElementTree

# Third-party imports
from PySide6.QtCore import QDir, QMetaObject
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget
from typing_extensions import override

# Local imports

if TYPE_CHECKING:
    from typing import Final

    from PySide6.QtWidgets import QWidget

__all__: Final = (
    'load_ui',
    'load_ui_from_resource',
)

_logger = logging.getLogger(__name__)


# Basically, what https://github.com/spyder-ide/qtpy/blob/master/qtpy/uic.py does,
# (permalink to date: https://github.com/spyder-ide/qtpy/blob/ad8d3453203c9046fc86a2b35195201a6ef3a921/qtpy/uic.py)
# but narrowed to PySide6, renamed it a bit, typed it, and fixed few minor bugs.
# In terms of license/copyright, what they have is itself based on various sources.
# But they are all more permissive than our MPL v2, so, it's fine.

# => Advantage: we can customise the importing of custom widgets, or the handling
# of working directory (to load icons and resources) in a way more tailored to our
# plugin system if needs come.


class UiLoader(QUiLoader):
    """
    Subclass of :class:`~PySide.QtUiTools.QUiLoader` to create the user
    interface in a base instance.

    Unlike :class:`~PySide.QtUiTools.QUiLoader` itself this class does not
    create a new instance of the top-level widget, but creates the user
    interface in an existing instance of the top-level class if needed.

    This mimics the behaviour of :func:`PyQt4.uic.loadUi`.
    """

    def __init__(
        self,
        base_instance: QWidget | None,
        custom_widgets: dict[str, type[QWidget]] | None = None,
    ) -> None:
        """
        Create a loader for the given ``base_instance``.

        The user interface is created in ``base_instance``, which must be an
        instance of the top-level class in the user interface to load, or a
        subclass thereof.

        ``custom_widgets`` is a dictionary mapping from class name to class
        object for custom widgets. Usually, this should be done by calling
        registerCustomWidget on the QUiLoader, but with PySide 1.1.2 on
        Ubuntu 12.04 x86_64 this causes a segfault.

        ``parent`` is the parent object of this loader.
        """

        QUiLoader.__init__(self, base_instance)

        self.base_instance = base_instance

        if custom_widgets is None:
            self.custom_widgets = {}
        else:
            self.custom_widgets = custom_widgets

    @override  # QUiLoader
    def createWidget(
        self,
        class_name: str,
        parent: QWidget | None = None,
        name: str = '',
    ) -> QWidget:
        """
        Function that is called for each widget defined in ui file,
        overridden here to populate base_instance instead.
        """

        if (parent is None) and self.base_instance:
            # supposed to create the top-level widget, return the base
            # instance instead
            return self.base_instance

        # For some reason, Line is not in the list of available
        # widgets, but works fine, so we have to special case it here.
        if (class_name in self.availableWidgets()) or (class_name == 'Line'):
            # create a new widget for child widgets
            widget = QUiLoader.createWidget(
                self,
                class_name,
                parent,
                name,
            )

        else:
            # If not in the list of availableWidgets, must be a custom
            # widget. This will raise KeyError if the user has not
            # supplied the relevant class_name in the dictionary or if
            # custom_widgets is empty.
            try:
                widget = self.custom_widgets[class_name](parent)
            except KeyError as error:
                msg = f'No custom widget {class_name} found in customwidgets'
                raise ValueError(msg) from error

        if self.base_instance:
            # set an attribute for the new child widget on the base
            # instance, just like PyQt4.uic.loadUi does.
            setattr(self.base_instance, name, widget)

        return widget


def _get_custom_widgets(ui_file: Path) -> dict[str, type[QWidget]]:
    """
    This function is used to parse a ui file and look for the <customwidgets>
    section, then automatically load all the custom widget classes.
    """

    # Parse the UI file
    etree = ElementTree()
    ui = etree.parse(ui_file)

    # Get the customwidgets section
    custom_widgets = ui.find('customwidgets')

    if custom_widgets is None:
        return {}

    custom_widget_classes: dict[str, type[QWidget]] = {}

    for custom_widget in list(custom_widgets):
        # TODO: Error handling. This is parsing external/user files. There can be weird things.
        cw_class = custom_widget.find('class').text
        cw_header = custom_widget.find('header').text

        module = importlib.import_module(cw_header)

        custom_widget_classes[cw_class] = cast('QWidget', getattr(module, cw_class))

    return custom_widget_classes


def load_ui(
    uifile: Path,
    base_instance: QWidget | None = None,
    working_directory: Path | None = None,
) -> QWidget:
    """
    Dynamically load a user interface from the given ``uifile``.

    ``uifile`` is a string containing a file name of the UI file to load.

    If ``base_instance`` is ``None``, the a new instance of the top-level
    widget will be created. Otherwise, the user interface is created within
    the given ``base_instance``. In this case ``base_instance`` must be an
    instance of the top-level widget class in the UI file to load, or a
    subclass thereof. In other words, if you've created a ``QMainWindow``
    interface in the designer, ``base_instance`` must be a ``QMainWindow``
    or a subclass thereof, too. You cannot load a ``QMainWindow`` UI file
    with a plain :class:`~PySide.QtGui.QWidget` as ``base_instance``.

    :method:`~PySide.QtCore.QMetaObject.connectSlotsByName()` is called on
    the created user interface, so you can implemented your slots according
    to its conventions in your widget class.

    Return ``base_instance``, if ``base_instance`` is not ``None``. Otherwise
    return the newly created instance of the user interface.
    """

    # We parse the UI file and import any required custom widgets
    custom_widgets = _get_custom_widgets(uifile)

    loader = UiLoader(base_instance, custom_widgets)

    if working_directory is not None:
        loader.setWorkingDirectory(QDir(working_directory))

    widget = loader.load(uifile)
    QMetaObject.connectSlotsByName(widget)
    return widget


def load_ui_from_resource(
    *ui_file: str,
    base_instance: QWidget | None = None,
) -> QWidget:
    if len(ui_file) != 2:
        ui_file_path, *_ = ui_file
        if not isinstance(ui_file_path, Path):
            ui_file_path = Path(ui_file_path)

        if ui_file_path.is_absolute():
            return load_ui(
                uifile=ui_file_path,
                base_instance=base_instance,
                working_directory=ui_file_path.parent,
            )

        ui_file = (str(ui_file_path.parent).replace('/', '.'), ui_file_path.name)

    ref = importlib.resources.files(ui_file[0]) / ui_file[1]
    with importlib.resources.as_file(ref) as path:
        return load_ui(uifile=path, base_instance=base_instance, working_directory=path.parent)

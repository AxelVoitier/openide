from __future__ import annotations

from typing import TYPE_CHECKING

from lookups import GenericLookup, InstanceContent
from openide.actions import ActionReference
from openide.windows import TopComponent

from nbm_selection_01.my_api.event import Event

if TYPE_CHECKING:
    from PySide6.QtWidgets import QLineEdit, QPushButton


@TopComponent.Description(
    preferred_id='MyEditorTopComponent',
    display_name='My Editor',
)
@TopComponent.Registration(
    location='central',
    open_at_startup=True,
    target_apps='nbm-selection-01',
)
@TopComponent.OpenActionRegistration(
    display_name='Open Editor',
    references=[ActionReference(path='Menu/Window')],
    target_apps='nbm-selection-01',
)
class MyEditor(TopComponent):
    pushButton: QPushButton
    lineEdit_1: QLineEdit
    lineEdit_2: QLineEdit

    def __init__(self) -> None:
        print('MyEditor created')
        super().__init__()

        self.load_ui(__name__, 'my_editor.ui')

        self._content = InstanceContent()
        self.lookup = GenericLookup(self._content)
        self.pushButton.clicked.connect(self.update_content)

        self.update_content()

    def update_content(self) -> None:
        print('Updating content')
        obj = Event()
        self.lineEdit_1.setText(f'Event #{obj.index}')
        self.lineEdit_2.setText(f'Created: {obj.date}')
        # setDisplayName(f'MyEditor {obj.index}')
        self.display_name = f'MyEditor {obj.index}'

        self._content.set([obj])

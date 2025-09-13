from __future__ import annotations

from typing import TYPE_CHECKING

from openide.actions import ActionReference
from openide.services import GlobalContext
from openide.windows import TopComponent
from typing_extensions import override

from nbm_selection_01.my_api.event import Event

if TYPE_CHECKING:
    from lookups import Result
    from PySide6.QtWidgets import QLabel


@TopComponent.Description(
    preferred_id='MyViewerTopComponent',
    display_name='My Viewer',
)
@TopComponent.Registration(
    location='left-panel',
    open_at_startup=True,
    target_apps='nbm-selection-01',
)
@TopComponent.OpenActionRegistration(
    display_name='My Viewer',
    target_id='MyViewerTopComponent',
    references=[ActionReference(path='Menu/Window')],
    target_apps='nbm-selection-01',
)
class MyViewerTopComponent(TopComponent):
    label_1: QLabel
    label_2: QLabel

    def __init__(self) -> None:
        print('MyViewerTopComponent created')
        super().__init__()

        self.load_ui(__name__, 'my_viewer.ui')
        self.name = 'MyViewer Window'
        self.tooltip = 'This is a MyViewer window'

        self.result: Result[Event] | None = None

    @override  # TopComponent
    def component_opened(self) -> None:
        self.result = GlobalContext().lookup_result(Event)
        self.result.listeners += self.result_changed

    @override  # TopComponent
    def component_closed(self) -> None:
        if self.result is not None:
            self.result.listeners -= self.result_changed

    def result_changed(self, result: Result[Event]) -> None:
        all_events = result.all_instances()
        if all_events:
            event = next(iter(all_events))
            self.label_1.setText(str(event.index))
            self.label_2.setText(str(event.date))
        else:
            self.label_1.setText('[Nothing selected]')
            self.label_2.setText('')

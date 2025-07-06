from openide.actions import ActionReference
from openide.services import GlobalContext
from openide.windows import Location, TopComponent

from nbm_selection_01.my_api.event import Event


@TopComponent.Description(
    preferred_id='MyViewerTopComponent',
)
@TopComponent.Registration(
    location=Location.Explorer,
    open_at_startup=True,
    target_apps='nbm-selection-01',
)
@TopComponent.OpenActionRegistration(
    display_name='MyViewer',
    target_id='MyViewerTopComponent',
    references=[ActionReference(path='Menu/Window')],
    target_apps='nbm-selection-01',
)
class MyViewerTopComponent(TopComponent):
    def __init__(self):
        print('MyViewerTopComponent created')
        super().__init__()

        self.load_ui(__name__, 'my_viewer.ui')
        self.name = 'MyViewer Window'
        self.tooltip = 'This is a MyViewer window'

        self._result = None

    def component_opened(self):
        self._result = GlobalContext().lookup_result(Event)
        self._result.listeners += self.result_changed

    def component_closed(self):
        self._result.listeners -= self.result_changed

    def result_changed(self, result):
        all_events = result.all_instances()
        if all_events:
            event = next(iter(all_events))
            self.label_1.setText(str(event.index))
            self.label_2.setText(str(event.date))
        else:
            self.label_1.setText('[Nothing selected]')
            self.label_2.setText('')

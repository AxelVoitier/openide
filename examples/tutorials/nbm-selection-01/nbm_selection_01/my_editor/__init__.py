from lookups import GenericLookup, InstanceContent
from openide.actions import ActionReference
from openide.windows import Location, TopComponent

from nbm_selection_01.my_api.event import Event


@TopComponent.Description(
    preferred_id='MyEditorTopComponent',
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
    def __init__(self):
        print('MyEditor created')
        super().__init__()

        self.load_ui(__name__, 'my_editor.ui')

        self._content = InstanceContent()
        self.set_lookup(GenericLookup(self._content))
        self.pushButton.clicked.connect(self.update_content)

        self.update_content()

    @property
    def lookup(self):
        return self._lookup

    def update_content(self):
        print('Updating content')
        obj = Event()
        self.lineEdit_1.setText(f'Event #{obj.index}')
        self.lineEdit_2.setText(f'Created: {obj.date}')
        # setDisplayName(f'MyEditor {obj.index}')
        self.name = f'MyEditor {obj.index}'

        self._content.set([obj])

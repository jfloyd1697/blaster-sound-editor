from typing import Optional

from PyQt6 import QtWidgets

from dataclass_editor import DataclassEditor
from persistence.editor_configs import EditorConfig
from models import TransitionDef


class StateEditor(QtWidgets.QWidget):
    def __init__(self, on_changed):
        super().__init__()
        self.on_changed = on_changed
        self.editor_config = EditorConfig()
        self._loading = False
        self._state_name: Optional[str] = None
        self._transition: Optional[TransitionDef] = None

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        layout.addLayout(form)

        self.state_name = QtWidgets.QLineEdit()
        self.state_name_label = QtWidgets.QLabel("State Name")
        form.addRow(self.state_name_label, self.state_name)

        self.transition_event = QtWidgets.QLineEdit()
        self.transition_event_label = QtWidgets.QLabel("Transition Event")
        form.addRow(self.transition_event_label, self.transition_event)

        self.transition_target = QtWidgets.QLineEdit()
        self.transition_target_label = QtWidgets.QLabel("Transition Target")
        form.addRow(self.transition_target_label, self.transition_target)

        self.hint = QtWidgets.QLabel("Select a state or transition in the tree.")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        layout.addStretch(1)

        self.transition_dc_editor = DataclassEditor(TransitionDef)
        self.transition_dc_editor.bind_line_edit("event", self.transition_event)
        self.transition_dc_editor.bind_line_edit("target", self.transition_target)
        self.transition_dc_editor.connect_changed(self._on_transition_changed)

        self.state_name.textChanged.connect(self._on_state_name_changed)

        self.show_nothing()

    def set_editor_config(self, config: EditorConfig):
        self.editor_config = config
        self.apply_editor_config()

    def _set_row_visible(self, label: QtWidgets.QWidget, field: QtWidgets.QWidget, visible: bool):
        label.setVisible(visible)
        field.setVisible(visible)

    def show_nothing(self):
        self._state_name = None
        self._transition = None
        self._loading = True
        try:
            self.state_name.clear()
            self.transition_dc_editor.clear()
            self.state_name.setDisabled(True)
            self.transition_event.setDisabled(True)
            self.transition_target.setDisabled(True)
            self.hint.setText("Select a state or transition in the tree.")
        finally:
            self._loading = False
            self.apply_editor_config()

    def set_state(self, name: str):
        self._state_name = name
        self._transition = None
        self._loading = True
        try:
            self.state_name.setText(name)
            self.transition_dc_editor.clear()
            self.state_name.setDisabled(False)
            self.transition_event.setDisabled(True)
            self.transition_target.setDisabled(True)
            self.hint.setText("Editing state properties.")
        finally:
            self._loading = False
            self.apply_editor_config()

    def set_transition(self, transition: TransitionDef):
        self._transition = transition
        self._state_name = None
        self._loading = True
        try:
            self.transition_dc_editor.set_value(transition)
            self.transition_event.setDisabled(False)
            self.transition_target.setDisabled(False)
            self.hint.setText("Editing transition properties.")
        finally:
            self._loading = False
            self.apply_editor_config()

    def _on_state_name_changed(self):
        if self._loading or self._state_name is None:
            return
        self.on_changed("rename_state", self.state_name.text().strip())

    def _on_transition_changed(self, updated: TransitionDef):
        if self._loading or self._transition is None:
            return
        self._transition.__dict__.clear()
        self._transition.__dict__.update(updated.__dict__)
        self.on_changed("transition_updated", None)

    def apply_editor_config(self):
        self.setVisible(self.editor_config.ui.showStateEditor)

        transition_cfg = self.editor_config.fields.transition

        self._set_row_visible(
            self.state_name_label,
            self.state_name,
            self._state_name is not None,
        )
        self._set_row_visible(
            self.transition_event_label,
            self.transition_event,
            self._transition is not None and transition_cfg.event.visible,
        )
        self._set_row_visible(
            self.transition_target_label,
            self.transition_target,
            self._transition is not None and transition_cfg.target.visible,
        )
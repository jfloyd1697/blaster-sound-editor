from typing import Optional

from PyQt6 import QtWidgets, QtGui

from dataclass_editor import DataclassEditor
from persistence.editor_configs import EditorConfig
from models import ActionDef, LightPatternDef, LightStepDef, ActionType, LightPatternMode


def sounds_to_model(text: str) -> list[str]:
    return [s.strip() for s in text.split(",") if s.strip()]


def sounds_from_model(value) -> str:
    return ", ".join(value or [])


def color_to_model(text: str) -> list[int]:
    parts = [p.strip() for p in text.split(",")]
    values = []
    for i in range(3):
        try:
            v = int(parts[i]) if i < len(parts) else 0
        except ValueError:
            v = 0
        values.append(max(0, min(255, v)))
    return values


def color_from_model(value) -> str:
    value = value or [0, 0, 0]
    if len(value) < 3:
        value = [0, 0, 0]
    return f"{value[0]},{value[1]},{value[2]}"


def zero_to_none(value: int) -> int | None:
    return None if value == 0 else value


def none_to_zero(value) -> int:
    return 0 if value is None else int(value)


def get_steps_from_table(table: QtWidgets.QTableWidget) -> list[LightStepDef]:
    result: list[LightStepDef] = []
    for row in range(table.rowCount()):
        vals: list[int] = []
        for col in range(4):
            item = table.item(row, col)
            try:
                vals.append(int(item.text()) if item else 0)
            except ValueError:
                vals.append(0)
        result.append(LightStepDef(color=(vals[0], vals[1], vals[2]), durationMs=vals[3]))
    return result


def set_steps_to_table(table: QtWidgets.QTableWidget, value) -> None:
    table.blockSignals(True)
    table.setRowCount(0)
    for step in value or []:
        row = table.rowCount()
        table.insertRow(row)
        vals = [*step.color[:3], step.durationMs]
        for col, val in enumerate(vals):
            table.setItem(row, col, QtWidgets.QTableWidgetItem(str(val)))
    table.blockSignals(False)


def clear_steps_table(table: QtWidgets.QTableWidget, default) -> None:
    set_steps_to_table(table, default or [])


def is_empty_pattern(pattern: LightPatternDef) -> bool:
    return (
            pattern.mode in ("", "solid", "Solid")
            and pattern.color == [0, 0, 0]
            and pattern.brightness is None
            and pattern.durationMs is None
            and pattern.count is None
            and pattern.intervalMs is None
            and len(pattern.steps) == 0
    )


class ActionEditor(QtWidgets.QWidget):
    def __init__(self, on_changed):
        super().__init__()
        self.on_changed = on_changed
        self.editor_config = EditorConfig()
        self._loading = False
        self._target_action: Optional[ActionDef] = None

        root = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        root.addLayout(form)

        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(list(ActionType))
        self.type_label = QtWidgets.QLabel("Type")
        form.addRow(self.type_label, self.type_combo)

        self.sound_edit = QtWidgets.QLineEdit()
        self.sound_label = QtWidgets.QLabel("Sound")
        form.addRow(self.sound_label, self.sound_edit)

        self.sounds_edit = QtWidgets.QLineEdit()
        self.sounds_edit.setPlaceholderText("comma,separated,paths.wav")
        self.sounds_label = QtWidgets.QLabel("Sounds")
        form.addRow(self.sounds_label, self.sounds_edit)

        self.loop_check = QtWidgets.QCheckBox("Loop")
        self.loop_label = QtWidgets.QLabel("Loop")
        form.addRow(self.loop_label, self.loop_check)

        self.event_edit = QtWidgets.QLineEdit()
        self.event_label = QtWidgets.QLabel("Event")
        form.addRow(self.event_label, self.event_edit)

        self.name_edit = QtWidgets.QLineEdit()
        self.name_label = QtWidgets.QLabel("Name")
        form.addRow(self.name_label, self.name_edit)

        self.amount_spin = QtWidgets.QSpinBox()
        self.amount_spin.setRange(-999999, 999999)
        self.amount_label = QtWidgets.QLabel("Amount")
        form.addRow(self.amount_label, self.amount_spin)

        self.delay_spin = QtWidgets.QSpinBox()
        self.delay_spin.setRange(0, 999999)
        self.delay_spin.setSuffix(" ms")
        self.delay_label = QtWidgets.QLabel("Delay")
        form.addRow(self.delay_label, self.delay_spin)

        self.pattern_mode = QtWidgets.QComboBox()
        self.pattern_mode.addItems(list(LightPatternMode))
        self.pattern_mode_label = QtWidgets.QLabel("Pattern Mode")
        form.addRow(self.pattern_mode_label, self.pattern_mode)

        self.pattern_color = QtWidgets.QLineEdit("0,0,0")
        self.pick_color_btn = QtWidgets.QPushButton("Pick Color")
        color_row = QtWidgets.QHBoxLayout()
        color_row.setContentsMargins(0, 0, 0, 0)
        color_row.addWidget(self.pattern_color)
        color_row.addWidget(self.pick_color_btn)
        self.color_wrap = QtWidgets.QWidget()
        self.color_wrap.setLayout(color_row)
        self.pattern_color_label = QtWidgets.QLabel("Pattern Color")
        form.addRow(self.pattern_color_label, self.color_wrap)

        self.pattern_brightness = QtWidgets.QSpinBox()
        self.pattern_brightness.setRange(0, 255)
        self.pattern_brightness_label = QtWidgets.QLabel("Brightness")
        form.addRow(self.pattern_brightness_label, self.pattern_brightness)

        self.pattern_duration = QtWidgets.QSpinBox()
        self.pattern_duration.setRange(0, 999999)
        self.pattern_duration.setSuffix(" ms")
        self.pattern_duration_label = QtWidgets.QLabel("Duration")
        form.addRow(self.pattern_duration_label, self.pattern_duration)

        self.pattern_count = QtWidgets.QSpinBox()
        self.pattern_count.setRange(0, 999999)
        self.pattern_count_label = QtWidgets.QLabel("Count")
        form.addRow(self.pattern_count_label, self.pattern_count)

        self.pattern_interval = QtWidgets.QSpinBox()
        self.pattern_interval.setRange(0, 999999)
        self.pattern_interval.setSuffix(" ms")
        self.pattern_interval_label = QtWidgets.QLabel("Interval")
        form.addRow(self.pattern_interval_label, self.pattern_interval)

        self.steps_table = QtWidgets.QTableWidget(0, 4)
        self.steps_table.setHorizontalHeaderLabels(["R", "G", "B", "Duration ms"])
        self.steps_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.steps_label = QtWidgets.QLabel("Pattern Steps")
        form.addRow(self.steps_label, self.steps_table)

        step_buttons = QtWidgets.QHBoxLayout()
        self.add_step_btn = QtWidgets.QPushButton("Add Step")
        self.remove_step_btn = QtWidgets.QPushButton("Remove Step")
        step_buttons.addWidget(self.add_step_btn)
        step_buttons.addWidget(self.remove_step_btn)
        self.step_wrap = QtWidgets.QWidget()
        self.step_wrap.setLayout(step_buttons)
        self.step_buttons_label = QtWidgets.QLabel("")
        form.addRow(self.step_buttons_label, self.step_wrap)

        self.clear_btn = QtWidgets.QPushButton("Clear Optional Fields")
        root.addWidget(self.clear_btn)
        root.addStretch(1)

        self.pattern_editor = DataclassEditor(LightPatternDef)
        self.pattern_editor.bind_combo_box("mode", self.pattern_mode)
        self.pattern_editor.bind_line_edit(
            "color",
            self.pattern_color,
            to_model=color_to_model,
            from_model=color_from_model,
        )
        self.pattern_editor.bind_spin_box(
            "brightness",
            self.pattern_brightness,
            to_model=zero_to_none,
            from_model=none_to_zero,
        )
        self.pattern_editor.bind_spin_box(
            "durationMs",
            self.pattern_duration,
            to_model=zero_to_none,
            from_model=none_to_zero,
        )
        self.pattern_editor.bind_spin_box(
            "count",
            self.pattern_count,
            to_model=zero_to_none,
            from_model=none_to_zero,
        )
        self.pattern_editor.bind_spin_box(
            "intervalMs",
            self.pattern_interval,
            to_model=zero_to_none,
            from_model=none_to_zero,
        )
        self.pattern_editor.bind_table(
            "steps",
            self.steps_table,
            get_value=get_steps_from_table,
            set_value=set_steps_to_table,
            clear_value=clear_steps_table,
        )

        self.action_dc_editor = DataclassEditor(ActionDef)
        self.action_dc_editor.bind_combo_box("type", self.type_combo)
        self.action_dc_editor.bind_line_edit("sound", self.sound_edit)
        self.action_dc_editor.bind_line_edit(
            "sounds",
            self.sounds_edit,
            to_model=sounds_to_model,
            from_model=sounds_from_model,
        )
        self.action_dc_editor.bind_check_box(
            "loop",
            self.loop_check,
            to_model=lambda v: True if v else None,
            from_model=lambda v: bool(v),
        )
        self.action_dc_editor.bind_line_edit("event", self.event_edit)
        self.action_dc_editor.bind_line_edit("name", self.name_edit)
        self.action_dc_editor.bind_spin_box(
            "amount",
            self.amount_spin,
            to_model=zero_to_none,
            from_model=none_to_zero,
        )
        self.action_dc_editor.bind_spin_box(
            "delayMs",
            self.delay_spin,
            to_model=zero_to_none,
            from_model=none_to_zero,
        )
        self.action_dc_editor.bind_optional_nested(
            "pattern",
            self.pattern_editor,
            is_empty=is_empty_pattern,
        )
        self.action_dc_editor.connect_changed(self._on_dataclass_changed)

        self.type_combo.currentTextChanged.connect(self.apply_editor_config)
        self.pattern_mode.currentTextChanged.connect(self.apply_editor_config)
        self.pick_color_btn.clicked.connect(self._pick_color)
        self.add_step_btn.clicked.connect(self._add_step)
        self.remove_step_btn.clicked.connect(self._remove_step)
        self.clear_btn.clicked.connect(self._clear_optional_fields)

        self.setDisabled(True)
        self.apply_editor_config()

    def set_editor_config(self, config: EditorConfig):
        self.editor_config = config
        self.apply_editor_config()

    def set_action(self, action: Optional[ActionDef]):
        self._target_action = action
        self.setDisabled(action is None)
        self._loading = True
        try:
            self.action_dc_editor.set_value(action)
        finally:
            self._loading = False
            self.apply_editor_config()

    def assign_asset_file(self, path: str):
        if self._target_action is None:
            return
        normalized = path.replace("\\", "/")
        if self.type_combo.currentText() == ActionType.PLAY_SOUND_RANDOM:
            current = sounds_to_model(self.sounds_edit.text())
            if normalized not in current:
                current.append(normalized)
            self.sounds_edit.setText(sounds_from_model(current))
        else:
            self.sound_edit.setText(normalized)

    @staticmethod
    def _set_row_visible(label: QtWidgets.QWidget, field: QtWidgets.QWidget, visible: bool):
        label.setVisible(visible)
        field.setVisible(visible)

    def _on_dataclass_changed(self, updated: ActionDef):
        if self._loading or self._target_action is None:
            return
        self._target_action.__dict__.clear()
        self._target_action.__dict__.update(updated.__dict__)
        self.apply_editor_config()
        self.on_changed()

    def _pick_color(self):
        rgb = color_to_model(self.pattern_color.text())
        chosen = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(rgb[0], rgb[1], rgb[2]),
            self,
            "Choose Color",
        )
        if chosen.isValid():
            self.pattern_color.setText(
                f"{chosen.red()},{chosen.green()},{chosen.blue()}"
            )

    def _add_step(self):
        row = self.steps_table.rowCount()
        self.steps_table.insertRow(row)
        for col, value in enumerate([0, 0, 0, 100]):
            self.steps_table.setItem(row, col, QtWidgets.QTableWidgetItem(str(value)))

    def _remove_step(self):
        row = self.steps_table.currentRow()
        if row >= 0:
            self.steps_table.removeRow(row)

    def _clear_optional_fields(self):
        if self._target_action is None:
            return
        self._loading = True
        try:
            self.action_dc_editor.clear()
        finally:
            self._loading = False
            updated = self.action_dc_editor.get_value()
            self._target_action.__dict__.clear()
            self._target_action.__dict__.update(updated.__dict__)
            self.apply_editor_config()
            self.on_changed()

    def apply_editor_config(self):
        action_type = self.type_combo.currentText()
        action_cfg = self.editor_config.actionTypes.get(action_type)
        field_cfgs = action_cfg.fields if action_cfg else {}

        def visible(name: str, default=True):
            cfg = field_cfgs.get(name)
            return default if cfg is None else cfg.visible

        def show_when(name: str) -> bool:
            cfg = field_cfgs.get(name)
            if cfg is None or not cfg.showWhen:
                return True
            for dep_name, expected in cfg.showWhen.items():
                if dep_name == "pattern.mode" and self.pattern_mode.currentText() != expected:
                    return False
                if dep_name == "type" and self.type_combo.currentText() != expected:
                    return False
            return True

        self._set_row_visible(self.type_label, self.type_combo, visible("type"))
        self._set_row_visible(self.sound_label, self.sound_edit, visible("sound"))
        self._set_row_visible(self.sounds_label, self.sounds_edit, visible("sounds"))
        self._set_row_visible(self.loop_label, self.loop_check, visible("loop"))
        self._set_row_visible(self.event_label, self.event_edit, visible("event"))
        self._set_row_visible(self.name_label, self.name_edit, visible("name"))
        self._set_row_visible(self.amount_label, self.amount_spin, visible("amount"))
        self._set_row_visible(self.delay_label, self.delay_spin, visible("delayMs"))

        self._set_row_visible(self.pattern_mode_label, self.pattern_mode, visible("pattern.mode"))
        self._set_row_visible(self.pattern_color_label, self.color_wrap, visible("pattern.color"))
        self._set_row_visible(self.pattern_brightness_label, self.pattern_brightness, visible("pattern.brightness"))
        self._set_row_visible(self.pattern_duration_label, self.pattern_duration, visible("pattern.durationMs"))
        self._set_row_visible(self.pattern_count_label, self.pattern_count, visible("pattern.count"))
        self._set_row_visible(self.pattern_interval_label, self.pattern_interval, visible("pattern.intervalMs"))

        steps_visible = visible("pattern.steps") and show_when("pattern.steps")
        self._set_row_visible(self.steps_label, self.steps_table, steps_visible)
        self._set_row_visible(self.step_buttons_label, self.step_wrap, steps_visible)

        self.clear_btn.setVisible(self.editor_config.ui.showActionEditor)

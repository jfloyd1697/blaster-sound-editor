from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from typing import Any, Callable, Generic, TypeVar, get_args, get_origin

from PyQt6 import QtWidgets

from persistence.editor_configs import EditorConfig, FieldConfig, WidgetType


T = TypeVar("T")


class SignalBinder:
    @staticmethod
    def connect(widget: QtWidgets.QWidget, callback: Callable[[], None]) -> None:
        if isinstance(widget, QtWidgets.QLineEdit):
            widget.textChanged.connect(callback)
        elif isinstance(widget, QtWidgets.QCheckBox):
            widget.stateChanged.connect(callback)
        elif isinstance(widget, QtWidgets.QComboBox):
            widget.currentTextChanged.connect(callback)
        elif isinstance(widget, QtWidgets.QSpinBox):
            widget.valueChanged.connect(callback)
        elif isinstance(widget, QtWidgets.QTableWidget):
            widget.itemChanged.connect(callback)


class WidgetAdapter:
    def __init__(self, widget: QtWidgets.QWidget, config: FieldConfig):
        self.widget = widget
        self.config = config
        self.apply_config()

    def apply_config(self):
        pass

    def set_value(self, value: Any) -> None:
        raise NotImplementedError

    def get_value(self) -> Any:
        raise NotImplementedError

    def clear(self, default: Any = None) -> None:
        self.set_value(default)


class LineEditAdapter(WidgetAdapter):
    widget: QtWidgets.QLineEdit

    def set_value(self, value: Any) -> None:
        self.widget.setText("" if value is None else str(value))

    def get_value(self) -> str:
        return self.widget.text().strip()


class CheckBoxAdapter(WidgetAdapter):
    widget: QtWidgets.QCheckBox

    def set_value(self, value: Any) -> None:
        self.widget.setChecked(bool(value))

    def get_value(self) -> bool:
        return self.widget.isChecked()


class ComboBoxAdapter(WidgetAdapter):
    widget: QtWidgets.QComboBox

    def apply_config(self) -> None:
        if not self.config.options:
            return
        current = self.widget.currentText()
        self.widget.blockSignals(True)
        self.widget.clear()
        self.widget.addItems(self.config.options)
        if current in self.config.options:
            self.widget.setCurrentText(current)
        elif self.config.default in self.config.options:
            self.widget.setCurrentText(str(self.config.default))
        self.widget.blockSignals(False)

    def set_value(self, value: Any) -> None:
        if value is None:
            value = self.config.default
        if value is not None:
            self.widget.setCurrentText(str(value))

    def get_value(self) -> str:
        return self.widget.currentText()


class SpinBoxAdapter(WidgetAdapter):
    widget: QtWidgets.QSpinBox

    def apply_config(self) -> None:
        min_value = self.config.min if self.config.min is not None else self.widget.minimum()
        max_value = self.config.max if self.config.max is not None else self.widget.maximum()
        self.widget.setRange(min_value, max_value)
        self.widget.setSuffix(self.config.suffix or "")

    def set_value(self, value: Any) -> None:
        self.widget.setValue(int(value or 0))

    def get_value(self) -> int:
        return self.widget.value()


class LightStepsTableAdapter(WidgetAdapter):
    widget: QtWidgets.QTableWidget

    def set_value(self, rows: list[dict[str, Any]] | None) -> None:
        table: QtWidgets.QTableWidget = self.widget
        table.blockSignals(True)
        table.setRowCount(0)
        for row_data in rows or []:
            row = table.rowCount()
            table.insertRow(row)
            color = row_data.get("color", [0, 0, 0])
            values = [*color[:3], row_data.get("durationMs", 0)]
            for col, value in enumerate(values):
                table.setItem(row, col, QtWidgets.QTableWidgetItem(str(value)))
        table.blockSignals(False)

    def get_value(self) -> list[dict[str, Any]]:
        table: QtWidgets.QTableWidget = self.widget
        result: list[dict[str, Any]] = []
        for row in range(table.rowCount()):
            values: list[int] = []
            for col in range(4):
                item = table.item(row, col)
                try:
                    values.append(int(item.text()) if item else 0)
                except ValueError:
                    values.append(0)
            result.append({"color": values[:3], "durationMs": values[3]})
        return result


class AdapterFactory:
    _adapters: dict[WidgetType, type[WidgetAdapter]] = {
        WidgetType.LineEdit: LineEditAdapter,
        WidgetType.CheckBox: CheckBoxAdapter,
        WidgetType.SpinBox: SpinBoxAdapter,
    }

    @classmethod
    def register(cls, widget_type: WidgetType, adapter: type[WidgetAdapter] = None, other: WidgetType = None):
        if adapter is None and other is not None:
            adapter = cls._adapters[other]

        cls._adapters[widget_type] = adapter

    @classmethod
    def create(cls, widget: QtWidgets.QWidget, config: FieldConfig) -> WidgetAdapter:
        widget_type = config.widget
        return cls._adapters.get(widget_type, LineEditAdapter)(widget, config)


AdapterFactory.register(WidgetType.AssetPath, LineEditAdapter)
AdapterFactory.register(WidgetType.StringList, LineEditAdapter)
AdapterFactory.register(WidgetType.RgbColor, LineEditAdapter)
AdapterFactory.register(WidgetType.LightStepsTable, LightStepsTableAdapter)


class Binding:
    def __init__(
        self,
        field_name: str,
        config: FieldConfig,
        widget: QtWidgets.QWidget,
        label: QtWidgets.QWidget | None = None,
        auxiliary_widgets: list[QtWidgets.QWidget] | None = None,
    ):
        self.field_name = field_name
        self.config = config
        self.widget = widget
        self.label = label
        self.auxiliary_widgets = auxiliary_widgets or []
        self.adapter = AdapterFactory.create(widget, config)
        self.apply_config()

    def apply_config(self) -> None:
        self._apply_read_only(self.config.readOnly)

    def set_visible(self, visible: bool) -> None:
        if self.label is not None:
            self.label.setVisible(visible)
        self.widget.setVisible(visible)
        for extra in self.auxiliary_widgets:
            extra.setVisible(visible)

    def set_value(self, value: Any) -> None:
        self.adapter.set_value(value)

    def get_value(self) -> Any:
        return self.adapter.get_value()

    def clear(self) -> None:
        self.adapter.clear(self.config.default)

    def connect_change_signal(self, callback: Callable[[], None]) -> None:
        SignalBinder.connect(self.widget, callback)

    def matches_show_when(self, resolver: Callable[[str], Any]) -> bool:
        if not self.config.showWhen:
            return True
        for dep_name, expected_value in self.config.showWhen.items():
            if resolver(dep_name) != expected_value:
                return False
        return True

    def _apply_read_only(self, read_only: bool) -> None:
        if hasattr(self.widget, "setReadOnly"):
            self.widget.setReadOnly(read_only)
        elif hasattr(self.widget, "setEnabled"):
            self.widget.setEnabled(not read_only)


class BindingCollection:
    def __init__(self):
        self._bindings: dict[str, Binding] = {}

    def register(
        self,
        field_name: str,
        config: FieldConfig,
        widget: QtWidgets.QWidget,
        label: QtWidgets.QWidget | None = None,
        auxiliary_widgets: list[QtWidgets.QWidget] | None = None,
    ) -> Binding:
        binding = Binding(field_name, config, widget, label, auxiliary_widgets)
        self._bindings[field_name] = binding
        return binding

    def get(self, field_name: str) -> Binding | None:
        return self._bindings.get(field_name)

    def items(self):
        return self._bindings.items()

    def connect_all(self, callback: Callable[[], None]) -> None:
        for binding in self._bindings.values():
            binding.connect_change_signal(callback)

    def clear_all(self) -> None:
        for binding in self._bindings.values():
            binding.clear()

    def apply_visibility(self, resolver: Callable[[str], Any]) -> None:
        for binding in self._bindings.values():
            binding.set_visible(
                binding.config.visible and binding.matches_show_when(resolver)
            )


class DataclassEditor(Generic[T]):
    def __init__(self, model_type: type[T], bindings: BindingCollection):
        if not is_dataclass(model_type):
            raise TypeError(f"{model_type!r} is not a dataclass type")
        self.model_type = model_type
        self.bindings = bindings
        self._suspend_updates = False

    def set_data(self, instance: T | None) -> None:
        self._suspend_updates = True
        try:
            if instance is None:
                self.clear()
                return
            for dataclass_field in fields(self.model_type):
                binding = self.bindings.get(dataclass_field.name)
                if binding is None:
                    continue
                value = getattr(instance, dataclass_field.name)
                binding.set_value(self._normalize_outgoing_value(value))
        finally:
            self._suspend_updates = False

    def get_data(self) -> T:
        kwargs: dict[str, Any] = {}
        for dataclass_field in fields(self.model_type):
            binding = self.bindings.get(dataclass_field.name)
            if binding is None:
                kwargs[dataclass_field.name] = self._default_for_field(dataclass_field)
                continue
            raw_value = binding.get_value()
            kwargs[dataclass_field.name] = self._coerce_incoming_value(
                raw_value,
                dataclass_field.type,
                dataclass_field,
            )
        return self.model_type(**kwargs)

    def clear(self) -> None:
        self._suspend_updates = True
        try:
            self.bindings.clear_all()
        finally:
            self._suspend_updates = False

    def connect_change_signals(self, callback: Callable[[T], None]) -> None:
        def wrapped():
            if self._suspend_updates:
                return
            callback(self.get_data())

        self.bindings.connect_all(wrapped)

    def apply_visibility(self, resolver: Callable[[str], Any]) -> None:
        self.bindings.apply_visibility(resolver)

    @staticmethod
    def _normalize_outgoing_value(value: Any) -> Any:
        if value is None:
            return None
        if is_dataclass(value):
            return {f.name: getattr(value, f.name) for f in fields(type(value))}
        if isinstance(value, list):
            normalized: list[Any] = []
            for item in value:
                if is_dataclass(item):
                    normalized.append(
                        {f.name: getattr(item, f.name) for f in fields(type(item))}
                    )
                else:
                    normalized.append(item)
            return normalized
        return value

    @staticmethod
    def _default_for_field(dataclass_field) -> Any:
        if dataclass_field.default is not MISSING:
            return dataclass_field.default
        if dataclass_field.default_factory is not MISSING:  # type: ignore[attr-defined]
            return dataclass_field.default_factory()
        return None

    def _coerce_incoming_value(self, raw_value: Any, annotation: Any, dataclass_field) -> Any:
        if raw_value in ("", None):
            return self._default_for_field(dataclass_field)

        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin is None:
            return self._coerce_simple_type(raw_value, annotation)

        if origin is list:
            item_type = args[0] if args else Any
            if is_dataclass(item_type):
                return [
                    item_type(**item) if isinstance(item, dict) else item
                    for item in raw_value
                ]
            return list(raw_value)

        if origin is getattr(__import__("typing"), "Union", None):
            non_none = [arg for arg in args if arg is not type(None)]
            if len(non_none) == 1:
                return self._coerce_incoming_value(raw_value, non_none[0], dataclass_field)

        return raw_value

    @staticmethod
    def _coerce_simple_type(raw_value: Any, annotation: Any) -> Any:
        if annotation is Any:
            return raw_value
        if annotation is bool:
            return bool(raw_value)
        if annotation is int:
            return int(raw_value)
        if annotation is float:
            return float(raw_value)
        if annotation is str:
            return str(raw_value)
        if is_dataclass(annotation) and isinstance(raw_value, dict):
            return annotation(**raw_value)
        return raw_value


class BindingBuilder:
    def __init__(self, editor_config: EditorConfig):
        self.editor_config = editor_config

    def build_action_bindings(
        self,
        action_type: str,
        widget_specs: dict[
            str,
            tuple[
                QtWidgets.QWidget,
                QtWidgets.QWidget | None,
                list[QtWidgets.QWidget] | None,
            ],
        ],
    ) -> BindingCollection:
        collection = BindingCollection()
        action_cfg = self.editor_config.actionTypes.get(action_type)
        field_cfgs = action_cfg.fields if action_cfg else {}

        for field_name, spec in widget_specs.items():
            widget, label, auxiliary = spec
            field_cfg = field_cfgs.get(field_name, FieldConfig())
            collection.register(field_name, field_cfg, widget, label, auxiliary)

        return collection

    def build_transition_bindings(
        self,
        widget_specs: dict[
            str,
            tuple[
                QtWidgets.QWidget,
                QtWidgets.QWidget | None,
                list[QtWidgets.QWidget] | None,
            ],
        ],
    ) -> BindingCollection:
        collection = BindingCollection()
        transition_cfgs = {
            "event": self.editor_config.fields.transition.event,
            "target": self.editor_config.fields.transition.target,
        }

        for field_name, spec in widget_specs.items():
            widget, label, auxiliary = spec
            field_cfg = transition_cfgs.get(field_name, FieldConfig())
            collection.register(field_name, field_cfg, widget, label, auxiliary)

        return collection
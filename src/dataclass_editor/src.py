from __future__ import annotations

import typing
from dataclasses import MISSING, fields
from typing import Any, Callable, Generic, TypeVar

from PyQt6 import QtWidgets

T = TypeVar("T")
W = TypeVar("W")


class WidgetBinder:
    def __init__(
        self,
        get_value: Callable[[], Any],
        set_value: Callable[[Any], None],
        clear_value: Callable[[Any], None],
        connect_changed: Callable[[Callable[[], None]], None],
    ):
        self._get_value = get_value
        self._set_value = set_value
        self._clear_value = clear_value
        self._connect_changed = connect_changed

    def get_value(self) -> Any:
        return self._get_value()

    def set_value(self, value: Any) -> None:
        self._set_value(value)

    def clear(self, default: Any = None) -> None:
        self._clear_value(default)

    def connect_changed(self, callback: Callable[[], None]) -> None:
        self._connect_changed(callback)


class DataclassEditor(Generic[T], WidgetBinder):
    def __init__(self, cls: type[T]):
        super().__init__(
            get_value=self.get_value,
            set_value=self.set_value,
            clear_value=self.clear,
            connect_changed=lambda cb: self.connect_changed(cb),
        )
        self.cls = cls
        self.bindings: dict[str, WidgetBinder | DataclassEditor] = {}
        self._suspend = False

    def bind(self, field_name: str, binder: WidgetBinder) -> typing.Self:
        self.bindings[field_name] = binder
        return self

    def bind_line_edit(
        self,
        field_name: str,
        widget: QtWidgets.QLineEdit,
        *,
        strip: bool = True,
        to_model: Callable[[str], Any] | None = None,
        from_model: Callable[[Any], str] | None = None,
    ) -> typing.Self:
        def read_widget() -> str:
            value = widget.text()
            return value.strip() if strip else value

        def get_value():
            raw = read_widget()
            return to_model(raw) if to_model else raw

        def set_value(value: Any):
            raw = from_model(value) if from_model else ("" if value is None else str(value))
            widget.setText(raw)

        def clear_value(default: Any):
            raw = from_model(default) if from_model else ("" if default is None else str(default))
            widget.setText(raw)

        def connect_changed(callback: Callable[[], None]):
            widget.textChanged.connect(callback)

        return self.bind(field_name, WidgetBinder(get_value, set_value, clear_value, connect_changed))

    def bind_check_box(
        self,
        field_name: str,
        widget: QtWidgets.QCheckBox,
        *,
        to_model: Callable[[bool], Any] | None = None,
        from_model: Callable[[Any], bool] | None = None,
    ) -> typing.Self:
        def get_value():
            raw = widget.isChecked()
            return to_model(raw) if to_model else raw

        def set_value(value: Any):
            raw = from_model(value) if from_model else bool(value)
            widget.setChecked(raw)

        def clear_value(default: Any):
            raw = from_model(default) if from_model else bool(default)
            widget.setChecked(raw)

        def connect_changed(callback: Callable[[], None]):
            widget.stateChanged.connect(callback)

        return self.bind(field_name, WidgetBinder(get_value, set_value, clear_value, connect_changed))

    def bind_spin_box(
        self,
        field_name: str,
        widget: QtWidgets.QSpinBox,
        *,
        to_model: Callable[[int], Any] | None = None,
        from_model: Callable[[Any], int] | None = None,
    ) -> typing.Self:
        def get_value():
            raw = widget.value()
            return to_model(raw) if to_model else raw

        def set_value(value: Any):
            raw = from_model(value) if from_model else int(value or 0)
            widget.setValue(raw)

        def clear_value(default: Any):
            raw = from_model(default) if from_model else int(default or 0)
            widget.setValue(raw)

        def connect_changed(callback: Callable[[], None]):
            widget.valueChanged.connect(callback)

        return self.bind(field_name, WidgetBinder(get_value, set_value, clear_value, connect_changed))

    def bind_double_spin_box(
        self,
        field_name: str,
        widget: QtWidgets.QDoubleSpinBox,
        *,
        to_model: Callable[[float], Any] | None = None,
        from_model: Callable[[Any], float] | None = None,
    ) -> typing.Self:
        def get_value():
            raw = widget.value()
            return to_model(raw) if to_model else raw

        def set_value(value: Any):
            raw = from_model(value) if from_model else float(value or 0.0)
            widget.setValue(raw)

        def clear_value(default: Any):
            raw = from_model(default) if from_model else float(default or 0.0)
            widget.setValue(raw)

        def connect_changed(callback: Callable[[], None]):
            widget.valueChanged.connect(callback)

        return self.bind(field_name, WidgetBinder(get_value, set_value, clear_value, connect_changed))

    def bind_combo_box(
        self,
        field_name: str,
        widget: QtWidgets.QComboBox,
        *,
        to_model: Callable[[str], Any] | None = None,
        from_model: Callable[[Any], str] | None = None,
    ) -> typing.Self:
        def get_value():
            raw = widget.currentText()
            return to_model(raw) if to_model else raw

        def set_value(value: Any):
            raw = from_model(value) if from_model else ("" if value is None else str(value))
            if raw:
                widget.setCurrentText(raw)
            elif widget.count() > 0:
                widget.setCurrentIndex(0)

        def clear_value(default: Any):
            raw = from_model(default) if from_model else ("" if default is None else str(default))
            if raw:
                widget.setCurrentText(raw)
            elif widget.count() > 0:
                widget.setCurrentIndex(0)

        def connect_changed(callback: Callable[[], None]):
            widget.currentTextChanged.connect(callback)

        return self.bind(field_name, WidgetBinder(get_value, set_value, clear_value, connect_changed))

    def bind_plain_text_edit(
        self,
        field_name: str,
        widget: QtWidgets.QPlainTextEdit,
        *,
        strip: bool = True,
        to_model: Callable[[str], Any] | None = None,
        from_model: Callable[[Any], str] | None = None,
    ) -> typing.Self:
        def read_widget() -> str:
            value = widget.toPlainText()
            return value.strip() if strip else value

        def get_value():
            raw = read_widget()
            return to_model(raw) if to_model else raw

        def set_value(value: Any):
            raw = from_model(value) if from_model else ("" if value is None else str(value))
            widget.setPlainText(raw)

        def clear_value(default: Any):
            raw = from_model(default) if from_model else ("" if default is None else str(default))
            widget.setPlainText(raw)

        def connect_changed(callback: Callable[[], None]):
            widget.textChanged.connect(callback)

        return self.bind(field_name, WidgetBinder(get_value, set_value, clear_value, connect_changed))

    def bind_table(
        self,
        field_name: str,
        widget: QtWidgets.QTableWidget,
        *,
        get_value: Callable[[QtWidgets.QTableWidget], Any],
        set_value: Callable[[QtWidgets.QTableWidget, Any], None],
        clear_value: Callable[[QtWidgets.QTableWidget, Any], None] | None = None,
    ) -> typing.Self:
        def _get_value():
            return get_value(widget)

        def _set_value(value: Any):
            set_value(widget, value)

        def _clear_value(default: Any):
            if clear_value is not None:
                clear_value(widget, default)
            else:
                set_value(widget, default)

        def connect_changed(callback: Callable[[], None]):
            widget.itemChanged.connect(callback)

        return self.bind(field_name, WidgetBinder(_get_value, _set_value, _clear_value, connect_changed))

    def bind_nested(
        self,
        field_name: str,
        editor: "DataclassEditor",
    ) -> typing.Self:
        return self.bind(field_name, editor)

    def bind_optional_nested(
            self,
            field_name: str,
            editor: "DataclassEditor",
            is_empty: Callable[[Any], bool],
    ) -> typing.Self:
        class OptionalNestedBinder(WidgetBinder):
            def __init__(self, inner: WidgetBinder, check):
                super().__init__(
                    get_value=inner.get_value,
                    set_value=inner.set_value,
                    clear_value=inner.clear,
                    connect_changed=inner.connect_changed,
                )
                self._check = check

            def get_value(self):
                value = super().get_value()
                return None if self._check(value) else value

        return self.bind(field_name, OptionalNestedBinder(editor, check=is_empty))

    def set_value(self, value: T | None) -> None:
        self._suspend = True
        try:
            if value is None:
                self.clear()
                return

            for f in fields(self.cls):
                binder = self.bindings.get(f.name)
                if binder is None:
                    continue

                field_value = getattr(value, f.name)
                binder.set_value(field_value)
        finally:
            self._suspend = False

    def get_value(self) -> T:
        kwargs = {}
        for f in fields(self.cls):
            binder = self.bindings.get(f.name)
            if binder is None:
                kwargs[f.name] = self._default_for_field(f)
                continue

            value = binder.get_value()
            kwargs[f.name] = self._default_for_field(f) if value in ("", None) else value

        return self.cls(**kwargs)

    def clear(self, default: Any = None) -> None:
        self._suspend = True
        try:
            for f in fields(self.cls):
                binder = self.bindings.get(f.name)
                default = self._default_for_field(f)
                if binder is None:
                    continue

                binder.clear(default)
        finally:
            self._suspend = False

    def connect_changed(self, callback: Callable[[T], None]) -> None:
        def wrapped(*args):
            if not self._suspend:
                callback(self.get_value())

        for binder in self.bindings.values():
            binder.connect_changed(wrapped)

    @staticmethod
    def _default_for_field(f):
        if f.default is not MISSING:
            return f.default
        if f.default_factory is not MISSING:
            return f.default_factory()
        return None
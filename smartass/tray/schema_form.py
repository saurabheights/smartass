# smartass/tray/schema_form.py
"""Render a SettingsSchema dict (from daemon) as a Qt form."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SchemaForm(QWidget):
    """Renders a schema dict emitted by SettingsSchema.to_dict()."""

    def __init__(
        self,
        schema: dict[str, Any],
        values: dict[str, Any],
        on_save: Callable[[dict[str, Any]], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._schema = schema
        self._on_save = on_save
        self._widgets: dict[str, QWidget] = {}

        root = QVBoxLayout(self)
        form = QFormLayout()
        for f in schema.get("fields", []):
            key = f["key"]
            label = f.get("label", key)
            w = self._make_widget(f, values.get(key, f.get("default")))
            self._widgets[key] = w
            form.addRow(QLabel(label), w)
            if f.get("description"):
                hint = QLabel(f["description"])
                hint.setStyleSheet("color: gray;")
                hint.setWordWrap(True)
                form.addRow(hint)
        root.addLayout(form)

        save = QPushButton("Save")
        save.clicked.connect(self._handle_save)
        root.addWidget(save, alignment=Qt.AlignmentFlag.AlignRight)

    def _make_widget(self, field: dict[str, Any], value: Any) -> QWidget:
        t = field["type"]
        if t == "string" or t == "secret":
            w = QLineEdit()
            w.setText("" if value is None else str(value))
            if t == "secret":
                w.setEchoMode(QLineEdit.EchoMode.Password)
            return w
        if t == "int":
            w = QSpinBox()
            if field.get("min") is not None:
                w.setMinimum(int(field["min"]))
            else:
                w.setMinimum(-2**31)
            if field.get("max") is not None:
                w.setMaximum(int(field["max"]))
            else:
                w.setMaximum(2**31 - 1)
            w.setValue(int(value if value is not None else field.get("default", 0)))
            return w
        if t == "bool":
            w = QCheckBox()
            w.setChecked(bool(value))
            return w
        if t == "select":
            w = QComboBox()
            for opt in field.get("options", []):
                w.addItem(opt)
            if value is not None and value in field.get("options", []):
                w.setCurrentText(str(value))
            return w
        # Unknown type → best-effort text
        w = QLineEdit()
        w.setText("" if value is None else str(value))
        return w

    def _handle_save(self) -> None:
        out: dict[str, Any] = {}
        for f in self._schema.get("fields", []):
            key = f["key"]
            w = self._widgets[key]
            t = f["type"]
            if t in ("string", "secret"):
                out[key] = w.text()
            elif t == "int":
                out[key] = int(w.value())
            elif t == "bool":
                out[key] = bool(w.isChecked())
            elif t == "select":
                out[key] = w.currentText()
            else:
                out[key] = w.text() if hasattr(w, "text") else None
        self._on_save(out)

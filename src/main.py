import json
import sys
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6 import QtWidgets, QtGui

from models import (
    DEFAULT_DOC,
    NodeRef,
    WeaponBehaviorDef,
)

from widgets import (
    AssetTreeView,
    ConfigTreeWidget,
    GraphView,
    ActionEditor,
    StateEditor,
)
from services import AssetService, DocumentService, TreeService, EditorConfigService, UndoRedoService


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Weapon Behavior Config Editor")
        self.resize(1700, 950)

        self.doc = WeaponBehaviorDef.from_dict(DEFAULT_DOC.to_dict())
        self.current_file: str | None = None
        self.assets_root: str | None = None
        self._last_selected_path: list[Any] | None = None

        self.asset_service = AssetService()
        self.document_service = DocumentService(self.doc)
        self.tree_service = TreeService()
        self.editor_config_service = EditorConfigService()
        self.undo_redo_service = UndoRedoService(
            get_doc=lambda: self.doc,
            set_doc=self._set_document_from_undo_redo,
        )

        self._build_ui()
        self._build_menu()
        self._load_editor_config()
        self._load_weapon_fields()
        self.rebuild_tree()
        self.refresh_json_preview()
        self.redraw_graph()

    def _build_ui(self):
        splitter = QtWidgets.QSplitter()
        self.setCentralWidget(splitter)

        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        splitter.addWidget(left)

        left_layout.addWidget(QtWidgets.QLabel("Config Structure"))
        self.tree = ConfigTreeWidget()
        self.tree.setHeaderLabels(["Config Structure"])
        left_layout.addWidget(self.tree)

        self.add_btn = QtWidgets.QPushButton("Add")
        self.remove_btn = QtWidgets.QPushButton("Remove")
        left_layout.addWidget(self.add_btn)
        left_layout.addWidget(self.remove_btn)

        center = QtWidgets.QWidget()
        center_layout = QtWidgets.QVBoxLayout(center)
        splitter.addWidget(center)

        form = QtWidgets.QFormLayout()
        center_layout.addLayout(form)

        self.version_spin = QtWidgets.QSpinBox()
        self.version_spin.setRange(1, 999)
        form.addRow("Version", self.version_spin)

        self.weapon_name = QtWidgets.QLineEdit()
        form.addRow("Weapon", self.weapon_name)

        self.magazine_size = QtWidgets.QSpinBox()
        self.magazine_size.setRange(0, 999999)
        form.addRow("Magazine Size", self.magazine_size)

        self.initial_state = QtWidgets.QLineEdit()
        form.addRow("Initial State", self.initial_state)

        self.state_editor = StateEditor(self._handle_state_editor_change)
        center_layout.addWidget(self.state_editor)

        self.action_editor = ActionEditor(self._on_action_changed)
        center_layout.addWidget(self.action_editor)

        right = QtWidgets.QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(right)

        preview_wrap = QtWidgets.QWidget()
        preview_layout = QtWidgets.QVBoxLayout(preview_wrap)
        preview_layout.addWidget(QtWidgets.QLabel("JSON Preview"))

        self.preview = QtWidgets.QTableWidget(0, 2)
        self.preview.setHorizontalHeaderLabels(["Path", "Value"])
        self.preview.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.preview.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        preview_layout.addWidget(self.preview)
        right.addWidget(preview_wrap)

        graph_wrap = QtWidgets.QWidget()
        graph_layout = QtWidgets.QVBoxLayout(graph_wrap)
        graph_layout.addWidget(QtWidgets.QLabel("State Graph"))
        self.graph_view = GraphView()
        graph_layout.addWidget(self.graph_view)
        right.addWidget(graph_wrap)

        assets_wrap = QtWidgets.QWidget()
        assets_layout = QtWidgets.QVBoxLayout(assets_wrap)
        assets_layout.addWidget(QtWidgets.QLabel("Assets"))

        self.set_assets_btn = QtWidgets.QPushButton("Set Assets Folder")
        assets_layout.addWidget(self.set_assets_btn)

        self.assets_label = QtWidgets.QLabel("No assets folder selected")
        assets_layout.addWidget(self.assets_label)

        self.asset_model = QtGui.QFileSystemModel()
        self.asset_model.setRootPath("")
        self.asset_tree = AssetTreeView()
        self.asset_tree.setModel(self.asset_model)
        self.asset_tree.setDragEnabled(True)
        assets_layout.addWidget(self.asset_tree)
        right.addWidget(assets_wrap)

        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.tree.fileDroppedOnNode.connect(self._handle_file_dropped_on_node)
        self.add_btn.clicked.connect(self._add_node)
        self.remove_btn.clicked.connect(self._remove_node)

        self.version_spin.valueChanged.connect(self._on_weapon_fields_changed)
        self.weapon_name.editingFinished.connect(self._on_weapon_fields_changed)
        self.magazine_size.valueChanged.connect(self._on_weapon_fields_changed)
        self.initial_state.editingFinished.connect(self._on_weapon_fields_changed)

        self.set_assets_btn.clicked.connect(self.choose_assets_folder)
        self.asset_tree.fileActivated.connect(self._assign_asset_from_browser)

    def _build_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("File")

        new_action = QtGui.QAction("New", self)
        open_action = QtGui.QAction("Open...", self)
        save_action = QtGui.QAction("Save", self)
        save_as_action = QtGui.QAction("Save As...", self)
        undo_action = QtGui.QAction("Undo", self)
        redo_action = QtGui.QAction("Redo", self)
        load_editor_config_action = QtGui.QAction("Load Editor Config...", self)

        undo_action.setShortcut("Ctrl+Z")
        redo_action.setShortcut("Ctrl+Y")

        new_action.triggered.connect(self.new_file)
        open_action.triggered.connect(self.open_file)
        save_action.triggered.connect(self.save_file)
        save_as_action.triggered.connect(self.save_file_as)
        undo_action.triggered.connect(self._undo)
        redo_action.triggered.connect(self._redo)
        load_editor_config_action.triggered.connect(self.load_editor_config_from_dialog)

        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(undo_action)
        file_menu.addAction(redo_action)
        file_menu.addSeparator()
        file_menu.addAction(load_editor_config_action)

    def _load_editor_config(self):
        default_path = Path("editor_config.json")
        if default_path.exists():
            try:
                self.editor_config_service.load_from_path(default_path)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Editor Config",
                    f"Failed to load editor config from '{default_path}': {exc}",
                )
        self.apply_editor_config()

    def load_editor_config_from_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Editor Config",
            "editor_config.json",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return

        try:
            self.editor_config_service.load_from_path(path)
            self.apply_editor_config()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(
                self,
                "Editor Config",
                f"Failed to load editor config: {exc}",
            )

    def apply_editor_config(self):
        config = self.editor_config_service.config

        self.tree.setVisible(config.ui.showTree)
        self.add_btn.setVisible(config.ui.showTree)
        self.remove_btn.setVisible(config.ui.showTree)

        self.preview.setVisible(config.ui.showJsonPreview)
        self.graph_view.setVisible(config.ui.showGraph)

        self.asset_tree.setVisible(config.ui.showAssets)
        self.set_assets_btn.setVisible(config.ui.showAssets)
        self.assets_label.setVisible(config.ui.showAssets)

        self.state_editor.set_editor_config(config)
        self.action_editor.set_editor_config(config)

        self.version_spin.setVisible(
            config.ui.showTopLevelFields and config.fields.topLevel.version.visible
        )
        self.weapon_name.setVisible(
            config.ui.showTopLevelFields and config.fields.topLevel.weapon.visible
        )
        self.magazine_size.setVisible(
            config.ui.showTopLevelFields and config.fields.topLevel.magazineSize.visible
        )
        self.initial_state.setVisible(
            config.ui.showTopLevelFields and config.fields.topLevel.initialState.visible
        )

        if (
            hasattr(self.graph_view, "autoscale_button")
            and self.graph_view.autoscale_button is not None
        ):
            self.graph_view.autoscale_button.setVisible(
                config.ui.graph.showAutoscaleButton
            )

    def _set_document_from_undo_redo(self, doc: WeaponBehaviorDef):
        self.doc = doc
        self.document_service.set_document(self.doc)
        self._load_weapon_fields()
        self.rebuild_tree()
        self.refresh_json_preview()
        self.redraw_graph()

    def _undo(self):
        self.undo_redo_service.undo()

    def _redo(self):
        self.undo_redo_service.redo()

    def _load_weapon_fields(self):
        self.version_spin.blockSignals(True)
        self.weapon_name.blockSignals(True)
        self.magazine_size.blockSignals(True)
        self.initial_state.blockSignals(True)

        self.version_spin.setValue(self.doc.version)
        self.weapon_name.setText(self.doc.weapon)
        self.magazine_size.setValue(self.doc.magazineSize)
        self.initial_state.setText(self.doc.initialState)

        self.version_spin.blockSignals(False)
        self.weapon_name.blockSignals(False)
        self.magazine_size.blockSignals(False)
        self.initial_state.blockSignals(False)

    def choose_assets_folder(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Assets Folder")
        if not path:
            return

        self.assets_root = path
        self.asset_service.set_assets_root(path)
        self.assets_label.setText(path)
        root_index = self.asset_model.setRootPath(path)
        self.asset_tree.setRootIndex(root_index)

        for col in range(1, self.asset_model.columnCount()):
            self.asset_tree.hideColumn(col)

    def new_file(self):
        self.doc = WeaponBehaviorDef.from_dict(DEFAULT_DOC.to_dict())
        self.document_service.set_document(self.doc)
        self.undo_redo_service.clear()
        self.current_file = None
        self._load_weapon_fields()
        self.rebuild_tree()
        self.refresh_json_preview()
        self.redraw_graph()

    def open_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Config",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return

        with open(path, "r", encoding="utf-8") as f:
            self.doc = WeaponBehaviorDef.from_json(f.read())

        self.document_service.set_document(self.doc)
        self.undo_redo_service.clear()
        self.current_file = path
        self._load_weapon_fields()
        self.rebuild_tree()
        self.refresh_json_preview()
        self.redraw_graph()

    def save_file(self):
        if not self.current_file:
            self.save_file_as()
            return

        with open(self.current_file, "w", encoding="utf-8") as f:
            f.write(self.doc.to_json(indent=2))

    def save_file_as(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Config",
            "weapon_behavior.json",
            "JSON Files (*.json)",
        )
        if not path:
            return

        self.current_file = path
        self.save_file()

    def rebuild_tree(self):
        self.tree.clear()
        root = self.tree_service.rebuild_tree(self.doc)
        self.tree.addTopLevelItem(root)
        self.tree.expandAll()

    def refresh_json_preview(self):
        rows = self.document_service.flatten_json_rows(json.loads(self.doc.to_json()))

        self.preview.setRowCount(0)
        for path, value in rows:
            row = self.preview.rowCount()
            self.preview.insertRow(row)
            self.preview.setItem(row, 0, QtWidgets.QTableWidgetItem(path))
            self.preview.setItem(row, 1, QtWidgets.QTableWidgetItem(value))

    def redraw_graph(self):
        self.graph_view.redraw(self.doc)

    def _on_tree_selection_changed(self):
        item = self.tree.currentItem()
        if item is None:
            return

        ref = item.data(0, Qt.ItemDataRole.UserRole)
        self.state_editor.show_nothing()
        self.action_editor.set_action(None)

        if not isinstance(ref, NodeRef):
            return

        if ref.kind == "state":
            self.state_editor.set_state(ref.path[0])
            return

        if ref.kind == "transition":
            state_name, transition_index = ref.path
            self.state_editor.set_transition(
                self.doc.states[state_name].transitions[transition_index]
            )
            return

        action = self.document_service.resolve_action_ref(ref)
        if action is not None:
            self.action_editor.set_action(action)

    def _on_weapon_fields_changed(self):
        if self.undo_redo_service.is_restoring:
            return

        self.undo_redo_service.capture_undo()
        self.doc.version = self.version_spin.value()
        self.doc.weapon = self.weapon_name.text().strip()
        self.doc.magazineSize = self.magazine_size.value()
        self.doc.initialState = self.initial_state.text().strip()

        self.rebuild_tree()
        self.refresh_json_preview()
        self.redraw_graph()

    def _add_node(self):
        item = self.tree.currentItem()
        if item is None:
            return

        ref = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(ref, NodeRef):
            return

        self.undo_redo_service.capture_undo()
        self.document_service.add_node(ref)
        self.rebuild_tree()
        self.refresh_json_preview()
        self.redraw_graph()

    def _remove_node(self):
        item = self.tree.currentItem()
        if item is None:
            return

        ref = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(ref, NodeRef):
            return

        try:
            self.undo_redo_service.capture_undo()
            self.document_service.remove_node(ref)
        except (KeyError, IndexError) as exc:
            QtWidgets.QMessageBox.warning(self, "Remove Failed", str(exc))
            return

        self.rebuild_tree()
        self.refresh_json_preview()
        self.redraw_graph()

    def _assign_asset_from_browser(self, src_path: str):
        item = self.tree.currentItem()
        if item is None:
            return

        ref = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(ref, NodeRef):
            return

        self._handle_file_dropped_on_node(src_path, ref)

    def _handle_file_dropped_on_node(self, src_path: str, ref: Any):
        try:
            src_path = self.asset_service.import_asset(src_path)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Asset Copy Failed", str(exc))
            return

        action = (
            self.document_service.resolve_action_ref(ref)
            if isinstance(ref, NodeRef)
            else None
        )
        if action is None:
            QtWidgets.QMessageBox.information(
                self,
                "Asset Drop",
                "Drop a file on an action node to bind it.",
            )
            return

        self.undo_redo_service.capture_undo()
        current_item = self.tree.currentItem()
        current_ref = (
            current_item.data(0, Qt.ItemDataRole.UserRole)
            if current_item is not None
            else None
        )

        if current_ref == ref:
            self.action_editor.assign_asset_file(src_path)
        else:
            self.action_editor.set_action(action)
            self.action_editor.assign_asset_file(src_path)

        self.refresh_json_preview()

    def _on_action_changed(self):
        if self.undo_redo_service.is_restoring:
            return
        self.undo_redo_service.capture_undo()
        self.rebuild_tree()
        self.refresh_json_preview()
        self.redraw_graph()

    def _handle_state_editor_change(self, command: str, value: Any):
        item = self.tree.currentItem()
        if item is None:
            return

        ref = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(ref, NodeRef):
            return

        if command == "transition_updated":
            if not self.undo_redo_service.is_restoring:
                self.undo_redo_service.capture_undo()

        if command == "rename_state" and ref.kind == "state":
            old_name = ref.path[0]
            new_name = (value or "").strip()

            try:
                self.undo_redo_service.capture_undo()
                self.document_service.rename_state(old_name, new_name)
            except ValueError as exc:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Rename State",
                    str(exc),
                )
                return

        self.rebuild_tree()
        self.refresh_json_preview()
        self.redraw_graph()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

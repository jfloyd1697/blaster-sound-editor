from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QTreeWidget


class ConfigTreeWidget(QTreeWidget):
    fileDroppedOnNode = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.DropOnly)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if not event.mimeData().hasUrls():
            super().dropEvent(event)
            return

        item = self.itemAt(event.position().toPoint())
        if item is None:
            event.ignore()
            return

        urls = event.mimeData().urls()
        local_files = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if not local_files:
            event.ignore()
            return

        ref = item.data(0, Qt.ItemDataRole.UserRole)
        self.fileDroppedOnNode.emit(local_files[0], ref)
        event.acceptProposedAction()

import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QTreeView


class AssetTreeView(QTreeView):
    fileActivated = pyqtSignal(str)

    def mouseDoubleClickEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            model = self.model()
            path = model.filePath(index)
            if os.path.isfile(path):
                self.fileActivated.emit(path)
        super().mouseDoubleClickEvent(event)

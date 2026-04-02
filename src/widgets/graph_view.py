import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6 import QtWidgets, QtGui

from models import WeaponBehaviorDef


class GraphNodeItem(QtWidgets.QGraphicsItem):
    def __init__(self, graph_view: "GraphView", state_name: str, radius: float = 34.0):
        super().__init__()
        self.graph_view = graph_view
        self.state_name = state_name
        self.radius = radius

        self.label = QtWidgets.QGraphicsSimpleTextItem(state_name, self)
        self.label.setFlag(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
            True,
        )
        self._center_label()

        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(2)

    def boundingRect(self) -> QRectF:
        pad = 4.0
        return QRectF(
            -self.radius - pad,
            -self.radius - pad,
            (self.radius + pad) * 2,
            (self.radius + pad) * 2,
        )

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget=None,
    ):
        pen = QtGui.QPen()
        pen.setWidth(3 if self.state_name == self.graph_view.initial_state else 1)
        if self.state_name == self.graph_view.initial_state:
            pen.setColor(Qt.GlobalColor.darkGreen)

        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush())
        painter.drawEllipse(
            QRectF(-self.radius, -self.radius, self.radius * 2, self.radius * 2)
        )

    def itemChange(self, change, value):
        if (
            change
            == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
        ):
            self.graph_view.update_connections()
            self._center_label()
        return super().itemChange(change, value)

    def _center_label(self):
        rect = self.label.boundingRect()
        self.label.setPos(-rect.width() / 2, -rect.height() / 2)


class GraphView(QtWidgets.QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QtWidgets.QGraphicsScene(self))
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        self.initial_state = ""
        self.node_items: dict[str, GraphNodeItem] = {}
        self.edge_items: list[
            tuple[
                str,
                str,
                str,
                QtWidgets.QGraphicsPathItem,
                QtWidgets.QGraphicsPolygonItem | None,
                QtWidgets.QGraphicsSimpleTextItem,
            ]
        ] = []

        self.autoscale_button = None

    def redraw(self, doc: WeaponBehaviorDef):
        scene = self.scene()
        scene.clear()

        self.autoscale_button = QtWidgets.QPushButton("Autoscale")
        self.autoscale_button.clicked.connect(self.autoscale)
        self.autoscale_proxy = self.scene().addWidget(self.autoscale_button)
        self.autoscale_proxy.setFlag(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
            True,
        )
        self.autoscale_proxy.setZValue(10)

        self.node_items.clear()
        self.edge_items.clear()
        self.initial_state = doc.initialState

        state_names = list(doc.states.keys())
        if not state_names:
            self.autoscale()
            return

        radius = 180
        center_x = 260
        center_y = 220
        positions: dict[str, QPointF] = {}

        if len(state_names) == 1:
            positions[state_names[0]] = QPointF(center_x, center_y)
        else:
            for i, name in enumerate(state_names):
                angle = (2 * math.pi * i) / max(1, len(state_names))
                positions[name] = QPointF(
                    center_x + radius * math.cos(angle),
                    center_y + radius * math.sin(angle),
                )

        for name, pos in positions.items():
            node = GraphNodeItem(self, name)
            node.setPos(pos)
            scene.addItem(node)
            self.node_items[name] = node

        for state_name, state in doc.states.items():
            for transition in state.transitions:
                if transition.target not in self.node_items:
                    continue

                path_item = QtWidgets.QGraphicsPathItem()
                path_item.setZValue(0)
                scene.addItem(path_item)

                arrow_item = None
                if state_name != transition.target:
                    arrow_item = QtWidgets.QGraphicsPolygonItem()
                    arrow_item.setZValue(1)
                    scene.addItem(arrow_item)

                label_item = QtWidgets.QGraphicsSimpleTextItem(
                    transition.event or ("self" if state_name == transition.target else "")
                )
                label_item.setFlag(
                    QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
                    True,
                )
                label_item.setZValue(1)
                scene.addItem(label_item)

                self.edge_items.append(
                    (
                        state_name,
                        transition.target,
                        transition.event or "",
                        path_item,
                        arrow_item,
                        label_item,
                    )
                )

        self.update_connections()
        self.autoscale()

    def update_connections(self):
        for (
                source_name,
                target_name,
                event_name,
                path_item,
                arrow_item,
                label_item,
        ) in self.edge_items:
            start_node = self.node_items[source_name]
            end_node = self.node_items[target_name]
            start = start_node.pos()
            end = end_node.pos()

            path = QtGui.QPainterPath()

            if source_name == target_name:
                loop_rect = QRectF(start.x() - 24, start.y() - 62, 48, 24)
                path.addEllipse(loop_rect)
                path_item.setPath(path)

                if arrow_item is not None:
                    arrow_item.setPolygon(QtGui.QPolygonF())

                label_item.setText(event_name or "self")
                label_item.setPos(start.x() + 22, start.y() - 64)
                continue

            dx = end.x() - start.x()
            dy = end.y() - start.y()
            distance = max((dx * dx + dy * dy) ** 0.5, 1.0)

            ux = dx / distance
            uy = dy / distance

            radius = start_node.radius
            start_point = QPointF(start.x() + ux * radius, start.y() + uy * radius)
            end_point = QPointF(end.x() - ux * radius, end.y() - uy * radius)

            mid_x = (start_point.x() + end_point.x()) / 2
            mid_y = (start_point.y() + end_point.y()) / 2
            offset_x = -uy * 24
            offset_y = ux * 24
            control = QPointF(mid_x + offset_x, mid_y + offset_y)

            path.moveTo(start_point)
            path.quadTo(control, end_point)
            path_item.setPath(path)

            label_item.setText(event_name or "")
            label_item.setPos(control.x(), control.y())

            if arrow_item is not None:
                self._update_arrowhead(arrow_item, control, end_point)

        self.autoscale()

    def _update_arrowhead(
        self,
        arrow_item: QtWidgets.QGraphicsPolygonItem,
        control: QPointF,
        tip: QPointF,
    ):
        dx = tip.x() - control.x()
        dy = tip.y() - control.y()
        length = max((dx * dx + dy * dy) ** 0.5, 1.0)

        ux = dx / length
        uy = dy / length

        arrow_len = 14.0
        arrow_width = 7.0

        base = QPointF(tip.x() - ux * arrow_len, tip.y() - uy * arrow_len)
        left = QPointF(
            base.x() - uy * arrow_width,
            base.y() + ux * arrow_width,
        )
        right = QPointF(
            base.x() + uy * arrow_width,
            base.y() - ux * arrow_width,
        )

        arrow_item.setPolygon(QtGui.QPolygonF([tip, left, right]))
        arrow_item.setBrush(QtGui.QBrush(Qt.GlobalColor.black))
        arrow_item.setPen(QtGui.QPen(Qt.GlobalColor.black))

    def autoscale(self):
        bounds = QRectF()

        for item in self.scene().items():
            if item is self.autoscale_proxy:
                continue

            item_rect = item.sceneBoundingRect()
            bounds = item_rect if bounds.isNull() else bounds.united(item_rect)

        if not bounds.isEmpty():
            self.fitInView(bounds.adjusted(-40, -40, 40, 40), Qt.AspectRatioMode.KeepAspectRatio)

        scene_pos = self.mapToScene(12, 12)
        self.autoscale_proxy.setPos(scene_pos)

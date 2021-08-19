from PyQt5 import QtCore, QtGui, QtWidgets
import cv2
from playback_manager import Event
import time

class ZoomableQLabel(QtWidgets.QLabel):
    """
    Base class that enables zooming and panning of the assigned image.
    Horizontal zoomig, vertical zooming and preserving aspect ratio can be enabled/disabled individually.

    BUG: If maintain_aspect_ratio is enabled and either of zooming options is disabled,
         the image is shown only partially when zoomed in. This combination of options
         is not currently used.
    """

    # A signal that is emitted every time user input is applied to this widget.
    userInputSignal = QtCore.pyqtSignal()

    boxSelectSignal = QtCore.pyqtSignal(tuple)

    def __init__(self, maintain_aspect_ratio = False, horizontal = True, vertical = True):
        super().__init__()
        self.setMouseTracking(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        self.horizontal_z = horizontal
        self.vertical_z = vertical
        self.zoom_01 = 0
        self.zoom_step = 1.0 / 3000
        self.max_zoom = 3

        self.maintain_aspect_ratio = maintain_aspect_ratio
        self.size_mult = 1

        self.displayed_image = None
        self.window_width = 0
        self.window_height = 0
        self.image_width = 0
        self.image_height = 0

        # In image coordinates
        self.x_min_limit = 280
        self.x_max_limit = 680
        self.y_min_limit = 50
        self.y_max_limit = 150
        self.x_pos = 0
        self.y_pos = 0

        self.drag_data = None

        # Debug window syncronization
        self.mouse_move_event = Event()

        self.mouse_down_left = None
        self.mouse_current_left = None

    def setImage(self, image):
        self.displayed_image = image
        self.applyPixmap()

    def minMaxMousePositions(self, m_pos1, m_pos2):
        """
        Coverts two mouse positions in image coordinates into a rectangle (min and max corners)
        in view coordinates.
        """
        x1, y1 = self.getMousePositionOnView(m_pos1)
        x2, y2 = self.getMousePositionOnView(m_pos2)
        return min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)

    def paintSelection(self):
        """
        Draws the selection box, when one exists. Needs to be called in paintEvent,
        implemented e.g. in an inheriting subclass.
        """
        if self.mouse_down_left is not None:

            min_x, max_x, min_y, max_y = self.minMaxMousePositions(self.mouse_down_left, self.mouse_current_left)

            painter = QtGui.QPainter(self)
            painter.setPen(QtCore.Qt.white)
            painter.drawRect(min_x, min_y, max_x - min_x, max_y - min_y)

    def resizeEvent(self, event):
        self.updateWindowZoom()
        self.applyPixmap()
        self.userInputSignal.emit()

    def wheelEvent(self, event):
        if self.drag_data is None:
            self.x_pos = self.view2imageX(event.x())
            self.y_pos = self.view2imageY(event.y())

            self.zoom_01 = max(0, min(self.zoom_01 + event.angleDelta().y() * self.zoom_step, 1))
            self.applyWindowZoom(event.x(), event.y())
            self.applyPixmap()
            self.userInputSignal.emit()

            self.mouse_move_event()

    def getMousePositionOnImage(self, event):
        return (self.view2imageX(event.x()), self.view2imageY(event.y()))

    def getMousePositionOnView(self, image_pos):
        return (self.image2viewX(image_pos[0]), self.image2viewY(image_pos[1]))

    def getMouseDragTuple(self, released):
        return (self.mouse_down_left, self.mouse_current_left, released)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.mouse_down_left = self.getMousePositionOnImage(event)
            self.mouse_current_left = self.mouse_down_left
        elif event.button() == QtCore.Qt.RightButton:
            self.drag_data = WindowDragData(event.x(), event.y(), self.x_min_limit, self.x_max_limit,
                                            self.y_min_limit, self.y_max_limit)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.boxSelectSignal.emit((self.mouse_down_left, self.mouse_current_left))
            self.mouse_down_left = None
            self.mouse_current_left = None
            self.update()

    def mouseMoveEvent(self, event):
        self.x_pos = self.view2imageX(event.x())
        self.y_pos = self.view2imageY(event.y())

        if self.drag_data is not None:
            if event.buttons() == QtCore.Qt.RightButton:
                self.applyWindowDrag(event.x(), event.y(), self.drag_data)
                self.applyPixmap()
                self.userInputSignal.emit()
                
            else:
                self.drag_data = None

        if self.mouse_down_left is not None:
            self.mouse_current_left = self.getMousePositionOnImage(event)
            self.update()

        # Debug window synchronization
        self.mouse_move_event()

    def setLimits(self, shape):
        self.x_min_limit = 0
        self.y_min_limit = 0
        if shape is not None:
            self.x_max_limit = self.image_width = shape[1]
            self.y_max_limit = self.image_height = shape[0]
        else:
            self.x_max_limit = 1
            self.y_max_limit = 1

    def resetView(self):
        self.setLimits(self.displayed_image.shape if self.displayed_image is not None else None)
        self.zoom_01 = 0
        self.applyPixmap()

    def resetViewToShape(self, shape):
        self.x_min_limit = 0
        self.y_min_limit = 0
        self.x_max_limit = shape[1]
        self.y_max_limit = shape[0]
        self.zoom_01 = 0

    def applyPixmap(self):
        sz = self.size()
        self.window_width = max(1, sz.width())
        self.window_height = max(1, sz.height())

        if self.displayed_image is not None:
            self.image_width = self.displayed_image.shape[1]
            self.image_height = self.displayed_image.shape[0]

            qformat = QtGui.QImage.Format_Indexed8
            if len(self.displayed_image.shape) == 3:
                if self.displayed_image.shape[2] == 4:
                    qformat = QtGui.QImage.Format_RGBA8888
                else:
                    qformat = QtGui.QImage.Format_RGB888

            img = self.fitToSize(self.displayed_image)
            img = QtGui.QImage(img, img.shape[1], img.shape[0], img.strides[0], qformat).rgbSwapped()
            self.figurePixmap = QtGui.QPixmap.fromImage(img)
            self.setPixmap(self.figurePixmap.scaled(self.size(), QtCore.Qt.KeepAspectRatio))

    def fitToSize(self, image):
        img = image
        img_shape = (img.shape[1], img.shape[0])

        if self.horizontal_z:
            # Zoom horizontally
            img = img[:, self.x_min_limit:self.x_max_limit]

        if self.vertical_z:
            # Zoom vertically
            img = img[self.y_min_limit:self.y_max_limit, :]

        if self.maintain_aspect_ratio:
            # Calculate size that fits the window
            sz = img_shape = (img.shape[1], img.shape[0])
            if sz[0] > self.window_width:
                mult = self.window_width / sz[0]
                sz = (max(1, int(mult * sz[0])), max(1, int(mult * sz[1])))
            if sz[1] > self.window_height:
                mult = self.window_height / sz[1]
                sz = (max(1, int(mult * sz[0])), max(1, int(mult * sz[1])))
            #return cv2.resize(img, sz)

        else:
            sz = (self.window_width, self.window_height)

        # Scale x- and y-axis separately to avoid Moire effects when scaling down
        # and allow linear interpolation when scaling up.
        if sz[0] > img_shape[0]:
            # Scale up width
            img = cv2.resize(img, (sz[0], img_shape[1]), interpolation=cv2.INTER_LINEAR)
            img_shape = (img.shape[1], img.shape[0])

        if sz[1] > img_shape[1]:
            # Scale up height
            img = cv2.resize(img, (img_shape[0], sz[1]), interpolation=cv2.INTER_LINEAR)
            img_shape = (img.shape[1], img.shape[0])

        if sz[0] <= img_shape[0]:
            # Scale down width
            img = cv2.resize(img, (sz[0], img_shape[1]), interpolation=cv2.INTER_AREA)
            img_shape = (img.shape[1], img.shape[0])

        if sz[1] <= img_shape[1]:
            # Scale down height
            img = cv2.resize(img, (img_shape[0], sz[1]), interpolation=cv2.INTER_AREA)

        return img

    def updateWindowZoom(self):
        if self.displayed_image is None:
            return

        if self.maintain_aspect_ratio:
            applied_min_zoom = min(self.window_width / self.image_width, self.window_height / self.image_height, 1)
            applied_zoom = (self.zoom_01 * (self.max_zoom - applied_min_zoom) + applied_min_zoom)
            total_width = applied_zoom  * self.image_width
            total_height = applied_zoom * self.image_height

        else:
            total_width = self.zoom_01 * (max(self.max_zoom * self.image_width, 2 * self.window_width) - self.window_width) + self.window_width
            total_height = self.zoom_01 * (max(self.max_zoom * self.image_height, 2 * self.window_height) - self.window_height) + self.window_height

        new_width = min(int(self.window_width / total_width * self.image_width), self.image_width)
        new_height = min(int(self.window_height / total_height * self.image_height), self.image_height)

        half_delta_width = (new_width - (self.x_max_limit - self.x_min_limit)) / 2
        half_delta_height = (new_height - (self.y_max_limit - self.y_min_limit)) / 2

        x_min = self.x_min_limit - half_delta_width
        x_max = self.x_max_limit + half_delta_width
        y_min = self.y_min_limit - half_delta_height
        y_max = self.y_max_limit + half_delta_height

        self.applyLimits(x_min, x_max, y_min, y_max)

    def applyWindowZoom(self, x, y):
        self.updateWindowZoom()

        correct_towards_mouse_x = self.x_pos - self.view2imageX(x)
        correct_towards_mouse_y = self.y_pos - self.view2imageY(y)

        x_min = self.x_min_limit + correct_towards_mouse_x
        x_max = self.x_max_limit + correct_towards_mouse_x
        y_min = self.y_min_limit + correct_towards_mouse_y
        y_max = self.y_max_limit + correct_towards_mouse_y

        self.applyLimits(x_min, x_max, y_min, y_max)

    def applyWindowDrag(self, x, y, data):
        offset_x = self.view2imageDirectionX(x - data.mouse_x)
        offset_y = self.view2imageDirectionY(y - data.mouse_y)

        x_min = data.x_min - offset_x
        x_max = data.x_max - offset_x
        y_min = data.y_min - offset_y
        y_max = data.y_max - offset_y

        self.applyLimits(x_min, x_max, y_min, y_max)

    def applyLimits(self, x_min, x_max, y_min, y_max):
        if self.horizontal_z:
            if x_min < 0:
                x_max = min(x_max - x_min, self.image_width)
                x_min = 0
            if x_max > self.image_width:
                x_min = max(0, x_min - (x_max - self.image_width))
                x_max = self.image_width

            self.x_min_limit = int(x_min)
            self.x_max_limit = int(x_max)
        else:
            self.x_min_limit = 0
            self.x_max_limit = self.image_width

        if self.vertical_z:
            if y_min < 0:
                y_max = min(y_max - y_min, self.image_height)
                y_min = 0
            if y_max > self.image_height:
                y_min = max(0, y_min - (y_max - self.image_height))
                y_max = self.image_height

            self.y_min_limit = int(y_min)
            self.y_max_limit = int(y_max)
        else:
            self.y_min_limit = 0
            self.y_max_limit = self.image_height

    def clear(self):
        super().clear()
        self.displayed_image = None
        

    # Transform functions to transform coordinates from one system to other are defined below.
    # Implemented transform are for positon and direction between image and viewport coordinates.

    def view2imageX(self, value):
        if self.pixmap() is not None:
            pixmap_width = self.pixmap().width()
            margin_x = (self.window_width - pixmap_width) / 2
            return ((value - margin_x) /pixmap_width) * (self.x_max_limit - self.x_min_limit) + self.x_min_limit
        return (value / self.window_width) * (self.x_max_limit - self.x_min_limit) + self.x_min_limit

    def view2imageDirectionX(self, value):
        return (value / self.window_width) * (self.x_max_limit - self.x_min_limit)

    def view2imageY(self, value):
        if self.pixmap() is not None:
            pixmap_height = self.pixmap().height()
            margin_y = (self.window_height - pixmap_height) / 2
            return ((value - margin_y) / pixmap_height) * (self.y_max_limit - self.y_min_limit) + self.y_min_limit
        return (value / self.window_height) * (self.y_max_limit - self.y_min_limit) + self.y_min_limit

    def view2imageDirectionY(self, value):
        return (value / self.window_height) * (self.y_max_limit - self.y_min_limit)

    def image2viewX(self, value):
        if self.pixmap() is not None:
            pixmap_width = self.pixmap().width()
            margin_x = (self.window_width - pixmap_width) / 2
            return (value - self.x_min_limit) / (self.x_max_limit - self.x_min_limit) * pixmap_width + margin_x
        return (value - self.x_min_limit) / (self.x_max_limit - self.x_min_limit) * self.window_width

    def image2viewDirectionX(self, value):
        return value / (self.x_max_limit - self.x_min_limit) * self.window_width

    def image2viewY(self, value):
        if self.pixmap() is not None:
            pixmap_height = self.pixmap().height()
            margin_y = (self.window_height - pixmap_height) / 2
            return (value - self.y_min_limit) / (self.y_max_limit - self.y_min_limit) * pixmap_height + margin_y
        return (value - self.y_min_limit) / (self.y_max_limit - self.y_min_limit) * self.window_height

    def image2viewDirectionY(self, value):
        return value / (self.y_max_limit - self.y_min_limit) * self.window_height


class WindowDragData:
    def __init__(self, mouse_x, mouse_y, x_min, x_max, y_min, y_max):
        self.mouse_x = mouse_x
        self.mouse_y = mouse_y
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max


class DebugZQLabel(QtWidgets.QLabel):
    def __init__(self, z_qlabel):
        super().__init__()
        self.z_qlabel = z_qlabel
        self.z_qlabel.mouse_move_event.append(self.update)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.figurePixmap = None

    def updatePixmap(self):
        sz = self.size()
        if self.z_qlabel.displayed_image is None:
            return

        img = cv2.resize(self.z_qlabel.displayed_image, (sz.width(), sz.height()))

        qformat = QtGui.QImage.Format_Indexed8
        if len(img.shape)==3:
            if img.shape[2]==4:
                qformat = QtGui.QImage.Format_RGBA8888
            else:
                qformat = QtGui.QImage.Format_RGB888

        img = QtGui.QImage(img, img.shape[1], img.shape[0], img.strides[0], qformat).rgbSwapped()
        self.figurePixmap = QtGui.QPixmap.fromImage(img)
        self.setPixmap(self.figurePixmap.scaled(sz, QtCore.Qt.KeepAspectRatio))

    def resizeEvent(self, event):
        self.updatePixmap()

    def paintEvent(self, event):
        if self.figurePixmap is None:
            return

        painter = QtGui.QPainter(self)
        painter.drawPixmap(self.rect(), self.figurePixmap)

        width = self.size().width()
        height = self.size().height()
        image_width = self.z_qlabel.image_width
        image_height = self.z_qlabel.image_height

        width_mult = width / image_width
        height_mult = height / image_height

        min_x = self.z_qlabel.x_min_limit * width_mult
        max_x = self.z_qlabel.x_max_limit * width_mult
        min_y = self.z_qlabel.y_min_limit * height_mult
        max_y = self.z_qlabel.y_max_limit * height_mult

        x_pos = self.z_qlabel.x_pos * width_mult
        y_pos = self.z_qlabel.y_pos * height_mult

        painter.setPen(QtGui.QPen(QtCore.Qt.red, 5, QtCore.Qt.SolidLine))
        painter.drawRect(min_x, min_y, max_x-min_x, max_y-min_y)
        painter.drawEllipse(x_pos, y_pos, 5, 5)

class TestZoomableQLabel(ZoomableQLabel):
    """
    Test class that enables drawing the selection box.
    """
    def __init__(self, b1, b2, b3):
        super().__init__(b1, b2, b3)

    def paintEvent(self, event):
        super().paintEvent(event)
        self.paintSelection()

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    z_label = TestZoomableQLabel(True, True, True)
    #z_label = TestZoomableQLabel(False, True, False)
    z_label.displayed_image = cv2.imread('echo_placeholder.png', 0)
    z_label.resetView()
    main_window.setCentralWidget(z_label)
    main_window.show()
    main_window.setWindowTitle("Main window")
    main_window.resize(400, 400)
    main_window.move(750, 400)

    debug_window = QtWidgets.QMainWindow()
    debug_label = DebugZQLabel(z_label)
    debug_window.setCentralWidget(debug_label)
    debug_window.show()
    debug_window.setWindowTitle("Debug window")
    debug_window.resize(z_label.image_width, z_label.image_height)
    debug_window.move(500, 100)

    sys.exit(app.exec_())
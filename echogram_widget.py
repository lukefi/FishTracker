from PyQt5 import QtCore, QtGui, QtWidgets
import cv2

class EchoFigure(QtWidgets.QLabel):
    parent = None

    def __init__(self, parent):
        QtWidgets.QLabel.__init__(self, parent)
        self.parent = parent
        self.figurePixmap = None
        self.test_img = cv2.imread('echo_placeholder.png', 0)
        self.setMouseTracking(True)

        self.progress = 0
        self.zoom_01 = 0.0
        self.max_zoom = 3.0
        self.min_limit = 0
        self.max_limit = 0
        self.image_width = 0
        self.window_width = 0

    def showTestImage(self):
        self.setAlignment(QtCore.Qt.AlignCenter)
        # self.setScaledContents(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

    def resizeEvent(self, event):
        self.applyPixmap()

    def applyPixmap(self):
        img = self.fitToSize(self.test_img)
        img = QtGui.QImage(img, img.shape[1], img.shape[0], img.strides[0], QtGui.QImage.Format_Indexed8).rgbSwapped()
        self.figurePixmap = QtGui.QPixmap.fromImage(img)
        self.setPixmap(self.figurePixmap.scaled(self.size(), QtCore.Qt.KeepAspectRatio))

    def fitToSize(self, image):
        sz = self.size()
        self.window_width = window_width = max(1, sz.width())
        window_height = max(1, sz.height())

        self.image_width = image_width = image.shape[1]

        total_width = self.zoom_01 * (max(self.max_zoom * image_width, 2 * window_width) - window_width) + window_width
        width_z = min(int(window_width / total_width * image_width), image_width)

        half_width = width_z / 2
        playhead_pos = self.progress * image_width
        self.min_limit = int(playhead_pos - half_width)
        self.max_limit = int(playhead_pos + half_width)
        if self.min_limit < 0:
            self.max_limit -= self.min_limit
            self.min_limit = 0
        elif self.max_limit > image_width:
            self.min_limit -= self.max_limit - image_width
            self.max_limit = image_width

        #self.applied_zoom = image_width / (max_limit - min_limit)
        #print(min_limit, max_limit, self.applied_zoom)

        img = image[:, self.min_limit:self.max_limit]
        img = cv2.resize(img, (window_width, window_height))
        return img

    def frame2xPos(self, value):
        # return value * width * self.applied_zoom
        return (value * self.image_width - self.min_limit) / (self.max_limit - self.min_limit) * self.window_width

    def xPos2Frame(self, value):
        #return value / width / self.applied_zoom
        return (value*(self.max_limit - self.min_limit)/self.window_width + self.min_limit) / self.image_width

    def paintEvent(self, event):
        size = self.size()
        width = size.width()
        height = size.height()

        h_pos = self.frame2xPos(self.progress) #self.applied_zoom * self.progress * width

        painter = QtGui.QPainter(self)
        painter.drawPixmap(self.rect(), self.figurePixmap)

        if h_pos < width:
            painter.setPen(QtCore.Qt.red)
            painter.drawLine(h_pos, 0, h_pos, height)

    #def mouseMoveEvent(self, event):
    #    #if event.buttons() == QtCore.Qt.NoButton:
    #    #    print("Simple mouse motion")
    #    if event.buttons() == QtCore.Qt.LeftButton:
    #        pass
    #    elif event.buttons() == QtCore.Qt.RightButton:
    #        pass
    #    super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.parent.setFrame(self.xPos2Frame(event.x())) #float(event.x()) / self.size().width())
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        self.zoom_01 = max(0, min(self.zoom_01 + event.angleDelta().y() / 2000, 1))
        self.applyPixmap()

class EchogramViewer(QtWidgets.QWidget):
    def __init__(self, playback_manager):
        super().__init__()

        self.playback_manager = playback_manager
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.figure = EchoFigure(self)
        self.horizontalLayout.addWidget(self.figure)
        self.figure.showTestImage()
        self.playback_manager.frame_available.append(self.updateLocation)

        self.setLayout(self.horizontalLayout)

    def updateLocation(self, frame):
        self.figure.progress = self.playback_manager.getRelativeIndex()
        self.figure.update()

    def setFrame(self, percentage):
        self.playback_manager.setRelativeIndex(percentage)



if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    playback_manager.openTestFile()
    playback_manager.play()
    echogram = EchogramViewer(playback_manager)
    main_window.setCentralWidget(echogram)
    main_window.show()
    sys.exit(app.exec_())
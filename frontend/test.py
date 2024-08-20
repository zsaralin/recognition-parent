from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton, QGraphicsOpacityEffect

class TestApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        self.label = QLabel('Hello', self)
        self.label.setStyleSheet("background-color: yellow; font-size: 20px;")
        layout.addWidget(self.label)

        fade_button = QPushButton('Fade', self)
        fade_button.clicked.connect(lambda: self.fade(self.label))
        layout.addWidget(fade_button)

        unfade_button = QPushButton('Unfade', self)
        unfade_button.clicked.connect(lambda: self.unfade(self.label))
        layout.addWidget(unfade_button)

    def fade(self, widget):
        self.effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(self.effect)

        self.animation = QtCore.QPropertyAnimation(self.effect, b"opacity")
        self.animation.setDuration(1000)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.start()

    def unfade(self, widget):
        self.effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(self.effect)

        self.animation = QtCore.QPropertyAnimation(self.effect, b"opacity")
        self.animation.setDuration(1000)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    ex = TestApp()
    ex.show()
    sys.exit(app.exec_())

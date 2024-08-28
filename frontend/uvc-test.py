import sys
import cv2
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QSlider, QVBoxLayout, QWidget, QCheckBox

class CameraWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        print(cv2.__version__)
        self.brightness = 0
        self.saturation = 1.0  # Default saturation value
        self.auto_exposure = True

        # Use OpenCV to access the camera
        self.cap = cv2.VideoCapture("0")
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)
        self.cap.set(cv2.CAP_PROP_SATURATION, 0.5)

        if not self.cap.isOpened():
            print("Failed to open camera")
            sys.exit()

    def initUI(self):
        # Layout
        layout = QVBoxLayout()

        # Label to display the camera feed
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(640, 480)  # Set a fixed size for the camera feed display
        layout.addWidget(self.image_label)

        # Brightness slider
        self.brightness_slider = QSlider(Qt.Horizontal, self)
        self.brightness_slider.setMinimum(0)
        self.brightness_slider.setMaximum(100)
        self.brightness_slider.setValue(50)  # Default is the middle value
        self.brightness_slider.valueChanged.connect(self.update_brightness)
        layout.addWidget(self.brightness_slider)

        # Saturation slider
        self.saturation_slider = QSlider(Qt.Horizontal, self)
        self.saturation_slider.setMinimum(0)
        self.saturation_slider.setMaximum(100)
        self.saturation_slider.setValue(50)  # Default is the middle value
        self.saturation_slider.valueChanged.connect(self.update_saturation)
        layout.addWidget(self.saturation_slider)

        # Checkbox for Auto Exposure
        self.auto_exposure_checkbox = QCheckBox("Auto Exposure", self)
        self.auto_exposure_checkbox.setChecked(True)
        self.auto_exposure_checkbox.stateChanged.connect(self.toggle_exposure)
        layout.addWidget(self.auto_exposure_checkbox)

        # Exposure Time slider (initially hidden)
        self.exposure_slider = QSlider(Qt.Horizontal, self)
        self.exposure_slider.setMinimum(1)
        self.exposure_slider.setMaximum(500)  # Adjust this range as needed
        self.exposure_slider.setValue(100)
        self.exposure_slider.setVisible(False)
        self.exposure_slider.valueChanged.connect(self.update_exposure)
        layout.addWidget(self.exposure_slider)

        # Set layout
        self.setLayout(layout)

        # Set up a timer to update the frame
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(20)  # Update every 20ms

        self.setWindowTitle('Camera with Brightness, Saturation, and Exposure Control')
        self.setFixedSize(650, 650)  # Adjusted size for new elements
        self.show()

    def update_brightness(self, value):
        # Convert slider value to the appropriate brightness range [0, 1]
        brightness_normalized = value
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness_normalized)

    def update_saturation(self, value):
        # Convert slider value to the appropriate saturation range [0, 1]
        saturation_normalized = value
        self.cap.set(cv2.CAP_PROP_SATURATION, saturation_normalized)

    def toggle_exposure(self, state):
        if state == Qt.Checked:
            self.auto_exposure = True
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)  # Enable auto exposure
            self.exposure_slider.setVisible(False)
        else:
            self.auto_exposure = False
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # Disable auto exposure (manual mode)
            self.exposure_slider.setVisible(True)
            self.update_exposure(self.exposure_slider.value())

    def update_exposure(self, value):
        if not self.auto_exposure:
            exposure_time = value / 1000.0  # Convert to seconds or fraction of a second
            self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure_time)

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Resize the frame to fit the label
            frame = cv2.resize(frame, (640, 480))

            # Convert the frame to QImage
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

            # Display the image
            self.image_label.setPixmap(QPixmap.fromImage(q_image))

    def closeEvent(self, event):
        # Release the camera when the window is closed
        self.cap.release()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CameraWindow()
    sys.exit(app.exec_())

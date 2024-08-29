import sys
import cv2
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame,
    QCheckBox, QSlider, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
from backend_communicator import set_camera_control

class CameraApp(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize camera
        self.cap = cv2.VideoCapture(0)

        # Set up the window layout
        self.initUI()

        # Set up a timer to grab frames from the camera
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update every 30 ms

        # Timer for checking brightness every 10 seconds
        self.brightness_timer = QTimer(self)
        self.brightness_timer.timeout.connect(self.check_and_adjust_brightness)

        # Initial values
        self.target_brightness = 100
        self.current_exposure = 1  # Initial exposure time

    def initUI(self):
        screen = QApplication.primaryScreen().availableGeometry()
        screen_width = screen.width()
        screen_height = screen.height()

        # Calculate the window size
        self.setWindowTitle('Camera with Side Panel')
        self.setGeometry(100, 100, screen_width // 2, screen_height // 2)

        # Set up the main layout
        layout = QHBoxLayout(self)

        # Create the camera display area
        self.video_frame = QLabel(self)
        self.video_frame.setFixedSize(screen_width // 2 - 150, screen_height // 2)  # Leave space for the side panel
        layout.addWidget(self.video_frame)

        # Create the side panel
        self.side_panel = QFrame(self)
        self.side_panel.setFixedSize(150, screen_height // 2)
        self.side_panel.setStyleSheet("background-color: lightgray;")
        layout.addWidget(self.side_panel)

        # Set up the checkboxes, labels, and sliders
        checkbox_layout = QVBoxLayout()
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        checkbox_layout.setSpacing(5)

        self.auto_exposure_checkbox = QCheckBox('Auto Exposure', self)
        self.manual_exposure_checkbox = QCheckBox('Manual Exposure', self)
        self.auto_ev_checkbox = QCheckBox('Auto EV', self)

        # Labels for sliders
        self.brightness_label = QLabel("Brightness", self)
        self.exposure_label = QLabel("Exposure Time", self)

        # Sliders for brightness and exposure time
        self.brightness_slider = QSlider(Qt.Horizontal, self)
        self.exposure_slider = QSlider(Qt.Horizontal, self)

        # Set range for exposure time slider (example range; adjust as needed)
        self.exposure_slider.setRange(1, 10000)  # Represents 1 to 10,000 (example values for exposure time)

        # Set range for brightness slider
        self.brightness_slider.setRange(50, 200)
        self.brightness_slider.setValue(100)  # Default to 100

        # Connect the signals to the functions
        self.auto_exposure_checkbox.toggled.connect(self.on_auto_exposure_toggled)
        self.manual_exposure_checkbox.toggled.connect(self.on_manual_exposure_toggled)
        self.exposure_slider.valueChanged.connect(self.on_exposure_slider_changed)
        self.auto_ev_checkbox.toggled.connect(self.on_auto_ev_toggled)
        self.brightness_slider.valueChanged.connect(self.on_brightness_slider_changed)

        # Disable Auto EV checkbox and sliders initially
        self.auto_ev_checkbox.setEnabled(False)
        self.brightness_slider.setEnabled(False)
        self.exposure_slider.setEnabled(False)

        checkbox_layout.addWidget(self.auto_exposure_checkbox)

        checkbox_layout.addWidget(self.manual_exposure_checkbox)
        checkbox_layout.addWidget(self.exposure_label)
        checkbox_layout.addWidget(self.exposure_slider)

        checkbox_layout.addWidget(self.auto_ev_checkbox)
        checkbox_layout.addWidget(self.brightness_label)
        checkbox_layout.addWidget(self.brightness_slider)

        # Spacer to push content to the top
        checkbox_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Add the checkboxes, labels, and sliders to the side panel
        self.side_panel.setLayout(checkbox_layout)

        # Set the layout
        self.setLayout(layout)

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, _ = frame.shape
            qimg = QImage(frame.data, width, height, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            scaled_pixmap = pixmap.scaled(self.video_frame.size(), Qt.KeepAspectRatio)
            self.video_frame.setPixmap(scaled_pixmap)

    def on_auto_exposure_toggled(self, checked):
        if checked:
            self.manual_exposure_checkbox.blockSignals(True)
            self.manual_exposure_checkbox.setChecked(False)
            self.manual_exposure_checkbox.blockSignals(False)
            self.auto_ev_checkbox.setEnabled(False)
            self.auto_ev_checkbox.setChecked(False)
            self.brightness_slider.setEnabled(False)
            self.exposure_slider.setEnabled(False)

            # Call set_camera_control for auto exposure
            set_camera_control('autoExposureMode', 2)  # 2 for automatic exposure

    def on_manual_exposure_toggled(self, checked):
        if checked:
            self.auto_exposure_checkbox.blockSignals(True)
            self.auto_exposure_checkbox.setChecked(False)
            self.auto_exposure_checkbox.blockSignals(False)
            self.auto_ev_checkbox.setEnabled(True)
            self.brightness_slider.setEnabled(False)
            self.exposure_slider.setEnabled(True)

            # Call set_camera_control for manual exposure
            set_camera_control('autoExposureMode', 1)  # 1 for manual exposure

    def on_exposure_slider_changed(self, value):
        """Handles changes in the exposure slider and sends the value to the backend."""
        self.current_exposure = value
        set_camera_control('absoluteExposureTime', value)

    def on_brightness_slider_changed(self, value):
        """Updates the target brightness based on the slider."""
        self.target_brightness = value

    def on_auto_ev_toggled(self, checked):
        if checked:
            self.brightness_timer.start(10000)  # Start the timer to check brightness every 10 seconds
            self.brightness_slider.setEnabled(True)
        else:
            self.brightness_timer.stop()  # Stop the timer if Auto EV is disabled

    def check_and_adjust_brightness(self):
        """Checks the current brightness and adjusts the exposure if it's outside the leeway range."""
        # Placeholder: simulate fetching the current brightness level (this should be fetched from the camera)
        current_brightness = self.get_current_brightness()

        # Check if current brightness is outside the target range with ±30 leeway
        if current_brightness < self.target_brightness - 30:
            # Increase exposure time to compensate for low brightness
            new_exposure = min(self.current_exposure + 500, 10000)  # Adjust by an arbitrary value; cap at max exposure
            self.exposure_slider.setValue(new_exposure)
            set_camera_control('absoluteExposureTime', new_exposure)
        elif current_brightness > self.target_brightness + 30:
            # Decrease exposure time to compensate for high brightness
            new_exposure = max(self.current_exposure - 500, 1)  # Adjust by an arbitrary value; cap at min exposure
            self.exposure_slider.setValue(new_exposure)
            set_camera_control('absoluteExposureTime', new_exposure)

    def get_current_brightness(self):
        """Simulates fetching the current brightness from the camera."""
        # This function should fetch the actual brightness value from the camera
        # Here, we simulate with a static value for demonstration purposes
        return 90  # Simulated brightness value

    def toggle_auto_ev_checkbox(self):
        """Enable or disable the Auto EV checkbox based on the Manual Exposure checkbox."""
        enabled = self.manual_exposure_checkbox.isChecked()
        self.auto_ev_checkbox.setEnabled(enabled)
        self.brightness_slider.setEnabled(enabled and self.auto_ev_checkbox.isChecked())
        self.exposure_slider.setEnabled(enabled and not self.auto_ev_checkbox.isChecked())

    def closeEvent(self, event):
        self.cap.release()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    cam_app = CameraApp()
    cam_app.show()
    sys.exit(app.exec_())

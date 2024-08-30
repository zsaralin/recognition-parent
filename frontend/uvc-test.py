import sys
import cv2
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame,
    QCheckBox, QSlider, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
from backend_communicator import set_camera_control, get_current_exposure_time

class CameraApp(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        self.current_exposure = self.get_initial_exposure_time()  # Initialize exposure time
        self.is_adjusting_exposure = False  # Flag to track if exposure adjustment is in progress
        self.cancel_adjustment = False  # Flag to cancel current adjustment loop

        # For FPS calculation
        self.last_time = time.time()
        self.fps = 0

        # Set up the window layout
        self.initUI()

        # Set up a timer to grab frames from the camera
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update every 30 ms

        # Timer for checking brightness every 5 seconds
        self.brightness_timer = QTimer(self)
        self.brightness_timer.timeout.connect(self.check_and_adjust_brightness)

        # Initial values
        self.target_brightness = 100
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
        self.white_balance_label = QLabel("White Balance", self)
        self.hue_label = QLabel("Hue", self)
        self.saturation_label = QLabel("Saturation", self)

        # Sliders for brightness, exposure time, white balance, hue, and saturation
        self.brightness_slider = QSlider(Qt.Horizontal, self)
        self.exposure_slider = QSlider(Qt.Horizontal, self)
        self.white_balance_slider = QSlider(Qt.Horizontal, self)
        self.hue_slider = QSlider(Qt.Horizontal, self)
        self.saturation_slider = QSlider(Qt.Horizontal, self)

        # Set range for exposure time slider
        self.exposure_slider.setRange(1, 1200)
        self.exposure_slider.setValue(self.current_exposure)

        # Set range for brightness slider
        self.brightness_slider.setRange(50, 200)
        self.brightness_slider.setValue(100)  # Default to 100

        # Set ranges for white balance, hue, and saturation
        self.white_balance_slider.setRange(2000, 6500)  # Example range for white balance (in Kelvin)
        self.white_balance_slider.setValue(4500)  # Default value
        self.hue_slider.setRange(-180, 180)  # Hue range in degrees
        self.hue_slider.setValue(0)  # Default value
        self.saturation_slider.setRange(0, 255)  # Saturation range
        self.saturation_slider.setValue(128)  # Default value

        # Connect the signals to the functions
        self.auto_exposure_checkbox.toggled.connect(self.on_auto_exposure_toggled)
        self.manual_exposure_checkbox.toggled.connect(self.on_manual_exposure_toggled)
        self.exposure_slider.valueChanged.connect(self.on_exposure_slider_changed)
        self.auto_ev_checkbox.toggled.connect(self.on_auto_ev_toggled)
        self.brightness_slider.valueChanged.connect(self.on_brightness_slider_changed)
        self.white_balance_slider.valueChanged.connect(self.on_white_balance_changed)
        self.hue_slider.valueChanged.connect(self.on_hue_changed)
        self.saturation_slider.valueChanged.connect(self.on_saturation_changed)

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
        checkbox_layout.addWidget(self.white_balance_label)
        checkbox_layout.addWidget(self.white_balance_slider)
        checkbox_layout.addWidget(self.hue_label)
        checkbox_layout.addWidget(self.hue_slider)
        checkbox_layout.addWidget(self.saturation_label)
        checkbox_layout.addWidget(self.saturation_slider)

        # Spacer to push content to the top
        checkbox_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Add the checkboxes, labels, and sliders to the side panel
        self.side_panel.setLayout(checkbox_layout)

        # Set the layout
        self.setLayout(layout)

    def get_initial_exposure_time(self):
        """Fetch the initial exposure time from the backend."""
        response = get_current_exposure_time()
        if response:
            try:
                # Extract the numeric value from the response
                exposure_time = int(response.split()[-1])  # Assumes the number is at the end of the string
                return exposure_time
            except ValueError as e:
                print(f"Error parsing exposure time: {e}")
                return 1  # Default to a minimum value if parsing fails
        else:
            return 1

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Calculate FPS
            current_time = time.time()
            self.fps = 1 / (current_time - self.last_time)
            self.last_time = current_time

            # Convert frame to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Overlay the FPS on the frame
            cv2.putText(frame, f"FPS: {int(self.fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)

            # Convert frame to QImage and display it
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
            set_camera_control('autoExposureMode', 8)  # 2 for automatic exposure

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
            
    def on_auto_ev_toggled(self, checked):
        """Handle the toggling of the Auto EV checkbox."""
        if checked:
            self.brightness_timer.start(5000)  # Start the timer to check brightness every 5 seconds
            self.brightness_slider.setEnabled(True)
        else:
            self.brightness_timer.stop()  # Stop the timer if Auto EV is disabled

    def on_exposure_slider_changed(self, value):
        """Handles changes in the exposure slider and sends the value to the backend."""
        self.current_exposure = value
        print(value)
        set_camera_control('absoluteExposureTime', value)

    def on_brightness_slider_changed(self, value):
        """Updates the target brightness based on the slider."""
        self.target_brightness = value

        # Cancel the current adjustment loop if running
        if self.is_adjusting_exposure:
            self.cancel_adjustment = True
            self.is_adjusting_exposure = False

        # Start a new adjustment loop
        self.check_and_adjust_brightness()

    def check_and_adjust_brightness(self):
        if self.is_adjusting_exposure:
            # Skip this execution if an adjustment is already in progress
            return
        
        self.is_adjusting_exposure = True
        self.cancel_adjustment = False  # Reset the cancel flag
        current_brightness = self.get_current_brightness()

        def adjust_exposure(current_brightness):
            if self.cancel_adjustment:
                # Stop the loop if a new brightness adjustment is requested
                self.is_adjusting_exposure = False
                return

            # Calculate the difference between current and target brightness
            brightness_difference = self.target_brightness - current_brightness

            # Determine step size based on the brightness difference
            step_size = max(1, abs(brightness_difference) // 10)  # Larger steps for larger differences, minimum step of 1

            if brightness_difference > 30 and self.current_exposure < 1000:  # Cap at 1000
                # Increase exposure time based on the step size, but cap it at 1000
                self.current_exposure = min(self.current_exposure + step_size, 1000)
                set_camera_control('absoluteExposureTime', self.current_exposure)
                self.exposure_slider.setValue(self.current_exposure)
            elif brightness_difference < -30 and self.current_exposure > 1:
                # Decrease exposure time based on the step size
                self.current_exposure = max(self.current_exposure - step_size, 1)
                set_camera_control('absoluteExposureTime', self.current_exposure)
                self.exposure_slider.setValue(self.current_exposure)
            else:
                # Exit the loop if brightness is within the desired range
                self.is_adjusting_exposure = False
                return  

            # Fetch the updated brightness after changing exposure
            current_brightness = self.get_current_brightness()

            # Delay the next adjustment by 1 second (1000 ms)
            QTimer.singleShot(1000, lambda: adjust_exposure(current_brightness))

        # Start the adjustment process
        adjust_exposure(current_brightness)
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

    def on_white_balance_changed(self, value):
        """Handles changes in the white balance slider and sends the value to the backend."""
        print(f"White Balance set to: {value}K")
        set_camera_control('whiteBalanceTemperature', value)

    def on_hue_changed(self, value):
        """Handles changes in the hue slider and sends the value to the backend."""
        print(f"Hue set to: {value}")
        set_camera_control('hue', value)

    def on_saturation_changed(self, value):
        """Handles changes in the saturation slider and sends the value to the backend."""
        print(f"Saturation set to: {value}")
        set_camera_control('saturation', value)
    def closeEvent(self, event):
        self.cap.release()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    cam_app = CameraApp()
    cam_app.show()
    sys.exit(app.exec_())

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel, QLineEdit, QPushButton, QCheckBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QFont
import config
from backend_communicator import set_camera_control

class SliderOverlay(QWidget):
    config_changed = pyqtSignal()  # Signal to notify when config changes
    font_size_changed = pyqtSignal(float)  # Signal to notify when font size changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.setFocusPolicy(Qt.StrongFocus)  # Ensure the widget can receive key events
        self.setFixedSize(320, 600)  # Set a fixed size for the window with extra width and height
        self.move(10, 10)  # Move the window to the top-left corner of the screen
        self.setStyleSheet("""
            background-color: white;  /* Set the background color to white */
        """)

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)  # Set spacing between widgets
        layout.setContentsMargins(15, 15, 15, 15)  # Set margins around the layout
        font = QFont()
        font.setPointSize(10)  # Reduce font size for all widgets

        self.gif_delay_label = QLabel('GIF Delay', self)
        self.gif_delay_label.setFont(font)
        self.gif_delay_slider = self.create_slider(1, 100, config.gif_delay)
        self.gif_delay_input = self.create_input(1, 100, is_double=False)
        self.gif_delay_input.setText(str(config.gif_delay))
        self.gif_delay_input.setFont(font)

        self.num_cols_label = QLabel('Num Cols', self)
        self.num_cols_label.setFont(font)
        self.num_cols_slider = self.create_slider(11, 41, config.num_cols, step=2)  # Ensure slider steps are odd
        self.num_cols_input = self.create_input(11, 41, is_double=False, only_odd=True)  # Enforce odd numbers in input
        self.num_cols_input.setText(str(config.num_cols))
        self.num_cols_input.setFont(font)

        self.middle_y_pos_label = QLabel('Middle Y Pos', self)
        self.middle_y_pos_label.setFont(font)
        self.middle_y_pos_slider = self.create_slider(-10, 10, config.middle_y_pos)
        self.middle_y_pos_input = self.create_input(-10, 10, is_double=False)
        self.middle_y_pos_input.setText(str(config.middle_y_pos))
        self.middle_y_pos_input.setFont(font)

        self.update_count_label = QLabel('Update Count', self)
        self.update_count_label.setFont(font)
        self.update_count_slider = self.create_slider(1, 100, config.update_count)
        self.update_count_input = self.create_input(1, 100, is_double=False)
        self.update_count_input.setText(str(config.update_count))
        self.update_count_input.setFont(font)

        self.update_delay_label = QLabel('Update Delay', self)
        self.update_delay_label.setFont(font)
        self.update_delay_slider = self.create_slider(0, 200, config.update_delay)
        self.update_delay_input = self.create_input(0, 200, is_double=False)
        self.update_delay_input.setText(str(config.update_delay))
        self.update_delay_input.setFont(font)

        self.update_int_label = QLabel('Update Interval', self)
        self.update_int_label.setFont(font)
        self.update_int_slider = self.create_slider(5, 100, config.update_int)
        self.update_int_input = self.create_input(5, 100, is_double=False)
        self.update_int_input.setText(str(config.update_int))
        self.update_int_input.setFont(font)

        self.bbox_multiplier_label = QLabel('BBox Multiplier', self)
        self.bbox_multiplier_label.setFont(font)
        self.bbox_multiplier_slider = self.create_slider(5, 30, int(config.bbox_multiplier * 10))
        self.bbox_multiplier_input = self.create_input(5, 30, is_double=False)
        self.bbox_multiplier_input.setText(str(int(config.bbox_multiplier * 10)))
        self.bbox_multiplier_input.setFont(font)

        self.font_size_label = QLabel('Font Size', self)
        self.font_size_label.setFont(font)
        self.font_size_slider = self.create_double_slider(0.1, 3.0, config.font_size, step=0.1)
        self.font_size_input = self.create_input(0.1, 3.0, is_double=True)
        self.font_size_input.setText(str(config.font_size))
        self.font_size_input.setFont(font)

        self.auto_exposure_time_label = QLabel('Auto Exposure Time', self)
        self.auto_exposure_time_label.setFont(font)
        self.auto_exposure_time_slider = self.create_slider(50, 10000, int(config.auto_exposure_time))
        self.auto_exposure_time_input = self.create_input(50, 10000, is_double=False)
        self.auto_exposure_time_input.setText(str(int(config.auto_exposure_time)))
        self.auto_exposure_time_input.setFont(font)

        self.gain_label = QLabel('Gain', self)
        self.gain_label.setFont(font)
        self.gain_slider = self.create_slider(1, 128, int(config.gain))
        self.gain_input = self.create_input(1, 128, is_double=False)
        self.gain_input.setText(str(int(config.gain)))
        self.gain_input.setFont(font)

        self.jump_threshold_label = QLabel('Jump Threshold', self)
        self.jump_threshold_label.setFont(font)
        self.jump_threshold_slider = self.create_slider(0, 200, config.jump_threshold)
        self.jump_threshold_input = self.create_input(0, 200, is_double=False)
        self.jump_threshold_input.setText(str(config.jump_threshold))
        self.jump_threshold_input.setFont(font)

        self.min_face_size_label = QLabel('Min Face Size', self)
        self.min_face_size_label.setFont(font)
        self.min_face_size_slider = self.create_slider(0, 200, config.min_face_size)
        self.min_face_size_input = self.create_input(0, 200, is_double=False)
        self.min_face_size_input.setText(str(config.min_face_size))
        self.min_face_size_input.setFont(font)

        self.create_sprites_checkbox = QCheckBox('Create Sprites', self)
        self.create_sprites_checkbox.setChecked(config.create_sprites)
        self.create_sprites_checkbox.setFont(font)

        self.show_fps_checkbox = QCheckBox('Show FPS', self)
        self.show_fps_checkbox.setChecked(config.show_fps)
        self.show_fps_checkbox.setFont(font)

        self.auto_update_checkbox = QCheckBox('Auto Update', self)
        self.auto_update_checkbox.setChecked(config.auto_update)
        self.auto_update_checkbox.setFont(font)

        self.show_saved_checkbox = QCheckBox('Show Saved Frame', self)  # New checkbox for showing saved frame
        self.show_saved_checkbox.setChecked(config.show_saved_frame)
        self.show_saved_checkbox.setFont(font)

        self.save_button = QPushButton('Save', self)
        self.save_button.setFont(font)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; /* Green background */
                color: white; /* White text */
                padding: 5px; /* Add padding */
                border: none; /* Remove border */
                border-radius: 5px; /* Add rounded corners */
            }
            QPushButton:hover {
                background-color: #45a049; /* Darker green on hover */
            }
        """)
        self.save_button.clicked.connect(self.save_values_to_config)

        layout.addWidget(self.gif_delay_label)
        layout.addWidget(self.gif_delay_slider)
        layout.addWidget(self.gif_delay_input)

        layout.addWidget(self.num_cols_label)
        layout.addWidget(self.num_cols_slider)
        layout.addWidget(self.num_cols_input)

        layout.addWidget(self.middle_y_pos_label)
        layout.addWidget(self.middle_y_pos_slider)
        layout.addWidget(self.middle_y_pos_input)

        layout.addWidget(self.update_count_label)
        layout.addWidget(self.update_count_slider)
        layout.addWidget(self.update_count_input)

        layout.addWidget(self.update_delay_label)
        layout.addWidget(self.update_delay_slider)
        layout.addWidget(self.update_delay_input)

        layout.addWidget(self.update_int_label)
        layout.addWidget(self.update_int_slider)
        layout.addWidget(self.update_int_input)

        layout.addWidget(self.bbox_multiplier_label)
        layout.addWidget(self.bbox_multiplier_slider)
        layout.addWidget(self.bbox_multiplier_input)

        layout.addWidget(self.font_size_label)
        layout.addWidget(self.font_size_slider)
        layout.addWidget(self.font_size_input)

        layout.addWidget(self.auto_exposure_time_label)
        layout.addWidget(self.auto_exposure_time_slider)
        layout.addWidget(self.auto_exposure_time_input)

        layout.addWidget(self.gain_label)
        layout.addWidget(self.gain_slider)
        layout.addWidget(self.gain_input)

        layout.addWidget(self.jump_threshold_label)
        layout.addWidget(self.jump_threshold_slider)
        layout.addWidget(self.jump_threshold_input)

        layout.addWidget(self.min_face_size_label)
        layout.addWidget(self.min_face_size_slider)
        layout.addWidget(self.min_face_size_input)

        layout.addWidget(self.create_sprites_checkbox)
        layout.addWidget(self.show_fps_checkbox)
        layout.addWidget(self.auto_update_checkbox)
        layout.addWidget(self.show_saved_checkbox)  # Add the new checkbox to the layout

        layout.addWidget(self.save_button)

        self.setLayout(layout)
        self.setWindowTitle('Overlay Controls')

    def create_slider(self, min_value, max_value, default_value=None, step=1):
        slider = QSlider(Qt.Horizontal, self)
        slider.setRange(min_value, max_value)
        if default_value is not None:
            slider.setValue(default_value)
        slider.setSingleStep(step)
        slider.valueChanged.connect(self.update_value_from_slider)

        # Apply stylesheet to make the handle and groove smaller
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #ddd; /* Groove color */
                height: 6px; /* Groove height */
            }
            QSlider::handle:horizontal {
                background-color: #2196F3; /* Thumb color */
                border: 1px solid #999; /* Border around thumb */
                width: 10px; /* Thumb width */
                height: 10px; /* Thumb height */
                margin: -2px 0; /* Center the handle on the groove */
                border-radius: 5px; /* Rounded corners */
            }
        """)

        return slider

    def create_double_slider(self, min_value, max_value, default_value=None, step=0.1):
        slider = QSlider(Qt.Horizontal, self)
        slider.setRange(int(min_value * 10), int(max_value * 10))
        if default_value is not None:
            slider.setValue(int(default_value * 10))
        slider.setSingleStep(int(step * 10))
        slider.valueChanged.connect(self.update_value_from_slider)

        # Apply the same style to ensure consistency
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #ddd; /* Groove color */
                height: 6px; /* Groove height */
            }
            QSlider::handle:horizontal {
                background-color: #2196F3; /* Thumb color */
                border: 1px solid #999; /* Border around thumb */
                width: 10px; /* Thumb width */
                height: 10px; /* Thumb height */
                margin: -2px 0; /* Center the handle on the groove */
                border-radius: 5px; /* Rounded corners */
            }
        """)

        return slider

    def create_input(self, min_value, max_value, is_double=False, only_odd=False):
        input_box = QLineEdit(self)
        if is_double:
            validator = QDoubleValidator(min_value, max_value, 1)
            validator.setNotation(QDoubleValidator.StandardNotation)
        else:
            validator = QIntValidator(min_value, max_value)
        input_box.setValidator(validator)
        input_box.returnPressed.connect(self.update_value_from_input)
        input_box.only_odd = only_odd  # Custom attribute to enforce odd numbers

        # Apply styles to make it look like an input field
        input_box.setStyleSheet("""
            QLineEdit {
                background-color: #f0f0f0;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
        """)

        return input_box

    def update_value_from_slider(self):
        sender = self.sender()
        if sender == self.num_cols_slider:
            # Ensure the value is odd
            value = sender.value()
            if value % 2 == 0:
                value += 1
                sender.setValue(value)
            self.num_cols_input.setText(str(value))
        elif sender == self.gif_delay_slider:
            self.gif_delay_input.setText(str(sender.value()))
        elif sender == self.update_count_slider:
            self.update_count_input.setText(str(sender.value()))
        elif sender == self.update_delay_slider:
            self.update_delay_input.setText(str(sender.value()))
        elif sender == self.update_int_slider:
            self.update_int_input.setText(str(sender.value()))
        elif sender == self.middle_y_pos_slider:
            self.middle_y_pos_input.setText(str(sender.value()))
        elif sender == self.bbox_multiplier_slider:
            self.bbox_multiplier_input.setText(str(sender.value() / 10))
        elif sender == self.font_size_slider:
            self.font_size_input.setText(str(sender.value() / 10))
            self.font_size_changed.emit(sender.value() / 10)  # Emit the font size changed signal
        elif sender == self.auto_exposure_time_slider:
            self.auto_exposure_time_input.setText(str(sender.value()))
            set_camera_control('absoluteExposureTime', sender.value())  # Call the backend function
        elif sender == self.gain_slider:
            self.gain_input.setText(str(sender.value()))
            set_camera_control('gain', sender.value())  # Call the backend function
        elif sender == self.jump_threshold_slider:
            self.jump_threshold_input.setText(str(sender.value()))
        elif sender == self.min_face_size_slider:
            self.min_face_size_input.setText(str(sender.value()))

    def update_value_from_input(self):
        sender = self.sender()
        if sender.only_odd:
            value = int(sender.text())
        else:
            value = float(sender.text())
        if sender == self.num_cols_input:
            # Ensure the value is odd
            if value % 2 == 0:
                value += 1 if value < sender.validator().top() else -1
            self.num_cols_slider.setValue(int(value))
        elif sender == self.gif_delay_input:
            self.gif_delay_slider.setValue(int(value))
        elif sender == self.update_count_input:
            self.update_count_slider.setValue(int(value))
        elif sender == self.update_delay_input:
            self.update_delay_slider.setValue(int(value))
        elif sender == self.update_int_input:
            self.update_int_slider.setValue(int(value))
        elif sender == self.middle_y_pos_input:
            self.middle_y_pos_slider.setValue(int(value))
        elif sender == self.bbox_multiplier_input:
            self.bbox_multiplier_slider.setValue(int(value * 10))
        elif sender == self.font_size_input:
            self.font_size_slider.setValue(int(value * 10))
            self.font_size_changed.emit(value)  # Emit the font size changed signal
        elif sender == self.auto_exposure_time_input:
            self.auto_exposure_time_slider.setValue(int(value))
            set_camera_control('auto_exposure_time', int(value))  # Call the backend function
        elif sender == self.gain_input:
            self.gain_slider.setValue(int(value))
            set_camera_control('gain', int(value))  # Call the backend function
        elif sender == self.jump_threshold_input:
            self.jump_threshold_slider.setValue(int(value))
        elif sender == self.min_face_size_input:
            self.min_face_size_slider.setValue(int(value))

    def save_values_to_config(self):
        config.gif_delay = self.gif_delay_slider.value()
        config.num_cols = self.num_cols_slider.value()
        config.middle_y_pos = self.middle_y_pos_slider.value()
        config.update_count = self.update_count_slider.value()
        config.update_delay = self.update_delay_slider.value()
        config.update_int = self.update_int_slider.value()
        config.bbox_multiplier = self.bbox_multiplier_slider.value() / 10.0
        config.font_size = self.font_size_slider.value() / 10.0
        config.create_sprites = self.create_sprites_checkbox.isChecked()
        config.show_fps = self.show_fps_checkbox.isChecked()
        config.auto_update = self.auto_update_checkbox.isChecked()
        config.show_saved_frame = self.show_saved_checkbox.isChecked()
        config.auto_exposure_time = self.auto_exposure_time_slider.value()
        config.gain = self.gain_slider.value()
        config.jump_threshold = self.jump_threshold_slider.value()
        config.min_face_size = self.min_face_size_slider.value()

        # Retain the demo value from the previous configuration
        demo_value = getattr(config, 'demo', False)
        config.demo = demo_value

        # Save the updated config to file
        with open('config.py', 'w') as config_file:
            config_file.write(f"gif_delay = {config.gif_delay}\n")
            config_file.write(f"num_cols = {config.num_cols}\n")
            config_file.write(f"middle_y_pos = {config.middle_y_pos}\n")
            config_file.write(f"update_count = {config.update_count}\n")
            config_file.write(f"update_delay = {config.update_delay}\n")
            config_file.write(f"update_int = {config.update_int}\n")
            config_file.write(f"bbox_multiplier = {config.bbox_multiplier}\n")
            config_file.write(f"font_size = {config.font_size}\n")
            config_file.write(f"create_sprites = {config.create_sprites}\n")
            config_file.write(f"show_fps = {config.show_fps}\n")
            config_file.write(f"auto_update = {config.auto_update}\n")
            config_file.write(f"show_saved_frame = {config.show_saved_frame}\n")
            config_file.write(f"auto_exposure_time = {config.auto_exposure_time}\n")
            config_file.write(f"gain = {config.gain}\n")
            config_file.write(f"jump_threshold = {config.jump_threshold}\n")
            config_file.write(f"min_face_size = {config.min_face_size}\n")
            config_file.write(f"demo = {config.demo}\n")  # Write the demo config value

        # Emit signal to update the config
        self.config_changed.emit()

    def keyPressEvent(self, event):
        print(f"Key pressed: {event.key()}")  # Print the key code for debugging

        if event.key() == Qt.Key_G or event.key() == Qt.Key_Escape:
            self.close()
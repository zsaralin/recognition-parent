from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel, QLineEdit, QPushButton, QCheckBox, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QFont
import config
from backend_communicator import set_camera_control, update_max_frames, update_min_frames, update_min_time_between_frames
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtGui import QIcon

class SliderOverlay(QWidget):
    config_changed = pyqtSignal()  # Signal to notify when config changes
    font_size_changed = pyqtSignal(float)  # Signal to notify when font size changes

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint)
        self.initUI()
        # self.setFocusPolicy(Qt.StrongFocus)  # Ensure the widget can receive key events
        self.setFixedSize(500, 600)  # Set a fixed size for the window with extra width and height
        self.move(10, 10)  # Move the window to the top-left corner of the screen
        self.is_visible = True  # Variable to track if the window is shown
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        # Set the entire widget's background color to white
        self.setStyleSheet("background-color: lightpink;")

    def initUI(self):
        wrapper = QWidget()
        wrapper.setStyleSheet("background-color: lightpink; padding: 5px;")

        main_layout = QVBoxLayout(wrapper)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Increase margins around the main layout

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(wrapper)
        self.layout().setContentsMargins(0, 0, 0, 0)

        font = QFont()
        font.setPointSize(10)  # Reduce font size for all widgets

        # Function to create a label, slider, and input box in a horizontal layout
        def create_slider_group(label_text, slider, input_box):
            layout = QHBoxLayout()
            layout.setSpacing(0)
            layout.setContentsMargins(0, 0, 0, 0)

            label = QLabel(label_text, self)
            label.setFont(font)
            layout.addWidget(label)

            layout.addWidget(slider)
            layout.addWidget(input_box)

            # Create a vertical layout for the up and down buttons
            arrow_button_layout = QVBoxLayout()

            increment_button = QPushButton("▲", self)
            increment_button.setFixedSize(20, 20)
            increment_button.clicked.connect(lambda: self.increment_input(slider))

            decrement_button = QPushButton("▼", self)
            decrement_button.setFixedSize(20, 20)
            decrement_button.clicked.connect(lambda: self.decrement_input(slider))

            # Add buttons to the vertical layout
            arrow_button_layout.addWidget(increment_button)
            arrow_button_layout.addWidget(decrement_button)

            # Add the arrow button layout to the main layout
            layout.addLayout(arrow_button_layout)

            return layout

        # Creating the sliders and input fields as before
        self.min_gif_delay_slider = self.create_slider(1, 100, config.min_gif_delay)
        self.min_gif_delay_input = self.create_input(1, 100, is_double=False)
        self.min_gif_delay_input.setText(str(config.min_gif_delay))

        self.max_gif_delay_slider = self.create_slider(1, 200, config.max_gif_delay)
        self.max_gif_delay_input = self.create_input(1, 200, is_double=False)
        self.max_gif_delay_input.setText(str(config.max_gif_delay))

        self.num_cols_slider = self.create_slider(11, 41, config.num_cols, step=2)
        self.num_cols_input = self.create_input(11, 41, is_double=False, only_odd=True)
        self.num_cols_input.setText(str(config.num_cols))

        self.middle_y_pos_slider = self.create_slider(-10, 10, config.middle_y_pos)
        self.middle_y_pos_input = self.create_input(-10, 10, is_double=False)
        self.middle_y_pos_input.setText(str(config.middle_y_pos))

        self.update_count_slider = self.create_slider(1, 100, config.update_count)
        self.update_count_input = self.create_input(1, 100, is_double=False)
        self.update_count_input.setText(str(config.update_count))

        self.update_delay_slider = self.create_slider(0, 200, config.update_delay)
        self.update_delay_input = self.create_input(0, 200, is_double=False)
        self.update_delay_input.setText(str(config.update_delay))

        self.update_int_slider = self.create_slider(5, 100, config.update_int)
        self.update_int_input = self.create_input(5, 100, is_double=False)
        self.update_int_input.setText(str(config.update_int))

        self.bbox_multiplier_slider = self.create_slider(5, 30, int(config.bbox_multiplier * 10))
        self.bbox_multiplier_input = self.create_input(5, 30, is_double=False)
        self.bbox_multiplier_input.setText(str(int(config.bbox_multiplier * 10)))

        self.font_size_slider = self.create_double_slider(0.1, 3.0, config.font_size, step=0.1)
        self.font_size_input = self.create_input(0.1, 3.0, is_double=True)
        self.font_size_input.setText(str(config.font_size))

        self.auto_exposure_time_slider = self.create_slider(50, 2000, int(config.auto_exposure_time))
        self.auto_exposure_time_input = self.create_input(50, 2000, is_double=False)
        self.auto_exposure_time_input.setText(str(int(config.auto_exposure_time)))

        self.gain_slider = self.create_slider(1, 128, int(config.gain))
        self.gain_input = self.create_input(1, 128, is_double=False)
        self.gain_input.setText(str(int(config.gain)))

        self.jump_threshold_slider = self.create_slider(0, 200, config.jump_threshold)
        self.jump_threshold_input = self.create_input(0, 200, is_double=False)
        self.jump_threshold_input.setText(str(config.jump_threshold))

        self.min_face_size_slider = self.create_slider(0, 200, config.min_face_size)
        self.min_face_size_input = self.create_input(0, 200, is_double=False)
        self.min_face_size_input.setText(str(config.min_face_size))

        self.cell_zoom_factor_slider = self.create_double_slider(0.5, 2.0, config.zoom_factor, step=0.1)
        self.cell_zoom_factor_input = self.create_input(0.5, 2.0, is_double=True)
        self.cell_zoom_factor_input.setText(str(config.zoom_factor))

        self.rotation_angle_slider = self.create_slider(0, 270, config.rotation_angle, step=90)
        self.rotation_angle_input = self.create_input(0, 270, is_double=False)
        self.rotation_angle_input.setText(str(config.rotation_angle))

        self.confidence_score_slider = self.create_double_slider(0.0, 1.0, config.confidence_score, step=0.1)
        self.confidence_score_input = self.create_input(0.0, 1.0, is_double=True)
        self.confidence_score_input.setText(str(config.confidence_score))

        self.move_threshold_slider = self.create_slider(10, 100, config.move_threshold)
        self.move_threshold_input = self.create_input(10, 100, is_double=False)
        self.move_threshold_input.setText(str(config.move_threshold))

        self.min_num_ss_frames_slider = self.create_slider(5, 300, config.min_num_ss_frames)
        self.min_num_ss_frames_input = self.create_input(5, 300, is_double=False)
        self.min_num_ss_frames_input.setText(str(config.min_num_ss_frames))

        self.max_num_rows_ss_frames_slider = self.create_slider(10, 20, config.max_num_rows_ss_frames)
        self.max_num_rows_ss_frames_input = self.create_input(10, 20, is_double=False)
        self.max_num_rows_ss_frames_input.setText(str(config.max_num_rows_ss_frames))

        self.min_time_between_spritesheet_slider = self.create_double_slider(0, 4, config.min_time_between_spritesheet, step=0.1)
        self.min_time_between_spritesheet_input = self.create_input(0, 4, is_double=True)
        self.min_time_between_spritesheet_input.setText(str(config.min_time_between_spritesheet))

        self.create_sprites_checkbox = QCheckBox('Create Sprites', self)
        self.create_sprites_checkbox.setChecked(config.create_sprites)
        self.create_sprites_checkbox.setFont(font)

        self.show_fps_checkbox = QCheckBox('Show FPS', self)
        self.show_fps_checkbox.setChecked(config.show_fps)
        self.show_fps_checkbox.setFont(font)
        self.show_fps_checkbox.stateChanged.connect(self.toggle_fps_display)

        self.auto_update_checkbox = QCheckBox('Auto Update', self)
        self.auto_update_checkbox.setChecked(config.auto_update)
        self.auto_update_checkbox.setFont(font)

        self.show_saved_checkbox = QCheckBox('Show Saved Frame', self)
        self.show_saved_checkbox.setChecked(config.show_saved_frame)
        self.show_saved_checkbox.setFont(font)

        self.mirror_checkbox = QCheckBox('Mirror', self)
        self.mirror_checkbox.setChecked(config.mirror)
        self.mirror_checkbox.setFont(font)

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

        self.auto_exposure_checkbox = QCheckBox('Auto Exposure', self)
        self.auto_exposure_checkbox.setFont(font)
        self.auto_exposure_checkbox.stateChanged.connect(self.toggle_auto_exposure)

        # Manual Exposure Checkbox
        self.manual_exposure_checkbox = QCheckBox('Manual Exposure', self)
        self.manual_exposure_checkbox.setFont(font)
        self.manual_exposure_checkbox.stateChanged.connect(self.toggle_manual_exposure)

        self.auto_exposure_checkbox.stateChanged.connect(self.sync_exposure_checkboxes)
        self.manual_exposure_checkbox.stateChanged.connect(self.sync_exposure_checkboxes)

    # Adding the groups to the main layout
        main_layout.addLayout(create_slider_group('Min GIF Delay', self.min_gif_delay_slider, self.min_gif_delay_input))
        main_layout.addLayout(create_slider_group('Max GIF Delay', self.max_gif_delay_slider, self.max_gif_delay_input))
        main_layout.addLayout(create_slider_group('Num Cols', self.num_cols_slider, self.num_cols_input))
        main_layout.addLayout(create_slider_group('Middle Y Pos', self.middle_y_pos_slider, self.middle_y_pos_input))
        main_layout.addLayout(create_slider_group('Update Count', self.update_count_slider, self.update_count_input))
        main_layout.addLayout(create_slider_group('Update Delay', self.update_delay_slider, self.update_delay_input))
        main_layout.addLayout(create_slider_group('Update Interval', self.update_int_slider, self.update_int_input))
        main_layout.addLayout(create_slider_group('BBox Multiplier', self.bbox_multiplier_slider, self.bbox_multiplier_input))
        main_layout.addLayout(create_slider_group('Font Size', self.font_size_slider, self.font_size_input))
        main_layout.addLayout(create_slider_group('Rotation Angle', self.rotation_angle_slider, self.rotation_angle_input))
        main_layout.addLayout(create_slider_group('Auto Exposure Time', self.auto_exposure_time_slider, self.auto_exposure_time_input))
        main_layout.addLayout(create_slider_group('Gain', self.gain_slider, self.gain_input))
        main_layout.addLayout(create_slider_group('Jump Threshold', self.jump_threshold_slider, self.jump_threshold_input))
        main_layout.addLayout(create_slider_group('Min Face Size', self.min_face_size_slider, self.min_face_size_input))
        main_layout.addLayout(create_slider_group('Min Confidence Score', self.confidence_score_slider, self.confidence_score_input))
        main_layout.addLayout(create_slider_group('Move Threshold', self.move_threshold_slider, self.move_threshold_input))
        main_layout.addLayout(create_slider_group('Min Num Spritesheet Frames', self.min_num_ss_frames_slider, self.min_num_ss_frames_input))
        main_layout.addLayout(create_slider_group('Max Num Rows Spritesheet Frames', self.max_num_rows_ss_frames_slider, self.max_num_rows_ss_frames_input))
        main_layout.addLayout(create_slider_group('Minutes between Spritesheets', self.min_time_between_spritesheet_slider, self.min_time_between_spritesheet_input))

        main_layout.addLayout(create_slider_group('Cell Zoom Factor', self.cell_zoom_factor_slider, self.cell_zoom_factor_input))
        main_layout.addWidget(self.auto_exposure_checkbox)
        main_layout.addWidget(self.manual_exposure_checkbox)

        # Add checkboxes and button directly
        main_layout.addWidget(self.create_sprites_checkbox)
        main_layout.addWidget(self.show_fps_checkbox)
        main_layout.addWidget(self.auto_update_checkbox)
        main_layout.addWidget(self.show_saved_checkbox)
        main_layout.addWidget(self.mirror_checkbox)
        main_layout.addWidget(self.save_button)

        self.setLayout(main_layout)
        self.setWindowTitle('Overlay Controls')
    def toggle_auto_exposure(self, state):
        if state == Qt.Checked:
            set_camera_control('autoExposureMode', 0)  # Auto exposure on

    def toggle_manual_exposure(self, state):
        if state == Qt.Checked:
            set_camera_control('autoExposureMode', 1)  # Manual exposure on

    def sync_exposure_checkboxes(self):
        """Ensure only one exposure mode checkbox is selected at a time."""
        if self.auto_exposure_checkbox.isChecked():
            self.manual_exposure_checkbox.setChecked(False)
        elif self.manual_exposure_checkbox.isChecked():
            self.auto_exposure_checkbox.setChecked(False)

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

    def increment_input(self, slider):
        slider.setValue(slider.value() + slider.singleStep())

    def decrement_input(self, slider):
        slider.setValue(slider.value() - slider.singleStep())

    def toggle_auto_exposure(self, state):
        if state == Qt.Checked:
            set_camera_control('autoExposureMode', 0)  # Auto exposure on
        else:
            set_camera_control('autoExposureMode', 1)  # Auto exposure off

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
                padding: 3px; /* Reduced padding */
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
        elif sender == self.min_gif_delay_slider:
            self.min_gif_delay_input.setText(str(sender.value()))
        elif sender == self.max_gif_delay_slider:
            self.max_gif_delay_input.setText(str(sender.value()))
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
        elif sender == self.cell_zoom_factor_slider:
            self.cell_zoom_factor_input.setText(str(sender.value() / 10.0))
        elif sender == self.move_threshold_slider:
            self.move_threshold_input.setText(str(sender.value()))
        elif sender == self.rotation_angle_slider:
            value = sender.value()
            snapped_value = round(value / 90) * 90
            if value != snapped_value:
                sender.blockSignals(True)
                sender.setValue(snapped_value)
                sender.blockSignals(False)
            self.rotation_angle_input.setText(str(snapped_value))
        elif sender == self.confidence_score_slider:
            self.confidence_score_input.setText(str(sender.value() / 10.0))
        elif sender == self.min_num_ss_frames_slider:
            self.min_num_ss_frames_input.setText(str(sender.value()))
        elif sender == self.max_num_rows_ss_frames_slider:
            self.max_num_rows_ss_frames_input.setText(str(sender.value()))
        elif sender == self.min_time_between_spritesheet_slider:
            self.min_time_between_spritesheet_input.setText(str(sender.value() / 10.0))
        self.config_changed.emit()

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
        elif sender == self.min_gif_delay_input:
            self.min_gif_delay_slider.setValue(int(value))
        elif sender == self.max_gif_delay_input:
            self.max_gif_delay_slider.setValue(int(value))
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
        elif sender == self.cell_zoom_factor_input:
            self.cell_zoom_factor_slider.setValue(int(value * 10))
        elif sender == self.confidence_score_input:
            self.confidence_score_slider.setValue(int(value) * 10)
        elif sender == self.move_threshold_input:
            self.move_threshold_slider.setValue(int(value))
        elif sender == self.rotation_angle_slider:
            value = sender.value()
            snapped_value = round(value / 90) * 90
            if value != snapped_value:
                sender.blockSignals(True)
                sender.setValue(snapped_value)
                sender.blockSignals(False)
            # Explicitly check and handle 0
            if snapped_value == 0:
                snapped_value = 0
            self.rotation_angle_input.setText(str(snapped_value))
        elif sender == self.min_num_ss_frames_input:
            self.min_num_ss_frames_slider.setValue(int(value))
        elif sender == self.max_num_rows_ss_frames_input:
            self.max_num_rows_ss_frames_slider.setValue(int(value))
        elif sender == self.min_time_between_spritesheet_input:
            self.min_time_between_spritesheet_slider.setValue(int(value * 10))
        self.config_changed.emit()

    def toggle_fps_display(self, state):
        config.show_fps = (state == Qt.Checked)  # Update the config immediately

    def save_values_to_config(self):

        new_min_frames = self.min_num_ss_frames_slider.value()
        new_max_rows = self.max_num_rows_ss_frames_slider.value()
        new_min_time = float(self.min_time_between_spritesheet_input.text())  # Assuming the input is properly formatted as float

        # Check if values have changed and update if they have
        if new_min_frames != config.min_num_ss_frames:
            update_min_frames(new_min_frames)

        if new_max_rows != config.max_num_rows_ss_frames:
            update_max_frames(new_max_rows)

        if new_min_time != config.min_time_between_spritesheet:
            update_min_time_between_frames(new_min_time)

        config.min_gif_delay = self.min_gif_delay_slider.value()
        config.max_gif_delay = self.max_gif_delay_slider.value()
        config.num_cols = self.num_cols_slider.value()
        config.middle_y_pos = self.middle_y_pos_slider.value()
        config.update_count = self.update_count_slider.value()
        config.update_delay = self.update_delay_slider.value()
        config.update_int = self.update_int_slider.value()
        config.bbox_multiplier = self.bbox_multiplier_slider.value() / 10.0
        config.font_size = self.font_size_slider.value() / 10.0
        config.rotation_angle = self.rotation_angle_slider.value()
        config.create_sprites = self.create_sprites_checkbox.isChecked()
        config.show_fps = self.show_fps_checkbox.isChecked()
        config.auto_update = self.auto_update_checkbox.isChecked()
        config.show_saved_frame = self.show_saved_checkbox.isChecked()
        config.mirror = self.mirror_checkbox.isChecked()
        config.auto_exposure_time = self.auto_exposure_time_slider.value()
        config.gain = self.gain_slider.value()
        config.jump_threshold = self.jump_threshold_slider.value()
        config.move_threshold = self.move_threshold_slider.value()
        config.min_num_ss_frames = self.min_num_ss_frames_slider.value()
        config.max_num_rows_ss_frames = self.max_num_rows_ss_frames_slider.value()
        config.min_time_between_spritesheet = self.min_time_between_spritesheet_slider.value() / 10.0

        config.min_face_size = self.min_face_size_slider.value()
        config.zoom_factor = self.cell_zoom_factor_slider.value() / 10.0  # Save the zoom factor
        config.confidence_score = self.confidence_score_slider.value() / 10.0
        config.auto_exposure = self.auto_exposure_checkbox.isChecked()

        # Retain the demo value from the previous configuration
        demo_value = getattr(config, 'demo', False)
        config.demo = demo_value

        # Save the updated config to file
        with open('config.py', 'w') as config_file:
            config_file.write(f"min_gif_delay = {config.min_gif_delay}\n")
            config_file.write(f"max_gif_delay = {config.max_gif_delay}\n")
            config_file.write(f"num_cols = {config.num_cols}\n")
            config_file.write(f"middle_y_pos = {config.middle_y_pos}\n")
            config_file.write(f"update_count = {config.update_count}\n")
            config_file.write(f"update_delay = {config.update_delay}\n")
            config_file.write(f"update_int = {config.update_int}\n")
            config_file.write(f"bbox_multiplier = {config.bbox_multiplier}\n")
            config_file.write(f"font_size = {config.font_size}\n")
            config_file.write(f"rotation_angle = {config.rotation_angle}\n")
            config_file.write(f"create_sprites = {config.create_sprites}\n")
            config_file.write(f"show_fps = {config.show_fps}\n")
            config_file.write(f"auto_update = {config.auto_update}\n")
            config_file.write(f"show_saved_frame = {config.show_saved_frame}\n")
            config_file.write(f"gain = {config.gain}\n")
            config_file.write(f"jump_threshold = {config.jump_threshold}\n")
            config_file.write(f"min_face_size = {config.min_face_size}\n")
            config_file.write(f"zoom_factor = {config.zoom_factor}\n")
            config_file.write(f"confidence_score = {config.confidence_score}\n")
            config_file.write(f"mirror = {config.mirror}\n")
            config_file.write(f"demo = {config.demo}\n")  # Write the demo config value
            config_file.write(f"move_threshold = {config.move_threshold}\n")
            config_file.write(f"min_num_ss_frames = {config.min_num_ss_frames}\n")
            config_file.write(f"max_num_rows_ss_frames = {config.max_num_rows_ss_frames}\n")
            config_file.write(f"min_time_between_spritesheet = {config.min_time_between_spritesheet}\n")

        # Emit signal to update the config
        self.config_changed.emit()

    def keyPressEvent(self, event):
        if self.parent():
            self.parent().keyPressEvent(event)
        super().keyPressEvent(event)

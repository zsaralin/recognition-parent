from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIntValidator
import config

class SliderOverlay(QWidget):
    config_changed = pyqtSignal()  # Signal to notify when config changes

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.gif_speed_label = QLabel('GIF Speed', self)
        self.gif_speed_slider = self.create_slider(1, 100, config.gif_speed)
        self.gif_speed_input = self.create_input(1, 100)
        self.gif_speed_input.setText(str(config.gif_speed))

        self.num_cols_label = QLabel('Num Cols', self)
        self.num_cols_slider = self.create_slider(11, 41, config.num_cols, step=2)  # Ensure slider steps are odd
        self.num_cols_input = self.create_input(11, 41, only_odd=True)  # Enforce odd numbers in input
        self.num_cols_input.setText(str(config.num_cols))

        self.middle_y_pos_label = QLabel('Middle Y Pos', self)
        self.middle_y_pos_slider = self.create_slider(-10, 10, config.middle_y_pos)
        self.middle_y_pos_input = self.create_input(-10, 10)
        self.middle_y_pos_input.setText(str(config.middle_y_pos))

        self.update_count_label = QLabel('Update Count', self)
        self.update_count_slider = self.create_slider(1, 100, config.update_count)
        self.update_count_input = self.create_input(1, 100)
        self.update_count_input.setText(str(config.update_count))

        self.update_delay_label = QLabel('Update Delay', self)
        self.update_delay_slider = self.create_slider(0, 200, config.update_delay)
        self.update_delay_input = self.create_input(0, 200)
        self.update_delay_input.setText(str(config.update_delay))

        self.bbox_multiplier_label = QLabel('BBox Multiplier', self)
        self.bbox_multiplier_slider = self.create_slider(5, 30, int(config.bbox_multiplier * 10))
        self.bbox_multiplier_input = self.create_input(5, 30)
        self.bbox_multiplier_input.setText(str(int(config.bbox_multiplier * 10)))

        self.save_button = QPushButton('Save', self)
        self.save_button.clicked.connect(self.save_values_to_config)

        layout.addWidget(self.gif_speed_label)
        layout.addWidget(self.gif_speed_slider)
        layout.addWidget(self.gif_speed_input)

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

        layout.addWidget(self.bbox_multiplier_label)
        layout.addWidget(self.bbox_multiplier_slider)
        layout.addWidget(self.bbox_multiplier_input)

        layout.addWidget(self.save_button)

        self.setLayout(layout)
        self.setWindowTitle('Overlay Controls')
        self.setGeometry(100, 100, 300, 400)

    def create_slider(self, min_value, max_value, default_value=None, step=1):
        slider = QSlider(Qt.Horizontal, self)
        slider.setRange(min_value, max_value)
        if default_value is not None:
            slider.setValue(default_value)
        slider.setSingleStep(step)
        slider.valueChanged.connect(self.update_value_from_slider)
        return slider

    def create_input(self, min_value, max_value, only_odd=False):
        input_box = QLineEdit(self)
        validator = QIntValidator(min_value, max_value)
        input_box.setValidator(validator)
        input_box.returnPressed.connect(self.update_value_from_input)
        input_box.only_odd = only_odd  # Custom attribute to enforce odd numbers
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
        elif sender == self.gif_speed_slider:
            self.gif_speed_input.setText(str(sender.value()))
        elif sender == self.update_count_slider:
            self.update_count_input.setText(str(sender.value()))
        elif sender == self.update_delay_slider:
            self.update_delay_input.setText(str(sender.value()))
        elif sender == self.middle_y_pos_slider:
            self.middle_y_pos_input.setText(str(sender.value()))
        elif sender == self.bbox_multiplier_slider:
            self.bbox_multiplier_input.setText(str(sender.value() / 10))

    def update_value_from_input(self):
        sender = self.sender()
        value = int(sender.text())
        if sender == self.num_cols_input:
            # Ensure the value is odd
            if value % 2 == 0:
                value += 1 if value < sender.validator().top() else -1
            self.num_cols_slider.setValue(value)
        elif sender == self.gif_speed_input:
            self.gif_speed_slider.setValue(value)
        elif sender == self.update_count_input:
            self.update_count_slider.setValue(value)
        elif sender == self.update_delay_input:
            self.update_delay_slider.setValue(value)
        elif sender == self.middle_y_pos_input:
            self.middle_y_pos_slider.setValue(value)
        elif sender == self.bbox_multiplier_input:
            self.bbox_multiplier_slider.setValue(int(value * 10))

    def save_values_to_config(self):
        config.gif_speed = self.gif_speed_slider.value()
        config.num_cols = self.num_cols_slider.value()
        config.middle_y_pos = self.middle_y_pos_slider.value()
        config.update_count = self.update_count_slider.value()
        config.update_delay = self.update_delay_slider.value()
        config.bbox_multiplier = self.bbox_multiplier_slider.value() / 10.0

        # Save the updated config to file
        with open('config.py', 'w') as config_file:
            config_file.write(f"gif_speed = {config.gif_speed}\n")
            config_file.write(f"num_cols = {config.num_cols}\n")
            config_file.write(f"middle_y_pos = {config.middle_y_pos}\n")
            config_file.write(f"update_count = {config.update_count}\n")
            config_file.write(f"update_delay = {config.update_delay}\n")
            config_file.write(f"bbox_multiplier = {config.bbox_multiplier}\n")

        # Emit signal to update the config, excluding middle_y_pos and num_cols
        self.config_changed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_G or event.key() == Qt.Key_Escape:
            self.close()

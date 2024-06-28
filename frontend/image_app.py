import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QGridLayout, QWidget, QVBoxLayout, QSpacerItem, QSizePolicy, QShortcut
from PyQt5.QtGui import QKeySequence, QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
import config
from gui import SliderOverlay
from text_overlay import add_text_overlay
from video_processor import VideoProcessor
from image_loader import ImageLoader
from backend_communicator import send_snapshot_to_server
from new_faces import set_curr_face, update_face_detection
from logger_setup import logger

class ImageApp(QWidget):
    def __init__(self, update_count=config.update_count):
        super().__init__()
        print("Initializing ImageApp.")
        self.sprites = []
        self.sprite_indices = []
        self.animating_labels = set()
        self.image_loader_thread = None
        self.image_loader_running = False  # Flag to indicate if the image loader is running
        self.middle_y_pos = config.middle_y_pos  # Use the middle_y_pos from config
        self.initUI()
        self.update_count = update_count  # Number of images to update per interval

        # Initialize indices for most and least similar
        self.most_similar_indices = []
        self.least_similar_indices = []
        self.most_similar_sprite_index = 0
        self.least_similar_sprite_index = 0

        # Initialize lists to store most and least similar images
        self.most_similar = []
        self.least_similar = []

        # Initialize the VideoProcessor
        self.video_processor = VideoProcessor(square_size=self.square_size * 3, callback=self.load_images)
        self.video_processor.frame_ready.connect(self.update_video_label)
        print("Starting VideoProcessor in ImageApp.")
        self.video_processor.start()

        # Set up a timer to update sprites
        self.sprite_timer = QTimer(self)
        self.sprite_timer.timeout.connect(self.update_sprites)
        self.sprite_timer.start(config.gif_speed)  # Use the delay from config

    def initUI(self):
        print("Setting up UI.")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setWindowTitle('Image Display App')
        self.overlay = None

        screen_sizes = [(screen.size().width(), screen.size().height()) for screen in QApplication.screens()]
        largest_screen_width, largest_screen_height = max(screen_sizes, key=lambda s: s[0] * s[1])
        print(f"Largest screen size: width={largest_screen_width}, height={largest_screen_height}")

        window_width = largest_screen_width // 2
        window_height = largest_screen_height
        self.setFixedSize(window_width, window_height)
        print(f"Window dimensions set: width={window_width}, height={window_height}")

        self.num_cols = config.num_cols
        self.square_size = window_width // self.num_cols
        print(f"Number of columns: {self.num_cols}, square size: {self.square_size}")

        self.num_rows = window_height // self.square_size
        print(f"Number of rows: {self.num_rows}")

        config.num_rows = self.num_rows

        config.num_vids = self.num_rows * self.num_cols
        print(f"Number of videos: {config.num_vids}")

        grid_widget = QWidget()
        self.grid_layout = QGridLayout()  # Store the grid layout as an instance variable
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_widget.setLayout(self.grid_layout)
        print("Grid layout created")

        spacer_top = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        spacer_bottom = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(spacer_top)
        self.layout.addWidget(grid_widget)
        self.layout.addItem(spacer_bottom)
        print("Grid layout added to main layout with spacers")

        self.image_labels = []
        for row in range(self.num_rows):
            for col in range(self.num_cols):
                label = QLabel(self)
                label.setFixedSize(self.square_size, self.square_size)
                label.setStyleSheet("background-color: black; border: 1px solid black;")
                label.setAlignment(Qt.AlignCenter)
                self.grid_layout.addWidget(label, row, col)
                self.image_labels.append(label)
                self.sprites.append([])  # Initialize empty list for each label
                self.sprite_indices.append(0)  # Initialize sprite index for each label
        print("Image labels created and added to grid layout")

        self.create_center_labels()

        self.show()
        print("Main window displayed")

        self.shortcut = QShortcut(QKeySequence("Escape"), self)
        self.shortcut.activated.connect(self.close)
        print("Escape shortcut set up")

    def create_center_labels(self):
        center_row = self.num_rows // 2 + self.middle_y_pos
        center_col = self.num_cols // 2

        video_label_width = self.square_size * 3
        video_label_height = self.square_size * 3

        # Create video label in the center
        self.video_label = QLabel(self)
        self.video_label.setFixedSize(video_label_width, video_label_height)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("border: 1px solid black; margin: 1px;")
        self.grid_layout.addWidget(self.video_label, center_row - 1, center_col - 1, 3, 3)
        print("Video label created and added to grid layout")

        # Create least similar image label next to the video (left side)
        self.least_similar_label = QLabel(self)
        self.least_similar_label.setFixedSize(video_label_width, video_label_height)
        self.least_similar_label.setAlignment(Qt.AlignCenter)
        self.least_similar_label.setStyleSheet("border: 1px solid black; margin: 1px;")
        self.grid_layout.addWidget(self.least_similar_label, center_row - 1, center_col - 4, 3, 3)
        print("Least similar label created and added to grid layout")

        # Create most similar image label next to the video (right side)
        self.most_similar_label = QLabel(self)
        self.most_similar_label.setFixedSize(video_label_width, video_label_height)
        self.most_similar_label.setAlignment(Qt.AlignCenter)
        self.most_similar_label.setStyleSheet("border: 1px solid black; margin: 1px;")
        self.grid_layout.addWidget(self.most_similar_label, center_row - 1, center_col + 2, 3, 3)
        print("Most similar label created and added to grid layout")

    def closeEvent(self, event):
        try:
            print("Close event triggered")
            if hasattr(self, 'video_processor'):
                print("Stopping VideoProcessor.")
                self.video_processor.stop()
                self.video_processor.wait()  # Ensure the thread has finished
            if self.image_loader_thread is not None:
                self.image_loader_thread.quit()
                self.image_loader_thread.wait()
            if self.overlay is not None:  # Close the overlay if it is open
                self.overlay.close()
            event.accept()
            print("Close event accepted")
        except Exception as e:
            print(f"Exception during close event: {e}")
            logger.exception("Exception during close event")
            event.ignore()  # Ignore the close event if there's an exception

    def handle_sprite_loaded(self, label_index, sprites):
        self.sprites[label_index] = sprites

    def handle_loading_completed(self):
        print("All images have been loaded.")
        logger.info("All images have been loaded.")
        self.image_loader_running = False  # Reset the flag after loading is completed

    def update_sprites(self):
        for i in range(len(self.image_labels)):
            if i < len(self.sprites) and self.sprites[i]:  # Safeguard to ensure valid index and non-empty sprites
                if self.sprite_indices[i] < len(self.sprites[i]):  # Ensure sprite index is within range
                    self.image_labels[i].setPixmap(self.cv2_to_qpixmap(self.sprites[i][self.sprite_indices[i]], self.square_size, self.square_size))
                    self.sprite_indices[i] = (self.sprite_indices[i] + 1) % len(self.sprites[i])

        # Rotate images for most similar label
        if self.most_similar_indices:
            most_similar_index = self.most_similar_indices[0]
            if most_similar_index < len(self.sprites) and self.sprites[most_similar_index]:
                sprite = self.sprites[most_similar_index][self.most_similar_sprite_index]
                self.most_similar_label.setPixmap(self.cv2_to_qpixmap(sprite, self.square_size * 3, self.square_size * 3, add_overlay=True, overlay_text="Closest Match"))
                self.most_similar_sprite_index = (self.most_similar_sprite_index + 1) % len(self.sprites[most_similar_index])

        # Rotate images for least similar label
        if self.least_similar_indices:
            least_similar_index = self.least_similar_indices[0]
            if least_similar_index < len(self.sprites) and self.sprites[least_similar_index]:
                sprite = self.sprites[least_similar_index][self.least_similar_sprite_index]
                self.least_similar_label.setPixmap(self.cv2_to_qpixmap(sprite, self.square_size * 3, self.square_size * 3, add_overlay=True, overlay_text="Farthest Match"))
                self.least_similar_sprite_index = (self.least_similar_sprite_index + 1) % len(self.sprites[least_similar_index])

    def update_video_label(self, q_img):
        self.video_label.setPixmap(QPixmap.fromImage(q_img))

    def cv2_to_qpixmap(self, cv_img, target_width, target_height, add_overlay=False, overlay_text=""):
        if not isinstance(cv_img, np.ndarray):
            print("Invalid image format:", type(cv_img))
            return QPixmap()
        cv_img_resized = cv2.resize(cv_img, (target_width, target_height), interpolation=cv2.INTER_AREA)
        height, width, channel = cv_img_resized.shape
        bytes_per_line = channel * width
        cv_img_rgb = cv2.cvtColor(cv_img_resized, cv2.COLOR_BGR2RGB)

        if add_overlay:
            add_text_overlay(cv_img_rgb, overlay_text)  # Add custom overlay text

        q_img = QImage(cv_img_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(q_img)

    def load_images(self, most_similar, least_similar):
        if self.image_loader_running:
            print("Image loader is already running. Skipping new load request.")
            return

        self.image_loader_running = True
        if self.image_loader_thread and self.image_loader_thread.isRunning():
            print("Image loader thread is already running, stopping it first.")
            self.image_loader_thread.quit()
            self.image_loader_thread.wait()

        # Set the most similar and least similar images
        self.most_similar = most_similar
        self.least_similar = least_similar

        # Initialize and start the ImageLoader thread
        self.image_loader_thread = QThread()
        self.image_loader = ImageLoader(self.middle_y_pos)
        self.image_loader.moveToThread(self.image_loader_thread)
        self.image_loader.set_data(most_similar, least_similar)
        self.image_loader.all_sprites_loaded.connect(self.handle_all_sprites_loaded)  # Connect new signal
        self.image_loader.loading_completed.connect(self.handle_loading_completed)
        self.image_loader_thread.started.connect(self.image_loader.run)
        self.image_loader_thread.start()

    def handle_all_sprites_loaded(self, all_sprites, most_similar_indices, least_similar_indices):
        self.all_sprites = all_sprites
        self.most_similar_indices = most_similar_indices  # Exclude index 0
        self.least_similar_indices = least_similar_indices  # Exclude index 0
        self.current_most_index = 0
        self.current_least_index = 0
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_next_sprites)
        self.update_timer.start(config.update_delay)  # Use delay from config
        print("Timer started for updating sprites.")
        logger.info("Timer started for updating sprites.")

        # Initialize sprite indices for most and least similar labels
        self.most_similar_sprite_index = 0
        self.least_similar_sprite_index = 0

    def update_next_sprites(self):
        updates_done = 0
        total_updates = min(
            self.update_count,
            len(self.most_similar_indices) - self.current_most_index +
            len(self.least_similar_indices) - self.current_least_index
        )

        while updates_done < total_updates:
            if self.current_most_index < len(self.most_similar_indices):
                grid_index = self.most_similar_indices[self.current_most_index]
                sprites = self.all_sprites[grid_index]
                if grid_index < len(self.sprites):  # Safeguard to ensure valid index
                    self.sprites[grid_index] = sprites
                    if sprites:
                        self.image_labels[grid_index].setPixmap(self.cv2_to_qpixmap(sprites[0], self.square_size, self.square_size))
                self.current_most_index += 1
                updates_done += 1

            if updates_done >= total_updates:
                break

            if self.current_least_index < len(self.least_similar_indices):
                grid_index = self.least_similar_indices[self.current_least_index]
                sprites = self.all_sprites[grid_index]
                if grid_index < len(self.sprites):  # Safeguard to ensure valid index
                    self.sprites[grid_index] = sprites
                    if sprites:
                        self.image_labels[grid_index].setPixmap(self.cv2_to_qpixmap(sprites[0], self.square_size, self.square_size))
                self.current_least_index += 1
                updates_done += 1

        if self.current_most_index >= len(self.most_similar_indices) and self.current_least_index >= len(self.least_similar_indices):
            self.update_timer.stop()
            print("All sprites have been batch loaded into the grid.")
            logger.info("All sprites have been batch loaded into the grid.")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_G:
            if self.overlay is None:
                self.overlay = SliderOverlay()
                self.overlay.show()
            else:
                self.overlay.close()
                self.overlay = None
        elif event.key() == Qt.Key_Escape:
            if self.overlay is not None:
                self.overlay.close()
            self.close()
            self.video_processor.stop()
            self.video_processor.wait()
            if hasattr(self, 'image_loader_thread') and self.image_loader_thread.isRunning():
                self.image_loader_thread.quit()
                self.image_loader_thread.wait()
            QApplication.quit()

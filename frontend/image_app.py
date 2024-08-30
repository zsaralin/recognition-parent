import sys
import math
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QShortcut
from PyQt5.QtGui import QKeySequence, QPixmap, QImage, QPainter
from PyQt5.QtCore import Qt, QTimer, QRectF, QRect
from backend_communicator import get_random_images
import config
from gui import SliderOverlay
from text_overlay import update_font_size
from video_processor import VideoProcessor
from logger_setup import logger
from new_faces import NewFaces
from sprite_manager import SpriteManager

class ImageApp(QWidget):
    def __init__(self, update_count=config.update_count, sprites_per_update=25, update_batch_size=80, batch_size=200):
        super().__init__()
        self.sprites = []
        self.sprite_indices = []
        self.animating_cells = set()
        self.middle_y_pos = config.middle_y_pos
        self.initUI()
        self.update_count = update_count
        self.sprites_per_update = sprites_per_update
        self.update_batch_size = update_batch_size
        self.batch_size = batch_size

        self.most_similar_indices = []
        self.least_similar_indices = []
        self.current_most_index = 0
        self.current_least_index = 0

        self.new_faces = NewFaces()

        self.video_processor = VideoProcessor(self.new_faces, square_size=int(self.square_size *3), callback=self.load_sprites)
        self.video_processor.frame_ready.connect(lambda pixmap: self.video_cell.setPixmap(pixmap))
        self.video_processor.start()

        self.overlay_visible = [False]
        self.overlay = SliderOverlay(self)
        self.overlay.font_size_changed.connect(update_font_size)

        self.sprite_manager = SpriteManager(len(self.grid_cells), self.square_size, self.middle_y_pos)
        self.sprite_manager.sprites_updated.connect(self.update_sprite_cells)
        if config.version == 0:
            self.sprite_manager.most_similar_updated.connect(lambda pixmap: self.most_similar_cell.setPixmap(pixmap))
            self.sprite_manager.least_similar_updated.connect(lambda pixmap: self.least_similar_cell.setPixmap(pixmap))

        self.overlay.font_size_changed.connect(self.video_processor.update_text_overlay)
        self.overlay.font_size_changed.connect(self.sprite_manager.update_static_overlays)
        # Set positions for cells only once
        self.set_cell_positions()
        self.load_random_images()

    def load_random_images(self):
        # Assume `get_random_images` is implemented and fetches `numVids` random images
        num_vids = self.num_rows * config.num_cols  # Same as the number of grid cells
        most_similar, least_similar, success = get_random_images(num_vids)
        if success:
            # Simulate loading of initial random images
            self.sprite_manager.load_sprites(most_similar, least_similar)
        else:
            logger.error("Failed to fetch initial random images.")
    def initUI(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setWindowTitle('Image Display App')
        self.setStyleSheet("background-color: black; border: none; margin: 0; padding: 0;")

        # Get the list of screens
        screens = QApplication.screens()

        # Identify the secondary screen (on the left)
        if len(screens) > 1:
            secondary_screen = screens[1]
        else:
            secondary_screen = screens[0]

        # Get the size of the secondary screen
        screen_size = secondary_screen.size()
        screen_geometry = secondary_screen.geometry()
        largest_screen_width = screen_size.width()
        largest_screen_height = screen_size.height()

        window_width = largest_screen_width // 2 if config.demo else largest_screen_width
        window_height = largest_screen_height

        self.num_cols = config.num_cols
        self.square_size = round(window_width / self.num_cols)

        self.num_rows = math.floor(window_height / self.square_size)

        config.num_rows = self.num_rows
        config.num_vids = self.num_rows * self.num_cols

        self.grid_cells = []
        for row in range(self.num_rows):
            for col in range(self.num_cols):
                cell = QLabel(self)
                cell.setFixedSize(int(self.square_size), int(self.square_size))
                cell.setStyleSheet("background-color: black; border: none; margin: 0; padding: 0;")
                cell.setAlignment(Qt.AlignCenter)
                self.grid_cells.append(cell)
                self.sprites.append([])
                self.sprite_indices.append(0)

        self.create_center_cells()

        # Move the window to the secondary screen
        self.move(screen_geometry.left(), screen_geometry.top())

        if not config.demo:
            self.setWindowFlags(Qt.FramelessWindowHint)
            self.showFullScreen()
        else:
            # self.setFixedSize(int(window_width), int(window_height))
            # self.show()
            self.setWindowFlags(Qt.FramelessWindowHint)
            self.showFullScreen()

        QApplication.setOverrideCursor(Qt.BlankCursor)

        self.shortcut = QShortcut(QKeySequence("Escape"), self)
        self.shortcut.activated.connect(self.close_app)

    def create_center_cells(self):
        if config.version == 0:
            video_cell_width = int(self.square_size * 3)
            video_cell_height = int(self.square_size * 3)
        else:
            video_cell_width = int(self.square_size)
            video_cell_height = int(self.square_size)

        self.video_cell = QLabel(self)
        self.video_cell.setFixedSize(video_cell_width, video_cell_height)
        self.video_cell.setAlignment(Qt.AlignCenter)
        self.video_cell.setStyleSheet("border: none; margin: 0;")
        self.grid_cells.append(self.video_cell)

        if config.version == 0:
            self.least_similar_cell = QLabel(self)
            self.least_similar_cell.setFixedSize(video_cell_width, video_cell_height)
            self.least_similar_cell.setAlignment(Qt.AlignCenter)
            self.least_similar_cell.setStyleSheet("border: none; margin: 0;")
            self.grid_cells.append(self.least_similar_cell)

            self.most_similar_cell = QLabel(self)
            self.most_similar_cell.setFixedSize(video_cell_width, video_cell_height)
            self.most_similar_cell.setAlignment(Qt.AlignCenter)
            self.most_similar_cell.setStyleSheet("border: none; margin: 0;")
            self.grid_cells.append(self.most_similar_cell)

    def set_cell_positions(self):
        vertical_offset = (self.height() - (self.num_rows * self.square_size)) // 2
        horizontal_offset = (self.width() - (self.num_cols * self.square_size)) // 2

        for index, cell in enumerate(self.grid_cells):
            if config.version == 0 and cell in [self.video_cell, getattr(self, 'least_similar_cell', None), getattr(self, 'most_similar_cell', None)]:
                continue
            row = index // self.num_cols
            col = index % self.num_cols
            x = col * self.square_size + horizontal_offset
            y = row * self.square_size + vertical_offset
            cell.move(int(x), int(y))

        center_row = self.num_rows // 2 + self.middle_y_pos
        center_col = self.num_cols // 2


        if config.version == 0:
            self.video_cell.move(
                int((center_col - 1) * self.square_size + horizontal_offset),
                int((center_row - 1) * self.square_size + vertical_offset)
            )
            self.least_similar_cell.move(
                int((center_col - 4) * self.square_size + horizontal_offset),
                int((center_row - 1) * self.square_size + vertical_offset)
            )

            self.most_similar_cell.move(
                int((center_col + 2) * self.square_size + horizontal_offset),
                int((center_row - 1) * self.square_size + vertical_offset)
            )
        else:
            center_row = (self.num_rows // 2) + self.middle_y_pos
            center_col = self.num_cols // 2

            # Center the video cell
            self.video_cell.move(
                int((center_col - (self.video_cell.width() // self.square_size) // 2) * self.square_size + horizontal_offset),
                int((center_row - (self.video_cell.height() // self.square_size) // 2) * self.square_size + vertical_offset)
            )
    def closeEvent(self, event):
        self.new_faces.stop_all_threads()
        event.accept()

    def update_sprite_cells(self):

        for index, cell in enumerate(self.grid_cells[:-3]):  # Exclude special cells
            sprite = self.sprite_manager.get_sprite(index)
            if sprite:
                cell.setPixmap(sprite)
            else:
                cell.clear()  # Clear the cell if no sprite is available

    def load_sprites(self, most_similar, least_similar):
        self.sprite_manager.load_sprites(most_similar, least_similar)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_G:
            if self.overlay.isVisible():
                self.overlay.close()  # Hide the overlay if it's visible
                QApplication.setOverrideCursor(Qt.BlankCursor)  # Hide the cursor if overlay is hidden
            else:
                self.overlay.show()  # Show the overlay if it's not visible
                QApplication.restoreOverrideCursor()  # Restore the cursor when overlay is shown
        elif event.key() == Qt.Key_Escape:
            if self.overlay.isVisible():
                self.overlay.close()  # Hide the overlay if pressing escape
                QApplication.setOverrideCursor(Qt.BlankCursor)
            self.close_app()  # Close the application whether the overlay is visible or not

    def close_app(self):
        if hasattr(self, 'video_processor') and self.video_processor is not None:
            self.video_processor.stop()
            if self.video_processor.isRunning():
                logger.warning("Video processor did not stop gracefully. Terminating...")
                self.video_processor.terminate()
        self.new_faces.stop_all_threads()
        QApplication.quit()
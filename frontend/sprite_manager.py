import cv2
import numpy as np
from PyQt5.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QPainter
import config
from text_overlay import add_text_overlay
from logger_setup import logger
from sprite_arranger import SpriteArranger

class SpriteManager(QObject):
    sprites_updated = pyqtSignal()
    most_similar_updated = pyqtSignal(QPixmap)
    least_similar_updated = pyqtSignal(QPixmap)

    def __init__(self, num_labels, square_size, middle_y_pos):
        super().__init__()
        self.sprites = [[] for _ in range(num_labels)]
        self.sprite_indices = [0] * num_labels
        self.sprite_arranger_running = False
        self.middle_y_pos = middle_y_pos
        self.square_size = square_size
        self.batch_size = 50

        self.high_res_most_similar_sprites = []
        self.high_res_least_similar_sprites = []

        self.is_updating_sprites = False
        self.current_most_index = 0
        self.current_least_index = 0
        self.most_similar_indices = []
        self.least_similar_indices = []

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_sprites)
        self.update_timer.start(config.gif_delay)

        self.most_similar_timer = QTimer()
        self.most_similar_timer.timeout.connect(self.update_most_similar)
        self.most_similar_timer.start(config.gif_delay)

        self.least_similar_timer = QTimer()
        self.least_similar_timer.timeout.connect(self.update_least_similar)
        self.least_similar_timer.start(config.gif_delay)

        # Pre-create the static overlays
        self.static_most_similar_overlay = self.preprocess_overlay_text("Closest Match")
        self.static_least_similar_overlay = self.preprocess_overlay_text("Farthest Match")

    def load_sprites(self, most_similar, least_similar):
        if self.sprite_arranger_running:
            return

        self.sprite_arranger_running = True
        self.most_similar = most_similar
        self.least_similar = least_similar

        self.sprite_arranger = SpriteArranger(self.middle_y_pos)
        self.sprite_arranger.set_data(most_similar, least_similar)
        self.sprite_arranger.sprites_arranged.connect(self.handle_all_sprites_loaded)
        self.sprite_arranger.arrangement_completed.connect(self.handle_arrangement_completed)
        self.sprite_arranger.arrange_sprites()

    def handle_all_sprites_loaded(self, all_sprites, most_similar_indices, least_similar_indices):
        self.all_sprites = all_sprites
        self.most_similar_indices = most_similar_indices
        self.least_similar_indices = least_similar_indices
        self.current_most_index = 0
        self.current_least_index = 0

        self.preprocess_high_res_sprites()
        self.update_next_sprites()

    def handle_arrangement_completed(self):
        logger.info("All sprites have been arranged.")
        self.sprite_arranger_running = False

    def preprocess_high_res_sprites(self):
        self.high_res_most_similar_sprites.clear()
        self.high_res_least_similar_sprites.clear()

        if self.most_similar_indices:
            most_similar_index = self.most_similar_indices[0]
            if most_similar_index < len(self.sprites) and self.sprites[most_similar_index]:
                for sprite in self.sprites[most_similar_index]:
                    high_res_sprite = self.preprocess_sprite(sprite)
                    high_res_sprite = self.apply_static_overlay(high_res_sprite, self.static_most_similar_overlay)
                    self.high_res_most_similar_sprites.append(high_res_sprite)

        if self.least_similar_indices:
            least_similar_index = self.least_similar_indices[0]
            if least_similar_index < len(self.sprites) and self.sprites[least_similar_index]:
                for sprite in self.sprites[least_similar_index]:
                    high_res_sprite = self.preprocess_sprite(sprite)
                    high_res_sprite = self.apply_static_overlay(high_res_sprite, self.static_least_similar_overlay)
                    self.high_res_least_similar_sprites.append(high_res_sprite)

        self.most_similar_sprite_index = 0
        self.least_similar_sprite_index = 0

    def preprocess_sprite(self, sprite):
        qimage = sprite.toImage()
        resized_qimage = qimage.scaled(
            qimage.width() * 3,
            qimage.height() * 3,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation
        )
        return QPixmap.fromImage(resized_qimage)

    def preprocess_overlay_text(self, overlay_text):
        # Create a blank image
        blank_image = np.zeros((int(self.square_size * 3), int(self.square_size * 3), 4), dtype=np.uint8)

        # Add the text overlay using the function provided
        overlay_image = add_text_overlay(blank_image, text=overlay_text)

        # Convert back to QPixmap
        return QPixmap.fromImage(QImage(overlay_image.data, overlay_image.shape[1], overlay_image.shape[0], QImage.Format_RGBA8888))

    def update_sprites(self):
        if self.is_updating_sprites:
            return

        for index in range(len(self.sprites) - 3):  # Exclude special labels
            if self.sprites[index]:
                self.sprite_indices[index] = (self.sprite_indices[index] + 1) % len(self.sprites[index])

        self.sprites_updated.emit()

        if self.current_most_index < len(self.most_similar_indices) or self.current_least_index < len(self.least_similar_indices):
            QTimer.singleShot(config.update_delay, self.update_next_sprites)
        else:
            logger.info("All sprites have been batch loaded into the grid.")
            self.is_updating_sprites = False

    def update_most_similar(self):
        if self.high_res_most_similar_sprites:
            sprite = self.high_res_most_similar_sprites[self.most_similar_sprite_index]
            self.most_similar_updated.emit(sprite)
            self.most_similar_sprite_index = (self.most_similar_sprite_index + 1) % len(self.high_res_most_similar_sprites)

    def update_least_similar(self):
        if self.high_res_least_similar_sprites:
            sprite = self.high_res_least_similar_sprites[self.least_similar_sprite_index]
            self.least_similar_updated.emit(sprite)
            self.least_similar_sprite_index = (self.least_similar_sprite_index + 1) % len(self.high_res_least_similar_sprites)

    def apply_static_overlay(self, sprite, overlay):
        painter = QPainter(sprite)
        painter.drawPixmap(0, 0, overlay)
        painter.end()
        return sprite

    def update_next_sprites(self):
        self.is_updating_sprites = True
        updates_in_batch = min(
            self.batch_size,
            (len(self.most_similar_indices) - self.current_most_index) + (len(self.least_similar_indices) - self.current_least_index)
        )
        updates_done = 0

        while updates_done < updates_in_batch:
            if self.current_most_index < len(self.most_similar_indices):
                grid_index = self.most_similar_indices[self.current_most_index]
                if grid_index < len(self.sprites):
                    sprites = self.all_sprites[grid_index]
                    if sprites:
                        self.sprites[grid_index] = sprites
                self.current_most_index += 1
                updates_done += 1

            if updates_done >= updates_in_batch:
                break

            if self.current_least_index < len(self.least_similar_indices):
                grid_index = self.least_similar_indices[self.current_least_index]
                if grid_index < len(self.sprites):
                    sprites = self.all_sprites[grid_index]
                    if sprites:
                        self.sprites[grid_index] = sprites
                self.current_least_index += 1
                updates_done += 1

        self.sprites_updated.emit()

        if self.current_most_index < len(self.most_similar_indices) or self.current_least_index < len(self.least_similar_indices):
            QTimer.singleShot(config.update_delay, self.update_next_sprites)
        else:
            logger.info("All sprites have been batch loaded into the grid.")
            self.is_updating_sprites = False

    def get_sprite(self, index):
        if 0 <= index < len(self.sprites):
            if self.sprites[index] and 0 <= self.sprite_indices[index] < len(self.sprites[index]):
                return self.sprites[index][self.sprite_indices[index]]
        return None

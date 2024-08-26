import cv2
import numpy as np
from PyQt5.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QPainter
import config
from text_overlay import add_text_overlay
from logger_setup import logger
from sprite_arranger import SpriteArranger
import random
import time
class SpriteManager(QObject):
    sprites_updated = pyqtSignal()
    most_similar_updated = pyqtSignal(QPixmap)
    least_similar_updated = pyqtSignal(QPixmap)

    def __init__(self, num_labels, square_size, middle_y_pos):
        super().__init__()
        self.sprites = [{'images': [], 'delay': None} for _ in range(num_labels)]
        self.sprite_indices = [0] * num_labels
        self.sprite_arranger_running = False
        self.middle_y_pos = middle_y_pos
        self.square_size = square_size

        self.high_res_most_similar_sprites = []
        self.high_res_least_similar_sprites = []

        self.is_updating_sprites = False
        self.current_most_index = 0
        self.current_least_index = 0
        self.most_similar_indices = []
        self.least_similar_indices = []

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_sprites)
        self.update_timer.start(config.min_gif_delay)

        self.most_similar_timer = QTimer()
        self.most_similar_timer.timeout.connect(self.update_most_similar)
        self.most_similar_timer.start(config.min_gif_delay)

        self.least_similar_timer = QTimer()
        self.least_similar_timer.timeout.connect(self.update_least_similar)
        self.least_similar_timer.start(config.min_gif_delay)

        # Initialize the static overlays
        self.static_most_similar_overlay = None
        self.static_least_similar_overlay = None
        self.black_overlay = None
        self.update_static_overlays()

        self.previous_most = None
        self.previous_least = None

        self.updating_next = False

    def update_static_overlays(self):
        """Update the static overlays for the sprites."""
        self.static_most_similar_overlay = self.preprocess_overlay_text("Closest Match")
        self.static_least_similar_overlay = self.preprocess_overlay_text("Farthest Match")

    def create_black_overlay(self, overlay=None):
        """Create a black overlay image or draw the provided overlay as a semi-transparent image."""
        overlay_image = np.zeros((int(self.square_size * 3), int(self.square_size * 3), 4), dtype=np.uint8)

        if overlay is None:
            overlay_image[:, :, 0:3] = 0  # RGB = 0, 0, 0 (black)
            overlay_image[:, :, 3] = 125  # Alpha = 125 (semi-transparency)
        else:
            painter = QPainter(QImage(overlay_image.data, overlay_image.shape[1], overlay_image.shape[0], QImage.Format_RGBA8888))
            painter.setOpacity(0.5)  # Set opacity to 50% for semi-transparency
            painter.drawPixmap(0, 0, overlay)
            painter.end()

        return QPixmap.fromImage(QImage(overlay_image.data, overlay_image.shape[1], overlay_image.shape[0], QImage.Format_RGBA8888))

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
        self.assign_random_delays()  # Assign random delays to each sprite
        self.update_next_sprites()

    def handle_arrangement_completed(self):
        logger.info("All sprites have been arranged.")
        self.sprite_arranger_running = False

    def preprocess_high_res_sprites(self):
        if self.high_res_most_similar_sprites:
            self.previous_most = self.high_res_most_similar_sprites[-1]
        if self.high_res_least_similar_sprites:
            self.previous_least = self.high_res_least_similar_sprites[-1]

        self.high_res_most_similar_sprites.clear()
        self.high_res_least_similar_sprites.clear()

        if self.most_similar_indices:
            most_similar_index = self.most_similar_indices[0]
            if most_similar_index < len(self.sprites) and self.sprites[most_similar_index]['images']:
                for sprite in self.sprites[most_similar_index]['images']:
                    high_res_sprite = self.preprocess_sprite(sprite)
                    high_res_sprite = self.apply_static_overlay(high_res_sprite, self.static_most_similar_overlay)
                    self.high_res_most_similar_sprites.append(high_res_sprite)

        if self.least_similar_indices:
            least_similar_index = self.least_similar_indices[0]
            if least_similar_index < len(self.sprites) and self.sprites[least_similar_index]['images']:
                for sprite in self.sprites[least_similar_index]['images']:
                    high_res_sprite = self.preprocess_sprite(sprite)
                    high_res_sprite = self.apply_static_overlay(high_res_sprite, self.static_least_similar_overlay)
                    self.high_res_least_similar_sprites.append(high_res_sprite)

        self.most_similar_sprite_index = 0
        self.least_similar_sprite_index = 0

    def qpixmap_to_cv2(self, qpixmap):
        qimage = qpixmap.toImage()
        qimage = qimage.convertToFormat(QImage.Format_RGBA8888)
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(height * width * 4)
        arr = np.array(ptr, dtype=np.uint8).reshape(height, width, 4)
        return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)

    def cv2_to_qpixmap(self, cv_img):
        height, width, channel = cv_img.shape
        bytes_per_line = 3 * width
        qimage = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qimage)

    def preprocess_sprite(self, sprite):
        qimage = sprite.toImage()

        zoom_factor = config.zoom_factor

        resized_qimage = qimage.scaled(
            int(qimage.width() * zoom_factor),
            int(qimage.height() * zoom_factor),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation
        )

        return QPixmap.fromImage(resized_qimage)

    def preprocess_overlay_text(self, overlay_text):
        scale_factor = 50  # Increase to make the text sharper
        blank_image = np.zeros((int(self.square_size * 3 * scale_factor), int(self.square_size * 3 * scale_factor), 4), dtype=np.uint8)

        # Adjust text rendering to match the scale factor
        overlay_image = add_text_overlay(blank_image, text=overlay_text, offset_from_bottom=12, scale_factor=scale_factor)

        # Scale down the image to the original size
        overlay_image = cv2.resize(overlay_image, (int(self.square_size * 3), int(self.square_size * 3)), interpolation=cv2.INTER_AREA)

        return QPixmap.fromImage(QImage(overlay_image.data, overlay_image.shape[1], overlay_image.shape[0], QImage.Format_RGBA8888))
    def assign_random_delays(self):
        """Assign a random delay to each sprite for updating."""
        for sprite in self.sprites:
            sprite['delay'] = random.choice([config.min_gif_delay, config.max_gif_delay])

    def update_sprites(self):
        current_time = time.time()
        for index in range(len(self.sprites) - 3):  # Exclude special labels
            sprite = self.sprites[index]
            if sprite['images']:
                if current_time >= sprite.get('next_update_time', 0):
                    self.sprite_indices[index] = (self.sprite_indices[index] + 1) % len(sprite['images'])
                    sprite['next_update_time'] = current_time + sprite['delay'] / 1000.0  # Delay in seconds

        self.sprites_updated.emit()

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
        original_width = sprite.width()
        original_height = sprite.height()

        overlay_width = overlay.width()
        overlay_height = overlay.height()

        x_pos = (original_width - overlay_width) // 2
        y_pos = (original_height - overlay_height) // 2

        painter = QPainter(sprite)

        painter.drawPixmap(x_pos, y_pos, overlay)
        painter.end()

        return sprite

    def update_next_sprites(self):
        self.is_updating_sprites = True
        self.preprocess_high_res_sprites()

        updates_in_batch = min(
            config.update_count,
            (len(self.most_similar_indices) - self.current_most_index) + (len(self.least_similar_indices) - self.current_least_index)
        )
        updates_done = 0

        while updates_done < updates_in_batch:
            if self.current_most_index < len(self.most_similar_indices):
                grid_index = self.most_similar_indices[self.current_most_index]
                if grid_index < len(self.sprites):
                    sprites = self.all_sprites[grid_index]
                    if sprites:
                        self.sprites[grid_index]['images'] = sprites
                        self.sprite_indices[grid_index] = random.randint(0, len(sprites) - 1)
                self.current_most_index += 1
                updates_done += 1

            if updates_done >= updates_in_batch:
                break

            if self.current_least_index < len(self.least_similar_indices):
                grid_index = self.least_similar_indices[self.current_least_index]
                if grid_index < len(self.sprites):
                    sprites = self.all_sprites[grid_index]
                    if sprites:
                        self.sprites[grid_index]['images'] = sprites
                        self.sprite_indices[grid_index] = random.randint(0, len(sprites) - 1)
                self.current_least_index += 1
                updates_done += 1

        self.sprites_updated.emit()
        self.update_most_similar()
        self.update_least_similar()

        if self.current_most_index < len(self.most_similar_indices) or self.current_least_index < len(self.least_similar_indices):
            QTimer.singleShot(config.update_delay, self.update_next_sprites)
        else:
            logger.info("All sprites have been batch loaded into the grid.")
            self.is_updating_sprites = False

    def get_sprite(self, index):
        if 0 <= index < len(self.sprites):
            if self.sprites[index]['images'] and 0 <= self.sprite_indices[index] < len(self.sprites[index]['images']):
                sprite = self.sprites[index]['images'][self.sprite_indices[index]]

                if config.zoom_factor != 1.0:
                    original_size = sprite.size()
                    new_width = int(original_size.width() * config.zoom_factor)
                    new_height = int(original_size.height() * config.zoom_factor)

                    sprite = sprite.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                    if new_width > original_size.width():
                        crop_x = (new_width - original_size.width()) // 2
                        crop_y = (new_height - original_size.height()) // 2
                        sprite = sprite.copy(crop_x, crop_y, original_size.width(), original_size.height())
                return sprite
        return None

    def clear_preloaded_images(self):
        self.sprite_arranger.clear_preloaded_images()

import sys
import math
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QShortcut
from PyQt5.QtGui import QKeySequence, QPixmap, QImage, QPainter, QColor
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QRectF

import config
from gui import SliderOverlay
from text_overlay import add_text_overlay, update_font_size
from video_processor import VideoProcessor
from image_loader import ImageLoader
from backend_communicator import send_snapshot_to_server
from logger_setup import logger
from new_faces import NewFaces

class ImageApp(QWidget):
    def __init__(self, update_count=config.update_count, sprites_per_update=25, update_batch_size=80, batch_size=200):
        super().__init__()
        self.sprites = []
        self.sprite_indices = []
        self.animating_labels = set()
        self.image_loader_thread = None
        self.image_loader_running = False
        self.middle_y_pos = config.middle_y_pos
        self.initUI()
        self.update_count = update_count
        self.sprites_per_update = sprites_per_update
        self.update_timer = QTimer(self)
        self.update_batch_size = update_batch_size
        self.current_update_index = 0
        self.batch_size = batch_size
        self.current_batch_start = 0

        self.most_similar_indices = []
        self.least_similar_indices = []
        self.current_most_index = 0
        self.current_least_index = 0

        self.most_similar_sprite_index = 0
        self.least_similar_sprite_index = 0

        self.most_similar = []
        self.least_similar = []
        self.new_faces = NewFaces()

        self.video_processor = VideoProcessor(self.new_faces, square_size=int(self.square_size * 3), callback=self.load_images)
        self.video_processor.frame_ready.connect(self.update_video_label)
        self.video_processor.start()

        self.overlay_visible = [False]
        self.overlay = SliderOverlay(self)
        self.overlay.font_size_changed.connect(update_font_size)

        self.is_updating_sprites = False
        self.update_timer.timeout.connect(self.update_sprites)
        self.update_timer.start(config.gif_delay)

    def initUI(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setWindowTitle('Image Display App')
        self.setStyleSheet("background-color: black; border: none; margin: 0; padding: 0;")

        screen_sizes = [(screen.size().width(), screen.size().height()) for screen in QApplication.screens()]
        largest_screen_width, largest_screen_height = min(screen_sizes, key=lambda s: s[0] * s[1])

        window_width = largest_screen_width / 2 if config.demo else largest_screen_width
        window_height = largest_screen_height

        self.num_cols = config.num_cols
        self.square_size = window_width // self.num_cols

        self.num_rows = math.floor(window_height / self.square_size)

        config.num_rows = self.num_rows
        config.num_vids = self.num_rows * self.num_cols

        self.image_labels = []
        for row in range(self.num_rows):
            for col in range(self.num_cols):
                label = QLabel(self)
                label.setFixedSize(int(self.square_size), int(self.square_size))
                label.setStyleSheet("background-color: black; border: none; margin: 0; padding: 0;")
                label.setAlignment(Qt.AlignCenter)
                self.image_labels.append(label)
                self.sprites.append([])
                self.sprite_indices.append(0)

        self.create_center_labels()

        if not config.demo:
            self.setWindowFlags(Qt.FramelessWindowHint)
            self.showFullScreen()
        else:
            self.setFixedSize(int(window_width), int(window_height))
            self.show()

        QApplication.setOverrideCursor(Qt.BlankCursor)

        self.shortcut = QShortcut(QKeySequence("Escape"), self)
        self.shortcut.activated.connect(self.close_app)

    def create_center_labels(self):
        center_row = self.num_rows // 2 + self.middle_y_pos
        center_col = self.num_cols // 2

        video_label_width = int(self.square_size * 3)
        video_label_height = int(self.square_size * 3)

        self.video_label = QLabel(self)
        self.video_label.setFixedSize(video_label_width, video_label_height)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("border: none; margin: 0;")
        self.image_labels.append(self.video_label)
        self.sprites.append([])
        self.sprite_indices.append(0)

        self.least_similar_label = QLabel(self)
        self.least_similar_label.setFixedSize(video_label_width, video_label_height)
        self.least_similar_label.setAlignment(Qt.AlignCenter)
        self.least_similar_label.setStyleSheet("border: none; margin: 0;")
        self.image_labels.append(self.least_similar_label)
        self.sprites.append([])
        self.sprite_indices.append(0)

        self.most_similar_label = QLabel(self)
        self.most_similar_label.setFixedSize(video_label_width, video_label_height)
        self.most_similar_label.setAlignment(Qt.AlignCenter)
        self.most_similar_label.setStyleSheet("border: none; margin: 0;")
        self.image_labels.append(self.most_similar_label)
        self.sprites.append([])
        self.sprite_indices.append(0)

    def closeEvent(self, event):
        self.new_faces.stop_all_threads()
        event.accept()

    def handle_sprite_loaded(self, label_index, sprites):
        self.sprites[label_index] = sprites

    def handle_loading_completed(self):
        logger.info("All images have been loaded.")
        self.image_loader_running = False

    def update_sprites(self):
        update_indices = list(range(len(self.image_labels) - 3))

        for index in update_indices:
            if index < len(self.sprites) and self.sprites[index]:
                self.sprite_indices[index] = (self.sprite_indices[index] + 1) % len(self.sprites[index])
                self.image_labels[index].setPixmap(self.sprites[index][self.sprite_indices[index]])

        self.update_special_label(self.most_similar_label, self.most_similar_indices, "most_similar")
        self.update_special_label(self.least_similar_label, self.least_similar_indices, "least_similar")

        # if self.is_updating_sprites:
        #     return
        #
        # update_indices = list(range(len(self.image_labels) - 3))
        # batch_end = self.current_batch_start + self.batch_size
        #
        # for i in range(self.current_batch_start, batch_end):
        #     if i >= len(update_indices):
        #         break
        #     index = update_indices[i]
        #     if index < len(self.sprites) and self.sprites[index]:
        #         self.sprite_indices[index] = (self.sprite_indices[index] + 1) % len(self.sprites[index])
        #         self.image_labels[index].setPixmap(self.cv2_to_qpixmap(
        #             self.sprites[index][self.sprite_indices[index]],
        #             int(self.square_size),
        #             int(self.square_size)
        #         ))
        #
        # self.current_batch_start = (batch_end) % len(update_indices)
        #
        # self.update_special_label(self.most_similar_label, self.most_similar_indices, "most_similar")
        # self.update_special_label(self.least_similar_label, self.least_similar_indices, "least_similar")

    def update_special_label(self, label, indices, label_type):
        if indices:
            index = indices[0]
            if index < len(self.sprites) and len(self.sprites[index]) > 0:
                sprite_index = getattr(self, f"{label_type}_sprite_index")
                sprite_index = (sprite_index + 1) % len(self.sprites[index])
                setattr(self, f"{label_type}_sprite_index", sprite_index)

                sprite = self.sprites[index][sprite_index]
                high_res_sprite = self.resize_to_square(sprite, int(self.square_size * 3))
                add_text_overlay(high_res_sprite, "Closest Match" if label_type == "most_similar" else "Farthest Match")
                label.setPixmap(self.cv2_to_qpixmap(high_res_sprite, int(self.square_size * 3), int(self.square_size * 3)))
            else:
                logger.error(f"Index out of range or empty sprite list for {label_type}: {index}")
        else:
            logger.error(f"No indices available for {label_type}")

    def update_video_label(self, q_img):
        self.video_label.setPixmap(QPixmap.fromImage(q_img))

    def cv2_to_qpixmap(self, cv_img, target_width, target_height, add_overlay=False, overlay_text=""):
        if not isinstance(cv_img, np.ndarray):
            return QPixmap()
        cv_img_resized = cv2.resize(cv_img, (target_width, target_height), interpolation=cv2.INTER_AREA)
        height, width, channel = cv_img_resized.shape
        bytes_per_line = channel * width
        cv_img_rgb = cv2.cvtColor(cv_img_resized, cv2.COLOR_BGR2RGB)

        if add_overlay:
            add_text_overlay(cv_img_rgb, overlay_text)

        q_img = QImage(cv_img_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(q_img)

    def load_images(self, most_similar, least_similar):
        if self.image_loader_running:
            return

        self.image_loader_running = True
        if self.image_loader_thread and self.image_loader_thread.isRunning():
            self.image_loader_thread.quit()
            self.image_loader_thread.wait()

        self.most_similar = most_similar
        self.least_similar = least_similar

        self.image_loader_thread = QThread()
        self.image_loader = ImageLoader(self.middle_y_pos)
        self.image_loader.moveToThread(self.image_loader_thread)
        self.image_loader.set_data(most_similar, least_similar)
        self.image_loader.all_sprites_loaded.connect(self.handle_all_sprites_loaded)
        self.image_loader.loading_completed.connect(self.handle_loading_completed)
        self.image_loader_thread.started.connect(self.image_loader.run)
        self.image_loader_thread.start()

    def handle_all_sprites_loaded(self, all_sprites, most_similar_indices, least_similar_indices):
        self.all_sprites = all_sprites
        self.most_similar_indices = most_similar_indices
        self.least_similar_indices = least_similar_indices
        self.current_most_index = 0
        self.current_least_index = 0
        self.update_next_sprites()

    def update_next_sprites(self):
        self.is_updating_sprites = True

        total_updates = min(self.update_batch_size, (len(self.most_similar_indices) - self.current_most_index) + (len(self.least_similar_indices) - self.current_least_index))
        updates_done = 0

        while updates_done < total_updates:
            if self.current_most_index < len(self.most_similar_indices):
                grid_index = self.most_similar_indices[self.current_most_index]
                if grid_index < len(self.sprites):
                    sprites = self.all_sprites[grid_index]
                    if sprites:
                        self.sprites[grid_index] = sprites
                        self.image_labels[grid_index].setPixmap(self.sprites[grid_index][0])
                        self.update_most_similar()
                self.current_most_index += 1
                updates_done += 1

            if updates_done >= total_updates:
                break

            if self.current_least_index < len(self.least_similar_indices):
                grid_index = self.least_similar_indices[self.current_least_index]
                if grid_index < len(self.sprites):
                    sprites = self.all_sprites[grid_index]
                    if sprites:
                        self.sprites[grid_index] = sprites
                        self.image_labels[grid_index].setPixmap(self.sprites[grid_index][0])
                        self.update_least_similar()
                self.current_least_index += 1
                updates_done += 1

        if self.current_most_index >= len(self.most_similar_indices) and self.current_least_index >= len(self.least_similar_indices):
            logger.info("All sprites have been batch loaded into the grid.")
            self.is_updating_sprites = False
        else:
            QTimer.singleShot(config.update_delay, self.update_next_sprites)

    def update_most_similar(self):
        if self.most_similar_indices:
            most_similar_index = self.most_similar_indices[0]
            if most_similar_index < len(self.sprites) and len(self.sprites[most_similar_index]) > self.most_similar_sprite_index:
                sprite = self.sprites[most_similar_index][self.most_similar_sprite_index]
                high_res_sprite = self.resize_to_square(sprite, int(self.square_size * 3))
                add_text_overlay(high_res_sprite, "Closest Match")
                resized_sprite = self.resize_to_square(high_res_sprite, int(self.square_size * 3))
                self.most_similar_label.setPixmap(self.cv2_to_qpixmap(resized_sprite, int(self.square_size * 3), int(self.square_size * 3)))
                self.most_similar_sprite_index = (self.most_similar_sprite_index + 1) % len(self.sprites[most_similar_index])

    def update_least_similar(self):
        if self.least_similar_indices:
            least_similar_index = self.least_similar_indices[0]
            if least_similar_index < len(self.sprites) and len(self.sprites[least_similar_index]) > self.least_similar_sprite_index:
                sprite = self.sprites[least_similar_index][self.least_similar_sprite_index]
                high_res_sprite = self.resize_to_square(sprite, int(self.square_size * 3))
                add_text_overlay(high_res_sprite, "Farthest Match")
                resized_sprite = self.resize_to_square(high_res_sprite, int(self.square_size * 3))
                self.least_similar_label.setPixmap(self.cv2_to_qpixmap(resized_sprite, int(self.square_size * 3), int(self.square_size * 3)))
                self.least_similar_sprite_index = (self.least_similar_sprite_index + 1) % len(self.sprites[least_similar_index])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_G:
            if self.overlay_visible[0]:
                self.overlay.close()
                self.overlay_visible[0] = False
                QApplication.setOverrideCursor(Qt.BlankCursor)
            else:
                self.overlay.show()
                self.overlay_visible[0] = True
                QApplication.restoreOverrideCursor()
        elif event.key() == Qt.Key_Escape:
            if self.overlay_visible[0]:
                self.overlay.close()
                self.overlay_visible[0] = False
                QApplication.setOverrideCursor(Qt.BlankCursor)
            self.close_app()

    def close_app(self):
        self.new_faces.stop_all_threads()
        self.video_processor.stop()
        self.video_processor.wait()
        if hasattr(self, 'image_loader_thread') and self.image_loader_thread.isRunning():
            self.image_loader_thread.quit()
            self.image_loader_thread.wait()
        QApplication.quit()

    def resize_to_square(self, frame, size):
        return frame #frame.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def paintEvent(self, event):
        painter = QPainter(self)
        total_height = self.num_rows * self.square_size
        total_width = self.num_cols * self.square_size
        vertical_offset = (self.height() - total_height) // 2
        horizontal_offset = (self.width() - total_width) // 2
        for row in range(self.num_rows):
            for col in range(self.num_cols):
                x = col * self.square_size + horizontal_offset
                y = row * self.square_size + vertical_offset
                rect = QRectF(x, y, self.square_size, self.square_size)
                painter.drawRect(rect)
        self.update_labels(vertical_offset, horizontal_offset)

    def update_labels(self, vertical_offset, horizontal_offset):
        for index, label in enumerate(self.image_labels):
            if label in [self.video_label, self.least_similar_label, self.most_similar_label]:
                continue
            row = index // self.num_cols
            col = index % self.num_cols
            x = col * self.square_size + horizontal_offset
            y = row * self.square_size + vertical_offset
            label.move(int(x), int(y))

        center_row = self.num_rows // 2 + self.middle_y_pos
        center_col = self.num_cols // 2

        video_x = (center_col - 1) * self.square_size + horizontal_offset
        video_y = (center_row - 1) * self.square_size + vertical_offset
        self.video_label.move(int(video_x), int(video_y))

        least_similar_x = (center_col - 4) * self.square_size + horizontal_offset
        least_similar_y = (center_row - 1) * self.square_size + vertical_offset
        self.least_similar_label.move(int(least_similar_x), int(least_similar_y))

        most_similar_x = (center_col + 2) * self.square_size + horizontal_offset
        most_similar_y = (center_row - 1) * self.square_size + vertical_offset
        self.most_similar_label.move(int(most_similar_x), int(most_similar_y))


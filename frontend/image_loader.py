from PyQt5.QtCore import QThread, pyqtSignal
import config
from logger_setup import logger
import time
import concurrent.futures
import cv2
import os

from PyQt5.QtCore import QThread, pyqtSignal
import config
from logger_setup import logger
import time
import concurrent.futures
from image_store import image_store  # Import the global instance

class ImageLoader(QThread):
    all_sprites_loaded = pyqtSignal(list, list, list)  # Signal to emit when all images are loaded
    loading_completed = pyqtSignal()  # Signal to emit when loading is completed

    def __init__(self, middle_row_offset=config.middle_y_pos):
        super().__init__()
        self.num_cols = config.num_cols
        self.num_rows = config.num_rows
        self.middle_row_offset = middle_row_offset
        self.most_similar = []
        self.least_similar = []

    def set_data(self, most_similar, least_similar):
        if most_similar is None or least_similar is None:
            raise ValueError("most_similar or least_similar data cannot be None")
        self.most_similar = most_similar
        self.least_similar = least_similar

    def run(self):
        logger.info('Starting image loading')
        start_time = time.time()  # Start the timer

        sprites = [[] for _ in range(self.num_cols * self.num_rows)]
        self.most_similar_indices = []  # Initialize indices list
        self.least_similar_indices = []  # Initialize indices list

        logger.info('Initial setup completed')

        # Central grid coordinates
        center_row = (self.num_rows // 2) + self.middle_row_offset
        center_col = self.num_cols // 2

        # Define ranges for the central exclusion area
        middle_col_index = center_col

        mid_block_start_col = center_col - 4
        mid_block_end_col = center_col + 4
        mid_block_start_row = center_row - 1
        mid_block_end_row = center_row + 1

        # Generate grid positions, excluding middle column and central block
        positions = [
            (r, c) for r in range(self.num_rows) for c in range(self.num_cols)
            if c != middle_col_index and not (mid_block_start_col <= c <= mid_block_end_col and mid_block_start_row <= r <= mid_block_end_row)
        ]

        logger.info('Grid positions generated')

        # Sort positions by their distance from the center of the grid
        positions.sort(key=lambda pos: (abs(pos[1] - center_col) ** 2 + abs(pos[0] - center_row) ** 2))

        logger.info('Grid positions sorted')

        # Load the central images
        if len(self.least_similar) > 1:
            self.load_and_append_image(self.least_similar[1], center_row * self.num_cols + (center_col - 4), sprites, self.least_similar_indices)

        if len(self.most_similar) > 1:
            self.load_and_append_image(self.most_similar[1], center_row * self.num_cols + (center_col + 2), sprites, self.most_similar_indices)

        logger.info('Central images loaded')

        least_similar_index = 2  # Start from index 2
        most_similar_index = 2  # Start from index 2

        def load_image(pos, image_info, indices_list):
            row, col = pos
            grid_index = row * self.num_cols + col
            self.load_and_append_image(image_info, grid_index, sprites, indices_list)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for pos in positions:
                if least_similar_index < len(self.least_similar) and pos[1] < center_col:
                    futures.append(executor.submit(load_image, pos, self.least_similar[least_similar_index], self.least_similar_indices))
                    least_similar_index += 1
                elif most_similar_index < len(self.most_similar) and pos[1] >= center_col:
                    futures.append(executor.submit(load_image, pos, self.most_similar[most_similar_index], self.most_similar_indices))
                    most_similar_index += 1

            concurrent.futures.wait(futures)

        logger.info('All images loaded')
        self.all_sprites_loaded.emit(sprites, self.most_similar_indices, self.least_similar_indices)
        self.loading_completed.emit()

        end_time = time.time()  # End the timer
        duration = end_time - start_time
        logger.info(f"Image loading completed in {duration:.2f} seconds")

    def load_and_append_image(self, image_info, grid_index, sprites, indices_list):
        image_path = image_info['path']
        image = image_store.get_image(image_path)
        if image is None:
            logger.error(f"Preloaded image at path {image_path} is None")
            return False

        loaded_images = []

        for i in range(image_info['numImages']):
            x = (i % 19) * 100
            y = (i // 19) * 100
            cropped_image = image[y:y + 100, x:x + 100]
            if cropped_image.shape[0] == 100 and cropped_image.shape[1] == 100:
                loaded_images.append(cropped_image)

        for img in loaded_images:
            sprites[grid_index].append(img)
        for img in reversed(loaded_images):
            sprites[grid_index].append(img)

        indices_list.append(grid_index)
        return True

    def load_new_spritesheet(self, spritesheet_path):
        # Load the new spritesheet into preloaded images
        if os.path.exists(spritesheet_path):
            image = cv2.imread(spritesheet_path)
            if image is not None:
                image_store.preloaded_images[spritesheet_path] = image
                logger.info(f"New spritesheet loaded: {spritesheet_path}")
                self.set_data([{'path': spritesheet_path, 'numImages': self.num_rows * self.num_cols}], [])
                self.run()  # Re-run the loader with the new spritesheet data
            else:
                logger.error(f"Failed to load new spritesheet from path: {spritesheet_path}")
        else:
            logger.error(f"Spritesheet path does not exist: {spritesheet_path}")

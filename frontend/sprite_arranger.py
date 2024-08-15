import time
from PyQt5.QtCore import pyqtSignal, QObject
import config
from logger_setup import logger
from image_store import image_store  # Import the global instance

class SpriteArranger(QObject):
    sprites_arranged = pyqtSignal(list, list, list)  # Signal to emit when all sprites are arranged
    arrangement_completed = pyqtSignal()  # Signal to emit when arrangement is completed

    def __init__(self, middle_row_offset=config.middle_y_pos):
        super().__init__()
        self.num_cols = config.num_cols
        self.num_rows = config.num_rows
        self.middle_row_offset = middle_row_offset
        self.most_similar = []
        self.least_similar = []
        self.is_arranging = False  # Flag to check if arrangement is in progress

    def set_data(self, most_similar, least_similar):
        if most_similar is None or least_similar is None:
            raise ValueError("most_similar or least_similar data cannot be None")
        self.most_similar = most_similar
        self.least_similar = least_similar

    def arrange_sprites(self):

        if self.is_arranging:
            logger.info('Sprite arrangement is already in progress. Skipping new request.')
            return

        self.is_arranging = True  # Set the flag to indicate arrangement is in progress
        logger.info('Starting sprite arrangement')
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

        # Arrange the central sprites
        if len(self.least_similar) > 1:
            self.arrange_sprite(self.least_similar[1], center_row * self.num_cols + (center_col - 4), sprites, self.least_similar_indices)

        if len(self.most_similar) > 1:
            self.arrange_sprite(self.most_similar[1], center_row * self.num_cols + (center_col + 2), sprites, self.most_similar_indices)

        logger.info('Central sprites arranged')

        least_similar_index = 2  # Start from index 2
        most_similar_index = 2  # Start from index 2

        for pos in positions:
            if least_similar_index < len(self.least_similar) and pos[1] < center_col:
                self.arrange_sprite(self.least_similar[least_similar_index], pos[0] * self.num_cols + pos[1], sprites, self.least_similar_indices)
                least_similar_index += 1
            elif most_similar_index < len(self.most_similar) and pos[1] >= center_col:
                self.arrange_sprite(self.most_similar[most_similar_index], pos[0] * self.num_cols + pos[1], sprites, self.most_similar_indices)
                most_similar_index += 1

        logger.info('All sprites arranged')
        self.sprites_arranged.emit(sprites, self.most_similar_indices, self.least_similar_indices)
        self.arrangement_completed.emit()

        end_time = time.time()  # End the timer
        duration = end_time - start_time
        logger.info(f"Sprite arrangement completed in {duration:.2f} seconds")
        self.is_arranging = False  # Reset the flag after arrangement is completed

    def arrange_sprite(self, sprite_info, grid_index, sprites, indices_list):
        subfolder_name = sprite_info['subfolder']  # Now using subfolder name

        sub_images = image_store.get_sub_images(subfolder_name)
        if not sub_images:
            print(f"Error: Preloaded sub-images for subfolder {subfolder_name} are None or empty")
            return False

        num_images = sprite_info['numImages']
        arranged_sprites = sub_images[:num_images]

        sprites[grid_index].extend(arranged_sprites)

        indices_list.append(grid_index)
        return True

    def clear_preloaded_images(self):
        image_store.clear_preloaded_images()

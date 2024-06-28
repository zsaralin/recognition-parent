from PyQt5.QtCore import QThread, pyqtSignal
import cv2
import config
from logger_setup import logger
from concurrent.futures import ThreadPoolExecutor

class ImageLoader(QThread):
    all_sprites_loaded = pyqtSignal(list, list, list)  # Update signal to accept two arguments
    loading_completed = pyqtSignal()  # Define a signal for loading completion

    def __init__(self, middle_row_offset=config.middle_y_pos):  # Default to config value
        super().__init__()
        self.num_cols = config.num_cols
        self.num_rows = config.num_rows
        self.middle_row_offset = middle_row_offset
        self.most_similar = []
        self.least_similar = []
        self.max_threads = 10  # Limit the number of threads

    def set_data(self, most_similar, least_similar):
        if most_similar is None or least_similar is None:
            raise ValueError("most_similar or least_similar data cannot be None")
        self.most_similar = most_similar
        self.least_similar = least_similar

    def run(self):
        print('Starting load')
        sprites = [[] for _ in range(self.num_cols * self.num_rows)]
        self.most_similar_indices = []  # Initialize indices list
        self.least_similar_indices = []  # Initialize indices list
        self.most_similar_sprite_index = 0
        self.least_similar_sprite_index = 0

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

        # Sort positions by their distance from the center of the grid
        positions.sort(key=lambda pos: (abs(pos[1] - center_col) ** 2 + abs(pos[0] - center_row) ** 2))

        # Use ThreadPoolExecutor to load images in parallel
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = []

            # Load the second most similar and second least similar images (index 1) into the central positions
            central_least_similar_index = (center_row * self.num_cols) + (center_col - 4)
            central_most_similar_index = (center_row * self.num_cols) + (center_col + 2)

            if len(self.least_similar) > 1:
                futures.append(executor.submit(self.load_and_append_image, self.least_similar[1], central_least_similar_index, sprites))
                self.least_similar_indices.append(central_least_similar_index)

            if len(self.most_similar) > 1:
                futures.append(executor.submit(self.load_and_append_image, self.most_similar[1], central_most_similar_index, sprites))
                self.most_similar_indices.append(central_most_similar_index)

            least_similar_index = 2  # Start from index 2
            most_similar_index = 2  # Start from index 2

            for pos in positions:
                row, col = pos
                grid_index = row * self.num_cols + col

                if col < center_col:
                    # Load least similar images on the left side
                    if least_similar_index < len(self.least_similar):
                        self.least_similar_indices.append(grid_index)
                        futures.append(executor.submit(self.load_and_append_image, self.least_similar[least_similar_index], grid_index, sprites))
                        least_similar_index += 1
                else:
                    # Load most similar images on the right side
                    if most_similar_index < len(self.most_similar):
                        self.most_similar_indices.append(grid_index)
                        futures.append(executor.submit(self.load_and_append_image, self.most_similar[most_similar_index], grid_index, sprites))
                        most_similar_index += 1

            for future in futures:
                future.result()  # Wait for all futures to complete

        self.all_sprites_loaded.emit(sprites, self.most_similar_indices, self.least_similar_indices)
        self.loading_completed.emit()

    def load_and_append_image(self, image_info, grid_index, sprites):
        image = cv2.imread(image_info['path'])
        if image is None:
            logger.error(f"Image at path {image_info['path']} could not be loaded")
            return False

        loaded_images = []

        # Load images in normal order
        for i in range(image_info['numImages']):
            x = (i % 19) * 100
            y = (i // 19) * 100
            cropped_image = image[y:y + 100, x:x + 100]
            if cropped_image.shape[0] == 100 and cropped_image.shape[1] == 100:
                loaded_images.append(cropped_image)

        # Append images in normal order
        for img in loaded_images:
            sprites[grid_index].append(img)

        # Append images in reverse order
        for img in reversed(loaded_images):
            sprites[grid_index].append(img)

        return True

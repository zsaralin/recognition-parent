import os
import cv2
import time  # Import time module for sleep function
from PyQt5.QtGui import QImage, QPixmap, QGuiApplication
from logger_setup import logger
import config
import psutil
from concurrent.futures import ThreadPoolExecutor
import shutil

class ImageStore:
    def __init__(self):
        self.preloaded_images = {}
        self.zoom_factor = 1  # Initial zoom factor, 1.0 means no zoom
        self.compression_ratios = []  # List to store compression ratios
        self.base_dir = None
        self.sprite_width = 200
        self.executor = ThreadPoolExecutor(max_workers=2)  # Use threads for parallel processing
        self.preloaded_folders = set()  # Track preloaded folders
    def preload_images(self, app, base_dir, num_cols=21, memory_threshold=0.95):
        self.base_dir = base_dir
        logger.info('Starting preload images')

        screen_sizes = [(screen.size().width(), screen.size().height()) for screen in app.screens()]
        largest_screen_width, largest_screen_height = min(screen_sizes, key=lambda s: s[0] * s[1])
        window_width = largest_screen_width // 2 if config.demo else largest_screen_width
        square_size = window_width // num_cols
        large_square_size = square_size * 3

        total_images = 0
        preloaded_count = 0

        # Initialize process variable
        process = psutil.Process(os.getpid())

        # Count total images
        for root, _, files in os.walk(base_dir):
            total_images += len([file for file in files if file.endswith(('.png', '.jpg', '.jpeg'))])

        # Preload images
        for root, dirs, files in sorted(os.walk(base_dir), reverse=True):  # Sort directories in reverse order
            dirs.sort(reverse=True)  # Ensure directories are processed in reverse order
            files.sort(reverse=True)  # Sort files in reverse order

            parent_dir = os.path.basename(os.path.dirname(root))

            for file in files:
                if file.endswith(('.png', '.jpg', '.jpeg')):
                    image_path = os.path.join(root, file)
                    image = cv2.imread(image_path)
                    if image is not None:
                        num_images = self.get_num_images_from_filename(file)
                        sub_images = self.split_into_sub_images(image, self.sprite_width, self.sprite_width, num_images)
                        sub_images_with_reversed = sub_images + sub_images[::-1]

                        standard_pixmaps = [self.cv2_to_qpixmap(self.resize_to_square(img, square_size)) for img in sub_images_with_reversed]
                        large_pixmaps = [self.cv2_to_qpixmap(self.resize_to_square(img, large_square_size)) for img in sub_images_with_reversed]

                        self.preloaded_images[parent_dir] = {
                            'standard': standard_pixmaps,
                            'large': large_pixmaps
                        }
                        preloaded_count += 1
                        self.preloaded_folders.add(root)  # Track the preloaded folder
                        print(f"Preloaded image: {parent_dir} ({preloaded_count}/{total_images})")

                        # Check memory usage after each image is loaded
                        current_memory = process.memory_info().rss  # in bytes
                        total_memory = psutil.virtual_memory().total  # in bytes
                        memory_used_percentage = current_memory / total_memory

                        print(f"Current memory used: {current_memory / (1024 * 1024):.2f} MB ({memory_used_percentage * 100:.2f}% of total memory)")

                        if memory_used_percentage > memory_threshold:
                            print(f"Memory usage exceeded threshold of {memory_threshold * 100}%. Waiting before deleting unpreloaded folders.")
                            time.sleep(3)  # Wait for 3 seconds before deletion
                            for root_dir, dir_names, _ in os.walk(base_dir):
                                for dir_name in dir_names:
                                    subfolder_path = os.path.join(root_dir, dir_name)
                                    if subfolder_path not in self.preloaded_folders:
                                        try:
                                            parent_folder = os.path.dirname(subfolder_path)  # Get the parent directory
                                            # Ensure the folder to delete is not the base_dir or any of its parents
                                            if parent_folder != base_dir and os.path.commonpath([parent_folder, base_dir]) == base_dir:
                                                shutil.rmtree(parent_folder)
                                                print(f"Deleted folder: {subfolder_path}")
                                        except Exception as e:
                                            logger.error(f"Failed to delete {subfolder_path}: {e}")
                            return self.preloaded_images
                    else:
                        logger.error(f"Failed to load image from path: {image_path}")

        # Print final memory usage
        final_memory = process.memory_info().rss  # in bytes
        print(f"Final memory used after preloading: {final_memory / (1024 * 1024):.2f} MB")

        logger.info(f'Preload images completed ({preloaded_count}/{total_images})')
        return self.preloaded_images


    def split_into_sub_images(self, image, sub_width, sub_height, num_images):
        sub_images = []
        height, width, _ = image.shape
        for y in range(0, height, sub_height):
            for x in range(0, width, sub_width):
                sub_image = image[y:y + sub_height, x:x + sub_width]
                if sub_image.shape[0] == sub_height and sub_image.shape[1] == sub_width:
                    sub_images.append(sub_image)
                if len(sub_images) >= num_images:
                    break
            if len(sub_images) >= num_images:
                break

        return sub_images

    def get_num_images_from_filename(self, filename):
        # Extract the number from the filename assuming the format is like "image_50.png"
        num_images = int(filename.split('_')[-1].split('.')[0])
        return num_images

    def resize_to_square(self, image, size):
        if self.zoom_factor == 1:
            # If zoom factor is 1, just resize the image to the square size directly
            return cv2.resize(image, (size, size), interpolation=cv2.INTER_AREA)

        # Calculate the new size based on the zoom factor
        zoomed_size = int(size * self.zoom_factor)

        # Calculate the center crop area
        height, width, _ = image.shape
        center_x, center_y = width // 2, height // 2
        half_zoomed_size = zoomed_size // 2

        # Crop the image around the center
        cropped_image = image[
                        max(center_y - half_zoomed_size, 0):min(center_y + half_zoomed_size, height),
                        max(center_x - half_zoomed_size, 0):min(center_x + half_zoomed_size, width)
                        ]

        # Resize the cropped image back to the square size
        resized_image = cv2.resize(cropped_image, (size, size), interpolation=cv2.INTER_AREA)

        # Calculate and store the compression ratio
        compression_ratio = (cropped_image.shape[0] / size) * 100
        self.compression_ratios.append(compression_ratio)

        return resized_image

    def cv2_to_qpixmap(self, cv_img):
        height, width, channel = cv_img.shape
        bytes_per_line = channel * width
        cv_img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        q_img = QImage(cv_img_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(q_img)

    def get_sub_images(self, image_path, size_type='standard'):
        """
        Retrieve preloaded images by path and size type.

        :param image_path: The path to the images.
        :param size_type: 'standard' or 'large' to specify which size to retrieve.
        :return: List of QPixmap objects of the requested size or an empty list if not found.
        """
        # Check if the image_path exists in the preloaded_images dictionary
        if image_path in self.preloaded_images:
            # Return the images of the requested size
            return self.preloaded_images[image_path].get(size_type, [])
        return []

    def add_image(self, subfolder_name, image_filename):
        if not self.base_dir:
            print("Base directory not set. Please call set_base_dir() before add_image().")
            return False

        base_dir = os.path.join(self.base_dir, subfolder_name)
        image_path = os.path.join(base_dir, 'spritesheet', image_filename)

        print(f"Trying to add image from path: {image_path}")

        if not os.path.exists(image_path):
            print(f"Image path does not exist: {image_path}")
            return False

        # Process the image in a separate thread to avoid blocking the main process
        self.executor.submit(self.process_image, subfolder_name, image_path, image_filename)

        return True

    def process_image(self, subfolder_name, image_path, image_filename):
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to load image from path: {image_path}")
            return False

        num_images = self.get_num_images_from_filename(image_filename)

        # Calculate sizes based on the preloading strategy
        square_size = self.calculate_square_size()  # Standard size
        large_square_size = square_size * 3  # Large size

        # Split images for both sizes
        sub_images = self.split_into_sub_images(image, self.sprite_width, self.sprite_width, num_images)
        sub_images_with_reversed = sub_images + sub_images[::-1]

        # Create pixmaps for both sizes
        standard_pixmaps = [self.cv2_to_qpixmap(self.resize_to_square(img, square_size)) for img in sub_images_with_reversed]
        large_pixmaps = [self.cv2_to_qpixmap(self.resize_to_square(img, large_square_size)) for img in sub_images_with_reversed]

        # Store both sets of images under their respective categories
        if subfolder_name not in self.preloaded_images:
            self.preloaded_images[subfolder_name] = {}

        self.preloaded_images[subfolder_name]['standard'] = standard_pixmaps
        self.preloaded_images[subfolder_name]['large'] = large_pixmaps

        print(f"Added new image to preloaded images under subfolder: {subfolder_name}, both standard and large sizes.")
        return True

    def calculate_square_size(self):
        app = QGuiApplication.instance()
        screen_sizes = [(screen.size().width(), screen.size().height()) for screen in app.screens()]
        largest_screen_width, largest_screen_height = min(screen_sizes, key=lambda s: s[0] * s[1])
        window_width = largest_screen_width // 2 if config.demo else largest_screen_width
        return window_width // config.num_cols

    def clear_preloaded_images(self):
        """Clear all preloaded images from memory."""
        self.preloaded_images.clear()
        print("Preloaded images cleared from memory.")

    def delete_specific_entries(self, keys_to_delete):
        for key in keys_to_delete:
            if key in self.preloaded_images:
                del self.preloaded_images[key]
                print(f"Deleted preloaded images for {key}")
            else:
                print(f"Key {key} not found in preloaded images.")
# Create a global instance
image_store = ImageStore()

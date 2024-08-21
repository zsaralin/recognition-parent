import os
import cv2
from PyQt5.QtGui import QImage, QPixmap, QGuiApplication
from logger_setup import logger
import config
import psutil

class ImageStore:
    def __init__(self):
        self.preloaded_images = {}
        self.zoom_factor = 1  # Initial zoom factor, 1.0 means no zoom
        self.compression_ratios = []  # List to store compression ratios
        self.base_dir = None
        self.sprite_width = 100
    def preload_images(self, app, base_dir, num_cols=21):
        self.base_dir = base_dir
        logger.info('Starting preload images')

        # Calculate square_size based on screen dimensions and number of columns
        screen_sizes = [(screen.size().width(), screen.size().height()) for screen in app.screens()]
        largest_screen_width, largest_screen_height = min(screen_sizes, key=lambda s: s[0] * s[1])
        window_width = largest_screen_width // 2 if config.demo else largest_screen_width
        square_size = window_width // num_cols

        # Define a larger size as three times the square size
        large_square_size = square_size * 3

        total_images = 0
        preloaded_count = 0

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss  # in bytes

        # Count total images
        for root, _, files in os.walk(base_dir):
            total_images += len([file for file in files if file.endswith(('.png', '.jpg', '.jpeg'))])

        for root, _, files in os.walk(base_dir):
            parent_dir = os.path.basename(os.path.dirname(root))
            for file in files:
                if file.endswith(('.png', '.jpg', '.jpeg')):
                    image_path = os.path.join(root, file)
                    image = cv2.imread(image_path)
                    if image is not None:
                        num_images = self.get_num_images_from_filename(file)
                        sub_images = self.split_into_sub_images(image, self.sprite_width, self.sprite_width, num_images)
                        sub_images_with_reversed = sub_images + sub_images[::-1]
                        # Create pixmaps for both sizes
                        standard_pixmaps = [self.cv2_to_qpixmap(self.resize_to_square(img, square_size)) for img in sub_images_with_reversed]
                        large_pixmaps = [self.cv2_to_qpixmap(self.resize_to_square(img, large_square_size)) for img in sub_images_with_reversed]
                        # Store both sets of images
                        self.preloaded_images[parent_dir] = {
                            'standard': standard_pixmaps,
                            'large': large_pixmaps
                        }
                        preloaded_count += 1
                        print(f"Preloaded image: {parent_dir} ({preloaded_count}/{total_images})")
                    else:
                        logger.error(f"Failed to load image from path: {image_path}")

        # Calculate final memory usage
        final_memory = process.memory_info().rss  # in bytes
        memory_used = final_memory - initial_memory  # in bytes
        total_memory = psutil.virtual_memory().total  # in bytes

        # Convert memory usage to MB
        memory_used_mb = memory_used / (1024 * 1024)
        total_memory_mb = total_memory / (1024 * 1024)

        # Calculate percentage of memory used
        memory_percentage = (memory_used / total_memory) * 100

        print(f"Memory used after preloading: {memory_used_mb:.2f} MB ({memory_percentage:.2f}% of total memory)")

        logger.info(f'Preload images completed ({preloaded_count}/{total_images})')
        return self.preloaded_images



    def split_into_sub_images(self, image, sub_width, sub_height, num_images):
        sub_images = []
        height, width, _ = image.shape
        for y in range(0, height, sub_height):
            for x in range(0, width, sub_width):
                sub_image = image[y+y: sub_height, x:x+ sub_width]
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
            return cv2.resize(image, (size, size), interpolation=cv2.INTER_LINEAR)

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
        resized_image = cv2.resize(cropped_image, (size, size), interpolation=cv2.INTER_LINEAR)

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
            raise ValueError("Base directory not set. Please call set_base_dir() before add_image().")

        base_dir = os.path.join(self.base_dir, subfolder_name)
        image_path = os.path.join(base_dir, image_filename)

        print(f"Trying to add image from path: {image_path}")

        # Verify that the image path is correct
        if not os.path.exists(image_path):
            print(f"Image path does not exist: {image_path}")
            return False

        # Load the image using OpenCV
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to load image from path: {image_path}")
            return False

        # Determine the number of sub-images based on your logic
        num_images = self.get_num_images_from_filename(image_filename)

        # Process the image as you do in preload_images
        square_size = self.calculate_square_size()  # Assuming you move the square size logic into a method
        sub_images = self.split_into_sub_images(image, 100, 100, num_images)
        sub_images_with_reversed = sub_images + sub_images[::-1]
        pixmap_images = [self.cv2_to_qpixmap(self.resize_to_square(img, square_size)) for img in sub_images_with_reversed]

        # Store the processed images in the dictionary
        self.preloaded_images[subfolder_name] = pixmap_images
        print(f"Added new image to preloaded images under subfolder: {subfolder_name}")
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
# Create a global instance
image_store = ImageStore()

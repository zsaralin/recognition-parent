import os
import cv2
from PyQt5.QtGui import QImage, QPixmap, QGuiApplication
from logger_setup import logger
import config
class ImageStore:
    def __init__(self):
        self.preloaded_images = {}
        self.zoom_factor = 1.3  # Initial zoom factor, 1.0 means no zoom
        self.compression_ratios = []  # List to store compression ratios

    def preload_images(self, app, base_dir, num_cols=21):
        logger.info('Starting preload images')

        # Calculate square_size based on screen dimensions and number of columns
        screen_sizes = [(screen.size().width(), screen.size().height()) for screen in app.screens()]
        largest_screen_width, largest_screen_height = min(screen_sizes, key=lambda s: s[0] * s[1])
        window_width = largest_screen_width // 2 if config.demo else largest_screen_width
        square_size = window_width // config.num_cols

        total_images = 0
        preloaded_count = 0

        # Count total images
        for root, _, files in os.walk(base_dir):
            total_images += len([file for file in files if file.endswith(('.png', '.jpg', '.jpeg'))])

        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith(('.png', '.jpg', '.jpeg')):  # Adjust based on your image formats
                    image_path = os.path.join(root, file)
                    image = cv2.imread(image_path)
                    if image is not None:
                        num_images = self.get_num_images_from_filename(file)
                        sub_images = self.split_into_sub_images(image, 100, 100, num_images)
                        sub_images_with_reversed = sub_images + sub_images[::-1]
                        pixmap_images = [self.cv2_to_qpixmap(self.resize_to_square(img, square_size)) for img in sub_images_with_reversed]
                        self.preloaded_images[image_path] = pixmap_images
                        preloaded_count += 1
                        print(f"Preloaded image: {image_path} ({preloaded_count}/{total_images})")
                    else:
                        logger.error(f"Failed to load image from path: {image_path}")

        # Print the accumulated zoom factors and compression ratios
        print(f"Image zoom factor: {self.zoom_factor}x")
        avg_compression_ratio = sum(self.compression_ratios) / len(self.compression_ratios) if self.compression_ratios else 0
        print(f"Average compression ratio: {avg_compression_ratio:.2f}% of square size")

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

    def get_sub_images(self, image_path):
        return self.preloaded_images.get(image_path, [])

    def add_image(self, image_path):
        image_path = os.path.join("..", "databases" , "database0", image_path)

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
        num_images = self.get_num_images_from_filename(os.path.basename(image_path))

        # Process the image as you do in preload_images
        square_size = self.calculate_square_size()  # Assuming you move the square size logic into a method
        sub_images = self.split_into_sub_images(image, 100, 100, num_images)
        sub_images_with_reversed = sub_images + sub_images[::-1]
        pixmap_images = [self.cv2_to_qpixmap(self.resize_to_square(img, square_size)) for img in sub_images_with_reversed]

        # Store the processed images in the dictionary
        self.preloaded_images[image_path] = pixmap_images
        print(f"Added new image to preloaded images: {image_path}")
        return True

    def calculate_square_size(self):
        app = QGuiApplication.instance()
        screen_sizes = [(screen.size().width(), screen.size().height()) for screen in app.screens()]
        largest_screen_width, largest_screen_height = min(screen_sizes, key=lambda s: s[0] * s[1])
        window_width = largest_screen_width // 2 if config.demo else largest_screen_width
        return window_width // config.num_cols

# Create a global instance
image_store = ImageStore()

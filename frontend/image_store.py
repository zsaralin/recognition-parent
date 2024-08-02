import os
import cv2
from logger_setup import logger

class ImageStore:
    def __init__(self):
        self.preloaded_images = {}

    def preload_images(self, base_dir):
        logger.info('Starting preload images')
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith(('.png', '.jpg', '.jpeg')):  # Adjust based on your image formats
                    image_path = os.path.join(root, file)
                    image = cv2.imread(image_path)
                    if image is not None:
                        self.preloaded_images[image_path] = image
                        print(f"Preloaded image: {image_path}")
                    else:
                        logger.error(f"Failed to load image from path: {image_path}")
        logger.info('Preload images completed')
        return self.preloaded_images

    def get_image(self, image_path):
        return self.preloaded_images.get(image_path)

    def add_image(self, image_path):
        image_path = os.path.join("..", "databases", "database0", image_path)
        logger.info(f"Trying to add image from path: {image_path}")
        if os.path.exists(image_path):
            image = cv2.imread(image_path)
            if image is not None:
                self.preloaded_images[image_path] = image
                logger.info(f"Added new image to preloaded images: {image_path}")
                return True
            else:
                logger.error(f"Failed to load image from path: {image_path}")
                return False
        else:
            logger.error(f"Image path does not exist: {image_path}")
            return False

# Create a global instance
image_store = ImageStore()

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
                        num_images = self.get_num_images_from_filename(file)
                        sub_images = self.split_into_sub_images(image, 100, 100, num_images)
                        sub_images_with_reversed = sub_images + sub_images[::-1]
                        self.preloaded_images[image_path] = sub_images_with_reversed
                        print(f"Preloaded image: {image_path}")
                    else:
                        logger.error(f"Failed to load image from path: {image_path}")
        logger.info('Preload images completed')
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
        num_images = min(155, int(filename.split('_')[-1].split('.')[0]))
        return num_images

    def get_sub_images(self, image_path):
        return self.preloaded_images.get(image_path, [])


# Create a global instance
image_store = ImageStore()

import os
import cv2
import time  # Import time module for sleep function
from PyQt5.QtGui import QImage, QPixmap, QGuiApplication
from logger_setup import logger
import config
import psutil
from concurrent.futures import ThreadPoolExecutor
import shutil
from PyQt5.QtCore import Qt
import gc  # Garbage collection module

class ImageStore:
    def __init__(self):
        self.preloaded_images = {}
        self.zoom_factor = 1  # Initial zoom factor, 1.0 means no zoom
        self.compression_ratios = []  # List to store compression ratios
        self.base_dir = None
        self.sprite_width = 200
        self.executor = ThreadPoolExecutor(max_workers=2)  # Use threads for parallel processing
        self.preloaded_folders = set()  # Track preloaded folders
        self.square_size = None; 
    
    def get_available_disk_space(self,path="/"):
        """Returns the available disk space in bytes."""
        return psutil.virtual_memory().available  # Returns available RAM in bytes

    def delete_half_folders_in_database(self,base_dir):
        """Deletes half of the folders inside database0 to free up space."""
        database_path = os.path.join(base_dir)
        if not os.path.exists(database_path):
            return

        folders = sorted(os.listdir(database_path))
        num_folders_to_delete = len(folders) // 2
        
        for folder in folders[:num_folders_to_delete]:
            folder_path = os.path.join(database_path, folder)
            if os.path.isdir(folder_path):
                try:
                    shutil.rmtree(folder_path)
                    print(f"Deleted folder: {folder_path}")
                except Exception as e:
                    print(f"Failed to delete {folder_path}: {e}")

    def preload_images(self, app, base_dir, num_cols=21, memory_threshold=0.9, storage_threshold_gb = 5):
        self.base_dir = base_dir
        logger.info('Starting preload images')
        storage_threshold_bytes = storage_threshold_gb * (1024 ** 3)  # Convert GB to bytes
        print(storage_threshold_bytes, self.get_available_disk_space())
        if self.get_available_disk_space() < storage_threshold_bytes:
                print("Low available memory detected! Deleting half of the database0 folders before continuing.")
                # self.delete_half_folders_in_database(base_dir)
    
        # Get the list of screens
        screens = app.screens()

        # Identify the secondary screen (on the left)
        if len(screens) > 1:
            secondary_screen = screens[1]
        else:
            secondary_screen = screens[0]

        # Get the size of the secondary screen
        screen_size = secondary_screen.size()
        screen_geometry = secondary_screen.geometry()
        largest_screen_width = screen_size.width()
        largest_screen_height = screen_size.height()
        window_width = largest_screen_width // 2 if config.demo else largest_screen_width
        window_height = largest_screen_height
        self.square_size = round(window_width / config.num_cols)
        large_square_size = self.square_size * 3
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
                    try:
                        image = cv2.imread(image_path)
                        if image is not None:
                            num_images = self.get_num_images_from_filename(file)
                            sub_images = self.split_into_sub_images(image, self.sprite_width, self.sprite_width, num_images)
                            sub_images_with_reversed = sub_images + sub_images[::-1]

                            standard_pixmaps = [self.cv2_to_qpixmap(img, self.square_size) for img in sub_images_with_reversed]
                            large_pixmaps = [self.cv2_to_qpixmap(img, large_square_size) for img in sub_images_with_reversed]

                            self.preloaded_images[parent_dir] = {
                                'standard': standard_pixmaps,
                                'large': large_pixmaps
                            }
                            preloaded_count += 1
                            self.preloaded_folders.add(root)  # Track the preloaded folder
                            print(f"Preloaded image: {parent_dir} ({preloaded_count}/{total_images})")

                            # Check memory usage after each image
                            system_memory = psutil.virtual_memory()
                            memory_used_percentage = system_memory.percent / 100

                            print(f"System memory used: {system_memory.used / (1024 * 1024):.2f} MB ({memory_used_percentage * 100:.2f}% of total memory)")

                            # If memory usage is above threshold, free up space
                            if memory_used_percentage > memory_threshold:
                                print(f"Memory usage exceeded {memory_threshold * 100}%. Running cleanup.")
                                self.cleanup_memory(base_dir)
                                gc.collect()  # Force garbage collection
                                time.sleep(3)  # Wait a bit for memory to clear

                    except MemoryError:
                        print("MemoryError detected! Running emergency cleanup.")
                        logger.error(f"MemoryError encountered while processing {image_path}")
                        self.cleanup_memory(base_dir)
                        gc.collect()
                        time.sleep(3)  # Wait before continuing to free memory
                    except Exception as e:
                        logger.error(f"Error processing {image_path}: {e}")


        # Print final memory usage
        final_memory = psutil.virtual_memory().used  # in bytes
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

    def cv2_to_qpixmap(self, cv_img, square):
        # Step 1: Convert to RGB
        cv_img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)

        # Step 3: Convert to QImage
        height, width, channel = cv_img_rgb.shape
        bytes_per_line = channel * width
        q_img = QImage(cv_img_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)

        # Step 4: Convert to QPixmap and apply final scaling
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(square, square, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        return scaled_pixmap

    def get_sub_images(self, image_path, size_type='standard'):
        """
        Retrieve preloaded images by path and size type.

        :param image_path: The path to the images.
        :param size_type: 'standard' or 'large' to specify which size to retrieve.
        :return: List of QPixmap objects of the requested size or an empty list if not found.
        """
        if image_path in self.preloaded_images:
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

        self.executor.submit(self.process_image, subfolder_name, image_path, image_filename)
        return True

    def process_image(self, subfolder_name, image_path, image_filename):
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to load image from path: {image_path}")
            return False

        num_images = self.get_num_images_from_filename(image_filename)

        # Calculate sizes based on the preloading strategy
        large_square_size = self.square_size * 3

        sub_images = self.split_into_sub_images(image, self.sprite_width, self.sprite_width, num_images)
        sub_images_with_reversed = sub_images + sub_images[::-1]

        standard_pixmaps = [self.cv2_to_qpixmap(img,  self.square_size ) for img in sub_images_with_reversed]
        large_pixmaps = [self.cv2_to_qpixmap(img, large_square_size) for img in sub_images_with_reversed]

        if subfolder_name not in self.preloaded_images:
            self.preloaded_images[subfolder_name] = {}

        self.preloaded_images[subfolder_name]['standard'] = standard_pixmaps
        self.preloaded_images[subfolder_name]['large'] = large_pixmaps

        print(f"Added new image to preloaded images under subfolder: {subfolder_name}, both standard and large sizes.")
        return True

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

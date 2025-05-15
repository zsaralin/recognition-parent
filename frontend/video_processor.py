import sys
import math
import cv2
import numpy as np
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QImage
from mediapipe_face_detection import MediaPipeFaceDetection
import config
from logger_setup import logger
from text_overlay import add_text_overlay
import time
from one_euro import OneEuroFilter
import asyncio
from backend_communicator import send_add_frame_request, send_no_face_detected_request, set_camera_control, get_camera_control

class FrameCaptureThread(QThread):
    new_frame = pyqtSignal(np.ndarray)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index)
        self.stopped = False

        if not self.cap.isOpened():
            logger.error("Failed to open camera.")

    def run(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.new_frame.emit(frame)

    def stop(self):
        self.stopped = True
        self.cap.release()

    def set_exposure(self, exposure_value):
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_GAIN, exposure_value)
            logger.info(f"Camera exposure set to {exposure_value}")
        else:
            logger.error("Failed to set camera exposure. Camera is not opened.")

class VideoProcessor(QThread):
    frame_ready = pyqtSignal(QPixmap)
    cropped_frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, new_faces, camera_index=0, square_size=300, callback=None):
        super().__init__()
        self.camera_index = camera_index
        self.square_size = square_size
        self.new_faces = new_faces

        self.face_detector = MediaPipeFaceDetection(self.new_faces)
        self.callback = callback

        self.capture_thread = FrameCaptureThread(camera_index=self.camera_index)
        self.capture_thread.new_frame.connect(self.process_frame)
        self.capture_thread.start()

        self.setPriority(QThread.HighestPriority)

        self.stopped = False

        # Initialize One Euro Filters for position and size
        self.freq = 30.0
        self.min_cutoff = .001
        self.beta = .0001
        self.euro_filter_cx = OneEuroFilter(self.freq, min_cutoff=self.min_cutoff, beta=self.beta)
        self.euro_filter_cy = OneEuroFilter(self.freq, min_cutoff=self.min_cutoff, beta=self.beta)
        self.euro_filter_w = OneEuroFilter(self.freq, min_cutoff=self.min_cutoff, beta=self.beta)
        self.euro_filter_h = OneEuroFilter(self.freq, min_cutoff=self.min_cutoff, beta=self.beta)

        self.last_cropped_frame = None
        self.last_cropped_position = None
        self.no_face_counter = 0

        # Tracking new face detection for saved frame feature
        self.consistent_detection_counter = 0
        self.capture_frame_counter = 0
        self.saved_frame = None
        self.position_history = []
        self.max_history_length = 20  # Number of frames to check for stability

        # Initialize FPS calculation
        self.prev_time = time.time()
        self.fps = 0

        # Initialize overlay image
        self.overlay_image = None

        # Timer to check brightness every minute
        # self.brightness_timer = QTimer(self)
        # self.brightness_timer.timeout.connect(self.handle_brightness_check)
        # self.brightness_timer.start(10000)  # Check brightness every 3 seconds

        # Flag to indicate if a face has been detected since the last brightness check
        self.face_detected_since_last_check = False

        # Exposure adjustment variables
        self.is_adjusting_exposure = False
        self.cancel_adjustment = False

        self.zoom_out_step = 2  # How much to zoom out per frame
        self.current_zoom_size = None
        self.max_zoom_size = None  # Maximum zoom size, i.e., the full frame size

        self.start_time = time.time()  # Capture the start time

    def handle_brightness_check(self):
        """Handles brightness check; only checks if a face has been detected since the last check."""
        if self.face_detected_since_last_check:
            self.check_brightness()
            self.face_detected_since_last_check = False
        else:
            logger.info("No face detected in the last check period. Skipping brightness check.")

    def check_brightness(self):
        """Check and adjust brightness based on the current frame if auto EV is enabled."""
        if self.last_cropped_frame is not None:
            # Convert to grayscale
            gray_frame = cv2.cvtColor(self.last_cropped_frame, cv2.COLOR_BGR2GRAY)
            # Calculate the average brightness
            brightness = np.mean(gray_frame)
            print(f"Average brightness of the cropped frame: {brightness:.2f}")

            # if config.auto_ev:
            #     self.adjust_exposure_based_on_brightness(brightness)

    def adjust_exposure_based_on_brightness(self, current_brightness):
        """Adjusts the exposure time based on the current brightness level."""
        # if self.is_adjusting_exposure:
        #     # Skip this execution if an adjustment is already in progress
        #     return

        # self.is_adjusting_exposure = True
        # self.cancel_adjustment = False  # Reset the cancel flag
        # target_brightness = config.brightness

        # def adjust_exposure(current_brightness):
        #     if self.cancel_adjustment:
        #         # Stop the loop if a new brightness adjustment is requested
        #         self.is_adjusting_exposure = False
        #         return

        #     # Calculate the difference between current and target brightness
        #     brightness_difference = target_brightness - current_brightness

        #     # Determine step size based on the brightness difference
        #     step_size = max(5, abs(brightness_difference) // 5)  # Larger steps for larger differences, minimum step of 5

        #     current_exposure = get_camera_control('absoluteExposureTime')
        #     print(f"Brightness difference: {brightness_difference}, Step size: {step_size}")

        #     if brightness_difference > 15 and current_exposure < 1200:  # Cap at 1200
        #         # Increase exposure time based on the step size, but cap it at 1200
        #         new_exposure = min(current_exposure + step_size, 1200)
        #         set_camera_control('absoluteExposureTime', new_exposure)
        #     elif brightness_difference < -15 and current_exposure > 1:
        #         # Decrease exposure time based on the step size
        #         new_exposure = max(current_exposure - step_size, 1)
        #         set_camera_control('absoluteExposureTime', new_exposure)
        #     else:
        #         # Exit the loop if brightness is within the desired range
        #         self.is_adjusting_exposure = False
        #         return

        #     # Fetch the updated brightness after changing exposure
        #     updated_brightness = self.get_updated_brightness()

        #     # Delay the next adjustment by 500 ms
        #     QTimer.singleShot(2000, lambda: adjust_exposure(updated_brightness))

        # # Start the adjustment process
        # adjust_exposure(current_brightness)

    def get_updated_brightness(self):
        """Calculates the brightness of the current frame."""
        if self.last_cropped_frame is not None:
            gray_frame = cv2.cvtColor(self.last_cropped_frame, cv2.COLOR_BGR2GRAY)
            return np.mean(gray_frame)
        return None

    def get_current_exposure_time(self):
        """Fetch the current exposure time from the backend."""
        response = get_current_exposure_time()
        if response:
            try:
                return int(response.split()[-1])  # Assumes the number is at the end of the string
            except ValueError as e:
                logger.error(f"Error parsing exposure time: {e}")
                return 1  # Default to a minimum value if parsing fails
        else:
            logger.error("Failed to get current exposure time.")
            return 1

    def is_stable(self):
        if len(self.position_history) < self.max_history_length:
            return False

        # Calculate the average position
        avg_cx = sum(pos[0] for pos in self.position_history) / len(self.position_history)
        avg_cy = sum(pos[1] for pos in self.position_history) / len(self.position_history)

        # Check if all positions are within the stability threshold
        for cx, cy in self.position_history:
            if abs(cx - avg_cx) > config.move_threshold or abs(cy - avg_cy) > config.move_threshold:
                return False

        return True

    def create_text_overlay(self, width, height):
        """Create the text overlay and resize it to the expected frame size."""
        scale_factor = 50  # Increase this to improve text sharpness
        high_res_width = width * scale_factor
        high_res_height = height * scale_factor

        # Create a high-resolution blank image
        overlay = np.zeros((high_res_height, high_res_width, 4), dtype=np.uint8)  # Using a 4-channel image for RGBA

        # Add text overlay at high resolution
        overlay_with_text = add_text_overlay(overlay, scale_factor=scale_factor)

        # Resize the overlay back to the original size
        overlay_with_text = cv2.resize(overlay_with_text, (width, height), interpolation=cv2.INTER_LANCZOS4)

        return overlay_with_text

    def update_text_overlay(self):
        """Update the overlay image whenever the font size changes."""
        self.overlay_image = self.create_text_overlay(self.square_size, self.square_size)

    def apply_text_overlay(self, frame):
        """Apply the current text overlay onto the frame."""
        if self.overlay_image is None:
            self.update_text_overlay()

        # Simply overlay the pre-rendered and pre-resized image
        alpha_channel = self.overlay_image[:, :, 3] / 255.0  # Extract alpha channel and normalize it to [0, 1]
        for c in range(3):  # For each RGB channel
            frame[:, :, c] = np.where(alpha_channel > 0, self.overlay_image[:, :, c], frame[:, :, c])

    def process_frame(self, frame):
        if self.stopped:
            return

        try:
            if frame is None or frame.size == 0:
                logger.error("No valid frame available. Retrying...")
                return
            frame = cv2.flip(frame, 1)  # Flip along the vertical axis to create a mirror effect
            # frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)  # Rotate the frame 90 degrees clockwise

            # Keep the original frame intact for zooming out
            original_frame = frame.copy()

            # Detect faces in the frame
            frame, bbox = self.face_detector.detect_faces(frame, self.callback)

            if bbox:
                # Face detected, smoothly zoom into the bounding box size
                x, y, w, h = bbox
                cx, cy = x + w // 2, y + h // 2

                w = int(w * config.bbox_multiplier)
                h = int(h * config.bbox_multiplier)

                # Filter the zoom-in size and position using One Euro filters
                filtered_cx = self.euro_filter_cx.filter(cx, time.time())
                filtered_cy = self.euro_filter_cy.filter(cy, time.time())
                filtered_w = self.euro_filter_w.filter(w, time.time())
                filtered_h = self.euro_filter_h.filter(h, time.time())

                filtered_w = max(1, int(filtered_w))
                filtered_h = max(1, int(filtered_h))
                filtered_cx = int(filtered_cx)
                filtered_cy = int(filtered_cy)

                forehead_offset = int(filtered_h * 0.1)  # Move the crop 20% of the face height lower
                filtered_cy -= forehead_offset  # Lower the crop by the forehead offset

                # Store the last known cropped position for smooth transitions
                self.last_cropped_position = (filtered_cx, filtered_cy, filtered_w, filtered_h)
                self.no_face_counter = 0


                # Update position history
                self.position_history.append((filtered_cx, filtered_cy))
                if len(self.position_history) > self.max_history_length:
                    self.position_history.pop(0)

                # Update consistent detection counter and handle saved frame logic
                if self.consistent_detection_counter < 30:
                    self.consistent_detection_counter += 1
                elif self.consistent_detection_counter == 30 and self.is_stable():
                    # Capture the saved frame after 30 consistent detections and stability
                    self.saved_frame = original_frame.copy()
                    self.consistent_detection_counter += 1  # Prevent further saving
                elif not self.is_stable():
                    self.new_faces.treat_as_no_face_detected()

                self.current_zoom_size = max(filtered_w, filtered_h)

                cropped_frame = self.extract_frame(original_frame, self.current_zoom_size, self.current_zoom_size, filtered_cx, filtered_cy)

            else:
                # No face detected: start or continue zooming out
                self.no_face_counter += 1
                if self.no_face_counter <= 50:
                    # Show the last known cropped position
                    if self.last_cropped_position:
                        filtered_cx, filtered_cy, filtered_w, filtered_h = self.last_cropped_position
                        cropped_frame = self.extract_frame(original_frame, filtered_w, filtered_h, filtered_cx, filtered_cy)
                    else:
                        # If no previous face was detected, show the center of the frame
                        h, w = original_frame.shape[:2]
                        cropped_frame = self.extract_frame(original_frame, self.square_size, self.square_size, w // 2, h // 2)
                else:
                    # After 50 frames without a face, start zooming out
                    cropped_frame = self.zoom_out(original_frame)

            # Resize and process the frame for display
            resized_frame = self.resize_to_square(cropped_frame, self.square_size)
            if bbox and config.create_sprites and self.is_stable():
                send_add_frame_request(cropped_frame, (x, y, w, h))

            # Apply text overlays, display FPS, and emit the processed frame
            self.apply_text_overlay(resized_frame)
            self.display_fps(resized_frame)
            pixmap = self.convert_to_qpixmap(resized_frame)
            self.frame_ready.emit(pixmap)

            # Store the last cropped frame
            self.last_cropped_frame = cropped_frame

        except Exception as e:
            logger.exception(f"Error processing frame: {e}")

    def zoom_out(self, frame):
        """Gradually zoom out from the last known cropped position, always returning a square crop."""
        h, w = frame.shape[:2]

        if self.current_zoom_size is None:
            # Start zoom-out from the last cropped area or from the center if no last position
            if self.last_cropped_position:
                _, _, last_w, last_h = self.last_cropped_position
                self.current_zoom_size = max(last_w, last_h)
            else:
                self.current_zoom_size = self.square_size

        # Gradually increase the zoom size to zoom out
        self.current_zoom_size += self.zoom_out_step

        # Ensure the zoom size doesn't exceed the frame dimensions
        self.current_zoom_size = min(self.current_zoom_size, min(w, h))

        # Apply One Euro filtering to smooth out the zoom size
        filtered_w = self.euro_filter_w.filter(self.current_zoom_size, time.time())
        filtered_h = self.euro_filter_h.filter(self.current_zoom_size, time.time())

        # Ensure the filtered zoom size doesn't exceed frame dimensions
        filtered_w = min(filtered_w, min(w, h))
        filtered_h = min(filtered_h, min(w, h))

        # Determine the center point (last face position or center of frame)
        if self.last_cropped_position:
            last_cx, last_cy, _, _ = self.last_cropped_position
            cx, cy = last_cx, last_cy  # Zoom out from the last face position
        else:
            cx, cy = w // 2, h // 2  # Default to center if no last position

        crop_w, crop_h = int(filtered_w), int(filtered_h)

        # Ensure the cropping area stays within frame bounds
        return self.extract_frame(frame, crop_w, crop_h, cx, cy)


    def extract_frame(self, frame, w, h, cx, cy):
        frame_height, frame_width = frame.shape[:2]

        size = max(w, h)
        x1 = max(0, cx - size // 2)
        y1 = max(0, cy - size // 2)
        x2 = min(frame_width, x1 + size)
        y2 = min(frame_height, y1 + size)

        if x2 - x1 < size:
            x1 = max(0, x2 - size)
        if y2 - y1 < size:
            y1 = max(0, y2 - size)

        crop_size = min(x2 - x1, y2 - y1)
        x2 = x1 + crop_size
        y2 = y1 + crop_size

        if crop_size <= 0:
            logger.error(f"Invalid crop size: {crop_size}. Frame extraction failed.")
            return None

        cropped_frame = frame[y1:y2, x1:x2]
        return cropped_frame if cropped_frame.size > 0 else None

    def resize_to_square(self, frame, size):
        if frame is None or frame.size == 0:
            logger.error("Cannot resize an empty frame.")
            return None
        return cv2.resize(frame, (size, size), interpolation=cv2.INTER_AREA) # INTER_LANCZOS4 , INTER_CUBIC

    def convert_to_qpixmap(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        q_img = QImage(frame.data, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_RGB888)
        return QPixmap.fromImage(q_img)

    def display_fps(self, frame):
        current_time = time.time()
        self.fps = 1.0 / (current_time - self.prev_time)
        self.prev_time = current_time

        if config.show_fps:
            cv2.putText(frame, f'FPS: {int(self.fps)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    def stop(self):
        self.stopped = True
        self.capture_thread.stop()
        if self.isRunning():
            self.terminate()

    def get_cropped_frame(self):
        return self.last_cropped_frame

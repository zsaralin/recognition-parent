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
from backend_communicator import send_add_frame_request, send_no_face_detected_request

class VideoProcessor(QThread):
    frame_ready = pyqtSignal(QPixmap)
    cropped_frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, new_faces, camera_index=0, square_size=300, callback=None):
        super().__init__()
        self.camera_index = camera_index
        self.square_size = square_size
        self.new_faces = new_faces

        self.face_detector = MediaPipeFaceDetection(self.new_faces)
        self.cap = cv2.VideoCapture(self.camera_index)
        self.callback = callback

        if not self.cap.isOpened():
            logger.error("Failed to open camera.")
            return

        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.timer.start(10)
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

    def is_stable(self):
        if len(self.position_history) < self.max_history_length:
            return False

        # Calculate the average position
        avg_cx = sum(pos[0] for pos in self.position_history) / len(self.position_history)
        avg_cy = sum(pos[1] for pos in self.position_history) / len(self.position_history)

        # Check if all positions are within the stability threshold
        for cx, cy in self.position_history:
            if abs(cx - avg_cx) > config.move_threshold or abs(cy - avg_cy) >  config.move_threshold:
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

    def process_frame(self):
        if self.stopped:
            return

        try:
            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                logger.error("No valid frame available. Retrying...")
                return

            # Flip the frame vertically if not in demo mode
            if not config.demo:
                frame = cv2.flip(frame, 0)

            # Apply rotation if a rotation angle is set
            if config.rotation_angle != 0:
                if config.rotation_angle == 90:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                elif config.rotation_angle == 180:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                elif config.rotation_angle == 270:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

            # Mirror the frame horizontally if the mirror option is enabled
            if config.mirror:
                frame = cv2.flip(frame, 1)

            # Detect faces in the frame
            original_frame = frame.copy()
            frame, bbox = self.face_detector.detect_faces(frame, self.callback)

            current_time = time.time()

            if bbox:
                x, y, w, h = bbox
                cx, cy = x + w // 2, y + h // 2

                w = int(w * config.bbox_multiplier)
                h = int(h * config.bbox_multiplier)

                filtered_cx = self.euro_filter_cx.filter(cx, current_time)
                filtered_cy = self.euro_filter_cy.filter(cy, current_time)
                filtered_w = self.euro_filter_w.filter(w, current_time)
                filtered_h = self.euro_filter_h.filter(h, current_time)

                filtered_w = max(1, int(filtered_w))
                filtered_h = max(1, int(filtered_h))
                filtered_cx = int(filtered_cx)
                filtered_cy = int(filtered_cy)

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

            else:
                self.no_face_counter += 1
                self.consistent_detection_counter = 0  # Reset if no face is detected
                self.position_history.clear()  # Clear position history when no face is detected
                if self.no_face_counter > 50:  # No face detected for a while, reset last known position
                    if self.saved_frame is not None and config.show_saved_frame:
                        frame = self.saved_frame
                    else:
                        logger.info("No saved frame available or not showing saved frame. Continuing with normal processing.")

            if self.last_cropped_position:
                filtered_cx, filtered_cy, filtered_w, filtered_h = self.last_cropped_position
            else:
                h, w = original_frame.shape[:2]
                filtered_cx, filtered_cy, filtered_w, filtered_h = w // 2, h // 2, w, h  # This case should rarely be reached now

            cropped_frame = self.extract_frame(frame, filtered_w, filtered_h, filtered_cx, filtered_cy)

            resized_frame = self.resize_to_square(cropped_frame, self.square_size)

            self.new_faces.set_cropped_frame(cropped_frame)

            if bbox and config.create_sprites and self.is_stable():
                send_add_frame_request(resized_frame, (x, y, w, h))

            self.apply_text_overlay(resized_frame)  # Apply the current overlay
            self.display_fps(resized_frame)
            pixmap = self.convert_to_qpixmap(resized_frame)

            self.frame_ready.emit(pixmap)
            self.cropped_frame_ready.emit(cropped_frame)

            self.last_cropped_frame = cropped_frame

        except Exception as e:
            logger.exception(f"Error processing frame: {e}")

    def convert_image_to_data_url(frame):
        """Convert an image to JPEG format and encode it as a Base64 string."""
        _, buffer = cv2.imencode('.jpg', frame)  # Encode the frame as JPEG
        jpg_as_text = base64.b64encode(buffer).decode()  # Convert to Base64
        return f"data:image/jpeg;base64,{jpg_as_text}"

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
        return cv2.resize(frame, (size, size), interpolation=cv2.INTER_LINEAR)

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
        self.timer.stop()
        if self.isRunning():
            self.terminate()

        self.cap.release()
    def set_exposure(self, exposure_value):
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_GAIN, exposure_value)
            logger.info(f"Camera exposure set to {exposure_value}")
        else:
            logger.error("Failed to set camera exposure. Camera is not opened.")

    def get_cropped_frame(self):
        return self.last_cropped_frame

import sys
import math
import cv2
import numpy as np
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage
from mediapipe_face_detection import MediaPipeFaceDetection
import config
from logger_setup import logger
from text_overlay import add_text_overlay
import time
from one_euro import OneEuroFilter  # Import the One Euro filter
import asyncio
from backend_communicator import send_add_frame_request

class VideoProcessor(QThread):
    frame_ready = pyqtSignal(QImage)

    def __init__(self, camera_index=0, square_size=300, callback=None):
        super().__init__()
        self.camera_index = camera_index
        self.square_size = square_size
        self.face_detector = MediaPipeFaceDetection()
        self.cap = cv2.VideoCapture(self.camera_index)
        self.callback = callback
        self.bbox_multiplier = config.bbox_multiplier

        if not self.cap.isOpened():
            logger.error("Failed to open camera.")
            return

        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.timer.start(10)  # Adjust timer interval for better performance
        self.setPriority(QThread.HighestPriority)

        self.stopped = False

        # Initialize One Euro Filters for position and size
        self.freq = 30.0  # Example frequency, you may need to adjust based on your application
        self.min_cutoff = .001  # Higher value for more smoothing
        self.beta = .0001       # Lower value for less reactivity to speed changes
        self.euro_filter_cx = OneEuroFilter(self.freq, min_cutoff=self.min_cutoff, beta=self.beta)
        self.euro_filter_cy = OneEuroFilter(self.freq, min_cutoff=self.min_cutoff, beta=self.beta)
        self.euro_filter_w = OneEuroFilter(self.freq, min_cutoff=self.min_cutoff, beta=self.beta)
        self.euro_filter_h = OneEuroFilter(self.freq, min_cutoff=(self.min_cutoff), beta=self.beta)

        self.last_cropped_frame = None  # Proper initialization of the attribute

        # Initialize FPS calculation
        self.prev_time = time.time()
        self.fps = 0

        # Initialize the active state tracking
        self.active_threshold = 10  # Define an appropriate threshold value
        self.is_active = False
        self.saved_frame = None  # Variable to store the frame when filter becomes inactive

        # Counter for consecutive frames without a face
        self.no_face_counter = 0
        self.no_face_threshold = 0  # Number of consecutive frames to consider no face detected

        # Tolerance for considering the frame as stable (e.g., in pixels)
        self.stability_threshold = 15  # Adjust as needed

        # Initialize previous bounding box center
        self.previous_cx = None
        self.previous_cy = None

        # Buffer for storing recent bounding box centers
        self.bbox_buffer = []
        self.bbox_buffer_size = 10  # Increase the number of frames to consider for stability

    def process_frame(self):
        if self.stopped:
            return

        try:
            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                logger.error("No valid frame available.")
                return

            # Flip the frame vertically if not in demo mode
            if not config.demo:
                frame = cv2.flip(frame, 0)

            original_frame = frame.copy()
            frame, bbox = self.face_detector.detect_faces(frame, self.callback)

            current_time = time.time()

            if bbox:
                x, y, w, h = bbox
                cx, cy = x + w // 2, y + h // 2

                # Apply bounding box multiplier
                w = int(w * self.bbox_multiplier)
                h = int(h * self.bbox_multiplier)

                # Apply One Euro filter
                filtered_cx = self.euro_filter_cx.filter(cx, current_time)
                filtered_cy = self.euro_filter_cy.filter(cy, current_time)
                filtered_w = self.euro_filter_w.filter(w, current_time)
                filtered_h = self.euro_filter_h.filter(h, current_time)

                # Ensure dimensions are valid
                filtered_w = max(1, int(filtered_w))
                filtered_h = max(1, int(filtered_h))
                filtered_cx = int(filtered_cx)
                filtered_cy = int(filtered_cy)

                self.last_cropped_position = (filtered_cx, filtered_cy, filtered_w, filtered_h)
                self.no_face_counter = 0
            else:
                self.no_face_counter += 1

            # Use the last known position if available, otherwise use the full frame
            if self.last_cropped_position:
                filtered_cx, filtered_cy, filtered_w, filtered_h = self.last_cropped_position
            else:
                h, w = original_frame.shape[:2]
                filtered_cx, filtered_cy, filtered_w, filtered_h = w // 2, h // 2, w, h

            # Extract frame based on filtered prediction or last known position
            cropped_frame = self.extract_frame(original_frame, filtered_w, filtered_h, filtered_cx, filtered_cy)
            resized_frame = self.resize_to_square(cropped_frame, self.square_size)

            if bbox and config.create_sprites:
                send_add_frame_request(resized_frame, (x, y, w, h))

            add_text_overlay(resized_frame)
            self.display_fps(resized_frame)
            q_img = self.convert_to_qimage(resized_frame)

            # Emit the frame ready signal
            self.frame_ready.emit(q_img)

            self.last_cropped_frame = cropped_frame

        except Exception as e:
            logger.exception(f"Error processing frame: {e}")

    def is_bbox_stable(self):
        if len(self.bbox_buffer) < self.bbox_buffer_size:
            return False
        avg_cx = sum(x for x, y in self.bbox_buffer) / self.bbox_buffer_size
        avg_cy = sum(y for x, y in self.bbox_buffer) / self.bbox_buffer_size
        return all(abs(cx - avg_cx) <= self.stability_threshold and abs(cy - avg_cy) <= self.stability_threshold
                   for cx, cy in self.bbox_buffer)

    def is_stable(self, cx, cy, filtered_cx, filtered_cy, threshold):
        return abs(cx - filtered_cx) <= threshold and abs(cy - filtered_cy) <= threshold

    def extract_frame(self, frame, w, h, cx, cy):
        frame_height, frame_width = frame.shape[:2]

        # Ensure square crop
        size = max(w, h)

        # Calculate crop boundaries
        x1 = max(0, cx - size // 2)
        y1 = max(0, cy - size // 2)
        x2 = min(frame_width, x1 + size)
        y2 = min(frame_height, y1 + size)

        # Adjust if crop goes over right or bottom edge
        if x2 - x1 < size:
            x1 = max(0, x2 - size)
        if y2 - y1 < size:
            y1 = max(0, y2 - size)

        # Final adjustment to ensure square crop
        crop_size = min(x2 - x1, y2 - y1)
        x2 = x1 + crop_size
        y2 = y1 + crop_size

        return frame[y1:y2, x1:x2]

    def resize_to_square(self, frame, size):
        return cv2.resize(frame, (size, size), interpolation=cv2.INTER_LINEAR)

    def convert_to_qimage(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        q_img = QImage(frame.data, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_RGB888)
        return q_img

    def display_fps(self, frame):
        current_time = time.time()
        self.fps = 1.0 / (current_time - self.prev_time)
        self.prev_time = current_time

        if config.show_fps:
            cv2.putText(frame, f'FPS: {int(self.fps)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    def stop(self):
        print("VideoProcessor: Stopping")
        self.stopped = True
        self.timer.stop()
        self.cap.release()
        self.quit()
        self.wait()

    def update_config(self):
        self.bbox_multiplier = config.bbox_multiplier

    def set_exposure(self, exposure_value):
        """
        Sets the exposure of the camera.
        :param exposure_value: The desired exposure value.
        """
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_GAIN, exposure_value)
            logger.info(f"Camera exposure set to {exposure_value}")
        else:
            logger.error("Failed to set camera exposure. Camera is not opened.")

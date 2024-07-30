from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage
from mediapipe_face_detection import MediaPipeFaceDetection
import numpy as np
import config
from logger_setup import logger
from text_overlay import add_text_overlay
import time
import cv2
from one_euro import OneEuroFilter  # Import the One Euro filter

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
        self.euro_filter_h = OneEuroFilter(self.freq, min_cutoff=self.min_cutoff, beta=self.beta)

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

        # Threshold for detecting a significant jump indicating a new face
        self.jump_threshold = 100  # Adjust as needed

        # Buffer for storing recent bounding box centers
        self.bbox_buffer = []
        self.bbox_buffer_size = 10  # Increase the number of frames to consider for stability

        # Timer for sending frame to backend
        self.send_frame_timer = QTimer()
        self.send_frame_timer.setSingleShot(True)
        self.send_frame_timer.timeout.connect(self.send_frame_to_backend)

    def run(self):
        self.exec_()

    def process_frame(self):
        if self.stopped:
            return

        try:
            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                if config.show_saved_frame and self.saved_frame is not None:
                    resized_frame = self.resize_to_square(self.saved_frame, self.square_size)
                    add_text_overlay(resized_frame)
                    self.display_fps(resized_frame)
                    q_img = self.convert_to_qimage(resized_frame)
                    self.frame_ready.emit(q_img)
                else:
                    logger.error("No valid frame available.")
                return

            original_frame = frame.copy()
            frame, bbox = self.face_detector.detect_faces(frame, self.callback)
            if bbox:
                x, y, w, h = bbox
                cx, cy = x + w // 2, y + h // 2

                # Check for significant jump indicating a new face
                if self.previous_cx is not None and self.previous_cy is not None:
                    if self.is_significant_jump(cx, cy, self.previous_cx, self.previous_cy, self.jump_threshold):
                        bbox = None  # Manually set bbox to None to indicate a new face
                        self.previous_cx = None
                        self.previous_cy = None

                if bbox is not None:
                    # Update previous bounding box center
                    self.previous_cx = cx
                    self.previous_cy = cy

                    # Apply bounding box multiplier
                    w = int(w * self.bbox_multiplier)
                    h = int(h * self.bbox_multiplier)

                    # Apply One Euro filter
                    current_time = time.time()
                    filtered_cx = self.euro_filter_cx.filter(cx, current_time)
                    filtered_cy = self.euro_filter_cy.filter(cy, current_time)
                    filtered_w = self.euro_filter_w.filter(w, current_time)
                    filtered_h = self.euro_filter_h.filter(h, current_time)

                    # Ensure dimensions are valid
                    filtered_w = max(1, int(filtered_w))
                    filtered_h = max(1, int(filtered_h))
                    filtered_cx = int(filtered_cx)
                    filtered_cy = int(filtered_cy)

                    # Extract frame based on filtered prediction
                    cropped_frame = self.extract_frame(original_frame, filtered_w, filtered_h, filtered_cx, filtered_cy)
                    resized_frame = self.resize_to_square(cropped_frame, self.square_size)

                    self.last_cropped_frame = cropped_frame
                    self.last_cropped_position = (filtered_cx, filtered_cy, filtered_w, filtered_h)  # Save the last position and size

                    add_text_overlay(resized_frame)
                    self.display_fps(resized_frame)
                    q_img = self.convert_to_qimage(resized_frame)

                    # Emit the frame ready signal
                    self.frame_ready.emit(q_img)

                    # Add the current bounding box center to the buffer
                    self.bbox_buffer.append((filtered_cx, filtered_cy))
                    if len(self.bbox_buffer) > self.bbox_buffer_size:
                        self.bbox_buffer.pop(0)

                    # Check if the bounding box is stable
                    if self.is_bbox_stable():
                        if not self.send_frame_timer.isActive():
                            self.send_frame_timer.start(1000)  # Wait for 1 second before sending

                    self.no_face_counter = 0

            else:
                self.no_face_counter += 1
                if self.no_face_counter >= self.no_face_threshold:
                    if self.last_cropped_frame is not None and self.last_cropped_position is not None:
                        filtered_cx, filtered_cy, filtered_w, filtered_h = self.last_cropped_position
                        cropped_frame = self.extract_frame(original_frame, filtered_w, filtered_h, filtered_cx, filtered_cy)
                        resized_frame = self.resize_to_square(cropped_frame, self.square_size)

                        add_text_overlay(resized_frame, text="Live")
                        self.display_fps(resized_frame)
                        q_img = self.convert_to_qimage(resized_frame)
                        self.frame_ready.emit(q_img)
                    else:
                        if config.show_saved_frame and self.saved_frame is not None:
                            resized_frame = self.resize_to_square(self.saved_frame, self.square_size)
                            add_text_overlay(resized_frame)
                            self.display_fps(resized_frame)
                            q_img = self.convert_to_qimage(resized_frame)
                            self.frame_ready.emit(q_img)

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

    def is_significant_jump(self, cx, cy, previous_cx, previous_cy, threshold):
        return abs(cx - previous_cx) > threshold or abs(cy - previous_cy) > threshold

    def extract_frame(self, frame, w, h, cx, cy):
        half_w = w // 2
        half_h = h // 2
        x1 = max(0, cx - half_w)
        y1 = max(0, cy - half_h)
        x2 = min(frame.shape[1], cx + half_w)
        y2 = min(frame.shape[0], cy + half_h)

        if (x2 - x1) != (y2 - y1):
            if (x2 - x1) > (y2 - y1):
                diff = (x2 - x1) - (y2 - y1)
                if y1 - diff // 2 < 0:
                    y2 = y1 + (x2 - x1)
                    y1 = 0
                elif y2 + diff // 2 > frame.shape[0]:
                    y1 = y2 - (x2 - x1)
                    y2 = frame.shape[0]
                else:
                    y1 = max(0, y1 - diff // 2)
                    y2 = min(frame.shape[0], y2 + diff // 2)
            else:
                diff = (y2 - y1) - (x2 - x1)
                if x1 - diff // 2 < 0:
                    x2 = x1 + (y2 - y1)
                    x1 = 0
                elif x2 + diff // 2 > frame.shape[1]:
                    x1 = x2 - (y2 - y1)
                    x2 = frame.shape[1]
                else:
                    x1 = max(0, x1 - diff // 2)
                    x2 = min(frame.shape[1], x2 + diff // 2)

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

    def send_frame_to_backend(self):
        if self.last_cropped_frame is not None:
            self.saved_frame = self.last_cropped_frame  # Set the saved frame to the last frame sent
            self.send_to_backend(self.last_cropped_frame)

    def send_to_backend(self, frame):
        # Implement the logic to send the frame to the backend
        pass

    def stop(self):
        print("VideoProcessor: Stopping")
        self.stopped = True
        self.timer.stop()
        self.cap.release()
        self.quit()
        self.wait()

    def update_config(self):
        self.bbox_multiplier = config.bbox_multiplier
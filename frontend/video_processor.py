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
        self.beta = .0001  # Lower value for less reactivity to speed changes
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
        self.no_face_threshold = 15  # Number of consecutive frames to consider no face detected

        # Counter to delay saving the frame
        self.save_frame_delay = 3
        self.save_frame_counter = 0

    def run(self):
        self.exec_()

    def process_frame(self):
        if self.stopped:
            return

        try:
            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                if self.saved_frame is not None:
                    # Handle case where saved frame is used when no valid frame is available
                    resized_frame = self.resize_to_square(self.saved_frame, self.square_size)
                    add_text_overlay(resized_frame, text="Live")
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

                # Apply bounding box multiplier
                w = int(w * self.bbox_multiplier)
                h = int(h * self.bbox_multiplier)

                # Apply One Euro filter
                current_time = time.time()
                cx = self.euro_filter_cx.filter(cx, current_time)
                cy = self.euro_filter_cy.filter(cy, current_time)
                w = self.euro_filter_w.filter(w, current_time)
                h = self.euro_filter_h.filter(h, current_time)

                # Ensure dimensions are valid
                w = max(1, int(w))
                h = max(1, int(h))
                cx = int(cx)
                cy = int(cy)

                # Extract frame based on filtered prediction
                cropped_frame = self.extract_frame(original_frame, w, h, cx, cy)
                resized_frame = self.resize_to_square(cropped_frame, self.square_size)

                self.last_cropped_frame = cropped_frame

                add_text_overlay(resized_frame)
                self.display_fps(resized_frame)
                q_img = self.convert_to_qimage(resized_frame)
                self.frame_ready.emit(q_img)

                # Check if the face movement distance exceeds threshold to determine activity
                distance = np.linalg.norm(np.array([x + w // 2, y + h // 2]) - np.array([cx, cy]))
                if distance > self.active_threshold:
                    self.is_active = True
                    self.save_frame_counter = 0  # Reset counter when activity is detected
                else:
                    if self.is_active:
                        self.save_frame_counter += 1
                        if self.save_frame_counter >= self.save_frame_delay:
                            self.saved_frame = cropped_frame
                            self.save_frame_counter = 0  # Reset counter after saving frame
                    self.is_active = False

                self.no_face_counter = 0  # Reset no face counter when a face is detected
            else:
                self.no_face_counter += 1
                if self.saved_frame is not None and self.no_face_counter >= self.no_face_threshold:
                    # Use saved frame when no face is detected for too long
                    resized_frame = self.resize_to_square(self.saved_frame, self.square_size)
                    add_text_overlay(resized_frame, text="Live")
                    self.display_fps(resized_frame)
                    q_img = self.convert_to_qimage(resized_frame)
                    self.frame_ready.emit(q_img)

        except Exception as e:
            logger.exception(f"Error processing frame: {e}")

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

    def stop(self):
        print("VideoProcessor: Stopping")
        self.stopped = True
        self.timer.stop()
        self.cap.release()
        self.quit()
        self.wait()

    def update_config(self):
        self.bbox_multiplier = config.bbox_multiplier

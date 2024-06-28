import cv2
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage
from mediapipe_face_detection import MediaPipeFaceDetection
import numpy as np
import config
from logger_setup import logger
from text_overlay import add_text_overlay  # Import the new function

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

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.timer.start(0)  # Process frames as quickly as possible

        self.stopped = False

        # Initialize Kalman Filter for position and size
        self.kalman = cv2.KalmanFilter(8, 4)
        self.kalman.measurementMatrix = np.zeros((4, 8), np.float32)
        self.kalman.measurementMatrix[0, 0] = 1
        self.kalman.measurementMatrix[1, 1] = 1
        self.kalman.measurementMatrix[2, 2] = 1
        self.kalman.measurementMatrix[3, 3] = 1

        self.kalman.transitionMatrix = np.eye(8, dtype=np.float32)
        for i in range(4):
            self.kalman.transitionMatrix[i, i + 4] = 1

        self.kalman.processNoiseCov = np.eye(8, dtype=np.float32) * 1e-5
        self.kalman.measurementNoiseCov = np.eye(4, dtype=np.float32) * 10

        self.last_cropped_frame = None  # Proper initialization of the attribute

    def run(self):
        # This method is required to start the QThread event loop
        self.exec_()

    def process_frame(self):
        if self.stopped:
            return

        try:
            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                if self.last_cropped_frame is not None:
                    resized_frame = self.resize_to_square(self.last_cropped_frame, self.square_size)
                    add_text_overlay(resized_frame)
                    q_img = self.convert_to_qimage(resized_frame)
                    self.frame_ready.emit(q_img)
                else:
                    logger.error("No valid frame available.")
                return  # Exit if no valid frame is available

            original_frame = frame.copy()  # Copy the full frame before processing
            frame, bbox = self.face_detector.detect_faces(frame, self.callback)
            if bbox:
                x, y, w, h = bbox
                cx, cy = x + w // 2, y + h // 2

                # Apply bounding box multiplier
                w = int(w * self.bbox_multiplier)
                h = int(h * self.bbox_multiplier)

                # Update Kalman Filter
                self.kalman.correct(np.array([[np.float32(cx)], [np.float32(cy)], [np.float32(w)], [np.float32(h)]]))
                prediction = self.kalman.predict()
                pred_cx, pred_cy = int(prediction[0]), int(prediction[1])
                pred_w = int(prediction[2])
                pred_h = int(prediction[3])

                # Ensure dimensions are valid
                pred_w = max(1, pred_w)
                pred_h = max(1, pred_h)

                # Extract frame based on Kalman prediction
                cropped_frame = self.extract_frame(frame, pred_w, pred_h, pred_cx, pred_cy)
                resized_frame = self.resize_to_square(cropped_frame, self.square_size)

                # Update global reference to the last cropped frame with a face
                self.last_cropped_frame = cropped_frame

                # Add "LIVE" text overlay
                add_text_overlay(resized_frame)

                # Emit the frame to be displayed
                q_img = self.convert_to_qimage(resized_frame)
                self.frame_ready.emit(q_img)

            elif self.last_cropped_frame is not None:
                # Add "LIVE" text overlay to the last cropped frame with face
                resized_frame = self.resize_to_square(self.last_cropped_frame, self.square_size)
                add_text_overlay(resized_frame)

                # Emit the last known good cropped frame
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

        # Ensure the extracted frame is square and does not warp
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
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Ensure the frame is in RGB format
        q_img = QImage(frame.data, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_RGB888)
        return q_img

    def stop(self):
        print("VideoProcessor: Stopping")
        self.stopped = True
        self.timer.stop()
        self.cap.release()
        self.quit()
        self.wait()

    def update_config(self):
        self.bbox_multiplier = config.bbox_multiplier

import cv2
import numpy as np
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import config
from logger_setup import logger
from backend_communicator import send_snapshot_to_server, send_no_face_detected_request, send_add_frame_request

class NewFaces:
    def __init__(self):
        self.curr_face = None
        self.no_face_counter = 0
        self.previous_backend_success = True
        self.awaiting_backend_response = False
        self.detection_counter = 0
        self.frame_buffer = []
        self.bbox_buffer = []
        self.frames_sent = False
        self.log_no_face_detected = False
        self.face_detected = False
        self.mediapipe_last_detection_time = 0
        self.mediapipe_valid_detection = False
        self.stop_threads = False
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.cropped_frame = None

        if config.auto_update:
            self.start_periodic_reset()

    def reset_face(self):
        self.curr_face = None
        self.detection_counter = 0
        self.frames_sent = False
        self.frame_buffer = []
        self.bbox_buffer = []
        logger.info("Face reset. curr_face set to None.")

    def periodic_reset(self):
        if self.stop_threads:
            return
        if self.mediapipe_valid_detection:
            self.reset_face()
        threading.Timer(config.update_int, self.periodic_reset).start()

    def start_periodic_reset(self):
        self.stop_threads = False
        if config.auto_update:
            self.periodic_reset()

    def set_cropped_frame(self, cropped_frame):
        self.cropped_frame = cropped_frame
        logger.info(f"Set cropped frame with shape: {cropped_frame.shape} and type: {type(cropped_frame)}")

    def set_curr_face(self, mediapipe_result, frame, callback):
        current_time = time.time()

        if mediapipe_result and mediapipe_result.detections:
            self.mediapipe_last_detection_time = current_time
            self.mediapipe_valid_detection = True

            self.log_no_face_detected = False
            self.face_detected = True

            self.no_face_counter = 0
            self.detection_counter += 1

            cropped_face = self.cropped_frame  # Use the cropped frame from VideoProcessor

            if cropped_face is None or cropped_face.size == 0:
                logger.error("Cropped face is empty.")
                return

            if self.curr_face is None and self.detection_counter >= 10:
                logger.info('New face detected')

                self.curr_face = cropped_face
                self.detection_counter = 0
                self.frames_sent = False
                self.frame_buffer = []
                self.bbox_buffer = []

                # Send the cropped face to the snapshot server
                self.send_cropped_face_to_server(cropped_face, callback)

        else:
            self.face_detected = False
            self.no_face_counter += 1
            self.detection_counter = 0
            self.mediapipe_valid_detection = False
            if self.no_face_counter >= 1:
                logger.info('No face detected')
                self.reset_face()
                if config.create_sprites:
                    send_no_face_detected_request()
                if not self.log_no_face_detected:
                    self.log_no_face_detected = True

    def send_cropped_face_to_server(self, cropped_face, callback):
        if self.awaiting_backend_response:
            return

        if cropped_face is None:
            logger.error("send_cropped_face_to_server: cropped_face is None")
            return

        if not isinstance(cropped_face, np.ndarray):
            logger.error(f"send_cropped_face_to_server: cropped_face is not a valid numpy array. Type: {type(cropped_face)}")
            return

        self.awaiting_backend_response = True

        def backend_task():
            return send_snapshot_to_server(cropped_face, callback)

        def backend_callback(future):
            most_similar, least_similar, success = future.result()
            self.awaiting_backend_response = False

            if success:
                self.previous_backend_success = True
                self.curr_face = cropped_face
                callback(most_similar, least_similar)
            else:
                self.previous_backend_success = False
                logger.warning("Failed to get matches from server, will retry with the next frame.")

        future = self.executor.submit(backend_task)
        future.add_done_callback(backend_callback)

    def stop_all_threads(self):
        self.stop_threads = True
        self.executor.shutdown(wait=False)

# Ensure cleanup on application exit
import atexit
atexit.register(lambda: NewFaces().stop_all_threads())

import cv2
import numpy as np
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import config
from logger_setup import logger
from backend_communicator import send_snapshot_to_server, send_no_face_detected_request

class NewFaces:
    def __init__(self):
        self.curr_face = None
        self.curr_bbox = None
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
        self.position_threshold = 50  # Pixel distance threshold for switching faces

        if config.auto_update:
            self.start_periodic_reset()

    def reset_face(self):
        self.curr_face = None
        self.curr_bbox = None
        self.detection_counter = 0
        self.frames_sent = False
        self.frame_buffer = []
        self.bbox_buffer = []
        logger.info("Face reset. curr_face set to None.")

    def periodic_reset(self):
        if self.stop_threads:
            return
        if self.face_detected:
            self.reset_face()
        threading.Timer(config.update_int, self.periodic_reset).start()

    def start_periodic_reset(self):
        self.stop_threads = False
        if config.auto_update:
            self.periodic_reset()

    def set_cropped_frame(self, cropped_frame):
        self.cropped_frame = cropped_frame
        logger.info(f"Set cropped frame with shape: {cropped_frame.shape} and type: {type(cropped_frame)}")

    def get_largest_face(self, detected_faces):
        """Find the detected face with the largest bounding box area."""
        largest_face = None
        max_area = 0

        for face in detected_faces:
            bbox = self.extract_bbox(face)
            if bbox is not None:
                area = bbox[2] * bbox[3]  # width * height
                if area > max_area:
                    max_area = area
                    largest_face = face

        return largest_face

    def get_closest_face(self, detected_faces):
        """Find the detected face closest to the last known position of the current face, or the largest face if no current face."""
        if self.curr_bbox is None:
            return self.get_largest_face(detected_faces)  # Default to the largest face if no current face is tracked

        min_distance = float('inf')
        closest_face = None

        for face in detected_faces:
            bbox = self.extract_bbox(face)
            if bbox is not None:
                distance = self.calculate_bbox_distance(self.curr_bbox, bbox)
                if distance < min_distance:
                    min_distance = distance
                    closest_face = face

        return closest_face

    def extract_bbox(self, detection):
        """Extract the bounding box from a detection result."""
        if detection.location_data and detection.location_data.relative_bounding_box:
            bbox = detection.location_data.relative_bounding_box
            return bbox.xmin, bbox.ymin, bbox.width, bbox.height
        return None

    def calculate_bbox_distance(self, bbox1, bbox2):
        """Calculate the Euclidean distance between the centers of two bounding boxes."""
        center1_x = bbox1[0] + bbox1[2] / 2
        center1_y = bbox1[1] + bbox1[3] / 2
        center2_x = bbox2[0] + bbox2[2] / 2
        center2_y = bbox2[1] + bbox2[3] / 2
        return np.sqrt((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2)

    def set_curr_face(self, mediapipe_result, frame, callback):
        current_time = time.time()

        if mediapipe_result and mediapipe_result.detections:
            self.mediapipe_last_detection_time = current_time
            self.mediapipe_valid_detection = True

            self.log_no_face_detected = False
            self.face_detected = True

            self.no_face_counter = 0
            self.detection_counter += 1

            # Find the closest face to the last known face position
            closest_face = self.get_closest_face(mediapipe_result.detections)
            bbox = self.extract_bbox(closest_face)

            if self.curr_bbox is not None:
                distance = self.calculate_bbox_distance(self.curr_bbox, bbox)
                if distance > self.position_threshold:
                    logger.info(f"Significant movement detected. Resetting face due to distance: {distance}")
                    self.treat_as_no_face_detected()
                    return

            self.curr_bbox = bbox

            cropped_face = self.cropped_frame  # Use the cropped frame from VideoProcessor

            if cropped_face is None or cropped_face.size == 0:
                logger.error("Cropped face is empty.")
                return

            if self.curr_face is None:
                if self.detection_counter >= 10:
                    logger.info('New face detected')

                    self.curr_face = cropped_face
                    self.detection_counter = 0
                    self.frames_sent = False
                    self.frame_buffer = []
                    self.bbox_buffer = []

                    # Send the cropped face to the snapshot server
                    self.send_cropped_face_to_server(cropped_face, callback)
            else:
                self.curr_face = cropped_face

        else:
            self.treat_as_no_face_detected()

    def treat_as_no_face_detected(self):
        """Handles the logic when no face is detected, including when a significant jump occurs."""
        self.face_detected = False
        self.no_face_counter += 1
        self.detection_counter = 0
        self.mediapipe_valid_detection = False
        if self.no_face_counter >= 1:
            logger.info('No face detected or significant movement detected')
            self.reset_face()
            if config.create_sprites:
                send_no_face_detected_request()
            if not self.log_no_face_detected:
                self.log_no_face_detected = True

    def send_cropped_face_to_server(self, cropped_face, callback):
        if self.awaiting_backend_response:
            return

        if cropped_face is None or cropped_face.size == 0:
            logger.error("Cropped face is empty or invalid.")
            return

        if not isinstance(cropped_face, np.ndarray):
            logger.error(f"send_cropped_face_to_server: cropped_face is not a valid numpy array. Type: {type(cropped_face)}")
            return

        self.awaiting_backend_response = True

        def backend_task():
            return send_snapshot_to_server(cropped_face, callback)

        def backend_callback(future):
            try:
                most_similar, least_similar, success = future.result()
                self.awaiting_backend_response = False

                if success:
                    self.previous_backend_success = True
                    self.curr_face = cropped_face
                    callback(most_similar, least_similar)
                else:
                    self.previous_backend_success = False
                    logger.warning("Failed to get matches from server, will retry with the next frame.")
            except Exception as e:
                self.awaiting_backend_response = False
                logger.exception(f"Error in backend_callback: {e}")

        future = self.executor.submit(backend_task)
        future.add_done_callback(backend_callback)

    def stop_all_threads(self):
        logger.info("Stopping all threads in NewFaces...")
        self.stop_threads = True

        try:
            logger.info("Shutting down executor with a timeout...")
            self.executor.shutdown(wait=True, timeout=5)
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")

        logger.info("Executor shutdown complete.")
        logger.info("All threads in NewFaces have been stopped.")

import cv2
import numpy as np
import requests
import base64
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import config
from logger_setup import logger
from backend_communicator import send_snapshot_to_server, send_no_face_detected_request, send_add_frame_request

# Global variables
curr_face = None
no_face_counter = 0
previous_backend_success = True
awaiting_backend_response = False
detection_counter = 0
frame_buffer = []
bbox_buffer = []
frames_sent = False
log_no_face_detected = False
face_detected = False
mediapipe_last_detection_time = 0
mediapipe_valid_detection = False
stop_threads = False
executor = ThreadPoolExecutor(max_workers=5)

def reset_face():
    global curr_face, detection_counter, frame_buffer, bbox_buffer, frames_sent
    curr_face = None
    detection_counter = 0
    frames_sent = False
    frame_buffer = []
    bbox_buffer = []

def periodic_reset():
    if stop_threads:
        return
    if mediapipe_valid_detection:
        reset_face()
    threading.Timer(config.update_int, periodic_reset).start()

def start_periodic_reset():
    global stop_threads
    stop_threads = False
    if config.auto_update:
        periodic_reset()

def set_curr_face(mediapipe_result, frame, callback):
    global curr_face, no_face_counter, detection_counter, frame_buffer, bbox_buffer, frames_sent, log_no_face_detected, face_detected, mediapipe_last_detection_time, mediapipe_valid_detection
    bbox_multiplier = config.bbox_multiplier

    current_time = time.time()

    if mediapipe_result and mediapipe_result.detections:
        mediapipe_last_detection_time = current_time
        mediapipe_valid_detection = True

        log_no_face_detected = False
        face_detected = True

        no_face_counter = 0
        detection_counter += 1

        detection = mediapipe_result.detections[0]
        bboxC = detection.location_data.relative_bounding_box
        ih, iw, _ = frame.shape
        x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)

        w = int(w * bbox_multiplier)
        h = w
        cx, cy = x + int(bboxC.width * iw // 2), y + int(bboxC.height * ih // 2)

        x = max(0, min(cx - w // 2, iw - w))
        y = max(0, min(cy - h // 2, ih - h))

        cropped_face = frame[y:y + h, x:x + w]

        if curr_face is None and detection_counter >= 10:
            print('new face')

            curr_face = cropped_face
            detection_counter = 0
            frames_sent = False
            frame_buffer = []
            bbox_buffer = []

            update_face_detection(frame, cropped_face, True, callback)

    else:
        face_detected = False
        no_face_counter += 1
        detection_counter = 0
        mediapipe_valid_detection = False
        if no_face_counter >= 1:
            print('no face')
            reset_face()
            send_no_face_detected_request()

            if not log_no_face_detected:
                log_no_face_detected = True

def update_face_detection(frame, cropped_face, new_face_detected, callback):
    global curr_face, previous_backend_success, awaiting_backend_response, frames_sent, face_detected

    if awaiting_backend_response:
        return

    if cropped_face is None:
        logger.error("update_face_detection: cropped_face is None")
        return

    if not isinstance(cropped_face, np.ndarray):
        logger.error(f"update_face_detection: cropped_face is not a valid numpy array. Type: {type(cropped_face)}")
        return

    if new_face_detected or not previous_backend_success:
        awaiting_backend_response = True

        def backend_task():
            most_similar, least_similar, success = send_snapshot_to_server(cropped_face, callback)
            return most_similar, least_similar, success

        def backend_callback(future):
            global previous_backend_success, awaiting_backend_response, curr_face
            most_similar, least_similar, success = future.result()
            awaiting_backend_response = False

            if success:
                previous_backend_success = True
                curr_face = cropped_face
                callback(most_similar, least_similar)
            else:
                previous_backend_success = False
                logger.warning("Failed to get matches from server, will retry with the next frame.")

        future = executor.submit(backend_task)
        future.add_done_callback(backend_callback)

def stop_all_threads():
    global stop_threads
    stop_threads = True
    executor.shutdown(wait=False)

# Ensure cleanup on application exit
import atexit
atexit.register(stop_all_threads)

# Start periodic reset if auto_update is enabled
if config.auto_update:
    start_periodic_reset()

import cv2
import numpy as np
from backend_communicator import send_snapshot_to_server, send_frames_to_backend
from logger_setup import logger
import config
import asyncio
import threading
import time

# Global variables
curr_face = None
no_face_counter = 0
previous_backend_success = True
awaiting_backend_response = False
detection_counter = 0
frame_buffer = []
bbox_buffer = []
MAX_FRAMES = 12 * 19
MIN_FRAMES = 4
frames_sent = False
log_no_face_detected = False
face_detected = False
mediapipe_last_detection_time = 0
mediapipe_valid_detection = False
stop_threads = False

def reset_face():
    global curr_face, detection_counter, frame_buffer, bbox_buffer, frames_sent
    curr_face = None
    detection_counter = 10
    frame_buffer = []
    bbox_buffer = []
    frames_sent = False
    print("Face reset triggered.")
    logger.info("Face reset triggered.")

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
        print(f"Starting periodic reset with interval {config.update_int} seconds.")
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

        cropped_face = cv2.resize(cropped_face, (100, 100))

        if curr_face is None and detection_counter >= 10:
            curr_face = cropped_face
            detection_counter = 0
            frames_sent = False
            frame_buffer = []
            bbox_buffer = []

            update_face_detection(frame, cropped_face, True, callback)

        if curr_face is not None:
            frame_buffer.append(cropped_face)
            bbox_buffer.append((x, y, w, h))

            if len(frame_buffer) >= MAX_FRAMES and not frames_sent:
                send_frames()
                frames_sent = True

    else:
        face_detected = False
        no_face_counter += 1
        detection_counter = 0
        mediapipe_valid_detection = False
        if no_face_counter >= 10:
            if len(frame_buffer) >= MIN_FRAMES and curr_face is not None and not frames_sent:
                send_frames()
                frames_sent = True
            curr_face = None
            no_face_counter = 0
            frame_buffer = []
            bbox_buffer = []

            if not log_no_face_detected:
                print('No face detected for 2 consecutive frames, resetting curr_face.')
                logger.info("No face detected for 2 consecutive frames, resetting curr_face.")
                log_no_face_detected = True

def update_face_detection(frame, cropped_face, new_face_detected, callback):
    logger.info("Updating Face Detect")

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
        print('Sending snapshot to server')
        logger.info("Sending snapshot to server")
        awaiting_backend_response = True
        most_similar, least_similar, success = send_snapshot_to_server(frame, callback)
        awaiting_backend_response = False

        if success:
            previous_backend_success = True
            curr_face = cropped_face
            callback(most_similar, least_similar)
        else:
            previous_backend_success = False
            print("Failed to get matches from server, will retry with the next frame.")
            logger.warning("Failed to get matches from server, will retry with the next frame.")
        #     if face_detected:
        #         update_face_detection(frame, cropped_face, new_face_detected, callback)

def send_frames():
    global frame_buffer, bbox_buffer, previous_backend_success, awaiting_backend_response

    if awaiting_backend_response:
        return

    if not frame_buffer or len(frame_buffer) < MIN_FRAMES:
        return

    def run_send_frames():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(send_frames_to_backend(frame_buffer, bbox_buffer))
        loop.close()
        run_send_frames_wrapper(success)

    print('Sending frames to server')
    logger.info("Sending frames to server")
    awaiting_backend_response = True

    thread = threading.Thread(target=run_send_frames)
    thread.start()

def run_send_frames_wrapper(success):
    global previous_backend_success, awaiting_backend_response
    previous_backend_success = success
    awaiting_backend_response = False

    if success:
        print("Spritesheet created successfully.")
        logger.info("Spritesheet created successfully.")
        frame_buffer.clear()
        bbox_buffer.clear()
    else:
        print("Failed to create spritesheet from server, will retry with the next frame.")
        logger.warning("Failed to create spritesheet from server, will retry with the next frame.")

def stop_all_threads():
    global stop_threads
    stop_threads = True

# Ensure cleanup on application exit
import atexit
atexit.register(stop_all_threads)

# Start periodic reset if auto_update is enabled
if config.auto_update:
    start_periodic_reset()
    print(f"Periodic reset started with interval {config.update_int} seconds.")

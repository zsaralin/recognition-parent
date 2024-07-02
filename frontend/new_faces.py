import cv2
import numpy as np
from backend_communicator import send_snapshot_to_server, send_frames_to_backend
from logger_setup import logger
import config
import asyncio
import threading

curr_face = None
no_face_counter = 0  # Counter for consecutive frames with no face detected
previous_backend_success = True  # Track the success of the previous backend call
awaiting_backend_response = False  # Track if we are waiting for a response from the backend
detection_counter = 0  # Counter for consecutive frames with face detected
frame_buffer = []  # Buffer to collect frames
bbox_buffer = []  # Buffer to collect bounding box coordinates
MAX_FRAMES = 12 * 19
MIN_FRAMES = 4
frames_sent = False  # Flag to track if frames have been sent

def set_curr_face(mediapipe_result, frame, callback):
    global curr_face, no_face_counter, detection_counter, frame_buffer, bbox_buffer, frames_sent
    bbox_multiplier = config.bbox_multiplier

    if mediapipe_result and mediapipe_result.detections:
        no_face_counter = 0  # Reset counter if a face is detected
        detection_counter += 1  # Increment detection counter

        # Assume the first detection is the face
        detection = mediapipe_result.detections[0]
        bboxC = detection.location_data.relative_bounding_box
        ih, iw, _ = frame.shape
        x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)

        # Apply bounding box multiplier and make the bounding box square
        w = int(w * bbox_multiplier)
        h = w
        cx, cy = x + int(bboxC.width * iw // 2), y + int(bboxC.height * ih // 2)

        # Calculate new top-left corner to keep the bounding box centered
        x = max(0, min(cx - w // 2, iw - w))
        y = max(0, min(cy - h // 2, ih - h))

        cropped_face = frame[y:y+h, x:x+w]

        # Resize the cropped face to 100x100
        cropped_face = cv2.resize(cropped_face, (100, 100))

        if curr_face is None and detection_counter >= 8:  # Wait for 8 detections before considering a new face
            curr_face = cropped_face  # Update curr_face
            detection_counter = 0  # Reset detection counter
            frames_sent = False  # Reset frames_sent flag
            frame_buffer = []  # Clear the frame buffer
            bbox_buffer = []  # Clear the bounding box buffer
            update_face_detection(frame, cropped_face, True, callback)

        if curr_face is not None:  # Start collecting frames only after a face is confirmed
            frame_buffer.append(cropped_face)  # Add the cropped face to the buffer
            bbox_buffer.append((x, y, w, h))  # Add the bounding box to the buffer

            if len(frame_buffer) >= MAX_FRAMES and not frames_sent:
                send_frames()  # Send frames when buffer exceeds MAX_FRAMES
                frames_sent = True  # Set the flag to indicate frames have been sent
    else:
        no_face_counter += 1
        detection_counter = 0  # Reset detection counter if no face is detected
        if no_face_counter >= 30:
            if len(frame_buffer) >= MIN_FRAMES and curr_face is not None and not frames_sent:
                send_frames()  # Send frames when no face detected for 30 consecutive frames and buffer has enough frames
                frames_sent = True  # Set the flag to indicate frames have been sent
            curr_face = None
            no_face_counter = 0  # Reset the counter
            frame_buffer = []  # Clear the buffer if no face is detected for a while
            bbox_buffer = []  # Clear the bounding box buffer
            print('No face detected for 30 consecutive frames, resetting curr_face.')
            logger.info("No face detected for 30 consecutive frames, resetting curr_face.")

def update_face_detection(frame, cropped_face, new_face_detected, callback):
    global curr_face, previous_backend_success, awaiting_backend_response, frames_sent

    if awaiting_backend_response:
        return  # Exit if we are already waiting for a backend response

    if cropped_face is None:
        logger.error("update_face_detection: cropped_face is None")
        return

    if not isinstance(cropped_face, np.ndarray):
        logger.error(f"update_face_detection: cropped_face is not a valid numpy array. Type: {type(cropped_face)}")
        return
    if new_face_detected or not previous_backend_success:
        print('Sending snapshot to server')
        logger.info("Sending snapshot to server")
        awaiting_backend_response = True  # Set the flag before sending the snapshot
        most_similar, least_similar, success = send_snapshot_to_server(cropped_face, callback)
        previous_backend_success = success  # Update the success status
        awaiting_backend_response = False  # Reset the flag after getting the response

        if success:
            curr_face = cropped_face  # Update curr_face only if backend call is successful
            callback(most_similar, least_similar)
        else:
            print("Failed to get matches from server, will retry with the next frame.")
            logger.warning("Failed to get matches from server, will retry with the next frame.")
    else:
        curr_face = cropped_face  # Update the current frame

def send_frames():
    global frame_buffer, bbox_buffer, previous_backend_success, awaiting_backend_response

    if awaiting_backend_response:
        return  # Exit if we are already waiting for a backend response

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
    awaiting_backend_response = True  # Set the flag before sending the frames

    thread = threading.Thread(target=run_send_frames)
    thread.start()

def run_send_frames_wrapper(success):
    global previous_backend_success, awaiting_backend_response
    previous_backend_success = success  # Update the success status
    awaiting_backend_response = False  # Reset the flag after getting the response

    if success:
        print("Spritesheet created successfully.")
        logger.info("Spritesheet created successfully.")
        frame_buffer.clear()  # Clear the buffer after successful sending to backend
        bbox_buffer.clear()  # Clear the bounding box buffer after successful sending to backend
    else:
        print("Failed to create spritesheet from server, will retry with the next frame.")
        logger.warning("Failed to create spritesheet from server, will retry with the next frame.")

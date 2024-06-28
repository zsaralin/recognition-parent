import cv2
import numpy as np
from backend_communicator import send_snapshot_to_server, send_frames_to_backend
from logger_setup import logger

curr_face = None
no_face_counter = 0  # Counter for consecutive frames with no face detected
previous_backend_success = True  # Track the success of the previous backend call
awaiting_backend_response = False  # Track if we are waiting for a response from the backend
detection_counter = 0  # Counter for consecutive frames with face detected
frame_buffer = []  # Buffer to collect frames
MAX_FRAMES = 12 * 19
MIN_FRAMES = 4

def set_curr_face(mediapipe_result, frame, callback):
    global curr_face, no_face_counter, detection_counter, frame_buffer
    if mediapipe_result and mediapipe_result.detections:
        no_face_counter = 0  # Reset counter if a face is detected
        detection_counter += 1  # Increment detection counter
        frame_buffer.append(frame)  # Add the frame to the buffer

        if detection_counter >= 8:  # Wait for 8 detections before sending to backend
            update_face_detection(frame, callback)
            detection_counter = 0  # Reset detection counter after sending to backend

        if len(frame_buffer) >= MAX_FRAMES:
            send_frames_to_backend()
            frame_buffer = []  # Clear the buffer after sending to backend
    else:
        no_face_counter += 1
        detection_counter = 0  # Reset detection counter if no face is detected
        if no_face_counter >= 10:
            if len(frame_buffer) >= MIN_FRAMES:
                send_frames_to_backend()
            curr_face = None
            no_face_counter = 0  # Reset the counter
            frame_buffer = []  # Clear the buffer if no face is detected for a while
            print('No face detected for 10 consecutive frames, resetting curr_face.')
            logger.info("No face detected for 10 consecutive frames, resetting curr_face.")

def update_face_detection(frame, callback):
    global curr_face, previous_backend_success, awaiting_backend_response

    if awaiting_backend_response:
        return  # Exit if we are already waiting for a backend response

    is_new_face = curr_face is None

    if frame is None:
        logger.error("update_face_detection: frame is None")
        return

    if not isinstance(frame, np.ndarray):
        logger.error(f"update_face_detection: frame is not a valid numpy array. Type: {type(frame)}")
        return

    if is_new_face or not previous_backend_success:
        print('Sending snapshot to server')
        logger.info("Sending snapshot to server")
        awaiting_backend_response = True  # Set the flag before sending the snapshot
        most_similar, least_similar, success = send_snapshot_to_server(frame, callback)
        previous_backend_success = success  # Update the success status
        awaiting_backend_response = False  # Reset the flag after getting the response

        if success:
            curr_face = frame  # Update curr_face only if backend call is successful
            callback(most_similar, least_similar)
        else:
            print("Failed to get matches from server, will retry with the next frame.")
            logger.warning("Failed to get matches from server, will retry with the next frame.")
    else:
        curr_face = frame  # Update the current frame

def send_frames_to_backend():
    global frame_buffer, previous_backend_success, awaiting_backend_response

    if awaiting_backend_response:
        return  # Exit if we are already waiting for a backend response

    if not frame_buffer or len(frame_buffer) < MIN_FRAMES:
        return

    print('Sending frames to server')
    logger.info("Sending frames to server")
    awaiting_backend_response = True  # Set the flag before sending the frames
    success = send_frames_to_backend(frame_buffer)
    previous_backend_success = success  # Update the success status
    awaiting_backend_response = False  # Reset the flag after getting the response

    if success:
        print("Spritesheet created successfully.")
        logger.info("Spritesheet created successfully.")
    else:
        print("Failed to create spritesheet from server, will retry with the next frame.")
        logger.warning("Failed to create spritesheet from server, will retry with the next frame.")

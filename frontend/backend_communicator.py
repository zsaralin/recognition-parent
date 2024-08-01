import json
import cv2
import numpy as np
import requests
import base64
import config
from logger_setup import logger
from image_store import image_store  # Import the global instance
import threading
import os

BASE_SERVER_URL = "http://localhost:3000"

def convert_image_to_data_url(image):
    if image is None:
        logger.error("convert_image_to_data_url: image is None")
        return None

    try:
        _, buffer = cv2.imencode('.jpg', image)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{jpg_as_text}"
        return data_url
    except Exception as e:
        logger.exception("Error in convert_image_to_data_url: %s", e)
        return None

def send_snapshot_to_server(frame, callback):
    print('SNEDING SNAPSHOTTTTTTTTTTTTTTTTTTTTTTT')
    if frame is None:
        logger.error("send_snapshot_to_server: frame is None")
        return None, None, False

    image_data_url = convert_image_to_data_url(frame)
    if image_data_url is None:
        logger.error("send_snapshot_to_server: Failed to convert frame to data URL")
        return None, None, False

    payload = {'image': image_data_url, 'numVids': config.num_vids}
    url = f"{BASE_SERVER_URL}/get-matches"

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            result = response.json()
            most_similar = result.get('mostSimilar')
            least_similar = result.get('leastSimilar')
            print(most_similar[0])
            if most_similar is None or least_similar is None:
                logger.error("Received None for most_similar or least_similar")
                return None, None, False

            # Call the callback function with the results
            callback(most_similar, least_similar)
            return most_similar, least_similar, True
        else:
            logger.error(f"Failed to get matches from server: {response.status_code}")
            logger.error(f"Server response: {response.text}")
            if response.status_code == 404 and "No face detected" in response.text:
                return None, None, False
    except Exception as e:
        logger.exception("Error sending snapshot to server: %s", e)

    return None, None, False

def load_frames(frame_paths):
    frames = []
    for frame_path in frame_paths:
        try:
            with open(frame_path, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                frames.append(encoded_string)
        except Exception as e:
            logger.exception(f"Failed to load frame from path: {frame_path}, error: {e}")
    return frames

def send_add_frame_request(frame, bbox):
    if frame is None or bbox is None:
        logger.error("send_add_frame_request: frame or bbox is None")
        return False

    image_data_url = convert_image_to_data_url(frame)
    payload = {'frame': image_data_url, 'bbox': bbox}
    url = f"{BASE_SERVER_URL}/addFrame"

    try:
        # logger.info(f"Sending request to {url} with payload: {payload}")
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            # logger.info("Frame added successfully")
            return True
        else:
            logger.error(f"Error adding frame: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.exception("Error sending add frame request to server: %s", e)
        return False

def send_no_face_detected_request():
    url = f"{BASE_SERVER_URL}/noFaceDetected"
    result = {}

    def make_request():
        nonlocal result
        try:
            response = requests.post(url)
            if response.status_code == 200:
                res_json = response.json()
                result['success'] = res_json.get('success', False)
                if result['success']:
                    file_path = res_json.get('filePath')
                    result['filePath'] = file_path
                    if file_path:
                        logger.info(f"Received new spritesheet path: {file_path}")
                        if image_store.add_image(file_path):
                            logger.info(f"Image {file_path} added to preloaded images.")
            else:
                result['success'] = False
                # logger.error(f"Error processing frames: {response.status_code}, {response.text}")
        except Exception as e:
            result['success'] = False
            # logger.exception("Error sending noFaceDetected request to server: %s", e)
        finally:
            handle_response(result)

    def handle_response(response):
        if response.get('success'):
            print("Spritesheet created and image added successfully:", response.get('filePath'))
        else:
            print("Failed to create spritesheet or add image.")

    threading.Thread(target=make_request).start()

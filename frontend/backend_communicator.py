import json

import cv2
import numpy as np
import requests
import base64
import config
from logger_setup import logger

BASE_SERVER_URL = "http://localhost:3000"

def convert_image_to_data_url(image):
    if image is None:
        logger.error("convert_image_to_data_url: image is None")
        return None

    _, buffer = cv2.imencode('.jpg', image)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    data_url = f"data:image/jpeg;base64,{jpg_as_text}"
    return data_url

def send_snapshot_to_server(frame, callback):
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
            logger.info(f"Most Similar: {most_similar}")
            logger.info(f"Least Similar: {least_similar}")

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
        with open(frame_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            frames.append(encoded_string)
    return frames

def convert_image_to_jpeg_bytes(image):
    _, buffer = cv2.imencode('.jpg', image)
    return buffer.tobytes()
def send_frames_to_backend(frames, bboxes):
    url = f"{BASE_SERVER_URL}/create-spritesheet"
    files = []
    for i, frame in enumerate(frames):
        jpeg_bytes = convert_image_to_jpeg_bytes(frame)
        files.append(('frames', ('frame%d.jpg' % i, jpeg_bytes, 'image/jpeg')))
    data = {'bboxes': json.dumps(bboxes)}  # Convert bboxes to a JSON string

    try:
        logger.info(f'Sending {len(frames)} frames to {url}')
        response = requests.post(url, files=files, data=data)

        logger.info(f'Request headers: {response.request.headers}')
        logger.info(f'Request payload size: {len(response.request.body) if response.request.body else 0} bytes')

        if response.status_code == 200:
            logger.info('Spritesheet created successfully.')
            print('Spritesheet created successfully.')\

        else:
            logger.error(f'Failed to create spritesheet: {response.status_code}')
            logger.error(f'Server response: {response.text}')
    except Exception as e:
        logger.exception("Error sending frames to backend: %s", e)
        print(f"Error sending frames to backend: {e}")

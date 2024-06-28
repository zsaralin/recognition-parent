import cv2
from logger_setup import logger

import cv2
from logger_setup import logger

def add_text_overlay(frame, text="Live", offset_from_bottom=10):
    try:
        font = cv2.FONT_HERSHEY_PLAIN
        font_scale = 1  # Font scale
        color = (255, 255, 255)  # White color in BGR
        thickness = 1  # Thickness of the text
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = frame.shape[0] - offset_from_bottom

        # Add black background for text
        background_x1 = text_x - 5
        background_y1 = text_y - text_size[1] - 5
        background_x2 = text_x + text_size[0] + 5
        background_y2 = text_y + 5
        cv2.rectangle(frame, (background_x1, background_y1), (background_x2, background_y2), (0, 0, 0), cv2.FILLED)

        # Add the text
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)
    except Exception as e:
        logger.exception(f"Error adding text overlay: {e}")

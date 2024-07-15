import cv2
from logger_setup import logger
import config  # Import the config module

def add_text_overlay(frame, text="Live", offset_from_bottom=12):
    try:
        font = cv2.FONT_HERSHEY_PLAIN
        high_res_scale_factor = 1  # Scale factor for higher resolution
        font_scale = config.font_size * high_res_scale_factor  # Use scaled font size
        color = (255, 255, 255)  # White color in BGR
        thickness = 1  # Increased thickness for better visibility
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = frame.shape[0] - offset_from_bottom * high_res_scale_factor

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

def update_font_size(font_size):
    config.font_size = font_size

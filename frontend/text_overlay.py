import cv2
import numpy as np
from logger_setup import logger
import config

def add_text_overlay(overlay, text="Live", offset_from_bottom=12, scale_factor=1):
    try:
        font = cv2.FONT_HERSHEY_PLAIN
        font_scale = config.font_size * scale_factor  # Scale the font size
        text_color = (255, 255, 255, 255)  # White color in RGBA
        background_color = (0, 0, 0, 255)  # Black color in RGBA
        thickness = int(scale_factor)  # Scale the thickness with the scale factor

        # Calculate text size and position
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (overlay.shape[1] - text_size[0]) // 2
        text_y = overlay.shape[0] - offset_from_bottom * scale_factor

        # Define the rectangle for the text background
        background_x1 = text_x - 5 * scale_factor
        background_y1 = text_y - text_size[1] - 5 * scale_factor
        background_x2 = text_x + text_size[0] + 5 * scale_factor
        background_y2 = text_y + 5 * scale_factor

        # Add the black background rectangle
        cv2.rectangle(overlay,
                      (int(background_x1), int(background_y1)),
                      (int(background_x2), int(background_y2)),
                      background_color,
                      cv2.FILLED)

        # Add the text with full opacity (alpha = 255)
        cv2.putText(overlay, text,
                    (int(text_x), int(text_y)),
                    font, font_scale, text_color,
                    thickness, cv2.LINE_AA)

        # Optionally, scale down the image to the original size after text rendering
        if scale_factor != 1:
            overlay = cv2.resize(overlay,
                                 (overlay.shape[1] // scale_factor, overlay.shape[0] // scale_factor),
                                 interpolation=cv2.INTER_AREA)

        return overlay
    except Exception as e:
        logger.exception(f"Error adding text overlay: {e}")
        return None

def update_font_size(font_size):
    config.font_size = font_size

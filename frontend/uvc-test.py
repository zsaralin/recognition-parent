import cv2
import sys

def print_camera_properties(cap):
    properties = [
        (cv2.CAP_PROP_BRIGHTNESS, "Brightness"),
        (cv2.CAP_PROP_CONTRAST, "Contrast"),
        (cv2.CAP_PROP_SATURATION, "Saturation"),
        (cv2.CAP_PROP_HUE, "Hue"),
        (cv2.CAP_PROP_GAIN, "Gain"),
        (cv2.CAP_PROP_EXPOSURE, "Exposure"),
        (cv2.CAP_PROP_AUTO_EXPOSURE, "Auto Exposure"),
        (cv2.CAP_PROP_GAMMA, "Gamma"),
        (cv2.CAP_PROP_TEMPERATURE, "Temperature"),
        (cv2.CAP_PROP_ZOOM, "Zoom")
    ]

    print("Camera Properties:")
    for prop_id, prop_name in properties:
        value = cap.get(prop_id)
        print(f"{prop_name}: {value}")

def test_property_range(cap, prop_id, prop_name, test_values):
    print(f"\nTesting {prop_name} range:")
    for value in test_values:
        success = cap.set(prop_id, value)
        actual_value = cap.get(prop_id)
        print(f"  Attempted to set {value}: Success = {success}, Actual value = {actual_value}")

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open camera")
        sys.exit()

    print_camera_properties(cap)

    # Test brightness range
    test_property_range(cap, cv2.CAP_PROP_BRIGHTNESS, "Brightness", [0, 0.5, 1, 50, 100])

    # Test saturation range
    test_property_range(cap, cv2.CAP_PROP_SATURATION, "Saturation", [0, 0.5, 1, 50, 100])

    # Test exposure range
    test_property_range(cap, cv2.CAP_PROP_EXPOSURE, "Exposure", [0, 0.01, 0.1, 1, 10, 100])

    cap.release()

if __name__ == "__main__":
    main()
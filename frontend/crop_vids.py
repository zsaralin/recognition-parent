import os
import cv2
import mediapipe as mp
from one_euro import OneEuroFilter

def detect_and_crop_face_continuously(video_path, output_path, target_size=100):
    mp_face_detection = mp.solutions.face_detection
    face_detection = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (target_size, target_size))

    bounding_box = None
    size = None  # Initialize size as None

    # Initialize the One Euro filter for x and y axes
    freq = 30.0
    min_cutoff = 1.0
    beta = .2
    euro_filter_x = OneEuroFilter(freq, min_cutoff=min_cutoff, beta=beta)
    euro_filter_y = OneEuroFilter(freq, min_cutoff=min_cutoff, beta=beta)
    current_time = 0.0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        current_time += 1.0 / fps

        if bounding_box is None:
            results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if results.detections:
                bboxC = results.detections[0].location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)

                # Ensure the crop is a square and 1.5 times the size of the bounding box
                size = int(2 * max(w, h))
                cx, cy = x + w // 2, y + h // 2
                x = max(0, cx - size // 2)
                y = max(0, cy - size // 2)
                bounding_box = (x, y, size, size)

        if bounding_box is not None:
            x, y, size, _ = bounding_box
            results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if results.detections:
                bboxC = results.detections[0].location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                new_x, new_y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)

                cx, cy = new_x + w // 2, new_y + h // 2
                new_x = max(0, cx - size // 2)
                new_y = max(0, cy - size // 2)

                # Apply One Euro Filter to the x and y coordinates
                smoothed_x = int(euro_filter_x.filter(new_x, current_time))
                smoothed_y = int(euro_filter_y.filter(new_y, current_time))
                bounding_box = (smoothed_x, smoothed_y, size, size)

            x, y, size, _ = bounding_box
            cropped_frame = frame[y:y + size, x:x + size]
            resized_frame = cv2.resize(cropped_frame, (target_size, target_size))
            out.write(resized_frame)

    cap.release()
    out.release()
    print(f"Processed video saved as {output_path}")

def process_videos_in_folder(folder_path):
    output_folder = folder_path + '-crop'
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(folder_path):
        if filename.endswith('.mp4'):
            video_path = os.path.join(folder_path, filename)
            output_path = os.path.join(output_folder, filename)
            detect_and_crop_face_continuously(video_path, output_path)

# Example usage
folder_path = '../videos/YouTube-real'  # Change to your folder path
process_videos_in_folder(folder_path)

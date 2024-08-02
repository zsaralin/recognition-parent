import cv2
import mediapipe as mp
from new_faces import set_curr_face
import math

# Adjustable parameters
MIN_FACE_SIZE = 100  # closer the face, larger the number
JUMP_THRESHOLD = 50  # Threshold for detecting significant jumps in the bounding box position

class MediaPipeFaceDetection:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)
        self.current_face_bbox = None  # Store the current face's bounding box
        self.previous_cx = None
        self.previous_cy = None

    def detect_faces(self, frame, callback):
        results = self.face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        closest_face = None
        min_distance = float('inf')

        if results.detections:
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box
                h, w, c = frame.shape
                bbox = int(bboxC.xmin * w), int(bboxC.ymin * h), \
                    int(bboxC.width * w), int(bboxC.height * h)

                # Calculate the distance of the face from the camera
                face_center_x = bbox[0] + bbox[2] // 2
                face_center_y = bbox[1] + bbox[3] // 2
                distance = (face_center_x - w // 2) ** 2 + (face_center_y - h // 2) ** 2

                # Find the closest face to the camera initially
                if self.current_face_bbox is None and distance < min_distance:
                    min_distance = distance
                    closest_face = bbox

                # Stick to the current face if it is still detected
                if self.current_face_bbox is not None:
                    current_cx = self.current_face_bbox[0] + self.current_face_bbox[2] // 2
                    current_cy = self.current_face_bbox[1] + self.current_face_bbox[3] // 2
                    if abs(face_center_x - current_cx) < JUMP_THRESHOLD and abs(face_center_y - current_cy) < JUMP_THRESHOLD:
                        closest_face = bbox
                        break

            # Update the current face's bounding box
            if closest_face is not None:
                if closest_face[2] < MIN_FACE_SIZE or closest_face[3] < MIN_FACE_SIZE or not self.is_face_facing_forward(frame, closest_face):
                    results = None  # Face is too small or not facing forward
                else:
                    if self.previous_cx is not None and self.previous_cy is not None:
                        if abs(closest_face[0] + closest_face[2] // 2 - self.previous_cx) > JUMP_THRESHOLD or \
                                abs(closest_face[1] + closest_face[3] // 2 - self.previous_cy) > JUMP_THRESHOLD:
                            results = None  # Significant jump in face position
                    self.current_face_bbox = closest_face
                    self.previous_cx = closest_face[0] + closest_face[2] // 2
                    self.previous_cy = closest_face[1] + closest_face[3] // 2
            else:
                self.current_face_bbox = None  # No valid face detected
        else:
            self.current_face_bbox = None  # No face detected at all

        # Call set_curr_face with the closest face result, frame, and callback
        set_curr_face(results, frame, callback)

        return frame, self.current_face_bbox

    def is_face_facing_forward(self, frame, bbox):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        x, y, w, h = bbox
        cropped_frame = rgb_frame[y:y+h, x:x+w]

        results = self.face_mesh.process(cropped_frame)

        if not results.multi_face_landmarks:
            return False

        landmarks = results.multi_face_landmarks[0].landmark

        # Key landmarks
        nose_tip = landmarks[1]
        left_eye = landmarks[33]
        right_eye = landmarks[263]

        # Calculate the midpoint between the eyes
        eye_midpoint_x = (left_eye.x + right_eye.x) / 2

        # Calculate the horizontal distance from nose to eye midpoint
        nose_to_midpoint = abs(nose_tip.x - eye_midpoint_x)

        # Calculate the distance between the eyes
        eye_distance = abs(left_eye.x - right_eye.x)
        # Calculate the ratio of nose-to-midpoint distance to eye distance
        ratio = nose_to_midpoint / eye_distance
        # Threshold for determining if the face is turned more than 90 degrees
        # This value may need adjustment based on testing
        threshold = 0.75
        is_facing_forward = ratio < threshold
        return is_facing_forward

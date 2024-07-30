import cv2
import mediapipe as mp
from new_faces import set_curr_face
import math

class MediaPipeFaceDetection:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)
        self.current_face_bbox = None  # Store the current face's bounding box

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
                if self.current_face_bbox is not None and \
                   self.current_face_bbox[0] <= face_center_x <= self.current_face_bbox[0] + self.current_face_bbox[2] and \
                   self.current_face_bbox[1] <= face_center_y <= self.current_face_bbox[1] + self.current_face_bbox[3]:
                    closest_face = bbox
                    break

            # Update the current face's bounding box
            if closest_face is not None:
                self.current_face_bbox = closest_face
            else:
                self.current_face_bbox = None  # No valid face detected
        else:
            self.current_face_bbox = None  # No face detected at all

        # Call set_curr_face with the results, frame, and callback
        set_curr_face(results, frame, callback)

        return frame, self.current_face_bbox

    def is_face_facing_forward(self, frame):
        results = self.face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                nose_tip = face_landmarks.landmark[self.mp_face_mesh.FACEMESH_NOSE_TIP]
                left_cheek = face_landmarks.landmark[self.mp_face_mesh.FACEMESH_LEFT_CHEEK]
                right_cheek = face_landmarks.landmark[self.mp_face_mesh.FACEMESH_RIGHT_CHEEK]

                # Calculate the angles to check if the face is within 45 degrees
                angle_left = math.degrees(math.atan2(nose_tip.y - left_cheek.y, nose_tip.x - left_cheek.x))
                angle_right = math.degrees(math.atan2(nose_tip.y - right_cheek.y, nose_tip.x - right_cheek.x))

                if abs(angle_left) <= 60 and abs(angle_right) <= 60:
                    return True
        return False

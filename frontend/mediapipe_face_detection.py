import cv2
import mediapipe as mp
from new_faces import set_curr_face

class MediaPipeFaceDetection:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

    def detect_faces(self, frame, callback):
        results = self.face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        bbox = None
        if results.detections:
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box
                h, w, c = frame.shape
                bbox = int(bboxC.xmin * w), int(bboxC.ymin * h), \
                    int(bboxC.width * w), int(bboxC.height * h)
                break  # Assuming one face, take the first detection
        # Call set_curr_face with the results, frame, and callback
        set_curr_face(results, frame, callback)

        return frame, bbox

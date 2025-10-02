import cv2
import mediapipe as mp
import math

class GestureRecognizer:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7)
        self.mp_draw = mp.solutions.drawing_utils
        self.latest_gesture = None
        self.hand_landmarks = None

    def _get_distance(self, p1, p2):
        """Calculate Euclidean distance between two points."""
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    def _is_pinch(self, hand_landmarks):
        """Detects a pinch gesture."""
        thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
        index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        distance = self._get_distance(thumb_tip, index_tip)
        # Normalize distance by the length of the index finger to make it scale-invariant
        index_mcp = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_MCP]
        index_length = self._get_distance(index_tip, index_mcp)
        return distance / index_length < 0.3

    def _is_open_palm(self, hand_landmarks):
        """Detects an open palm gesture."""
        # A simple heuristic: check if fingertips are far from the wrist
        wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
        finger_tips = [
            self.mp_hands.HandLandmark.THUMB_TIP,
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP,
            self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
            self.mp_hands.HandLandmark.RING_FINGER_TIP,
            self.mp_hands.HandLandmark.PINKY_TIP,
        ]

        # Check that all fingers are extended (tip is further from wrist than pip)
        for tip_id in finger_tips[1:]: # Skip thumb for this check
            tip = hand_landmarks.landmark[tip_id]
            pip = hand_landmarks.landmark[tip_id - 2] # PIP joint
            if self._get_distance(wrist, tip) < self._get_distance(wrist, pip):
                return False
        return True

    def _is_closed_palm(self, hand_landmarks):
        """Detects a closed palm (fist) gesture."""
        wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
        # Check if finger tips are closer to the wrist than their MCP joints
        for i in range(1, 5):
            tip = hand_landmarks.landmark[i*4 + 4]
            mcp = hand_landmarks.landmark[i*4 + 1]
            if self._get_distance(wrist, tip) > self._get_distance(wrist, mcp):
                return False
        return True

    def recognize_gesture(self, hand_landmarks):
        """Recognizes a specific gesture from hand landmarks."""
        if self._is_pinch(hand_landmarks):
            return "PINCH"
        if self._is_closed_palm(hand_landmarks):
            return "CLOSED_PALM"
        if self._is_open_palm(hand_landmarks):
            return "OPEN_PALM"

        # Placeholder for drag gesture detection
        # This would require tracking movement across frames
        return "HAND_DETECTED"

    def process_frame(self, frame):
        """Processes a single frame to detect and recognize hand gestures."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False # Performance optimization
        results = self.hands.process(frame_rgb)
        frame.flags.writeable = True

        self.latest_gesture = None
        self.hand_landmarks = None

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                self.hand_landmarks = hand_landmarks
                self.latest_gesture = self.recognize_gesture(hand_landmarks)
                break # Process only one hand

        return frame, self.latest_gesture

    def close(self):
        self.hands.close()
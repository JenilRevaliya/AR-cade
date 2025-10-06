import cv2
import numpy as np
import mediapipe as mp
import math
from dataclasses import dataclass
from PyQt5.QtCore import Qt

from game_base import BaseGame

# --- Data Classes & Kalman Filter ---
@dataclass
class Person:
    box: tuple; centroid: tuple; landmarks: any; histogram: np.ndarray

class KalmanFilter:
    def __init__(self, dt=1.0, std_acc=1., std_meas=0.1):
        self.dt, self.A, self.H = dt, np.array([[1, dt, 0, 0], [0, 1, 0, 0], [0, 0, 1, dt], [0, 0, 0, 1]]), np.array([[1, 0, 0, 0], [0, 0, 1, 0]])
        self.Q, self.R, self.P, self.x = np.eye(self.A.shape[1]) * std_acc, np.eye(self.H.shape[0]) * std_meas, np.eye(self.A.shape[1]), np.zeros((self.A.shape[1], 1))
    def predict(self): self.x = np.dot(self.A, self.x); self.P = np.dot(np.dot(self.A, self.P), self.A.T) + self.Q; return self.x
    def update(self, z):
        S = np.dot(self.H, np.dot(self.P, self.H.T)) + self.R; K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        self.x += np.dot(K, (z - np.dot(self.H, self.x))); self.P = np.dot(np.eye(self.P.shape[0]) - np.dot(K, self.H), self.P)
        return self.x

class Player:
    def __init__(self, player_id, person_data: Person):
        self.id = player_id; self.kf = KalmanFilter(); self.kf.x[[0, 2], 0] = person_data.centroid
        self.histogram = person_data.histogram; self.centroid = person_data.centroid
        self.person_data = person_data; self.hand_landmarks, self.hand_gesture, self.hand_closed = None, "OTHER", False
        self.frames_lost, self.consistent_frames = 0, 1
    def predict(self): return self.kf.predict()
    def update(self, person_data: Person):
        self.kf.update(np.array([[person_data.centroid[0]], [person_data.centroid[1]]]))
        self.centroid = (int(self.kf.x[0, 0]), int(self.kf.x[2, 0]))
        self.histogram = self.histogram * 0.9 + person_data.histogram * 0.1
        self.person_data, self.frames_lost, self.consistent_frames = person_data, 0, self.consistent_frames + 1
    def lost(self): self.frames_lost, self.consistent_frames = self.frames_lost + 1, 0
    def is_tracking(self): return self.frames_lost < 10

# --- Main Game Class ---
class ARTicTacToe(BaseGame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AR Tic Tac Toe - Premium")
        self.mp_holistic = mp.solutions.holistic
        self.holistic = self.mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.mp_draw = mp.solutions.drawing_utils

        self.TEXT_COLOR, self.ERROR_COLOR, self.INFO_COLOR = (255, 255, 255), (0, 0, 255), (255, 255, 0)
        self.P1_COLOR, self.P2_COLOR = (255, 100, 100), (100, 100, 255)
        self.BOARD_LINE_COLOR, self.WIN_LINE_COLOR, self.HIGHLIGHT_COLOR = (0, 255, 255), (0, 255, 0), (255, 255, 255)

        self.MIN_CONSISTENT_FRAMES, self.HIST_CORR_THRESHOLD, self.MIN_PLAYER_SEPARATION, self.DEBOUNCE_FRAMES = 15, 0.6, 200, 15
        self.RESTART_TIME_FRAMES = 90
        self.debug_mode = False
        self.reset_game()

    def reset_game(self):
        self.players, self.next_player_id, self.persons_in_frame = {}, 1, []
        self.board, self.board_anim_state = np.zeros((3, 3), dtype=int), np.zeros((3, 3), dtype=int)
        self.current_player_id, self.game_over, self.winner, self.winning_line = 1, False, None, None
        self.scores = {1: 0, 2: 0}
        self.board_center, self.board_size, self.cell_size = (0, 0), 0, 0
        self.hovered_cell, self.gesture_cooldown, self.vfx_counter = None, 0, 0
        self.end_game_hand_closed, self.end_game_timer = {1: False, 2: False}, 0
        self.instruction_text, self.game_state = "Waiting for two players...", "WAITING_FOR_PLAYERS"
        print("Game reset.")

    def start(self): super().start()
    def update_game(self):
        if not self.running: return
        ret, frame = self.cap.read()
        if not ret: return
        frame = cv2.flip(frame, 1)
        self.vfx_counter += 1

        holistic_results = self.holistic.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        self.persons_in_frame = self._detect_persons(holistic_results, frame)
        self._update_players(self.persons_in_frame)
        self.update_game_state()

        if self.game_state in ["PLAYING", "GAME_OVER"]:
            self._calculate_board_transform()
            self._assign_hands_to_players(holistic_results)
            self.handle_gestures(holistic_results)

        frame = self.draw_ui(frame, holistic_results)
        self.render_frame(frame)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() == Qt.Key_D: self.debug_mode = not self.debug_mode
        if event.key() == Qt.Key_R: self.reset_game()

    def _calculate_histogram(self, frame, box):
        x1, y1, x2, y2 = box; torso_y1, torso_y2 = y1 + int((y2 - y1) * 0.2), y1 + int((y2 - y1) * 0.6)
        torso = frame[torso_y1:torso_y2, x1:x2]
        if torso.size == 0: return None
        hsv_torso = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv_torso], [0, 1], None, [180, 256], [0, 180, 0, 256])
        return cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    def _detect_persons(self, results, frame):
        detected_persons = []
        if results.pose_landmarks:
            h, w, _ = frame.shape; landmarks = results.pose_landmarks.landmark
            x_coords, y_coords = [lm.x * w for lm in landmarks if lm.visibility > 0.5], [lm.y * h for lm in landmarks if lm.visibility > 0.5]
            if not x_coords or not y_coords: return []
            box = (int(min(x_coords)), int(min(y_coords)), int(max(x_coords)), int(max(y_coords)))
            r_shoulder, l_shoulder = landmarks[self.mp_holistic.PoseLandmark.RIGHT_SHOULDER], landmarks[self.mp_holistic.PoseLandmark.LEFT_SHOULDER]
            centroid = (int(((r_shoulder.x + l_shoulder.x) / 2) * w), int(((r_shoulder.y + l_shoulder.y) / 2) * h))
            hist = self._calculate_histogram(frame, box)
            if hist is not None: detected_persons.append(Person(box=box, centroid=centroid, landmarks=landmarks, histogram=hist))
        return detected_persons

    def _update_players(self, detected_persons):
        for p in self.players.values(): p.predict()
        unmatched_persons = list(detected_persons)
        matches, matched_person_indices = [], set()

        for p_id, player in self.players.items():
            best_match_idx, max_score = -1, -1
            for i, person in enumerate(unmatched_persons):
                dist = np.linalg.norm(player.kf.predict()[:3:2].flatten() - np.array(person.centroid))
                hist_corr = cv2.compareHist(player.histogram, person.histogram, cv2.HISTCMP_CORREL)
                score = (1 / (1 + dist / 100)) * hist_corr
                if score > max_score and hist_corr > self.HIST_CORR_THRESHOLD: max_score, best_match_idx = score, i
            if best_match_idx != -1:
                matches.append((p_id, unmatched_persons[best_match_idx]))
                matched_person_indices.add(best_match_idx)

        unmatched_persons = [p for i, p in enumerate(unmatched_persons) if i not in matched_person_indices]
        for p_id, person_data in matches: self.players[p_id].update(person_data)
        for p_id, player in self.players.items():
            if p_id not in [m[0] for m in matches]: player.lost()

        for person in unmatched_persons:
            if len(self.players) < 2:
                new_id = self.next_player_id
                self.players[new_id] = Player(new_id, person)
                self.next_player_id = 3 - new_id

        lost_ids = [p_id for p_id, p in self.players.items() if p.frames_lost > 30]
        for p_id in lost_ids: del self.players[p_id]

    def update_game_state(self):
        num_tracked = len([p for p in self.players.values() if p.is_tracking()])
        if self.game_state == "WAITING_FOR_PLAYERS":
            if num_tracked < 2: self.instruction_text = "Waiting for two players..."
            elif len(self.persons_in_frame) > 2: self.instruction_text = "More than two people detected!"
            elif num_tracked == 2: self.game_state = "CALIBRATING"
        elif self.game_state == "CALIBRATING":
            if num_tracked < 2: self.game_state, self.players = "WAITING_FOR_PLAYERS", {}
            elif all(p.consistent_frames >= self.MIN_CONSISTENT_FRAMES for p in self.players.values()):
                self.game_state, self.instruction_text = "PLAYING", f"Player {self.current_player_id}'s Turn"
            else:
                frames = min(p.consistent_frames for p in self.players.values()) if self.players else 0
                self.instruction_text = f"Calibrating... Please stand still. ({frames}/{self.MIN_CONSISTENT_FRAMES})"

    def _assign_hands_to_players(self, results):
        for p in self.players.values(): p.hand_landmarks = None
        all_hands = []
        if results.right_hand_landmarks: all_hands.append(results.right_hand_landmarks)

        for hand_landmarks in all_hands:
            hand_centroid_x = np.mean([lm.x for lm in hand_landmarks.landmark]) * self.width()
            min_dist, assigned_player_id = float('inf'), -1

            for p_id, player in self.players.items():
                dist = abs(hand_centroid_x - player.centroid[0])
                if dist < min_dist: min_dist, assigned_player_id = dist, p_id

            if assigned_player_id != -1: self.players[assigned_player_id].hand_landmarks = hand_landmarks

    def _get_cell_from_coords(self, x, y):
        board_x1, board_y1 = self.board_center[0] - self.board_size // 2, self.board_center[1] - self.board_size // 2
        if self.board_size > 0 and board_x1 <= x < board_x1 + self.board_size and board_y1 <= y < board_y1 + self.board_size:
            return (int((y - board_y1) / self.cell_size), int((x - board_x1) / self.cell_size))
        return None

    def _is_closed_palm(self, hand_landmarks):
        wrist = hand_landmarks.landmark[0]; dist_sum = 0
        for tip_id in [8, 12, 16, 20]: dist_sum += np.linalg.norm(np.array([wrist.x, wrist.y]) - np.array([hand_landmarks.landmark[tip_id].x, hand_landmarks.landmark[tip_id].y]))
        return dist_sum < 1.0

    def handle_gestures(self, holistic_results):
        if self.game_over: self.handle_end_game_gestures(holistic_results); return
        if self.gesture_cooldown > 0: self.gesture_cooldown -= 1; return

        player = self.players.get(self.current_player_id)
        if not player or not player.hand_landmarks:
            self.hovered_cell = None; return

        hand_pos = player.hand_landmarks.landmark[9]
        self.hovered_cell = self._get_cell_from_coords(int(hand_pos.x * self.width()), int(hand_pos.y * self.height()))

        is_closed = self._is_closed_palm(player.hand_landmarks)
        if is_closed: player.hand_closed = True
        elif not is_closed and player.hand_closed:
            if self.hovered_cell: self.mark_position(self.hovered_cell)
            player.hand_closed = False

    def handle_end_game_gestures(self, results):
        for i in range(1, 3): self.end_game_hand_closed[i] = False
        all_hands = []
        if results.left_hand_landmarks: all_hands.append(results.left_hand_landmarks)
        if results.right_hand_landmarks: all_hands.append(results.right_hand_landmarks)

        for hand_landmarks in all_hands:
            if self._is_closed_palm(hand_landmarks):
                hand_cx = np.mean([lm.x for lm in hand_landmarks.landmark]) * self.width()
                player_id = 1 if hand_cx < self.width() / 2 else 2
                if player_id in self.end_game_hand_closed: self.end_game_hand_closed[player_id] = True

        if all(self.end_game_hand_closed.values()):
            self.end_game_timer += 1
            if self.end_game_timer > self.RESTART_TIME_FRAMES: self.reset_game()
        else: self.end_game_timer = 0

    def mark_position(self, cell):
        r, c = cell
        if self.board[r, c] == 0:
            self.board[r, c], self.board_anim_state[r, c] = self.current_player_id, self.vfx_counter
            if self.check_winner():
                self.game_over, self.scores[self.winner] = True, self.scores.get(self.winner, 0) + 1
                self.instruction_text = f"Player {self.winner} Wins! Hold fists to restart."
            elif np.all(self.board != 0):
                self.game_over, self.instruction_text = True, "It's a Draw! Hold fists to restart."
            else:
                self.current_player_id = 2 if self.current_player_id == 1 else 1
                self.instruction_text = f"Player {self.current_player_id}'s Turn"
            self.gesture_cooldown = self.DEBOUNCE_FRAMES

    def check_winner(self):
        for i in range(3):
            if np.all(self.board[i, :] == self.current_player_id): self.winning_line = ("row", i)
            elif np.all(self.board[:, i] == self.current_player_id): self.winning_line = ("col", i)
        if self.board[0, 0] == self.board[1, 1] == self.board[2, 2] == self.current_player_id: self.winning_line = ("diag", 1)
        if self.board[0, 2] == self.board[1, 1] == self.board[2, 0] == self.current_player_id: self.winning_line = ("diag", 2)
        if self.winning_line: self.winner = self.current_player_id; return True
        return False

    def _calculate_board_transform(self):
        if len(self.players) == 2 and all(p.is_tracking() for p in self.players.values()):
            p1, p2 = self.players[1], self.players[2]
            mid_x, mid_y = int((p1.centroid[0] + p2.centroid[0]) / 2), int((p1.centroid[1] + p2.centroid[1]) / 2)
            dist = np.linalg.norm(np.array(p1.centroid) - np.array(p2.centroid))
            self.board_size, self.cell_size = int(np.clip(dist * 0.8, 300, 600)), self.board_size // 3 if self.board_size > 0 else 100
            self.board_center = (mid_x, mid_y)

    def _draw_player_huds(self, frame):
        for p_id, player in self.players.items():
            if not player.is_tracking(): continue
            h, w, _ = frame.shape; nose_lm = player.person_data.landmarks[self.mp_holistic.PoseLandmark.NOSE]
            head_x, head_y = int(nose_lm.x * w), int(nose_lm.y * h)
            hud_w, hud_h = 220, 110; hud_x, hud_y = head_x - hud_w // 2, head_y - hud_h - 70
            y_offset = int(math.sin((self.vfx_counter + p_id * 25) * 0.05) * 6); hud_y += y_offset
            overlay = frame.copy(); cv2.rectangle(overlay, (hud_x, hud_y), (hud_x + hud_w, hud_y + hud_h), (30, 30, 30), -1)
            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
            player_color = self.P1_COLOR if p_id == 1 else self.P2_COLOR
            cv2.rectangle(frame, (hud_x, hud_y), (hud_x + hud_w, hud_y + hud_h), player_color, 2)
            marker = "X" if p_id == 1 else "O"; cv2.putText(frame, f"Player {p_id} ({marker})", (hud_x + 15, hud_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.TEXT_COLOR, 2)
            cv2.putText(frame, f"Score: {self.scores.get(p_id, 0)}", (hud_x + 15, hud_y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.TEXT_COLOR, 1)
            if p_id == self.current_player_id and not self.game_over: cv2.putText(frame, "TURN", (hud_x + hud_w - 80, hud_y + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.INFO_COLOR, 2)

    def _get_pulse_scale(self, age):
        pulse_duration = 15.0;
        if age < 0 or age > pulse_duration: return 1.0
        return 0.85 + (age / (pulse_duration / 2)) * 0.20 if age < pulse_duration / 2 else 1.05 - ((age - pulse_duration / 2) / (pulse_duration / 2)) * 0.20

    def _draw_premium_board(self, frame):
        if self.board_size == 0: return
        board_x, board_y = self.board_center[0] - self.board_size // 2, self.board_center[1] - self.board_size // 2
        for i in range(1, 3):
            cv2.line(frame, (board_x + i * self.cell_size, board_y), (board_x + i * self.cell_size, board_y + self.board_size), self.BOARD_LINE_COLOR, 3)
            cv2.line(frame, (board_x, board_y + i * self.cell_size), (board_x + self.board_size, board_y + i * self.cell_size), self.BOARD_LINE_COLOR, 3)
        if self.hovered_cell and not self.game_over and self.board[self.hovered_cell] == 0:
            r, c = self.hovered_cell; cell_x, cell_y = board_x + c * self.cell_size, board_y + r * self.cell_size
            highlight_overlay = frame.copy(); cv2.rectangle(highlight_overlay, (cell_x, cell_y), (cell_x + self.cell_size, cell_y + self.cell_size), self.HIGHLIGHT_COLOR, -1)
            frame = cv2.addWeighted(highlight_overlay, 0.3, frame, 0.7, 0)
        for r in range(3):
            for c in range(3):
                if self.board[r,c] != 0:
                    cell_x, cell_y = board_x + c * self.cell_size, board_y + r * self.cell_size
                    scale = self._get_pulse_scale(self.vfx_counter - self.board_anim_state[r, c])
                    size = int((self.cell_size//2 - 30) * scale)
                    center_x, center_y = cell_x + self.cell_size//2, cell_y + self.cell_size//2
                    if self.board[r,c] == 1:
                        cv2.line(frame, (center_x - size, center_y - size), (center_x + size, center_y + size), self.P1_COLOR, 5)
                        cv2.line(frame, (center_x + size, center_y - size), (center_x - size, center_y + size), self.P1_COLOR, 5)
                    else: cv2.circle(frame, (center_x, center_y), size, self.P2_COLOR, 5)
        if self.winning_line:
            line_type, index = self.winning_line
            if line_type == "row": cv2.line(frame, (board_x, board_y + index * self.cell_size + self.cell_size//2), (board_x + self.board_size, board_y + index * self.cell_size + self.cell_size//2), self.WIN_LINE_COLOR, 10)
            elif line_type == "col": cv2.line(frame, (board_x + index * self.cell_size + self.cell_size//2, board_y), (board_x + index * self.cell_size + self.cell_size//2, board_y + self.board_size), self.WIN_LINE_COLOR, 10)
            elif line_type == "diag":
                if index == 1: cv2.line(frame, (board_x, board_y), (board_x + self.board_size, board_y + self.board_size), self.WIN_LINE_COLOR, 10)
                else: cv2.line(frame, (board_x + self.board_size, board_y), (board_x, board_y + self.board_size), self.WIN_LINE_COLOR, 10)

    def draw_ui(self, frame, results):
        (w, h), _ = cv2.getTextSize(self.instruction_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        x = (frame.shape[1] - w) // 2
        cv2.putText(frame, self.instruction_text, (x, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, self.INFO_COLOR, 2, cv2.LINE_AA)
        if self.debug_mode:
            if results.pose_landmarks: self.mp_draw.draw_landmarks(frame, results.pose_landmarks, self.mp_holistic.POSE_CONNECTIONS)
            if results.left_hand_landmarks: self.mp_draw.draw_landmarks(frame, results.left_hand_landmarks, self.mp_holistic.HAND_CONNECTIONS)
            if results.right_hand_landmarks: self.mp_draw.draw_landmarks(frame, results.right_hand_landmarks, self.mp_holistic.HAND_CONNECTIONS)
            for p_id, p in self.players.items():
                cv2.rectangle(frame, p.person_data.box[:2], p.person_data.box[2:], (255,0,0), 2)
                cv2.circle(frame, p.centroid, 10, (0,0,255), -1)
                cv2.putText(frame, f"P{p_id}", p.centroid, cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        if self.game_state in ["PLAYING", "GAME_OVER"]:
            self._draw_premium_board(frame)
            self._draw_player_huds(frame)
        return frame

    def exit(self):
        self.holistic.close()
        super().exit()
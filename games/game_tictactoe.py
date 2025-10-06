import cv2
import numpy as np
import mediapipe as mp
import math
from game_base import BaseGame

class MultiHandGestureRecognizer:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.mp_draw = mp.solutions.drawing_utils

    def _get_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    def _is_open_palm(self, hand_landmarks):
        wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
        for tip_id in [8, 12, 16, 20]:
            tip = hand_landmarks.landmark[tip_id]
            pip = hand_landmarks.landmark[tip_id - 2]
            if self._get_distance(wrist, tip) < self._get_distance(wrist, pip):
                return False
        return True

    def _is_closed_palm(self, hand_landmarks):
        wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
        for i in range(1, 5):
            tip = hand_landmarks.landmark[i*4 + 4]
            mcp = hand_landmarks.landmark[i*4 + 1]
            if self._get_distance(wrist, tip) > self._get_distance(wrist, mcp):
                return False
        return True

    def recognize_gesture(self, hand_landmarks):
        if self._is_closed_palm(hand_landmarks):
            return "CLOSED_PALM"
        if self._is_open_palm(hand_landmarks):
            return "OPEN_PALM"
        return "OTHER"

    def process_frame(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)

        detected_hands = []
        if results.multi_hand_landmarks:
            sorted_hands = sorted(results.multi_hand_landmarks, key=lambda lm: lm.landmark[0].x)

            for i, hand_landmarks in enumerate(sorted_hands):
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                player = i + 1
                gesture = self.recognize_gesture(hand_landmarks)
                detected_hands.append({
                    "player": player,
                    "landmarks": hand_landmarks,
                    "gesture": gesture
                })
        return frame, detected_hands

    def close(self):
        self.hands.close()

class ARTicTacToe(BaseGame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AR Tic Tac Toe")

        self.CELL_SIZE = 150
        self.BOARD_SIZE = 3 * self.CELL_SIZE
        self.LINE_COLOR = (0, 255, 255)
        self.X_COLOR = (255, 100, 100)
        self.O_COLOR = (100, 100, 255)
        self.TEXT_COLOR = (255, 255, 255)
        self.HIGHLIGHT_COLOR = (255, 255, 255)
        self.WIN_LINE_COLOR = (0, 255, 0)
        self.board_x, self.board_y = 0, 0

        self.reset_game()

        self.gesture_recognizer = MultiHandGestureRecognizer()

    def reset_game(self):
        self.board = np.zeros((3, 3), dtype=int)
        self.current_player = 1
        self.game_over = False
        self.winner = None
        self.winning_line = None
        self.instruction_text = "Player 1's Turn (X)"
        self.hovered_cell = None
        self.player_hand_closed = {1: False, 2: False}
        self.end_game_hand_closed = {1: False, 2: False}
        self.end_game_timer = 0
        self.RESTART_TIME_FRAMES = 90 # 3 seconds at 30fps
        self.gesture_cooldown = 0
        self.DEBOUNCE_FRAMES = 15

    def start(self):
        super().start()

    def update_game(self):
        if not self.running: return
        ret, frame = self.cap.read()
        if not ret: return

        frame = cv2.flip(frame, 1)
        frame, detected_hands = self.gesture_recognizer.process_frame(frame)

        self.handle_gestures(detected_hands, frame.shape)

        frame = self.draw_board(frame)
        frame = self.draw_ui_overlay(frame)
        self.render_frame(frame)

    def _get_cell_from_coords(self, x, y):
        if self.board_x <= x < self.board_x + self.BOARD_SIZE and \
           self.board_y <= y < self.board_y + self.BOARD_SIZE:
            col = int((x - self.board_x) / self.CELL_SIZE)
            row = int((y - self.board_y) / self.CELL_SIZE)
            return (row, col)
        return None

    def handle_gestures(self, detected_hands, frame_shape):
        self.hovered_cell = None
        h, w, _ = frame_shape

        if self.gesture_cooldown > 0:
            self.gesture_cooldown -= 1

        if self.game_over:
            self.handle_end_game_gestures(detected_hands)
            return

        for hand in detected_hands:
            player, gesture = hand["player"], hand["gesture"]

            if player == self.current_player:
                hand_pos = hand["landmarks"].landmark[9]
                cursor_x, cursor_y = int(hand_pos.x * w), int(hand_pos.y * h)
                cell = self._get_cell_from_coords(cursor_x, cursor_y)
                if cell:
                    self.hovered_cell = cell

                if gesture == "CLOSED_PALM":
                    self.player_hand_closed[player] = True
                elif gesture == "OPEN_PALM" and self.player_hand_closed[player]:
                    if self.hovered_cell and self.gesture_cooldown == 0:
                        self.mark_position(self.hovered_cell)
                    self.player_hand_closed[player] = False
                elif gesture != "CLOSED_PALM":
                     self.player_hand_closed[player] = False

    def handle_end_game_gestures(self, detected_hands):
        for i in range(1, 3): self.end_game_hand_closed[i] = False

        for hand in detected_hands:
            if hand["gesture"] == "CLOSED_PALM":
                self.end_game_hand_closed[hand["player"]] = True

        if all(self.end_game_hand_closed.values()):
            self.end_game_timer += 1
            if self.end_game_timer > self.RESTART_TIME_FRAMES:
                self.reset_game()
        else:
            self.end_game_timer = 0


    def mark_position(self, cell):
        r, c = cell
        if self.board[r, c] == 0:
            self.board[r, c] = self.current_player

            if self.check_winner():
                self.game_over = True
                if self.winner:
                    self.instruction_text = f"Player {self.winner} Wins! Hold fists to restart."
                else:
                    self.instruction_text = "It's a Draw! Hold fists to restart."
            else:
                self.current_player = 2 if self.current_player == 1 else 1
                player_symbol = "X" if self.current_player == 1 else "O"
                self.instruction_text = f"Player {self.current_player}'s Turn ({player_symbol})"

            self.gesture_cooldown = self.DEBOUNCE_FRAMES

    def check_winner(self):
        for i in range(3):
            if np.all(self.board[i, :] == self.current_player):
                self.winner = self.current_player
                self.winning_line = ("row", i)
                return True
            if np.all(self.board[:, i] == self.current_player):
                self.winner = self.current_player
                self.winning_line = ("col", i)
                return True
        if self.board[0, 0] == self.board[1, 1] == self.board[2, 2] == self.current_player:
            self.winner = self.current_player
            self.winning_line = ("diag", 1)
            return True
        if self.board[0, 2] == self.board[1, 1] == self.board[2, 0] == self.current_player:
            self.winner = self.current_player
            self.winning_line = ("diag", 2)
            return True
        if not np.any(self.board == 0):
            return True
        return False

    def draw_board(self, frame):
        h, w, _ = frame.shape
        self.board_x = (w - self.BOARD_SIZE) // 2
        self.board_y = (h - self.BOARD_SIZE) // 2

        overlay = frame.copy()
        cv2.rectangle(overlay, (self.board_x, self.board_y), (self.board_x + self.BOARD_SIZE, self.board_y + self.BOARD_SIZE), (20, 20, 20), -1)
        frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)

        for i in range(1, 3):
            cv2.line(frame, (self.board_x + i * self.CELL_SIZE, self.board_y), (self.board_x + i * self.CELL_SIZE, self.board_y + self.BOARD_SIZE), self.LINE_COLOR, 3)
            cv2.line(frame, (self.board_x, self.board_y + i * self.CELL_SIZE), (self.board_x + self.BOARD_SIZE, self.board_y + i * self.CELL_SIZE), self.LINE_COLOR, 3)

        if self.hovered_cell and not self.game_over:
            r, c = self.hovered_cell
            cell_x, cell_y = self.board_x + c * self.CELL_SIZE, self.board_y + r * self.CELL_SIZE
            highlight_overlay = frame.copy()
            cv2.rectangle(highlight_overlay, (cell_x, cell_y), (cell_x + self.CELL_SIZE, cell_y + self.CELL_SIZE), self.HIGHLIGHT_COLOR, -1)
            frame = cv2.addWeighted(highlight_overlay, 0.3, frame, 0.7, 0)

        for r in range(3):
            for c in range(3):
                cell_x, cell_y = self.board_x + c * self.CELL_SIZE, self.board_y + r * self.CELL_SIZE
                if self.board[r, c] == 1:
                    cv2.line(frame, (cell_x + 30, cell_y + 30), (cell_x + self.CELL_SIZE - 30, cell_y + self.CELL_SIZE - 30), self.X_COLOR, 5)
                    cv2.line(frame, (cell_x + self.CELL_SIZE - 30, cell_y + 30), (cell_x + 30, cell_y + self.CELL_SIZE - 30), self.X_COLOR, 5)
                elif self.board[r, c] == 2:
                    center = (cell_x + self.CELL_SIZE // 2, cell_y + self.CELL_SIZE // 2)
                    cv2.circle(frame, center, self.CELL_SIZE // 2 - 30, self.O_COLOR, 5)

        if self.winning_line:
            line_type, index = self.winning_line
            if line_type == "row":
                y = self.board_y + index * self.CELL_SIZE + self.CELL_SIZE // 2
                cv2.line(frame, (self.board_x, y), (self.board_x + self.BOARD_SIZE, y), self.WIN_LINE_COLOR, 10)
            elif line_type == "col":
                x = self.board_x + index * self.CELL_SIZE + self.CELL_SIZE // 2
                cv2.line(frame, (x, self.board_y), (x, self.board_y + self.BOARD_SIZE), self.WIN_LINE_COLOR, 10)
            elif line_type == "diag":
                if index == 1:
                    cv2.line(frame, (self.board_x, self.board_y), (self.board_x + self.BOARD_SIZE, self.board_y + self.BOARD_SIZE), self.WIN_LINE_COLOR, 10)
                else:
                    cv2.line(frame, (self.board_x + self.BOARD_SIZE, self.board_y), (self.board_x, self.board_y + self.BOARD_SIZE), self.WIN_LINE_COLOR, 10)
        return frame

    def draw_ui_overlay(self, frame):
        cv2.putText(frame, self.instruction_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, self.TEXT_COLOR, 2, cv2.LINE_AA)
        if self.game_over:
            msg = f"Player {self.winner} Wins!" if self.winner else "It's a Draw!"
            (w, h), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 2, 3)
            x, y = (frame.shape[1] - w) // 2, (frame.shape[0] + h) // 2
            cv2.putText(frame, msg, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 2, self.TEXT_COLOR, 3, cv2.LINE_AA)
        return frame

    def exit(self):
        print("Cleaning up AR Tic Tac Toe.")
        super().exit()
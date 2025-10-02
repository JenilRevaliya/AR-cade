import sys
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QHBoxLayout,
                             QVBoxLayout, QScrollArea, QGraphicsDropShadowEffect)
from PyQt5.QtGui import QPixmap, QColor, QFont
from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from game_loader import load_games
from gesture_recognition import GestureRecognizer
from utils import convert_cv_qt

class GameCard(QWidget):
    """A 'card' widget to display a game with an icon and title."""
    def __init__(self, game_class, parent=None):
        super().__init__(parent)
        self.game_class = game_class
        self.setFixedSize(220, 280)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(200, 200)
        self.icon_label.setStyleSheet("background-color: #2E3B4E; border-radius: 10px;")
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.title_label = QLabel(game_class.__name__.replace("Game", ""), self)
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #FFFFFF;")

        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.title_label)

        self.setAutoFillBackground(True)
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 15px;")

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.shadow.setOffset(0, 5)
        self.setGraphicsEffect(self.shadow)

    def set_selected(self, selected):
        if selected:
            self.setStyleSheet("background-color: rgba(0, 255, 255, 0.3); border: 2px solid #00FFFF; border-radius: 15px;")
        else:
            self.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 15px;")

class HomePage(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AR-cade")
        self.setGeometry(100, 100, 1280, 720)
        self.setStyleSheet("background-color: #1C2533;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Video Feed
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.video_label)

        # Game Carousel
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFixedHeight(320)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")

        self.scroll_widget = QWidget()
        self.scroll_layout = QHBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(20, 0, 20, 0)
        self.scroll_area.setWidget(self.scroll_widget)
        self.layout.addWidget(self.scroll_area)

        self.games = load_games()
        self.game_cards = []
        self.init_game_list()

        self.cap = cv2.VideoCapture(0)
        self.gesture_recognizer = GestureRecognizer()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(20) # ~50 FPS for smoother gestures

        self.selected_card_index = -1
        self.gesture_cooldown = 0
        self.drag_start_x = None

    def init_game_list(self):
        for game_class in self.games:
            card = GameCard(game_class)
            self.scroll_layout.addWidget(card)
            self.game_cards.append(card)
        self.scroll_layout.addStretch()

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1) # Flip horizontally for intuitive control
        processed_frame, gesture = self.gesture_recognizer.process_frame(frame)

        if self.gesture_cooldown > 0:
            self.gesture_cooldown -= 1
        else:
            self.handle_gestures(gesture)

        pixmap = convert_cv_qt(processed_frame, self.video_label.width(), self.video_label.height())
        self.video_label.setPixmap(pixmap)

    def handle_gestures(self, gesture):
        if self.gesture_recognizer.hand_landmarks is None:
            self.drag_start_x = None
            return

        hand_cx = self.gesture_recognizer.hand_landmarks.landmark[9].x * self.width()

        # Gesture: OPEN_PALM for selection
        if gesture == "OPEN_PALM":
            self.update_selection(hand_cx)
            self.drag_start_x = None # Reset drag on selection
        # Gesture: PINCH for launch
        elif gesture == "PINCH" and self.selected_card_index != -1:
            self.launch_game(self.game_cards[self.selected_card_index].game_class)
            self.gesture_cooldown = 50 # 1 sec cooldown
        # Gesture: DRAG (emulated with hand movement)
        else:
            if self.drag_start_x is None:
                self.drag_start_x = hand_cx

            delta_x = hand_cx - self.drag_start_x
            if abs(delta_x) > 30: # Drag threshold
                scrollbar = self.scroll_area.horizontalScrollBar()
                new_value = scrollbar.value() - int(delta_x * 1.5) # Scroll multiplier

                self.anim = QPropertyAnimation(scrollbar, b"value")
                self.anim.setDuration(300)
                self.anim.setStartValue(scrollbar.value())
                self.anim.setEndValue(new_value)
                self.anim.setEasingCurve(QEasingCurve.OutCubic)
                self.anim.start()

                self.drag_start_x = hand_cx # Reset drag start position

    def update_selection(self, hand_cx):
        new_selected_index = -1
        for i, card in enumerate(self.game_cards):
            card_pos = card.mapToGlobal(card.pos())
            if card_pos.x() < hand_cx < card_pos.x() + card.width():
                new_selected_index = i
                break

        if new_selected_index != self.selected_card_index:
            if self.selected_card_index != -1:
                self.game_cards[self.selected_card_index].set_selected(False)
            if new_selected_index != -1:
                self.game_cards[new_selected_index].set_selected(True)
            self.selected_card_index = new_selected_index

    def launch_game(self, game_class):
        self.timer.stop()
        self.game_instance = game_class()
        self.game_instance.show()
        self.game_instance.start()
        # Connect a signal to know when the game closes
        self.game_instance.destroyed.connect(self.game_closed)
        self.hide()

    def game_closed(self):
        self.show()
        self.timer.start(20)
        self.selected_card_index = -1
        for card in self.game_cards:
            card.set_selected(False)

    def closeEvent(self, event):
        self.cap.release()
        self.gesture_recognizer.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    home = HomePage()
    home.show()
    sys.exit(app.exec_())
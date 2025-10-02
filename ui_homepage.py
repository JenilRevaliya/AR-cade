import sys
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QHBoxLayout,
                             QVBoxLayout, QScrollArea, QGraphicsDropShadowEffect)
from PyQt5.QtGui import QPixmap, QColor, QFont
from PyQt5.QtCore import (QTimer, Qt, QPropertyAnimation, QEasingCurve, QPoint, QRect,
                           QSequentialAnimationGroup)
from game_loader import load_games
from gesture_recognition import GestureRecognizer
from utils import convert_cv_qt

class GameCard(QWidget):
    """A 'card' widget to display a game with an icon and title."""
    def __init__(self, game_class, parent=None):
        super().__init__(parent)
        self.game_class = game_class
        self.setFixedSize(220, 300) # Increased height for floating room
        self.setStyleSheet("background-color: transparent;")

        # This is the widget we'll actually animate
        self.main_widget = QWidget(self)
        self.main_widget.setGeometry(0, 20, 220, 280) # Start in the "down" position

        self.layout = QVBoxLayout(self.main_widget)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.icon_label = QLabel(self.main_widget)
        self.icon_label.setFixedSize(200, 200)
        self.icon_label.setStyleSheet("background-color: #2E3B4E; border-radius: 10px;")
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.title_label = QLabel(game_class.__name__.replace("Game", ""), self.main_widget)
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #FFFFFF;")

        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.title_label)

        self.main_widget.setAutoFillBackground(True)
        self.base_style = "background-color: rgba(255, 255, 255, 0.1); border-radius: 15px;"
        self.hover_style = "background-color: rgba(255, 255, 255, 0.2); border: 1px solid #FFFFFF; border-radius: 15px;"
        self.selected_style = "background-color: rgba(0, 255, 255, 0.3); border: 2px solid #00FFFF; border-radius: 15px;"
        self.main_widget.setStyleSheet(self.base_style)

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.shadow.setOffset(0, 5)
        self.main_widget.setGraphicsEffect(self.shadow)

        self.float_animation = QPropertyAnimation(self.main_widget, b"pos")
        self.float_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.float_animation.setDuration(200)

    def set_hovered(self, hovered):
        is_selected = self.main_widget.styleSheet() == self.selected_style

        if not is_selected:
            self.main_widget.setStyleSheet(self.hover_style if hovered else self.base_style)

        self.float_animation.setEndValue(QPoint(0, 0) if hovered else QPoint(0, 20))
        self.float_animation.start()

    def set_selected(self, selected):
        if selected:
            self.main_widget.setStyleSheet(self.selected_style)
            self.play_click_animation()
        else:
            self.main_widget.setStyleSheet(self.base_style)
            # Ensure it floats down if unselected
            self.set_hovered(False)

    def play_click_animation(self):
        anim_group = QSequentialAnimationGroup(self)
        start_geo = self.main_widget.geometry()

        anim_shrink = QPropertyAnimation(self.main_widget, b"geometry")
        anim_shrink.setDuration(100)
        anim_shrink.setEndValue(QRect(start_geo.x() + 5, start_geo.y() + 5, start_geo.width() - 10, start_geo.height() - 10))

        anim_expand = QPropertyAnimation(self.main_widget, b"geometry")
        anim_expand.setDuration(100)
        anim_expand.setEndValue(start_geo)

        anim_group.addAnimation(anim_shrink)
        anim_group.addAnimation(anim_expand)
        anim_group.start()

class HomePage(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AR-cade")
        self.setStyleSheet("background-color: #1C2533;")
        self.setWindowState(Qt.WindowFullScreen)
        self.setWindowFlag(Qt.FramelessWindowHint)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Logo Placeholder
        self.logo_label = QLabel("AR-cade")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setFont(QFont("Segoe UI", 36, QFont.Bold))
        self.logo_label.setStyleSheet("color: #00FFFF; padding: 20px;")
        self.logo_label.setFixedHeight(100)
        self.layout.addWidget(self.logo_label)

        # Video Feed
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.video_label, 1) # Give video feed extra space

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

        self.hovered_card_index = -1
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

        # Process the original frame for gestures, which no longer draws on the frame
        processed_frame, gesture = self.gesture_recognizer.process_frame(frame)

        if self.gesture_cooldown > 0:
            self.gesture_cooldown -= 1
        else:
            self.handle_gestures(gesture)

        # Apply a subtle glass overlay for display
        overlay = processed_frame.copy()
        # A dark, semi-transparent blue tint for the glass effect
        cv2.rectangle(overlay, (0, 0), (overlay.shape[1], overlay.shape[0]), (50, 25, 0), -1)
        alpha = 0.1
        display_frame = cv2.addWeighted(overlay, alpha, processed_frame, 1 - alpha, 0)

        pixmap = convert_cv_qt(display_frame, self.video_label.width(), self.video_label.height())
        self.video_label.setPixmap(pixmap)

    def handle_gestures(self, gesture):
        if self.gesture_recognizer.hand_landmarks is None:
            # No hand detected, reset everything
            if self.hovered_card_index != -1:
                self.game_cards[self.hovered_card_index].set_hovered(False)
                self.hovered_card_index = -1
            if self.selected_card_index != -1:
                self.game_cards[self.selected_card_index].set_selected(False)
                self.selected_card_index = -1
            self.drag_start_x = None
            return

        hand_cx = self.gesture_recognizer.hand_landmarks.landmark[9].x * self.width()

        # Find which card is under the hand
        currently_over_card_index = -1
        for i, card in enumerate(self.game_cards):
            card_pos = card.mapToGlobal(card.pos())
            if card_pos.x() <= hand_cx < card_pos.x() + card.width():
                currently_over_card_index = i
                break

        # State: A card is already selected, waiting for launch confirmation
        if self.selected_card_index != -1:
            if gesture == "OPEN_PALM" and currently_over_card_index == self.selected_card_index:
                self.launch_game(self.game_cards[self.selected_card_index].game_class)
                self.gesture_cooldown = 50 # 1 sec cooldown
            return

        # Update hover state
        if currently_over_card_index != self.hovered_card_index:
            if self.hovered_card_index != -1:
                self.game_cards[self.hovered_card_index].set_hovered(False)
            if currently_over_card_index != -1:
                self.game_cards[currently_over_card_index].set_hovered(True)
            self.hovered_card_index = currently_over_card_index

        # Handle Selection
        if gesture == "CLOSED_PALM" and self.hovered_card_index != -1:
            self.selected_card_index = self.hovered_card_index
            self.game_cards[self.selected_card_index].set_selected(True)
            self.gesture_cooldown = 30 # 0.6 sec cooldown
            self.drag_start_x = None # Stop dragging when selecting
            return

        # Handle Drag/Scroll (only if not hovering to avoid conflict)
        if self.hovered_card_index == -1:
            if self.drag_start_x is None:
                self.drag_start_x = hand_cx

            delta_x = hand_cx - self.drag_start_x
            if abs(delta_x) > 30: # Drag threshold
                scrollbar = self.scroll_area.horizontalScrollBar()
                new_value = scrollbar.value() - int(delta_x * 1.5)

                self.anim = QPropertyAnimation(scrollbar, b"value")
                self.anim.setDuration(300)
                self.anim.setStartValue(scrollbar.value())
                self.anim.setEndValue(new_value)
                self.anim.setEasingCurve(QEasingCurve.OutCubic)
                self.anim.start()

                self.drag_start_x = hand_cx
        else:
            self.drag_start_x = None

    def launch_game(self, game_class):
        self.timer.stop() # Pause gesture processing

        # Create a temporary animated card
        selected_card = self.game_cards[self.selected_card_index]
        start_geo = selected_card.main_widget.geometry()
        start_geo.moveTopLeft(selected_card.mapTo(self, QPoint(0,0)) + QPoint(0,20))

        self.animating_card = GameCard(game_class, self)
        self.animating_card.main_widget.setStyleSheet(selected_card.selected_style)
        self.animating_card.setGeometry(start_geo)
        self.animating_card.show()

        # Hide the real UI
        self.scroll_area.hide()
        self.logo_label.hide()

        # Animation to expand the card
        self.launch_anim = QPropertyAnimation(self.animating_card, b"geometry")
        self.launch_anim.setDuration(400)
        self.launch_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.launch_anim.setEndValue(self.rect())
        self.launch_anim.finished.connect(lambda: self.start_game_instance(game_class))
        self.launch_anim.start()

    def start_game_instance(self, game_class):
        self.game_instance = game_class()
        self.game_instance.show()
        self.game_instance.start()
        self.game_instance.destroyed.connect(self.game_closed)
        self.hide() # Hide the main window

    def game_closed(self):
        # Clean up animation card if it exists
        if hasattr(self, 'animating_card'):
            self.animating_card.deleteLater()
            del self.animating_card

        # Restore UI
        self.scroll_area.show()
        self.logo_label.show()
        self.show()
        self.timer.start(20)

        # Reset all interaction states
        if self.hovered_card_index != -1:
            self.game_cards[self.hovered_card_index].set_hovered(False)
        if self.selected_card_index != -1:
            self.game_cards[self.selected_card_index].set_selected(False)
        self.hovered_card_index = -1
        self.selected_card_index = -1
        self.drag_start_x = None

    def closeEvent(self, event):
        self.cap.release()
        self.gesture_recognizer.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    home = HomePage()
    home.show()
    sys.exit(app.exec_())
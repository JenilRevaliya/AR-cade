import sys
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QHBoxLayout,
                             QVBoxLayout, QGridLayout, QGraphicsDropShadowEffect)
import math
from PyQt5.QtGui import (QPixmap, QColor, QFont, QPainter, QLinearGradient,
                           QTransform, QRegion)
from PyQt5.QtCore import (QTimer, Qt, QPropertyAnimation, QEasingCurve, QPoint, QRect,
                           QSequentialAnimationGroup, QParallelAnimationGroup)
from game_loader import load_games
from gesture_recognition import GestureRecognizer
from utils import convert_cv_qt

class GameCard(QWidget):
    """A 'card' widget for the game hub."""
    def __init__(self, game_class, parent=None):
        super().__init__(parent)
        self.game_class = game_class
        self.setFixedSize(220, 300) # Compact size without reflection
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
        self.title_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #FFFFFF;")

        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.title_label)

        self.main_widget.setAutoFillBackground(True)
        self.base_style = "background-color: rgba(0, 0, 0, 0.3); border-radius: 15px;"
        self.hover_style = "background-color: rgba(0, 0, 0, 0.4); border: 1px solid #FFFFFF; border-radius: 15px;"
        self.main_widget.setStyleSheet(self.base_style)

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.shadow.setOffset(0, 5)
        self.main_widget.setGraphicsEffect(self.shadow)

        self.float_animation = QPropertyAnimation(self.main_widget, b"pos")
        self.float_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.float_animation.setDuration(200)

        self.glow_animation = QPropertyAnimation(self.shadow, b"blurRadius")
        self.glow_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.glow_animation.setDuration(200)

    def set_hovered(self, hovered):
        self.main_widget.setStyleSheet(self.hover_style if hovered else self.base_style)
        self.float_animation.setEndValue(QPoint(0, 0) if hovered else QPoint(0, 20))
        self.glow_animation.setEndValue(40 if hovered else 20) # Intensify glow
        self.float_animation.start()
        self.glow_animation.start()

    def play_click_animation(self):
        # Size animation
        size_anim_group = QSequentialAnimationGroup()
        start_geo = self.main_widget.geometry()
        anim_shrink = QPropertyAnimation(self.main_widget, b"geometry")
        anim_shrink.setDuration(100)
        anim_shrink.setEndValue(QRect(start_geo.x() + 5, start_geo.y() + 5, start_geo.width() - 10, start_geo.height() - 10))
        anim_shrink.valueChanged.connect(self.update)
        anim_expand = QPropertyAnimation(self.main_widget, b"geometry")
        anim_expand.setDuration(100)
        anim_expand.setEndValue(start_geo)
        anim_expand.valueChanged.connect(self.update)
        size_anim_group.addAnimation(anim_shrink)
        size_anim_group.addAnimation(anim_expand)

        # Glow pulse animation
        glow_pulse_anim = QSequentialAnimationGroup()
        anim_glow_up = QPropertyAnimation(self.shadow, b"blurRadius")
        anim_glow_up.setDuration(100)
        anim_glow_up.setEndValue(60)
        anim_glow_down = QPropertyAnimation(self.shadow, b"blurRadius")
        anim_glow_down.setDuration(100)
        anim_glow_down.setEndValue(40) # Return to hovered glow state
        glow_pulse_anim.addAnimation(anim_glow_up)
        glow_pulse_anim.addAnimation(anim_glow_down)

        # Run both animations in parallel
        parallel_group = QParallelAnimationGroup(self)
        parallel_group.addAnimation(size_anim_group)
        parallel_group.addAnimation(glow_pulse_anim)
        parallel_group.start()

class HomePage(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AR-cade Hub")
        self.setStyleSheet("background-color: #000000;")
        self.setWindowState(Qt.WindowFullScreen)
        self.setWindowFlag(Qt.FramelessWindowHint)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.video_label = QLabel(self.central_widget)

        self.ui_overlay = QWidget(self.central_widget)
        self.ui_overlay.setStyleSheet("background-color: transparent;")
        self.overlay_layout = QVBoxLayout(self.ui_overlay)
        self.overlay_layout.setContentsMargins(50, 20, 50, 20)

        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(0)

        logo_label = QLabel("AR-cade Hub")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setFont(QFont("Arial", 48, QFont.Bold))
        logo_label.setStyleSheet("color: #00FFFF; padding-bottom: 0px;")

        desc_label = QLabel("Select a game using only your hands")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setFont(QFont("Arial", 16))
        desc_label.setStyleSheet("color: #FFFFFF; padding-top: 0px;")

        # Navigation Bar
        self.nav_bar = QWidget()
        nav_bar_layout = QHBoxLayout(self.nav_bar)
        self.nav_bar.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-family: 'Arial';
                font-size: 16px;
                padding: 10px 20px;
                background-color: transparent;
                border-radius: 15px;
            }
            QLabel#hover_tab {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QLabel#active_tab {
                background-color: rgba(0, 255, 255, 0.2);
                color: #00FFFF;
                font-weight: bold;
            }
        """)

        self.nav_tabs = []
        home_tab, games_tab, settings_tab = QLabel("Home"), QLabel("Games"), QLabel("Settings")
        home_tab.setObjectName("active_tab")
        self.nav_tabs.extend([home_tab, games_tab, settings_tab])

        nav_bar_layout.addStretch()
        for tab in self.nav_tabs:
            nav_bar_layout.addWidget(tab)
        nav_bar_layout.addStretch()

        header_layout.addWidget(logo_label)
        header_layout.addWidget(desc_label)
        header_layout.addWidget(self.nav_bar)
        self.overlay_layout.addWidget(header_widget, 0, Qt.AlignTop)
        self.overlay_layout.addStretch(1)

        self.game_grid_container = QWidget()
        grid_container_layout = QHBoxLayout(self.game_grid_container)
        self.game_grid = QGridLayout()
        self.game_grid.setSpacing(40)
        grid_container_layout.addStretch(1)
        grid_container_layout.addLayout(self.game_grid)
        grid_container_layout.addStretch(1)

        self.overlay_layout.addWidget(self.game_grid_container)
        self.overlay_layout.addStretch(2)

        self.games = load_games()
        self.game_cards = []
        self.init_game_list()

        self.cap = cv2.VideoCapture(0)
        self.gesture_recognizer = GestureRecognizer()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(20)

        self.hologram_timer = QTimer(self)
        self.hologram_timer.timeout.connect(self.update_hologram_effect)
        self.hologram_timer.start(50)
        self.hologram_counter = 0

        self.hovered_card_index = -1
        self.is_awaiting_confirmation = False
        self.card_to_launch_index = -1

        # Nav bar interaction state
        self.hovered_nav_index = -1
        self.active_nav_index = 0 # 'Home' is active by default
        self.nav_awaiting_confirmation = False

        self.gesture_cooldown = 0

        # Cursor for hand tracking
        self.cursor = QLabel(self.ui_overlay)
        self.cursor.setFixedSize(40, 40)
        self.cursor.setStyleSheet("background-color: rgba(0, 255, 255, 0.5); border: 2px solid white; border-radius: 20px;")
        self.cursor.hide()

    def init_game_list(self):
        # Add games to the grid, 3 columns per row
        row, col = 0, 0
        for i, game_class in enumerate(self.games):
            # Limit to 6 games for now as per the new design
            if i >= 6:
                break
            card = GameCard(game_class)
            self.game_grid.addWidget(card, row, col)
            self.game_cards.append(card)

            col += 1
            if col % 3 == 0:
                row += 1
                col = 0

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.video_label.setGeometry(self.rect())
        self.ui_overlay.setGeometry(self.rect())

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret: return
        frame = cv2.flip(frame, 1)
        processed_frame, gesture = self.gesture_recognizer.process_frame(frame)

        if self.gesture_cooldown > 0:
            self.gesture_cooldown -= 1
        else:
            self.handle_gestures(gesture)

        # Update cursor visibility and position
        if self.gesture_recognizer.hand_landmarks:
            self.cursor.show()
            hand_pos = self.gesture_recognizer.hand_landmarks.landmark[9]
            cursor_x = int(hand_pos.x * self.ui_overlay.width() - self.cursor.width() / 2)
            cursor_y = int(hand_pos.y * self.ui_overlay.height() - self.cursor.height() / 2)
            self.cursor.move(cursor_x, cursor_y)
        else:
            self.cursor.hide()

        # Convert the processed frame (which is in BGR) to RGB for Qt display
        rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        pixmap = convert_cv_qt(rgb_frame, self.video_label.width(), self.video_label.height())
        self.video_label.setPixmap(pixmap)

    def update_hologram_effect(self):
        self.hologram_counter += 1
        for i, card in enumerate(self.game_cards):
            # Only animate cards that are not currently being interacted with
            if i != self.hovered_card_index and i != self.card_to_launch_index:
                # Check if the main float-on-hover animation is running
                if card.float_animation.state() == QPropertyAnimation.State.Stopped:
                    # Calculate new y position using a sine wave for smooth floating
                    offset = math.sin((self.hologram_counter + i * 5) * 0.1) * 5  # 5 pixels of movement
                    card.main_widget.move(0, 20 + int(offset)) # Base y-position is 20

    def handle_gestures(self, gesture):
        if not self.gesture_recognizer.hand_landmarks:
            if self.hovered_card_index != -1:
                self.game_cards[self.hovered_card_index].set_hovered(False)
                self.hovered_card_index = -1
            if self.hovered_nav_index != -1:
                self.nav_tabs[self.hovered_nav_index].setObjectName("")
                self.style().polish(self.nav_bar)
                self.hovered_nav_index = -1
            self.is_awaiting_confirmation = False
            self.nav_awaiting_confirmation = False
            return

        cursor_rect = self.cursor.geometry()

        # --- NAV BAR INTERACTION ---
        new_hovered_nav_index = -1
        for i, tab in enumerate(self.nav_tabs):
            tab_rect_in_overlay = tab.geometry()
            tab_rect_in_overlay.moveTopLeft(tab.mapTo(self.ui_overlay, QPoint(0,0)))
            if tab_rect_in_overlay.intersects(cursor_rect):
                new_hovered_nav_index = i
                break

        if new_hovered_nav_index != -1:
            if self.hovered_card_index != -1:
                self.game_cards[self.hovered_card_index].set_hovered(False)
                self.hovered_card_index = -1

            if new_hovered_nav_index != self.hovered_nav_index:
                if self.hovered_nav_index != -1 and self.hovered_nav_index != self.active_nav_index:
                    self.nav_tabs[self.hovered_nav_index].setObjectName("")
                if new_hovered_nav_index != self.active_nav_index:
                    self.nav_tabs[new_hovered_nav_index].setObjectName("hover_tab")
                self.hovered_nav_index = new_hovered_nav_index
                self.style().polish(self.nav_bar)

            if gesture == "CLOSED_PALM" and self.hovered_nav_index != -1 and not self.nav_awaiting_confirmation:
                self.nav_awaiting_confirmation = True
                self.gesture_cooldown = 40
            elif gesture == "OPEN_PALM" and self.nav_awaiting_confirmation:
                if self.hovered_nav_index != -1 and self.hovered_nav_index != self.active_nav_index:
                    self.nav_tabs[self.active_nav_index].setObjectName("")
                    self.nav_tabs[self.hovered_nav_index].setObjectName("active_tab")
                    self.active_nav_index = self.hovered_nav_index
                    self.style().polish(self.nav_bar)
                    self.gesture_cooldown = 50
                self.nav_awaiting_confirmation = False
            return

        if self.hovered_nav_index != -1:
            if self.hovered_nav_index != self.active_nav_index:
                self.nav_tabs[self.hovered_nav_index].setObjectName("")
            self.style().polish(self.nav_bar)
            self.hovered_nav_index = -1

        # --- GAME CARD INTERACTION ---
        new_hovered_card_index = -1
        for i, card in enumerate(self.game_cards):
            if card.geometry().intersects(cursor_rect):
                new_hovered_card_index = i
                break

        # If we are waiting for a click confirmation, don't change the hover state
        if not self.is_awaiting_confirmation:
            if new_hovered_card_index != self.hovered_card_index:
                if self.hovered_card_index != -1:
                    self.game_cards[self.hovered_card_index].set_hovered(False)
                if new_hovered_card_index != -1:
                    self.game_cards[new_hovered_card_index].set_hovered(True)
                self.hovered_card_index = new_hovered_card_index

        if gesture == "CLOSED_PALM" and self.hovered_card_index != -1:
            if not self.is_awaiting_confirmation:
                self.is_awaiting_confirmation = True
                self.card_to_launch_index = self.hovered_card_index
                self.game_cards[self.card_to_launch_index].play_click_animation()
                self.gesture_cooldown = 40
        elif gesture == "OPEN_PALM" and self.is_awaiting_confirmation:
            if self.hovered_card_index == self.card_to_launch_index:
                game_class = self.game_cards[self.card_to_launch_index].game_class
                self.launch_game(game_class)
                self.gesture_cooldown = 50
            self.is_awaiting_confirmation = False

    def launch_game(self, game_class):
        self.timer.stop()
        self.hologram_timer.stop()

        selected_card = self.game_cards[self.card_to_launch_index]
        start_geo = selected_card.geometry()
        start_geo.moveTopLeft(selected_card.mapTo(self.ui_overlay, QPoint(0,0)))

        self.animating_card = GameCard(game_class, self.ui_overlay)
        self.animating_card.setGeometry(start_geo)
        self.animating_card.show()

        self.game_grid_container.hide()

        geom_anim = QPropertyAnimation(self.animating_card, b"geometry")
        geom_anim.setDuration(400)
        geom_anim.setEasingCurve(QEasingCurve.InOutCubic)
        geom_anim.setEndValue(self.ui_overlay.rect())

        glow_anim = QPropertyAnimation(self.animating_card.shadow, b"blurRadius")
        glow_anim.setDuration(400)
        glow_anim.setEasingCurve(QEasingCurve.InQuad)
        glow_anim.setEndValue(200)

        self.launch_anim_group = QParallelAnimationGroup(self)
        self.launch_anim_group.addAnimation(geom_anim)
        self.launch_anim_group.addAnimation(glow_anim)
        self.launch_anim_group.finished.connect(lambda: self.start_game_instance(game_class))
        self.launch_anim_group.start()

    def start_game_instance(self, game_class):
        self.game_instance = game_class()
        self.game_instance.show()
        self.game_instance.start()
        self.game_instance.destroyed.connect(self.game_closed)
        self.hide()

    def game_closed(self):
        if hasattr(self, 'animating_card'):
            self.animating_card.deleteLater()
            del self.animating_card

        self.game_grid_container.show()
        self.show()
        self.timer.start(20)
        self.hologram_timer.start(50)

        self.hovered_card_index = -1
        self.is_awaiting_confirmation = False
        self.card_to_launch_index = -1
        self.hovered_nav_index = -1
        self.nav_awaiting_confirmation = False

    def closeEvent(self, event):
        self.cap.release()
        self.gesture_recognizer.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    home = HomePage()
    home.show()
    sys.exit(app.exec_())
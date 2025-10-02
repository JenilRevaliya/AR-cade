import cv2
from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtCore import QTimer
from utils import convert_cv_qt

class BaseGame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.image_label = QLabel(self)
        self.image_label.resize(self.width(), self.height())

        self.cap = cv2.VideoCapture(0)

        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_game)

    def start(self):
        """Initializes the game window and resources."""
        print("Game started!")
        self.running = True
        self.game_timer.start(30) # 30ms ~ 33 FPS
        self.show()

    def update_game(self):
        """Main loop for game logic and rendering, driven by a QTimer."""
        if not self.running:
            return

        ret, frame = self.cap.read()
        if ret:
            # Game logic and rendering here
            # For now, just display the camera feed
            self.render_frame(frame)

    def render_frame(self, frame):
        """Renders a single frame to the widget."""
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qt_image = convert_cv_qt(rgb_image, self.width(), self.height())
        self.image_label.setPixmap(qt_image)

    def exit(self):
        """Closes the game and returns to the homepage."""
        print("Exiting game.")
        self.running = False
        self.game_timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        self.close()
        # Note: We need a way to signal the homepage to show itself again.
        # This will be handled in ui_homepage.py

    def resizeEvent(self, event):
        self.image_label.resize(self.width(), self.height())
        super().resizeEvent(event)

    def closeEvent(self, event):
        """Handle the window close event."""
        self.exit()
        event.accept()
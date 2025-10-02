import cv2
from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtCore import QTimer, Qt
from utils import convert_cv_qt
from gesture_recognition import GestureRecognizer

class BaseGame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.image_label = QLabel(self)
        self.image_label.resize(self.width(), self.height())

        self.cap = cv2.VideoCapture(0)
        self.gesture_recognizer = GestureRecognizer()

        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_game)

        self.exit_gesture_counter = 0
        self.EXIT_GESTURE_THRESHOLD = 60 # 2 seconds at ~30fps

    def start(self):
        """Initializes the game window and resources."""
        print("Game started!")
        self.running = True
        self.game_timer.start(30) # 30ms ~ 33 FPS
        self.showFullScreen()
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.show()

    def update_game(self):
        """Main loop for game logic and rendering, driven by a QTimer."""
        if not self.running:
            return

        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            # Process gestures but don't draw on the frame
            _, gesture = self.gesture_recognizer.process_frame(frame)
            self.handle_exit_gesture(gesture)

            # Game logic and rendering here
            self.render_frame(frame)

    def handle_exit_gesture(self, gesture):
        if gesture == "CLOSED_PALM":
            self.exit_gesture_counter += 1
            if self.exit_gesture_counter > self.EXIT_GESTURE_THRESHOLD:
                self.exit()
        else:
            self.exit_gesture_counter = 0

    def render_frame(self, frame):
        """Renders a single frame to the widget."""
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qt_image = convert_cv_qt(rgb_image, self.width(), self.height())
        self.image_label.setPixmap(qt_image)

    def exit(self):
        """Closes the game and returns to the homepage."""
        if not self.running: return # Avoid multiple exits
        print("Exiting game.")
        self.running = False
        self.game_timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        self.gesture_recognizer.close()
        self.close()

    def resizeEvent(self, event):
        self.image_label.resize(self.width(), self.height())
        super().resizeEvent(event)

    def closeEvent(self, event):
        """Handle the window close event."""
        self.exit()
        event.accept()
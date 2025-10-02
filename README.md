# AR-cade: The Augmented Reality Gesture-Controlled Game Hub

![AR-cade Banner](https://i.imgur.com/your-banner-image.png) <!--- Placeholder for a cool project banner -->

**AR-cade** is a futuristic, modular game hub that uses your hand gestures to navigate and play a variety of augmented reality mini-games. Built with Python, PyQt5, OpenCV, and MediaPipe, this project transforms your webcam into a powerful controller, creating an immersive and intuitive user experience.

## ✨ Features

-   **Gesture-Based Navigation:** Control the entire interface without a mouse or keyboard.
    -   🖐️ **Open Palm:** Highlight a game to select it.
    -   🤏 **Pinch:** Confirm your selection and launch the game.
    -   ↔️ **Drag Hand:** Scroll left and right through the game library.
    -   ✊ **Closed Palm:** Exit a game and return to the main menu.
-   **Dynamic Game Loading:** Simply drop new game files into the `games/` directory, and they will automatically appear on the homepage. No core system modifications needed!
-   **Premium UI:** A modern, sleek interface designed with a "glassmorphism" aesthetic, featuring a dark theme and neon highlights for a premium feel.
-   **Extensible Game Framework:** A simple `BaseGame` class makes it easy for developers to create and add their own AR games to the platform.
-   **Live AR Overlay:** The application overlays UI elements and game graphics onto your live webcam feed.

## 🚀 Getting Started

Follow these instructions to get AR-cade up and running on your local machine.

### Prerequisites

You will need Python 3 and `pip` installed on your system.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd AR-cade
    ```

2.  **Install the required dependencies:**
    The project relies on a few key libraries. Install them using the following command:
    ```bash
    pip install opencv-python PyQt5 mediapipe
    ```

### Running the Application

Once the dependencies are installed, you can launch the AR-cade hub with a single command:

```bash
python main.py
```

The application window will open, and your webcam will activate. You can now use hand gestures to navigate the interface.

## 🎮 Creating Your Own Game

Want to add your own game to AR-cade? It's easy!

1.  **Create a new Python file** inside the `games/` directory. The filename **must** start with `game_` (e.g., `game_mycoolgame.py`).

2.  **Inherit from `BaseGame`:** In your new file, import the `BaseGame` class and create your own game class that inherits from it.

3.  **Implement the core methods:**
    -   `__init__(self, parent=None)`: Initialize your game's state and UI elements.
    -   `update_game(self)`: This method is called on every frame. Put your main game logic and rendering calls here.
    -   `exit(self)`: Clean up any resources when the game closes.

Here is a basic template to get you started:

```python
# In games/game_myawesomegame.py

from game_base import BaseGame
from PyQt5.QtWidgets import QLabel # Example widget

class MyAwesomeGame(BaseGame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("My Awesome Game")
        # Add your game's UI elements here
        self.my_label = QLabel("Welcome to my game!", self)
        self.my_label.setStyleSheet("color: white; font-size: 24px;")

    def update_game(self):
        # This is your game loop!
        # First, call the parent method to render the camera feed
        super().update_game()

        # Add your game logic here
        # For example, move your label around
        current_pos = self.my_label.pos()
        self.my_label.move(current_pos.x() + 1, current_pos.y())
        if current_pos.x() > self.width():
            self.my_label.move(0, current_pos.y())

    def exit(self):
        print("Cleaning up my awesome game.")
        super().exit()

```

That's it! Save the file, and your new game will appear in the AR-cade hub the next time you launch it.

## 🛠️ Project Structure

```
.
├── games/
│   ├── game_test.py      # An example game
│   └── ...               # Your other games go here
├── game_base.py          # The base class all games must inherit from
├── game_loader.py        # Dynamically loads games from the games/ directory
├── gesture_recognition.py# Handles hand tracking and gesture detection
├── main.py               # The main entry point of the application
├── ui_homepage.py        # The main UI for the game hub
├── utils.py              # Utility functions (e.g., image conversion)
└── README.md
```

## 🤝 Contributing

Contributions are welcome! If you have ideas for new features, games, or improvements, feel free to fork the repository and submit a pull request.
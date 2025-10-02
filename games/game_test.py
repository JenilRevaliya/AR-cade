from game_base import BaseGame

class TestGame(BaseGame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test Game")

    def update_game(self):
        # Override to provide test-specific game logic if needed
        super().update_game()

    def exit(self):
        # Override to provide test-specific cleanup if needed
        super().exit()
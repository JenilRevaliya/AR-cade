import unittest
import os
from game_loader import load_games

class TestGameLoader(unittest.TestCase):

    def test_load_games(self):
        """
        Tests that the load_games function correctly finds and loads game files.
        """
        # Ensure the dummy game file exists
        if not os.path.exists('games/game_test.py'):
            self.fail("Test setup failed: games/game_test.py not found.")
        if not os.path.exists('games/game_tictactoe.py'):
            self.fail("Test setup failed: games/game_tictactoe.py not found.")

        games = load_games()
        self.assertEqual(len(games), 2)

        game_class_names = [g.__name__ for g in games]
        self.assertIn('TestGame', game_class_names)
        self.assertIn('ARTicTacToe', game_class_names)

if __name__ == '__main__':
    unittest.main()
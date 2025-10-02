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

        games = load_games()
        self.assertEqual(len(games), 1)

        game_class = games[0]
        self.assertEqual(game_class.__name__, 'TestGame')

if __name__ == '__main__':
    unittest.main()
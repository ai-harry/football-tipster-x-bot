import unittest
from unittest.mock import patch, MagicMock
from src.odds_api_client import OddsAPIClient

class TestOddsAPIClient(unittest.TestCase):
    def setUp(self):
        self.client = OddsAPIClient("test_api_key")

    @patch('requests.Session')
    def test_get_odds(self, mock_session):
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_session.return_value.get.return_value = mock_response

        # Test the get_odds method
        result = self.client.get_odds("soccer_epl")
        
        # Verify the result
        self.assertEqual(result, {"test": "data"})

if __name__ == '__main__':
    unittest.main() 
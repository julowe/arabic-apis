import unittest
from unittest.mock import patch, Mock


class TestQuranApi(unittest.TestCase):
    @patch("quran_api.requests.post")
    def test_get_access_token_returns_token_from_response(self, mock_post):
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "abc123"}
        mock_post.return_value = mock_response

        # Act
        from quran_api import get_access_token

        token = get_access_token("https://example.com", "client_id", "client_secret")

        # Assert
        self.assertEqual(token, "abc123")
        mock_post.assert_called_once()

    @patch("quran_api.requests.get")
    def test_get_recitations_returns_raw_json(self, mock_get):
        data = {"recitations": [{"id": 1}, {"id": 2}]}
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_get.return_value = mock_response

        from quran_api import get_recitations

        result = get_recitations("https://api", "token", "client")

        self.assertIs(result, data)
        mock_get.assert_called_once()

    @patch("quran_api.requests.get")
    def test_get_recitation_filelist_returns_raw_json(self, mock_get):
        data = {"audio_files": ["a.mp3", "b.mp3"]}
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_get.return_value = mock_response

        from quran_api import get_recitation_filelist

        result = get_recitation_filelist("https://api", "token", "client", 7, 2)

        self.assertIs(result, data)
        mock_get.assert_called_once()

    @patch("quran_api.requests.get")
    def test_get_chapter_returns_raw_json(self, mock_get):
        data = {"chapter": {"id": 1}}
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_get.return_value = mock_response

        from quran_api import get_chapter

        result = get_chapter("https://api", "token", "client", 1)

        self.assertIs(result, data)
        mock_get.assert_called_once()

    @patch("quran_api.requests.get")
    def test_get_verse_returns_raw_json(self, mock_get):
        data = {"verse": {"key": "1:1"}}
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_get.return_value = mock_response

        from quran_api import get_verse

        result = get_verse("https://api", "token", "client", 1, 1, translations=[20])

        self.assertIs(result, data)
        mock_get.assert_called_once()

    @patch("quran_api.requests.get")
    def test_get_translations_returns_raw_json(self, mock_get):
        data = {"translations": ["en", "ur"]}
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_get.return_value = mock_response

        from quran_api import get_translations

        result = get_translations("https://api", "token", "client")

        self.assertIs(result, data)
        mock_get.assert_called_once()


if __name__ == "__main__":
    unittest.main()

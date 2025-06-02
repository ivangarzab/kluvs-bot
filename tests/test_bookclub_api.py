import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
import requests

# Add parent directory to path to import the BookClubAPI class
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.bookclub_api import BookClubAPI, ResourceNotFoundError, ValidationError, AuthenticationError, APIError

class TestBookClubAPI(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.api = BookClubAPI(
            base_url="http://test-url.supabase.co",
            api_key="test-key"
        )
        self.test_guild_id = "1039326367428395038"
        
        # Verify the headers are set correctly
        self.assertEqual(self.api.headers["Content-Type"], "application/json")
        self.assertEqual(self.api.headers["Authorization"], "Bearer test-key")
        self.assertEqual(self.api.functions_url, "http://test-url.supabase.co/functions/v1")

    # Server endpoint tests
    @patch('requests.post')
    def test_register_server(self, mock_post):
        """Test register_server method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Server registered successfully",
            "server": {"id": self.test_guild_id, "name": "Test Server"}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Call the method
        result = self.api.register_server(self.test_guild_id, "Test Server")
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["server"]["name"], "Test Server")
        mock_post.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/server",
            headers=self.api.headers,
            json={"id": self.test_guild_id, "name": "Test Server"}
        )

    @patch('requests.get')
    def test_get_server(self, mock_get):
        """Test get_server method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": self.test_guild_id,
            "name": "Test Server",
            "created_at": "2025-01-01T00:00:00Z",
            "clubs": [{"id": "club-1", "name": "Test Club"}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.api.get_server(self.test_guild_id)
        
        # Assertions
        self.assertEqual(result["name"], "Test Server")
        self.assertEqual(len(result["clubs"]), 1)
        mock_get.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/server",
            headers=self.api.headers,
            params={"id": self.test_guild_id}
        )

    @patch('requests.put')
    def test_update_server(self, mock_put):
        """Test update_server method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Server updated successfully",
            "server": {"id": self.test_guild_id, "name": "Updated Server"}
        }
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        # Call the method
        result = self.api.update_server(self.test_guild_id, "Updated Server")
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["server"]["name"], "Updated Server")
        mock_put.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/server",
            headers=self.api.headers,
            json={"id": self.test_guild_id, "name": "Updated Server"}
        )

    @patch('requests.delete')
    def test_delete_server(self, mock_delete):
        """Test delete_server method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Server and all associated data deleted successfully"
        }
        mock_response.raise_for_status = Mock()
        mock_delete.return_value = mock_response
        
        # Call the method
        result = self.api.delete_server(self.test_guild_id)
        
        # Assertions
        self.assertTrue(result["success"])
        mock_delete.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/server",
            headers=self.api.headers,
            params={"id": self.test_guild_id}
        )

    # Club endpoint tests (updated for multi-server)
    @patch('requests.get')
    def test_get_club(self, mock_get):
        """Test get_club method with guild_id."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "club-1", 
            "name": "Test Club",
            "server_id": self.test_guild_id,
            "members": [{"id": 1, "name": "Test Member"}],
            "active_session": None,
            "past_sessions": []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.api.get_club("club-1", self.test_guild_id)
        
        # Assertions
        self.assertEqual(result["name"], "Test Club")
        self.assertEqual(result["server_id"], self.test_guild_id)
        self.assertEqual(len(result["members"]), 1)
        mock_get.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/club",
            headers=self.api.headers,
            params={"id": "club-1", "server_id": self.test_guild_id}
        )

    @patch('requests.post')
    def test_create_club(self, mock_post):
        """Test create_club method with guild_id."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Club created successfully",
            "club": {"id": "new-club", "name": "New Club", "server_id": self.test_guild_id}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Test data
        club_data = {
            "name": "New Club",
            "members": []
        }
        
        # Call the method
        result = self.api.create_club(club_data, self.test_guild_id)
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["club"]["name"], "New Club")
        self.assertEqual(result["club"]["server_id"], self.test_guild_id)
        
        # Verify the server_id was added to the data
        expected_data = {**club_data, "server_id": self.test_guild_id}
        mock_post.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/club",
            headers=self.api.headers,
            json=expected_data
        )

    @patch('requests.put')
    def test_update_club(self, mock_put):
        """Test update_club method with guild_id."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Club updated successfully",
            "club": {"id": "club-1", "name": "Updated Club Name", "server_id": self.test_guild_id}
        }
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        # Call the method
        update_data = {"name": "Updated Club Name"}
        result = self.api.update_club("club-1", update_data, self.test_guild_id)
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["club"]["name"], "Updated Club Name")
        mock_put.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/club",
            headers=self.api.headers,
            json={"id": "club-1", "server_id": self.test_guild_id, **update_data}
        )

    @patch('requests.delete')
    def test_delete_club(self, mock_delete):
        """Test delete_club method with guild_id."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Club deleted successfully"
        }
        mock_response.raise_for_status = Mock()
        mock_delete.return_value = mock_response
        
        # Call the method
        result = self.api.delete_club("club-1", self.test_guild_id)
        
        # Assertions
        self.assertTrue(result["success"])
        mock_delete.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/club",
            headers=self.api.headers,
            params={"id": "club-1", "server_id": self.test_guild_id}
        )

    # Member endpoint tests (unchanged - members aren't server-specific)
    @patch('requests.get')
    def test_get_member(self, mock_get):
        """Test get_member method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 1,
            "name": "Test Member",
            "points": 100,
            "books_read": 5,
            "clubs": [{"id": "club-1", "name": "Test Club"}],
            "shame_clubs": []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.api.get_member(1)
        
        # Assertions
        self.assertEqual(result["name"], "Test Member")
        self.assertEqual(result["points"], 100)
        mock_get.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/member",
            headers=self.api.headers,
            params={"id": 1}
        )

    @patch('requests.post')
    def test_create_member(self, mock_post):
        """Test create_member method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Member created successfully",
            "member": {"id": 1, "name": "New Member", "points": 0, "books_read": 0}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Test data
        member_data = {
            "name": "New Member",
            "points": 0,
            "books_read": 0,
            "clubs": ["club-1"]
        }
        
        # Call the method
        result = self.api.create_member(member_data)
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["member"]["name"], "New Member")
        mock_post.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/member",
            headers=self.api.headers,
            json=member_data
        )

    @patch('requests.put')
    def test_update_member(self, mock_put):
        """Test update_member method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Member updated successfully",
            "member": {"id": 1, "name": "Updated Member", "points": 150},
            "clubs_updated": True
        }
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        # Test data
        update_data = {
            "name": "Updated Member",
            "points": 150,
            "clubs": ["club-1", "club-2"]
        }
        
        # Call the method
        result = self.api.update_member(1, update_data)
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["member"]["name"], "Updated Member")
        self.assertTrue(result["clubs_updated"])
        mock_put.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/member",
            headers=self.api.headers,
            json={"id": 1, **update_data}
        )

    @patch('requests.delete')
    def test_delete_member(self, mock_delete):
        """Test delete_member method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Member deleted successfully"
        }
        mock_response.raise_for_status = Mock()
        mock_delete.return_value = mock_response
        
        # Call the method
        result = self.api.delete_member(1)
        
        # Assertions
        self.assertTrue(result["success"])
        mock_delete.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/member",
            headers=self.api.headers,
            params={"id": 1}
        )

    # Session endpoint tests (unchanged - sessions inherit server context from clubs)
    @patch('requests.get')
    def test_get_session(self, mock_get):
        """Test get_session method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "session-1",
            "club": {"id": "club-1", "name": "Test Club"},
            "book": {"id": 1, "title": "Test Book", "author": "Test Author"},
            "due_date": "2025-04-15",
            "discussions": [{"id": "disc-1", "title": "Chapter 1-3", "date": "2025-04-01"}],
            "shame_list": []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.api.get_session("session-1")
        
        # Assertions
        self.assertEqual(result["book"]["title"], "Test Book")
        self.assertEqual(len(result["discussions"]), 1)
        mock_get.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/session",
            headers=self.api.headers,
            params={"id": "session-1"}
        )

    @patch('requests.post')
    def test_create_session(self, mock_post):
        """Test create_session method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Session created successfully",
            "session": {
                "id": "new-session",
                "club_id": "club-1",
                "book": {"id": 1, "title": "New Book", "author": "Author Name"}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Test data
        session_data = {
            "club_id": "club-1",
            "book": {"title": "New Book", "author": "Author Name"},
            "due_date": "2025-05-15",
            "discussions": [
                {"title": "First Discussion", "date": "2025-05-01"}
            ]
        }
        
        # Call the method
        result = self.api.create_session(session_data)
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["session"]["book"]["title"], "New Book")
        mock_post.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/session",
            headers=self.api.headers,
            json=session_data
        )

    @patch('requests.put')
    def test_update_session(self, mock_put):
        """Test update_session method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Session updated successfully",
            "updates": {
                "book": True,
                "session": True,
                "discussions": False
            }
        }
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        # Test data
        update_data = {
            "due_date": "2025-06-15",
            "book": {"edition": "Revised Edition"}
        }
        
        # Call the method
        result = self.api.update_session("session-1", update_data)
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertTrue(result["updates"]["book"])
        self.assertTrue(result["updates"]["session"])
        mock_put.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/session",
            headers=self.api.headers,
            json={"id": "session-1", **update_data}
        )

    @patch('requests.delete')
    def test_delete_session(self, mock_delete):
        """Test delete_session method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Session deleted successfully"
        }
        mock_response.raise_for_status = Mock()
        mock_delete.return_value = mock_response
        
        # Call the method
        result = self.api.delete_session("session-1")
        
        # Assertions
        self.assertTrue(result["success"])
        mock_delete.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/session",
            headers=self.api.headers,
            params={"id": "session-1"}
        )

    # Error handling tests
    @patch('requests.get')
    def test_resource_not_found_error(self, mock_get):
        """Test ResourceNotFoundError handling."""
        # Set up mock to raise a 404 error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error", response=mock_response
        )
        mock_get.return_value = mock_response
        
        # Call the method and expect a ResourceNotFoundError
        with self.assertRaises(ResourceNotFoundError):
            self.api.get_club("non-existent-club", self.test_guild_id)

    @patch('requests.post')
    def test_validation_error(self, mock_post):
        """Test ValidationError handling."""
        # Set up mock to raise a 400 error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "400 Client Error", response=mock_response
        )
        mock_post.return_value = mock_response
        
        # Call the method and expect a ValidationError
        with self.assertRaises(ValidationError):
            self.api.create_club({"invalid": "data"}, self.test_guild_id)

    @patch('requests.get')
    def test_authentication_error(self, mock_get):
        """Test AuthenticationError handling."""
        # Set up mock to raise a 401 error
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Client Error", response=mock_response
        )
        mock_get.return_value = mock_response
        
        # Call the method and expect an AuthenticationError
        with self.assertRaises(AuthenticationError):
            self.api.get_club("club-1", self.test_guild_id)

    @patch('requests.get')
    def test_connection_error(self, mock_get):
        """Test connection error handling."""
        # Set up mock to raise a ConnectionError
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        # Call the method and expect an APIError
        with self.assertRaises(APIError) as context:
            self.api.get_club("club-1", self.test_guild_id)
        
        # Verify the error message contains helpful information
        self.assertIn("Connection error", str(context.exception))
        self.assertIn("server is running", str(context.exception))

    @patch('requests.get')
    def test_general_api_error(self, mock_get):
        """Test general API error handling."""
        # Set up mock to raise a 500 error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error", response=mock_response
        )
        mock_get.return_value = mock_response
        
        # Call the method and expect an APIError
        with self.assertRaises(APIError) as context:
            self.api.get_club("club-1", self.test_guild_id)
        
        # Verify the error message contains the status code
        self.assertIn("500", str(context.exception))


if __name__ == '__main__':
    unittest.main()
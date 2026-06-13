import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
import requests
import asyncio

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

    @patch('requests.get')
    def test_get_club_by_uuid(self, mock_get):
        """Test get_club_by_uuid fetches club by ID without guild context."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "club-uuid-1",
            "name": "Dashboard Club",
            "discord_channel": None,
            "members": []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.api.get_club_by_uuid("club-uuid-1")

        self.assertEqual(result["id"], "club-uuid-1")
        self.assertEqual(result["name"], "Dashboard Club")
        mock_get.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/club",
            headers=self.api.headers,
            params={"id": "club-uuid-1"}
        )

    @patch('requests.get')
    def test_get_club_by_uuid_not_found(self, mock_get):
        """Test get_club_by_uuid raises ResourceNotFoundError on 404."""
        from requests.exceptions import HTTPError
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        with self.assertRaises(ResourceNotFoundError):
            self.api.get_club_by_uuid("nonexistent-uuid")

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

    @patch('requests.get')
    def test_get_member_by_discord_id_found(self, mock_get):
        """Test get_member_by_discord_id returns member data when found."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 1,
            "name": "Alice",
            "discord_id": "123456789",
            "clubs": [{"id": "club-1", "name": "Test Club"}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.api.get_member_by_discord_id("123456789")

        self.assertEqual(result["name"], "Alice")
        self.assertEqual(result["discord_id"], "123456789")
        mock_get.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/member",
            headers=self.api.headers,
            params={"discord_id": "123456789"}
        )

    @patch('requests.get')
    def test_get_member_by_discord_id_not_found(self, mock_get):
        """Test get_member_by_discord_id returns None on 404."""
        from requests.exceptions import HTTPError
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        result = self.api.get_member_by_discord_id("nonexistent")

        self.assertIsNone(result)

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
            "discussions": [{"id": "disc-1", "title": "Chapter 1-3", "scheduled_at": "2025-04-01T18:00:00+00:00"}],
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
                {"title": "First Discussion", "scheduled_at": "2025-05-01T18:00:00+00:00"}
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

    @patch('requests.put')
    def test_finish_session_success(self, mock_put):
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Session finished",
            "members_credited": 3,
        }
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response

        result = self.api.finish_session("session-1")

        self.assertTrue(result["success"])
        self.assertEqual(result["members_credited"], 3)
        mock_put.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/session",
            headers=self.api.headers,
            json={"id": "session-1", "finish": True},
        )

    @patch('requests.put')
    def test_finish_session_already_finished(self, mock_put):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Session is already finished"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "400 Client Error", response=mock_response
        )
        mock_put.return_value = mock_response

        with self.assertRaises(ValidationError):
            self.api.finish_session("session-1")

    @patch('requests.put')
    def test_finish_session_not_found(self, mock_put):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error", response=mock_response
        )
        mock_put.return_value = mock_response

        with self.assertRaises(ResourceNotFoundError):
            self.api.finish_session("session-1")

    @patch('requests.put')
    def test_finish_session_auth_error(self, mock_put):
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Client Error", response=mock_response
        )
        mock_put.return_value = mock_response

        with self.assertRaises(AuthenticationError):
            self.api.finish_session("session-1")

    @patch('requests.put')
    def test_update_session_members_success(self, mock_put):
        mock_response = Mock()
        mock_response.json.return_value = {"success": True, "message": "Members updated"}
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response

        members = [
            {"member_id": 1, "is_reading": True},
            {"member_id": 2, "is_reading": False},
        ]
        result = self.api.update_session_members("session-1", members)

        self.assertTrue(result["success"])
        mock_put.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/session",
            headers=self.api.headers,
            json={"id": "session-1", "session_members": members},
        )

    @patch('requests.put')
    def test_update_session_members_not_found(self, mock_put):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error", response=mock_response
        )
        mock_put.return_value = mock_response

        with self.assertRaises(ResourceNotFoundError):
            self.api.update_session_members("session-1", [])

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

    @patch('requests.get')
    def test_get_club_by_discord_channel(self, mock_get):
        """Test get_club_by_discord_channel method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "club-1",
            "name": "Test Club",
            "discord_channel": "123456789",
            "server_id": self.test_guild_id
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call the method
        result = self.api.get_club_by_discord_channel("123456789", self.test_guild_id)

        # Assertions
        self.assertEqual(result["name"], "Test Club")
        self.assertEqual(result["discord_channel"], "123456789")
        mock_get.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/club",
            headers=self.api.headers,
            params={"discord_channel": "123456789", "server_id": self.test_guild_id}
        )

    @patch('requests.get')
    def test_find_club_in_channel_found(self, mock_get):
        """Test find_club_in_channel when club is found."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "club-1",
            "name": "Test Club",
            "discord_channel": "123456789"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call the method
        result = self.api.find_club_in_channel("123456789", self.test_guild_id)

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Test Club")

    @patch('requests.get')
    def test_find_club_in_channel_not_found(self, mock_get):
        """Test find_club_in_channel when no club is found."""
        # Set up mock to raise 404
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Club not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found", response=mock_response
        )
        mock_get.return_value = mock_response

        # Call the method - should return None instead of raising exception
        result = self.api.find_club_in_channel("999999999", self.test_guild_id)

        # Assertions
        self.assertIsNone(result)

    @patch('requests.get')
    def test_get_all_servers(self, mock_get):
        """Test get_all_servers method."""
        # Set up mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "servers": [
                {"id": "server-1", "name": "Server 1"},
                {"id": "server-2", "name": "Server 2"}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call the method
        result = self.api.get_all_servers()

        # Assertions
        self.assertEqual(len(result["servers"]), 2)
        mock_get.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/server",
            headers=self.api.headers
        )

    @patch('requests.get')
    def test_get_server_clubs(self, mock_get):
        """Test get_server_clubs method."""
        # Set up mock response - get_server_clubs calls get_server internally
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": self.test_guild_id,
            "name": "Test Server",
            "clubs": [
                {"id": "club-1", "name": "Club 1"},
                {"id": "club-2", "name": "Club 2"}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call the method
        result = self.api.get_server_clubs(self.test_guild_id)

        # Assertions
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Club 1")
        # Should call get_server endpoint
        mock_get.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/server",
            headers=self.api.headers,
            params={"id": self.test_guild_id}
        )

    # Book endpoint tests
    @patch('requests.get')
    def test_search_books_success(self, mock_get):
        """Test search_books with valid query."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "books": [
                {
                    "external_google_id": "abc123",
                    "title": "Dune",
                    "author": "Frank Herbert",
                    "year": 1965
                },
                {
                    "external_google_id": "def456",
                    "title": "Foundation",
                    "author": "Isaac Asimov",
                    "year": 1951
                }
            ],
            "total": 2
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.api._search_books_sync("dune")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "Dune")
        self.assertEqual(result[0]["external_google_id"], "abc123")
        mock_get.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/book",
            headers=self.api.headers,
            params={"q": "dune"}
        )

    def test_search_books_min_query_length(self):
        """Test search_books returns empty list for short query."""
        result = self.api._search_books_sync("a")
        self.assertEqual(result, [])

    @patch('requests.post')
    def test_register_book_success(self, mock_post):
        """Test register_book creates a new book."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Book registered successfully",
            "book": {
                "id": 42,
                "title": "Dune",
                "author": "Frank Herbert",
                "external_google_id": "abc123",
                "year": 1965
            },
            "created": True
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.api._register_book_sync("Dune", "Frank Herbert", "abc123")

        self.assertEqual(result["id"], 42)
        self.assertEqual(result["title"], "Dune")
        mock_post.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/book",
            headers=self.api.headers,
            json={"title": "Dune", "author": "Frank Herbert", "external_google_id": "abc123"}
        )

    @patch('requests.post')
    def test_register_book_idempotent(self, mock_post):
        """Test register_book returns existing book if google_id exists."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Book already registered",
            "book": {
                "id": 42,
                "title": "Dune",
                "author": "Frank Herbert",
                "external_google_id": "abc123"
            },
            "created": False
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.api._register_book_sync("Dune", "Frank Herbert", "abc123")

        self.assertEqual(result["id"], 42)
        self.assertFalse(result.get("created", False))

    @patch('requests.post')
    def test_register_book_no_google_id(self, mock_post):
        """Test register_book without external_google_id."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Book registered successfully",
            "book": {"id": 43, "title": "Foundation", "author": "Asimov"},
            "created": True
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.api._register_book_sync("Foundation", "Asimov")

        self.assertEqual(result["id"], 43)
        mock_post.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/book",
            headers=self.api.headers,
            json={"title": "Foundation", "author": "Asimov"}
        )

    # Error handling tests
    @patch('requests.get')
    def test_handle_404_error(self, mock_get):
        """Test 404 error raises ResourceNotFoundError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        with self.assertRaises(ResourceNotFoundError):
            self.api.get_server("nonexistent-id")

    @patch('requests.get')
    def test_handle_400_error(self, mock_get):
        """Test 400 error raises ValidationError."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        with self.assertRaises(ValidationError):
            self.api.get_server("test-id")

    @patch('requests.get')
    def test_handle_401_error(self, mock_get):
        """Test 401 error raises AuthenticationError."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        with self.assertRaises(AuthenticationError):
            self.api.get_server("test-id")

    @patch('requests.get')
    def test_handle_403_error(self, mock_get):
        """Test 403 error raises AuthenticationError."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        with self.assertRaises(AuthenticationError):
            self.api.get_server("test-id")

    @patch('requests.get')
    def test_handle_500_error(self, mock_get):
        """Test 500 error raises APIError."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        with self.assertRaises(APIError):
            self.api.get_server("test-id")

    @patch('requests.get')
    def test_handle_connection_error(self, mock_get):
        """Test connection error raises APIError."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        with self.assertRaises(APIError) as context:
            self.api.get_server("test-id")
        self.assertIn("Connection error", str(context.exception))

    @patch('requests.post')
    def test_register_book_validation_error(self, mock_post):
        """Test register_book with invalid data raises ValidationError."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Title is required"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response

        with self.assertRaises(ValidationError):
            self.api._register_book_sync("", "Author")  # Empty title

    @patch('requests.get')
    def test_search_books_connection_error(self, mock_get):
        """Test search_books with connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        with self.assertRaises(APIError):
            self.api._search_books_sync("dune")

    @patch('requests.post')
    def test_create_member_success(self, mock_post):
        """Test create_member with valid data."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Member created",
            "member": {"id": 1, "name": "John Doe", "points": 0}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.api.create_member({"name": "John Doe"})

        self.assertEqual(result["member"]["name"], "John Doe")
        mock_post.assert_called_once()

    @patch('requests.put')
    def test_update_member_success(self, mock_put):
        """Test update_member with valid data."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Member updated",
            "member": {"id": 1, "name": "Jane Doe"}
        }
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response

        result = self.api.update_member(1, {"name": "Jane Doe"})

        self.assertEqual(result["member"]["name"], "Jane Doe")

    @patch('requests.delete')
    def test_delete_member_success(self, mock_delete):
        """Test delete_member."""
        mock_response = Mock()
        mock_response.json.return_value = {"success": True, "message": "Member deleted"}
        mock_response.raise_for_status = Mock()
        mock_delete.return_value = mock_response

        result = self.api.delete_member(1)

        self.assertTrue(result["success"])

    @patch('requests.get')
    def test_find_club_in_channel_not_found(self, mock_get):
        """Test find_club_in_channel returns None when not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        result = self.api.find_club_in_channel("channel-123", "guild-456")

        self.assertIsNone(result)

    @patch('requests.get')
    def test_get_member_by_discord_id_not_found(self, mock_get):
        """Test get_member_by_discord_id returns None when not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        result = self.api.get_member_by_discord_id("discord-id")

        self.assertIsNone(result)

    @patch.object(BookClubAPI, '_search_books_sync')
    def test_search_books_async(self, mock_sync):
        """Test search_books async wrapper."""
        mock_sync.return_value = [{"id": "1", "title": "Dune"}]

        result = asyncio.run(self.api.search_books("dune"))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Dune")
        mock_sync.assert_called_once_with("dune")

    @patch.object(BookClubAPI, '_register_book_sync')
    def test_register_book_async_with_optional_params(self, mock_sync):
        """Test register_book async wrapper with optional parameters."""
        mock_sync.return_value = {"id": 42, "title": "Dune", "edition": "First"}

        result = asyncio.run(self.api.register_book(
            "Dune",
            "Frank Herbert",
            "abc123",
            edition="First",
            year=1965,
            isbn="123-456",
            page_count=688,
            image_url="https://example.com/dune.jpg"
        ))

        self.assertEqual(result["title"], "Dune")
        self.assertEqual(result["edition"], "First")
        mock_sync.assert_called_once_with(
            "Dune", "Frank Herbert", "abc123", "First", 1965, "123-456", 688, "https://example.com/dune.jpg"
        )

    @patch('requests.post')
    def test_register_book_sync_with_optional_params(self, mock_post):
        """Test _register_book_sync with optional parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "book": {"id": 42, "title": "Foundation", "year": 1951}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.api._register_book_sync(
            "Foundation",
            "Isaac Asimov",
            "xyz789",
            edition="Original",
            year=1951,
            isbn="978-0-553",
            page_count=255,
            image_url="https://example.com/foundation.jpg"
        )

        self.assertEqual(result["title"], "Foundation")
        self.assertEqual(result["year"], 1951)
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]['json']
        self.assertEqual(call_args['edition'], "Original")
        self.assertEqual(call_args['year'], 1951)
        self.assertEqual(call_args['isbn'], "978-0-553")
        self.assertEqual(call_args['page_count'], 255)
        self.assertEqual(call_args['image_url'], "https://example.com/foundation.jpg")

    @patch('requests.post')
    def test_create_discussion(self, mock_post):
        """Test create_discussion with valid data."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "discussion-new",
            "session_id": "session-1",
            "title": "Chapters 1-3",
            "scheduled_at": "2025-05-01T18:00:00+00:00",
            "location": "Library"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        discussion_data = {
            "session_id": "session-1",
            "title": "Chapters 1-3",
            "scheduled_at": "2025-05-01T18:00:00+00:00",
            "location": "Library"
        }

        result = self.api.create_discussion(discussion_data)

        self.assertEqual(result["id"], "discussion-new")
        self.assertEqual(result["title"], "Chapters 1-3")
        mock_post.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/discussion",
            headers=self.api.headers,
            json=discussion_data
        )

    @patch('requests.post')
    def test_create_discussion_session_not_found(self, mock_post):
        """Test create_discussion when the parent session doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Session not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error", response=mock_response
        )
        mock_post.return_value = mock_response

        with self.assertRaises(ResourceNotFoundError):
            self.api.create_discussion({"session_id": "missing-session", "title": "Chapters 1-3", "scheduled_at": "2025-05-01T18:00:00+00:00"})

    @patch('requests.put')
    def test_update_discussion(self, mock_put):
        """Test update_discussion with valid data."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "discussion-123",
            "title": "Updated Discussion",
            "scheduled_at": "2025-05-10T18:00:00+00:00",
            "location": "Online"
        }
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response

        update_data = {"title": "Updated Discussion", "scheduled_at": "2025-05-10T18:00:00+00:00", "location": "Online"}

        result = self.api.update_discussion("discussion-123", update_data)

        self.assertEqual(result["title"], "Updated Discussion")
        mock_put.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/discussion",
            headers=self.api.headers,
            json={"id": "discussion-123", **update_data}
        )

    @patch('requests.put')
    def test_update_discussion_not_found(self, mock_put):
        """Test update_discussion when the discussion doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Discussion not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error", response=mock_response
        )
        mock_put.return_value = mock_response

        with self.assertRaises(ResourceNotFoundError):
            self.api.update_discussion("missing-discussion", {"title": "New Title"})

    @patch('requests.delete')
    def test_delete_discussion_success(self, mock_delete):
        """Test delete_discussion with valid ID."""
        mock_response = Mock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = Mock()
        mock_delete.return_value = mock_response

        result = self.api.delete_discussion("discussion-123")

        self.assertTrue(result["success"])
        mock_delete.assert_called_once_with(
            "http://test-url.supabase.co/functions/v1/discussion",
            headers=self.api.headers,
            params={"id": "discussion-123"}
        )

    @patch('requests.delete')
    def test_delete_discussion_empty_response_body(self, mock_delete):
        """Test delete_discussion when the API returns a 204 with no body."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.content = b""
        mock_response.raise_for_status = Mock()
        mock_delete.return_value = mock_response

        result = self.api.delete_discussion("discussion-123")

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Discussion deleted successfully")
        mock_response.json.assert_not_called()

    @patch('requests.delete')
    def test_delete_discussion_not_found(self, mock_delete):
        """Test delete_discussion when the discussion doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Discussion not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error", response=mock_response
        )
        mock_delete.return_value = mock_response

        with self.assertRaises(ResourceNotFoundError):
            self.api.delete_discussion("missing-discussion")

    @patch('requests.post')
    def test_create_club_connection_error(self, mock_post):
        """Test create_club with connection error."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

        with self.assertRaises(APIError):
            self.api.create_club({"name": "Test Club", "discord_channel": "123"}, "guild-1")

    @patch('requests.get')
    def test_get_club_connection_error(self, mock_get):
        """Test get_club with connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        with self.assertRaises(APIError):
            self.api.get_club("club-1", "guild-1")


if __name__ == '__main__':
    unittest.main()
# bookclub_api.py
import os
import requests
from typing import Dict, List, Optional, Union, Any

class APIError(Exception):
    """Raised when there's an error communicating with the API."""
    pass

class ResourceNotFoundError(APIError):
    """Raised when the requested resource doesn't exist."""
    pass

class ValidationError(APIError):
    """Raised when the API rejects the request due to invalid data."""
    pass

class AuthenticationError(APIError):
    """Raised when there's an authentication issue."""
    pass

class BookClubAPI:
    """SDK for interacting with Book Club API powered by Supabase Edge Functions."""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the Book Club API client.
        
        Args:
            base_url: The base URL for the Supabase project (e.g., 'https://your-project.supabase.co')
            api_key: The Supabase API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.functions_url = f"{self.base_url}/functions/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def _handle_request_error(self, error: requests.exceptions.RequestException, resource_type: str, resource_id: Optional[str] = None) -> None:
        """
        Handle request errors and raise appropriate custom exceptions.
        
        Args:
            error: The original request exception
            resource_type: The type of resource being accessed (e.g., 'club', 'member')
            resource_id: The ID of the resource, if applicable
            
        Raises:
            ResourceNotFoundError: If the resource was not found (404)
            ValidationError: If the request was invalid (400)
            AuthenticationError: If there was an authentication issue (401, 403)
            APIError: For other API errors
        """
        if isinstance(error, requests.exceptions.HTTPError):
            status_code = error.response.status_code
            error_text = error.response.text
            
            if status_code == 404:
                id_info = f" with ID '{resource_id}'" if resource_id else ""
                raise ResourceNotFoundError(
                    f"{resource_type.capitalize()}{id_info} not found. "
                    f"Check if it exists in this environment."
                ) from error
            
            elif status_code == 400:
                raise ValidationError(f"Invalid request: {error_text}") from error
            
            elif status_code in (401, 403):
                raise AuthenticationError(f"Authentication error: {error_text}") from error
            
            else:
                raise APIError(f"API error ({status_code}): {error_text}") from error
        
        elif isinstance(error, requests.exceptions.ConnectionError):
            raise APIError(f"Connection error: Could not connect to the API. "
                          f"Check if the server is running and the URL is correct.") from error
        
        else:
            raise APIError(f"Request failed: {str(error)}") from error
    
    # Server Methods
    def register_server(self, guild_id: str, server_name: str) -> Dict:
        """
        Register a Discord server with the API.
        
        Args:
            guild_id: Discord guild ID
            server_name: Name of the Discord server
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ValidationError: If the server data is invalid
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/server"
        data = {
            "id": guild_id,
            "name": server_name
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "server")
    
    def get_server(self, guild_id: str) -> Dict:
        """
        Get server details including all clubs with detailed information.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dict containing server details and clubs with member counts and latest sessions
            
        Raises:
            ResourceNotFoundError: If the server doesn't exist
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/server"
        params = {"id": guild_id}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "server", guild_id)

    def get_all_servers(self) -> Dict:
        """
        Get all registered servers with their clubs.
        
        Returns:
            Dict containing all servers and their clubs
            
        Raises:
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/server"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "servers")

    def get_server_clubs(self, guild_id: str) -> List[Dict]:
        """
        Get all clubs for a specific server (simplified version of get_server).
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            List of club dictionaries with basic info (id, name, discord_channel)
            
        Raises:
            ResourceNotFoundError: If the server doesn't exist
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        try:
            server_data = self.get_server(guild_id)
            return server_data.get('clubs', [])
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "server", guild_id)
    
    def update_server(self, guild_id: str, server_name: str) -> Dict:
        """
        Update server information.
        
        Args:
            guild_id: Discord guild ID
            server_name: Updated name of the Discord server
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ResourceNotFoundError: If the server doesn't exist
            ValidationError: If the server data is invalid
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/server"
        data = {
            "id": guild_id,
            "name": server_name
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "server", guild_id)
    
    def delete_server(self, guild_id: str) -> Dict:
        """
        Delete a server and all associated data.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ResourceNotFoundError: If the server doesn't exist
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/server"
        params = {"id": guild_id}
        
        try:
            response = requests.delete(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "server", guild_id)
    
    # Club Methods
    def get_club(self, club_id: str, guild_id: str) -> Dict:
        """
        Get details for a specific club by ID.
        
        Args:
            club_id: The ID of the club to retrieve
            guild_id: Discord guild ID where the club exists
            
        Returns:
            Dict containing club details including members and active session
            
        Raises:
            ResourceNotFoundError: If the club doesn't exist in this server
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/club"
        params = {"id": club_id, "server_id": guild_id}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            json = response.json()
            print(f"[DEBUG] Fetched club data: {json}")  # Debug log
            return json
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "club", club_id)
    
    def get_club_by_discord_channel(self, discord_channel_id: str, guild_id: str) -> Dict:
        """
        Get details for a specific club by Discord channel ID.
        
        Args:
            discord_channel_id: The Discord channel ID associated with the club
            guild_id: Discord guild ID where the club exists
            
        Returns:
            Dict containing club details including members and active session
            
        Raises:
            ResourceNotFoundError: If no club is found with this Discord channel in this server
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/club"
        params = {"discord_channel": discord_channel_id, "server_id": guild_id}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            json = response.json()
            print(f"[DEBUG] Fetched club data by Discord channel: {json}")  # Debug log
            return json
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "club", f"discord_channel:{discord_channel_id}")
    
    def find_club_in_channel(self, channel_id: str, guild_id: str) -> Optional[Dict]:
        """
        Convenience method to find a club in the current Discord channel.
        Returns None if no club is found instead of raising an exception.
        
        Args:
            channel_id: Discord channel ID to search for
            guild_id: Discord guild ID where the club exists
            
        Returns:
            Dict containing club details if found, None otherwise
            
        Raises:
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors (but not ResourceNotFoundError)
        """
        try:
            return self.get_club_by_discord_channel(channel_id, guild_id)
        except ResourceNotFoundError:
            return None
    
    def create_club(self, club_data: Dict, guild_id: str) -> Dict:
        """
        Create a new club with all its associated data.
        
        Args:
            club_data: Dict containing club data including name, discord_channel, members, etc.
                Example:
                {
                    "name": "Classic Literature Club",
                    "discord_channel": "123456789012345678",  # Optional
                    "members": [  # Optional
                        {"id": 1, "name": "John Doe"},
                        {"id": 2, "name": "Jane Smith"}
                    ],
                    "active_session": {  # Optional
                        "book": {
                            "title": "To Kill a Mockingbird",
                            "author": "Harper Lee"
                        },
                        "due_date": "2023-12-31"
                    }
                }
            guild_id: Discord guild ID where the club will be created
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ValidationError: If the club data is invalid
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/club"
        
        # Add server_id to the club data
        data = {**club_data, "server_id": guild_id}
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "club")
    
    def update_club(self, club_id: str, update_data: Dict, guild_id: str) -> Dict:
        """
        Update a club.
        
        Args:
            club_id: The ID of the club to update
            update_data: Dict containing fields to update (name, discord_channel, shame_list)
                Example:
                {
                    "name": "New Club Name",  # Optional
                    "discord_channel": "987654321098765432",  # Optional
                    "shame_list": [1, 2, 3]  # Optional - list of member IDs
                }
            guild_id: Discord guild ID where the club exists
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ResourceNotFoundError: If the club doesn't exist in this server
            ValidationError: If the club data is invalid
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/club"
        data = {"id": club_id, "server_id": guild_id, **update_data}
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "club", club_id)
    
    def delete_club(self, club_id: str, guild_id: str) -> Dict:
        """
        Delete a club and all associated data.
        
        Args:
            club_id: The ID of the club to delete
            guild_id: Discord guild ID where the club exists
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ResourceNotFoundError: If the club doesn't exist in this server
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/club"
        params = {"id": club_id, "server_id": guild_id}
        
        try:
            response = requests.delete(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "club", club_id)
    
    # Member Methods (unchanged - members aren't server-specific)
    def get_member(self, member_id: int) -> Dict:
        """
        Get details for a specific member.
        
        Args:
            member_id: The ID of the member to retrieve
            
        Returns:
            Dict containing member details including clubs and shame_clubs
            
        Raises:
            ResourceNotFoundError: If the member doesn't exist
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/member"
        params = {"id": member_id}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "member", str(member_id))
    
    def create_member(self, member_data: Dict) -> Dict:
        """
        Create a new member.
        
        Args:
            member_data: Dict containing member data
                Example:
                {
                    "name": "John Doe",
                    "points": 0,  # Optional
                    "books_read": 0,  # Optional
                    "clubs": ["club-id-1", "club-id-2"]  # Optional - list of club IDs
                }
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ValidationError: If the member data is invalid
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/member"
        
        try:
            response = requests.post(url, headers=self.headers, json=member_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "member")
    
    def update_member(self, member_id: int, update_data: Dict) -> Dict:
        """
        Update member details.
        
        Args:
            member_id: The ID of the member to update
            update_data: Dict containing fields to update
                Example:
                {
                    "name": "New Name",  # Optional
                    "points": 10,  # Optional
                    "books_read": 5,  # Optional
                    "clubs": ["club-id-1", "club-id-3"]  # Optional - complete list of club IDs
                }
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ResourceNotFoundError: If the member doesn't exist
            ValidationError: If the member data is invalid
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/member"
        data = {"id": member_id, **update_data}
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "member", str(member_id))
    
    def delete_member(self, member_id: int) -> Dict:
        """
        Delete a member.
        
        Args:
            member_id: The ID of the member to delete
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ResourceNotFoundError: If the member doesn't exist
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/member"
        params = {"id": member_id}
        
        try:
            response = requests.delete(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "member", str(member_id))
    
    # Session Methods (unchanged - sessions are tied to clubs, which are server-specific)
    def get_session(self, session_id: str) -> Dict:
        """
        Get details for a specific session.
        
        Args:
            session_id: The ID of the session to retrieve
            
        Returns:
            Dict containing session details including book, club info, and discussions
            
        Raises:
            ResourceNotFoundError: If the session doesn't exist
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/session"
        params = {"id": session_id}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "session", session_id)
    
    def create_session(self, session_data: Dict) -> Dict:
        """
        Create a new reading session.
        
        Args:
            session_data: Dict containing session data
                Example:
                {
                    "club_id": "club-id-1",
                    "book": {
                        "title": "The Great Gatsby",
                        "author": "F. Scott Fitzgerald",
                        "year": 1925  # Optional
                    },
                    "due_date": "2023-11-30",  # Optional
                    "discussions": [  # Optional
                        {
                            "title": "Chapters 1-3",
                            "date": "2023-11-15",
                            "location": "Library"  # Optional
                        }
                    ]
                }
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ValidationError: If the session data is invalid
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/session"
        
        try:
            response = requests.post(url, headers=self.headers, json=session_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "session")
    
    def update_session(self, session_id: str, update_data: Dict) -> Dict:
        """
        Update session details.
        
        Args:
            session_id: The ID of the session to update
            update_data: Dict containing fields to update
                Example:
                {
                    "book": {  # Optional
                        "title": "Updated Title",
                        "author": "Updated Author",
                        "edition": "Second Edition",  # Optional
                        "year": 1925,  # Optional
                        "isbn": "978-3-16-148410-0"  # Optional
                    },
                    "due_date": "2023-12-15",  # Optional
                    "discussions": [  # Optional - replaces all discussions
                        {
                            "id": "existing-discussion-id",  # Include for existing discussions
                            "title": "Updated Discussion",
                            "date": "2023-11-20",
                            "location": "Library"  # Optional
                        },
                        {
                            "title": "New Discussion",  # New discussion (no ID)
                            "date": "2023-12-01",
                            "location": "Online"  # Optional
                        }
                    ],
                    "discussion_ids_to_delete": ["discussion-id-1"]  # Optional
                }
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ResourceNotFoundError: If the session doesn't exist
            ValidationError: If the session data is invalid
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/session"
        data = {"id": session_id, **update_data}
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "session", session_id)

    def delete_session(self, session_id: str) -> Dict:
        """
        Delete a session.
        
        Args:
            session_id: The ID of the session to delete
            
        Returns:
            Dict containing success status and message
            
        Raises:
            ResourceNotFoundError: If the session doesn't exist
            AuthenticationError: If there's an authentication issue
            APIError: For other API errors
        """
        url = f"{self.functions_url}/session"
        params = {"id": session_id}
        
        try:
            response = requests.delete(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "session", session_id)


# Example usage
if __name__ == "__main__":
    # Initialize the API client
    api = BookClubAPI(
        base_url=os.getenv("SUPABASE_URL", "http://localhost:54321"),
        api_key=os.getenv("SUPABASE_KEY", "your-local-anon-key")
    )
    
    # Example of context-aware usage
    guild_id = "1039326367428395038"  # Would come from Discord interaction
    channel_id = "987654321098765432"  # Would come from Discord interaction
    
    try:
        # Example 1: Get all servers
        all_servers = api.get_all_servers()
        print(f"Found {len(all_servers['servers'])} servers")
        
        # Example 2: Get specific server with detailed club info
        server = api.get_server(guild_id)
        print(f"Server: {server['name']} has {len(server['clubs'])} clubs")
        
        # Example 3: Find club by Discord channel
        club = api.get_club_by_discord_channel(channel_id, guild_id)
        print(f"Found club '{club['name']}' in channel {channel_id}")
        
        # Example 4: Convenience method for finding club (returns None if not found)
        club = api.find_club_in_channel(channel_id, guild_id)
        if club:
            print(f"Club found: {club['name']}")
        else:
            print("No club found in this channel")
            
    except ResourceNotFoundError as e:
        print(f"Resource not found: {e}")
    except ValidationError as e:
        print(f"Validation error: {e}")
    except AuthenticationError as e:
        print(f"Authentication error: {e}")
    except APIError as e:
        print(f"API error: {e}")
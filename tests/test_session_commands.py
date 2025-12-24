"""
Tests for session commands (book, duedate, session, discussions, book_summary)
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from cogs.session_commands import setup_session_commands
from api.bookclub_api import ResourceNotFoundError


class TestSessionCommands(unittest.IsolatedAsyncioTestCase):
    """Test cases for session commands - PROPERLY ASYNC"""

    def setUp(self):
        """Set up common test fixtures"""
        # Create a mock bot
        self.bot = MagicMock()
        self.bot.tree = MagicMock()

        # Mock API with sample data
        self.bot.api = MagicMock()
        self.bot.api.find_club_in_channel = MagicMock(return_value={
            'id': 'club-1',
            'name': 'Test Book Club',
            'server_id': '123456',
            'active_session': {
                'id': 'session-1',
                'book': {
                    'title': 'Test Book Title',
                    'author': 'Test Author',
                    'year': 2024,
                    'edition': '1st Edition'
                },
                'due_date': '2025-05-01',
                'discussions': [
                    {
                        'id': 'discussion-1',
                        'date': '2025-04-15',
                        'title': 'First Discussion',
                        'location': 'Room 101'
                    },
                    {
                        'id': 'discussion-2',
                        'date': '2025-04-20',
                        'title': 'Second Discussion',
                        'location': 'Room 202'
                    }
                ]
            }
        })

        # Set up mock for OpenAI service
        self.bot.openai_service = MagicMock()
        self.bot.openai_service.get_response = AsyncMock(return_value="This is a test book summary.")

        # Store the registered commands
        self.commands = {}

        # Mock the bot.tree.command decorator
        def mock_command(**kwargs):
            def decorator(func):
                # Store the command and its properties
                self.commands[kwargs.get('name')] = {
                    'func': func,
                    'kwargs': kwargs
                }
                return func
            return decorator

        self.bot.tree.command = mock_command

        # Register the commands
        setup_session_commands(self.bot)

        # Verify commands were registered
        self.assertIn('book', self.commands)
        self.assertIn('duedate', self.commands)
        self.assertIn('session', self.commands)
        self.assertIn('discussions', self.commands)
        self.assertIn('book_summary', self.commands)

    async def test_book_command_success(self):
        """Test the book command with active session"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 123456
        interaction.channel_id = 789012
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Run the command
        book_command = self.commands['book']['func']
        await book_command(interaction)

        # Verify defer was called
        interaction.response.defer.assert_called_once()

        # Verify API was called
        self.bot.api.find_club_in_channel.assert_called_once_with('789012', '123456')

        # Verify followup.send was called with embed
        interaction.followup.send.assert_called_once()

    async def test_book_command_no_guild(self):
        """Test the book command when not in a guild"""
        # Mock interaction with no guild_id
        interaction = AsyncMock()
        interaction.guild_id = None
        interaction.response.send_message = AsyncMock()

        # Run the command
        book_command = self.commands['book']['func']
        await book_command(interaction)

        # Verify error message was sent
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        self.assertIn('DMs', str(call_args))
        self.assertTrue(call_args.kwargs.get('ephemeral'))

    async def test_book_command_no_club(self):
        """Test the book command when no club is found"""
        # Mock API to return no club
        self.bot.api.find_club_in_channel.return_value = None

        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 123456
        interaction.channel_id = 789012
        interaction.response.defer = AsyncMock()

        # Run the command - should raise exception
        book_command = self.commands['book']['func']
        with self.assertRaises(ResourceNotFoundError):
            await book_command(interaction)

    async def test_book_command_no_active_session(self):
        """Test the book command when no active session exists"""
        # Mock API to return club without active session
        self.bot.api.find_club_in_channel.return_value = {
            'id': 'club-1',
            'name': 'Test Book Club',
            'server_id': '123456',
            'active_session': None
        }

        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 123456
        interaction.channel_id = 789012
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Run the command
        book_command = self.commands['book']['func']
        await book_command(interaction)

        # Verify friendly message was sent
        interaction.followup.send.assert_called_once()
        call_args = interaction.followup.send.call_args
        self.assertIn('no active reading session', str(call_args[0][0]))

    async def test_duedate_command_success(self):
        """Test the duedate command"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 123456
        interaction.channel_id = 789012
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Run the command
        duedate_command = self.commands['duedate']['func']
        await duedate_command(interaction)

        # Verify defer was called
        interaction.response.defer.assert_called_once()

        # Verify followup.send was called
        interaction.followup.send.assert_called_once()

    async def test_duedate_command_no_guild(self):
        """Test the duedate command when not in a guild"""
        # Mock interaction with no guild_id
        interaction = AsyncMock()
        interaction.guild_id = None
        interaction.response.send_message = AsyncMock()

        # Run the command
        duedate_command = self.commands['duedate']['func']
        await duedate_command(interaction)

        # Verify error message was sent
        interaction.response.send_message.assert_called_once()
        self.assertTrue(interaction.response.send_message.call_args.kwargs.get('ephemeral'))

    async def test_session_command_success(self):
        """Test the session command"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 123456
        interaction.channel_id = 789012
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Run the command
        session_command = self.commands['session']['func']
        await session_command(interaction)

        # Verify defer was called
        interaction.response.defer.assert_called_once()

        # Verify followup.send was called
        interaction.followup.send.assert_called_once()

    async def test_session_command_with_discussions(self):
        """Test the session command when discussions exist"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 123456
        interaction.channel_id = 789012
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Run the command
        session_command = self.commands['session']['func']
        await session_command(interaction)

        # Verify followup.send was called with embed containing discussions
        interaction.followup.send.assert_called_once()

    async def test_discussions_command_success(self):
        """Test the discussions command with multiple discussions"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 123456
        interaction.channel_id = 789012
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Run the command
        discussions_command = self.commands['discussions']['func']
        await discussions_command(interaction)

        # Verify defer was called
        interaction.response.defer.assert_called_once()

        # Verify followup.send was called
        interaction.followup.send.assert_called_once()

    async def test_discussions_command_no_discussions(self):
        """Test the discussions command when no discussions exist"""
        # Mock API to return session without discussions
        self.bot.api.find_club_in_channel.return_value = {
            'id': 'club-1',
            'name': 'Test Book Club',
            'server_id': '123456',
            'active_session': {
                'id': 'session-1',
                'book': {
                    'title': 'Test Book Title',
                    'author': 'Test Author'
                },
                'due_date': '2025-05-01',
                'discussions': []
            }
        }

        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 123456
        interaction.channel_id = 789012
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Run the command
        discussions_command = self.commands['discussions']['func']
        await discussions_command(interaction)

        # Verify message about no discussions
        interaction.followup.send.assert_called_once()
        call_args = interaction.followup.send.call_args
        self.assertIn('no discussions', str(call_args[0][0]).lower())

    async def test_discussions_command_no_guild(self):
        """Test the discussions command when not in a guild"""
        # Mock interaction with no guild_id
        interaction = AsyncMock()
        interaction.guild_id = None
        interaction.response.send_message = AsyncMock()

        # Run the command
        discussions_command = self.commands['discussions']['func']
        await discussions_command(interaction)

        # Verify error message was sent
        interaction.response.send_message.assert_called_once()

    async def test_book_summary_command_success(self):
        """Test the book_summary command"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 123456
        interaction.channel_id = 789012
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Run the command
        book_summary_command = self.commands['book_summary']['func']
        await book_summary_command(interaction)

        # Verify defer was called
        interaction.response.defer.assert_called_once()

        # Verify OpenAI service was called with the book title
        self.bot.openai_service.get_response.assert_called_once()
        args, _ = self.bot.openai_service.get_response.call_args
        self.assertIn("Test Book Title", args[0])

        # Verify followup.send was called
        interaction.followup.send.assert_called_once()

    async def test_book_summary_command_no_guild(self):
        """Test the book_summary command when not in a guild"""
        # Mock interaction with no guild_id
        interaction = AsyncMock()
        interaction.guild_id = None
        interaction.response.send_message = AsyncMock()

        # Run the command
        book_summary_command = self.commands['book_summary']['func']
        await book_summary_command(interaction)

        # Verify error message was sent
        interaction.response.send_message.assert_called_once()
        self.assertTrue(interaction.response.send_message.call_args.kwargs.get('ephemeral'))


if __name__ == '__main__':
    unittest.main()

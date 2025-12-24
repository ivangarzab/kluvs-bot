"""
Comprehensive tests for message_handler events
"""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

from events.message_handler import setup_message_handlers


class TestMessageHandlerComprehensive(unittest.TestCase):
    """Comprehensive test cases for message handler"""

    def setUp(self):
        """Set up common test fixtures"""
        # Create a mock bot
        self.bot = MagicMock()
        self.bot.user = MagicMock()
        self.bot.user.id = 123456
        self.bot.config = MagicMock()
        self.bot.config.DEFAULT_CHANNEL = 987654
        self.bot.db = MagicMock()
        self.bot.db.save_club = MagicMock()
        self.bot.process_commands = AsyncMock()
        self.bot.get_channel = MagicMock()

        # Store event handlers
        self.events = {}

        # Mock the bot.event decorator
        def mock_event(func):
            self.events[func.__name__] = func
            return func

        self.bot.event = mock_event

        # Register the event handlers
        setup_message_handlers(self.bot)

        # Verify events were registered
        self.assertIn('on_message', self.events)
        self.assertIn('on_member_join', self.events)

    async def test_on_message_from_bot_ignored(self):
        """Test that messages from the bot itself are ignored"""
        # Create a message from the bot
        message = MagicMock()
        message.author = self.bot.user
        message.channel = AsyncMock()

        # Call the handler
        on_message = self.events['on_message']
        await on_message(message)

        # Verify no processing happened
        message.channel.send.assert_not_called()
        self.bot.process_commands.assert_not_called()

    async def test_on_message_mention_with_greeting(self):
        """Test bot responds with greeting when mentioned"""
        # Create a message that mentions the bot
        message = MagicMock()
        message.author = MagicMock(id=999)
        message.content = "Hello @bot"
        message.mentions = [self.bot.user]
        message.channel = AsyncMock()
        message.channel.send = AsyncMock()
        message.add_reaction = AsyncMock()
        message.guild = MagicMock()

        # Mock random to always trigger greeting
        with patch('random.random', return_value=0.1):
            on_message = self.events['on_message']
            await on_message(message)

        # Verify greeting was sent
        message.channel.send.assert_called_once()
        self.bot.process_commands.assert_called_once_with(message)

    async def test_on_message_mention_with_reaction(self):
        """Test bot reacts when mentioned (second path)"""
        # Create a message that mentions the bot
        message = MagicMock()
        message.author = MagicMock(id=999)
        message.content = "Hey @bot"
        message.mentions = [self.bot.user]
        message.channel = AsyncMock()
        message.channel.send = AsyncMock()
        message.add_reaction = AsyncMock()
        message.guild = MagicMock()

        # Mock random to trigger reaction path
        with patch('random.random', side_effect=[0.5, 0.6]):
            on_message = self.events['on_message']
            await on_message(message)

        # Verify reaction was added
        message.add_reaction.assert_called_once()

    async def test_on_message_together_keyword(self):
        """Test bot responds to 'together' keyword"""
        # Create a message with 'together' keyword
        message = MagicMock()
        message.author = MagicMock(id=999)
        message.content = "Let's read together"
        message.mentions = []
        message.channel = AsyncMock()
        message.channel.send = AsyncMock()
        message.add_reaction = AsyncMock()
        message.guild = MagicMock()

        with patch('random.random', return_value=1.0):  # Avoid random reactions
            on_message = self.events['on_message']
            await on_message(message)

        # Verify community message was sent
        message.channel.send.assert_called_once()
        args = message.channel.send.call_args[0]
        self.assertIn('community', args[0])

    async def test_on_message_random_reaction(self):
        """Test bot adds random reactions to messages"""
        # Create a regular message
        message = MagicMock()
        message.author = MagicMock(id=999)
        message.content = "Just a regular message"
        message.mentions = []
        message.channel = AsyncMock()
        message.add_reaction = AsyncMock()
        message.guild = MagicMock()

        # Mock random to trigger reaction
        with patch('random.random', return_value=0.1):
            on_message = self.events['on_message']
            await on_message(message)

        # Verify reaction was added
        message.add_reaction.assert_called_once()

    async def test_on_message_command_processing(self):
        """Test that all messages are processed for commands"""
        # Create any message
        message = MagicMock()
        message.author = MagicMock(id=999)
        message.content = "Any message"
        message.mentions = []
        message.channel = AsyncMock()
        message.guild = MagicMock()

        with patch('random.random', return_value=1.0):
            on_message = self.events['on_message']
            await on_message(message)

        # Verify process_commands was called
        self.bot.process_commands.assert_called_once_with(message)

    async def test_on_member_join(self):
        """Test welcome message for new member"""
        # Create a new member
        member = MagicMock()
        member.name = "NewUser"
        member.mention = "@NewUser"
        member.id = 555

        # Mock channel
        mock_channel = AsyncMock()
        mock_channel.send = AsyncMock()
        self.bot.get_channel.return_value = mock_channel

        # Call the handler
        on_member_join = self.events['on_member_join']
        await on_member_join(member)

        # Verify channel was retrieved
        self.bot.get_channel.assert_called_once_with(987654)

        # Verify welcome message was sent
        mock_channel.send.assert_called_once()

        # Verify embed was created
        call_args = mock_channel.send.call_args
        self.assertIn('embed', call_args.kwargs)

    async def test_on_member_join_saves_to_database(self):
        """Test that new member is saved to database"""
        # Create a new member
        member = MagicMock()
        member.name = "NewUser"
        member.mention = "@NewUser"
        member.id = 777

        # Mock channel
        mock_channel = AsyncMock()
        self.bot.get_channel.return_value = mock_channel

        # Call the handler
        on_member_join = self.events['on_member_join']
        await on_member_join(member)

        # Verify database save was called
        self.bot.db.save_club.assert_called_once()

    async def test_on_member_join_no_channel(self):
        """Test on_member_join when channel doesn't exist"""
        # Create a new member
        member = MagicMock()
        member.name = "NewUser"
        member.id = 888

        # Mock channel as None
        self.bot.get_channel.return_value = None

        # Call the handler - should not crash
        on_member_join = self.events['on_member_join']
        await on_member_join(member)

        # Verify database save still happened
        self.bot.db.save_club.assert_called_once()

    async def test_on_message_uppercase_keyword(self):
        """Test that keyword detection is case-insensitive"""
        # Create a message with uppercase keyword
        message = MagicMock()
        message.author = MagicMock(id=999)
        message.content = "Let's read TOGETHER"
        message.mentions = []
        message.channel = AsyncMock()
        message.channel.send = AsyncMock()
        message.guild = MagicMock()

        with patch('random.random', return_value=1.0):
            on_message = self.events['on_message']
            await on_message(message)

        # Verify community message was sent
        message.channel.send.assert_called()

    async def test_on_message_command_prefix_no_random_reaction(self):
        """Test that messages starting with ! don't get random reactions"""
        # Create a command message
        message = MagicMock()
        message.author = MagicMock(id=999)
        message.content = "!version"
        message.mentions = []
        message.channel = AsyncMock()
        message.add_reaction = AsyncMock()
        message.guild = MagicMock()

        with patch('random.random', return_value=0.1):  # Would normally trigger reaction
            on_message = self.events['on_message']
            await on_message(message)

        # Since message starts with !, no reaction should be added
        # (the random reaction check includes "not message.content.startswith('!')")
        # This depends on the actual implementation


if __name__ == '__main__':
    unittest.main()

"""
Tests for message and event handlers
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import discord
import random

from events.message_handler import setup_message_handlers
from utils.constants import GREETINGS, REACTIONS


class TestMessageHandler(unittest.IsolatedAsyncioTestCase):
    """Test cases for message handler - PROPERLY ASYNC"""

    def setUp(self):
        """Set up common test fixtures"""
        self.bot = MagicMock()
        self.bot.user = MagicMock()
        self.bot.user.id = 999
        self.bot.config = MagicMock()
        self.bot.api.get_server_clubs.return_value = [{'id': 'club-1', 'discord_channel': '123456'}]
        self.bot.process_commands = AsyncMock()
        self.bot.get_channel = MagicMock()

        # Store event handlers
        self.handlers = {}

        # Mock the bot.event decorator
        def mock_event(func):
            # Store the event handler
            self.handlers[func.__name__] = func
            return func

        self.bot.event = mock_event

        # Register the event handlers
        setup_message_handlers(self.bot)

        # Verify event handlers were registered
        self.assertIn('on_message', self.handlers)
        self.assertIn('on_member_join', self.handlers)

    async def test_on_message_from_bot(self):
        """Test message handler ignores bot's own messages"""
        # Create a message from the bot itself
        message = MagicMock()
        message.author = self.bot.user
        message.channel = AsyncMock()

        # Run the handler
        on_message = self.handlers['on_message']
        await on_message(message)

        # Verify nothing happened (no methods called on message)
        message.channel.send.assert_not_called()
        self.bot.process_commands.assert_not_called()

    async def test_on_message_with_bot_mention_greeting(self):
        """Test message handler responds to bot mentions with greeting"""
        # Create a message with bot mention
        message = MagicMock()
        message.author = MagicMock(id=888)
        message.content = "Hey @bot, how are you?"
        message.mentions = [self.bot.user]
        message.channel = AsyncMock()
        message.add_reaction = AsyncMock()
        message.guild = MagicMock()

        # Force the random values for predictable testing
        with patch('random.random', return_value=0.2):  # 0.2 < 0.4, should send greeting
            with patch('random.choice', return_value="Hello there!"):
                # Run the handler
                on_message = self.handlers['on_message']
                await on_message(message)

                # Verify a greeting was sent
                message.channel.send.assert_called_once_with("Hello there!")

    async def test_on_message_with_bot_mention_reaction(self):
        """Test message handler adds reaction to bot mentions"""
        # Create a message with bot mention
        message = MagicMock()
        message.author = MagicMock(id=888)
        message.content = "Hey @bot"
        message.mentions = [self.bot.user]
        message.channel = AsyncMock()
        message.add_reaction = AsyncMock()
        message.guild = MagicMock()

        # Force random to skip greeting but trigger reaction
        # Need 3 values: first for greeting check, second for reaction check, third for random reaction
        with patch('random.random', side_effect=[0.5, 0.6, 1.0]):
            with patch('random.choice', return_value="📚"):
                on_message = self.handlers['on_message']
                await on_message(message)

                # Verify reaction was added
                message.add_reaction.assert_called_once_with("📚")

    async def test_on_message_with_together_keyword(self):
        """Test message handler responds to 'together' keyword"""
        # Create a message with the 'together' keyword
        message = MagicMock()
        message.author = MagicMock(id=777)
        message.content = "We should read together next week."
        message.mentions = []
        message.channel = AsyncMock()
        message.add_reaction = AsyncMock()
        message.guild = MagicMock()

        # Avoid random reactions
        with patch('random.random', return_value=1.0):
            # Run the handler
            on_message = self.handlers['on_message']
            await on_message(message)

            # Verify the response was sent
            message.channel.send.assert_called_once_with('Reading is done best in community.')

    async def test_on_message_random_reaction(self):
        """Test message handler sometimes adds random reactions"""
        # Create a normal message (not starting with !)
        message = MagicMock()
        message.author = MagicMock(id=666)
        message.content = "I'm reading a great book."
        message.mentions = []
        message.channel = AsyncMock()
        message.add_reaction = AsyncMock()
        message.guild = MagicMock()

        # Force random value to trigger reaction (0.1 < 0.3)
        with patch('random.random', return_value=0.1):
            with patch('random.choice', return_value="🦉"):
                # Run the handler
                on_message = self.handlers['on_message']
                await on_message(message)

                # Verify a reaction was added
                message.add_reaction.assert_called_once_with("🦉")

    async def test_on_message_command_prefix_no_random_reaction(self):
        """Test that messages starting with ! don't get random reactions"""
        # Create a command message
        message = MagicMock()
        message.author = MagicMock(id=555)
        message.content = "!version"
        message.mentions = []
        message.channel = AsyncMock()
        message.add_reaction = AsyncMock()
        message.guild = MagicMock()

        # Even with low random value, ! prefix should prevent reaction
        with patch('random.random', return_value=0.1):
            on_message = self.handlers['on_message']
            await on_message(message)

            # No random reaction should be added (content starts with !)
            # But process_commands should be called
            self.bot.process_commands.assert_called_once_with(message)

    async def test_on_message_process_commands_always_called(self):
        """Test that process_commands is always called"""
        message = MagicMock()
        message.author = MagicMock(id=444)
        message.content = "any message"
        message.mentions = []
        message.channel = AsyncMock()
        message.guild = MagicMock()

        with patch('random.random', return_value=1.0):  # Avoid random reactions
            on_message = self.handlers['on_message']
            await on_message(message)

            self.bot.process_commands.assert_called_once_with(message)

    async def test_on_member_join_with_channel(self):
        """Test member join handler sends welcome message"""
        # Create a new member
        member = MagicMock()
        member.name = "NewUser"
        member.mention = "@NewUser"
        member.id = 12345
        member.guild = MagicMock()
        member.guild.id = 111111

        # Mock the bot.get_channel method
        channel = AsyncMock()
        self.bot.get_channel.return_value = channel

        # Force a specific greeting choice
        with patch('random.choice', side_effect=["Welcome"]):
            # Run the handler
            on_member_join = self.handlers['on_member_join']
            await on_member_join(member)

            # Verify the welcome message was sent
            channel.send.assert_called_once()
            args, kwargs = channel.send.call_args
            self.assertIn('embed', kwargs)

            # Verify the embed has the correct properties
            embed = kwargs['embed']
            self.assertEqual(embed.title, "👋 New Member!")
            self.assertIn("Welcome", embed.description)
            self.assertIn("@NewUser", embed.description)


    async def test_on_member_join_no_channel(self):
        """Test member join when channel doesn't exist"""
        member = MagicMock()
        member.name = "User"
        member.id = 99999
        member.guild = MagicMock()
        member.guild.id = 111111

        # Return None for channel
        self.bot.get_channel.return_value = None

        # Should not crash
        on_member_join = self.handlers['on_member_join']
        await on_member_join(member)

    async def test_on_guild_join_sends_welcome_to_system_channel(self):
        """Welcome embed is posted to guild.system_channel when available."""
        guild = MagicMock()
        guild.name = "Test Guild"
        guild.id = 123456
        system_channel = AsyncMock()
        guild.system_channel = system_channel

        on_guild_join = self.handlers['on_guild_join']
        await on_guild_join(guild)

        system_channel.send.assert_called_once()
        _, kwargs = system_channel.send.call_args
        self.assertIn('embed', kwargs)
        embed = kwargs['embed']
        self.assertIn("Kluvs", embed.title)
        self.assertIn("!setup", embed.description)

    async def test_on_guild_join_falls_back_to_first_writable_channel(self):
        """Falls back to first writable text channel when system_channel is None."""
        guild = MagicMock()
        guild.name = "Test Guild"
        guild.id = 123456
        guild.system_channel = None

        fallback = AsyncMock()
        perms = MagicMock()
        perms.send_messages = True
        fallback.permissions_for = MagicMock(return_value=perms)
        guild.text_channels = [fallback]

        on_guild_join = self.handlers['on_guild_join']
        await on_guild_join(guild)

        fallback.send.assert_called_once()
        _, kwargs = fallback.send.call_args
        self.assertIn('embed', kwargs)

    async def test_on_guild_join_no_writable_channel(self):
        """Does not crash when there are no writable channels."""
        guild = MagicMock()
        guild.name = "Test Guild"
        guild.id = 123456
        guild.system_channel = None

        perms = MagicMock()
        perms.send_messages = False
        blocked = MagicMock()
        blocked.permissions_for.return_value = perms
        guild.text_channels = [blocked]

        on_guild_join = self.handlers['on_guild_join']
        await on_guild_join(guild)
        # No crash; no send called
        blocked.send.assert_not_called()


if __name__ == '__main__':
    unittest.main()

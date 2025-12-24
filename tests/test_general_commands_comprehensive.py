"""
Comprehensive tests for general commands (help, usage)
"""
import unittest
from unittest.mock import MagicMock, AsyncMock

from cogs.general_commands import setup_general_commands


class TestGeneralCommandsComprehensive(unittest.TestCase):
    """Comprehensive test cases for general commands"""

    def setUp(self):
        """Set up common test fixtures"""
        # Create a mock bot
        self.bot = MagicMock()
        self.bot.tree = MagicMock()

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
        setup_general_commands(self.bot)

        # Verify commands were registered
        self.assertIn('help', self.commands)
        self.assertIn('usage', self.commands)

    async def test_help_command(self):
        """Test the help command"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command
        help_command = self.commands['help']['func']
        await help_command(interaction)

        # Verify response was sent
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        self.assertIn('embed', call_args.kwargs)

    async def test_help_command_embed_content(self):
        """Test that help command embed has correct content"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command
        help_command = self.commands['help']['func']
        await help_command(interaction)

        # Get the embed that was sent
        call_args = interaction.response.send_message.call_args
        embed = call_args.kwargs['embed']

        # Verify embed properties
        self.assertIn("Quill's Orientation", embed.title)
        self.assertIn("book club", embed.description)

    async def test_usage_command(self):
        """Test the usage command"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command
        usage_command = self.commands['usage']['func']
        await usage_command(interaction)

        # Verify response was sent
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        self.assertIn('embed', call_args.kwargs)

    async def test_usage_command_embed_content(self):
        """Test that usage command embed has correct content"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command
        usage_command = self.commands['usage']['func']
        await usage_command(interaction)

        # Get the embed that was sent
        call_args = interaction.response.send_message.call_args
        embed = call_args.kwargs['embed']

        # Verify embed properties
        self.assertIn("Quill's Commands", embed.title)
        self.assertIn("help you", embed.description)

    async def test_help_command_has_reading_commands(self):
        """Test that help command includes reading commands"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command
        help_command = self.commands['help']['func']
        await help_command(interaction)

        # Get the embed that was sent
        call_args = interaction.response.send_message.call_args
        embed = call_args.kwargs['embed']

        # Check that reading commands are mentioned
        fields_text = ' '.join([f.name + f.value for f in embed.fields])
        self.assertIn('/session', fields_text)
        self.assertIn('/book', fields_text)

    async def test_usage_command_has_all_categories(self):
        """Test that usage command includes all command categories"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command
        usage_command = self.commands['usage']['func']
        await usage_command(interaction)

        # Get the embed that was sent
        call_args = interaction.response.send_message.call_args
        embed = call_args.kwargs['embed']

        # Check that all categories are present
        fields_text = ' '.join([f.name for f in embed.fields])
        self.assertIn('Reading Commands', fields_text)
        self.assertIn('Fun Commands', fields_text)
        self.assertIn('Utility Commands', fields_text)


if __name__ == '__main__':
    unittest.main()

"""
Tests for general commands (help, usage)
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from cogs.general_commands import setup_general_commands
from utils.embeds import create_embed

class TestGeneralCommands(unittest.IsolatedAsyncioTestCase):
    """Test cases for general commands - PROPERLY ASYNC"""
    
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
        self.assertIn('vote', self.commands)

    @patch('cogs.general_commands.create_embed')
    async def test_help_command(self, mock_create_embed):
        """Test the help command"""
        # Mock an interaction
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        
        # Mock the embed creation
        mock_embed = MagicMock()
        mock_create_embed.return_value = mock_embed
        
        # Run the command
        help_command = self.commands['help']['func']
        await help_command(interaction)
        
        # Verify the embed was created with the right parameters
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        self.assertEqual(kwargs['title'], "🦉 Kluvs Orientation")
        self.assertIn("Welcome to Kluvs", kwargs['description'])
        self.assertEqual(kwargs['color_key'], "info")
        
        # Check that the embed has fields
        mock_embed.add_field.assert_called()
        
        # Verify the interaction response was sent
        interaction.response.send_message.assert_called_once_with(embed=mock_embed)

    @patch('cogs.general_commands.create_embed')
    async def test_usage_command(self, mock_create_embed):
        """Test the usage command"""
        # Mock an interaction
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        
        # Mock the embed creation
        mock_embed = MagicMock()
        mock_create_embed.return_value = mock_embed
        
        # Run the command
        usage_command = self.commands['usage']['func']
        await usage_command(interaction)
        
        # Verify the embed was created with the right parameters
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        self.assertEqual(kwargs['title'], "📚 Kluvs Commands")
        self.assertIn("Here are all the commands", kwargs['description'])
        self.assertEqual(kwargs['color_key'], "info")
        
        # Check that the embed has fields for different command categories
        call_args_list = mock_embed.add_field.call_args_list
        field_names = [call[1]['name'] for call in call_args_list]

        self.assertIn("📖 Reading Commands", field_names)
        
        # Verify the interaction response was sent
        interaction.response.send_message.assert_called_once_with(embed=mock_embed)

    @patch('cogs.general_commands.create_embed')
    async def test_vote_command(self, mock_create_embed):
        """Test the vote command"""
        interaction = AsyncMock()
        interaction.response = AsyncMock()

        mock_embed = MagicMock()
        mock_create_embed.return_value = mock_embed

        vote_command = self.commands['vote']['func']
        await vote_command(interaction)

        mock_create_embed.assert_called_once()
        _, kwargs = mock_create_embed.call_args
        self.assertEqual(kwargs['title'], "🗳️ Vote for Kluvs")
        self.assertEqual(kwargs['color_key'], "royal")

        call_args = interaction.response.send_message.call_args
        self.assertEqual(call_args.kwargs['embed'], mock_embed)
        self.assertIsNotNone(call_args.kwargs['view'])
        self.assertTrue(call_args.kwargs['ephemeral'])

if __name__ == '__main__':
    unittest.main()
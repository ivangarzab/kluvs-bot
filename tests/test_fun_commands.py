"""
Tests for fun commands
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import discord
import random

# Import the command module and related utilities
from cogs.fun_commands import setup_fun_commands
from utils.embeds import create_embed

class TestFunCommands(unittest.IsolatedAsyncioTestCase):
    """Test cases for fun commands - PROPERLY ASYNC"""
    
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
        
        # Set up fixed random seed for predictable results
        random.seed(42)
        
        # Register the commands
        setup_fun_commands(self.bot)
        
        # Verify commands were registered
        self.assertIn('rolldice', self.commands)
        self.assertIn('flipcoin', self.commands)
        self.assertIn('choose', self.commands)

    @patch('cogs.fun_commands.create_embed')
    async def test_rolldice_command(self, mock_create_embed):
        """Test the rolldice command"""
        # Mock an interaction
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        
        # Mock the embed creation
        mock_embed = MagicMock()
        mock_create_embed.return_value = mock_embed
        
        # Run the command
        rolldice_command = self.commands['rolldice']['func']
        await rolldice_command(interaction)
        
        # Verify the embed was created with the right parameters
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        self.assertEqual(kwargs['title'], "🎲 Dice Roll")
        self.assertIn("You rolled a **", kwargs['description'])
        self.assertEqual(kwargs['color_key'], "fun")
        
        # Verify the interaction response was sent
        interaction.response.send_message.assert_called_once_with(embed=mock_embed)

    @patch('cogs.fun_commands.create_embed')
    async def test_flipcoin_command(self, mock_create_embed):
        """Test the flipcoin command"""
        # Mock an interaction
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        
        # Mock the embed creation
        mock_embed = MagicMock()
        mock_create_embed.return_value = mock_embed
        
        # Run the command
        flipcoin_command = self.commands['flipcoin']['func']
        await flipcoin_command(interaction)
        
        # Verify the embed was created with the right parameters
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        self.assertEqual(kwargs['title'], "🪙 Coin Flip")
        self.assertIn("You got **", kwargs['description'])
        self.assertIn("HEADS", kwargs['description'], "Coin flip result should be HEADS or TAILS")
        self.assertEqual(kwargs['color_key'], "fun")
        
        # Verify the interaction response was sent
        interaction.response.send_message.assert_called_once_with(embed=mock_embed)

    @patch('cogs.fun_commands.create_embed')
    @patch('random.choice')
    async def test_choose_command_with_options(self, mock_random_choice, mock_create_embed):
        """Test the choose command with valid options"""
        # Mock random.choice to return predictable value
        mock_random_choice.return_value = "banana"

        # Mock an interaction
        interaction = AsyncMock()
        interaction.response = AsyncMock()

        # Mock the embed creation
        mock_embed = MagicMock()
        mock_create_embed.return_value = mock_embed

        # Run the command with options
        choose_command = self.commands['choose']['func']
        await choose_command(interaction, options="apple banana cherry")

        # Verify the embed was created with the right parameters
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        self.assertEqual(kwargs['title'], "🎯 Choice Made")
        self.assertIn("banana", kwargs['description'], "One of the options should be chosen")
        self.assertEqual(kwargs['color_key'], "fun")
        
        # Verify the interaction response was sent
        interaction.response.send_message.assert_called_once_with(embed=mock_embed)

    async def test_choose_command_no_options(self):
        """Test the choose command with no options"""
        # Mock an interaction
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        
        # Run the command with empty options
        choose_command = self.commands['choose']['func']
        await choose_command(interaction, options="")

        # Verify an error message was sent
        interaction.response.send_message.assert_called_once()
        args, kwargs = interaction.response.send_message.call_args
        self.assertIn("provide some options", args[0])
        self.assertTrue(kwargs.get('ephemeral', False), "Error message should be ephemeral")

if __name__ == '__main__':
    unittest.main()
"""
Comprehensive tests for fun commands (rolldice, flipcoin, choose)
"""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import random

from cogs.fun_commands import setup_fun_commands


class TestFunCommandsComprehensive(unittest.IsolatedAsyncioTestCase):
    """Comprehensive test cases for fun commands - PROPERLY ASYNC"""

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
                self.commands[kwargs.get('name')] = {
                    'func': func,
                    'kwargs': kwargs
                }
                return func
            return decorator

        self.bot.tree.command = mock_command

        # Register the commands
        setup_fun_commands(self.bot)

        # Verify commands were registered
        self.assertIn('rolldice', self.commands)
        self.assertIn('flipcoin', self.commands)
        self.assertIn('choose', self.commands)

    async def test_rolldice_command(self):
        """Test the rolldice command"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command multiple times to test randomness
        rolldice_command = self.commands['rolldice']['func']

        with patch('random.randint', return_value=4):
            await rolldice_command(interaction)

        # Verify response was sent
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        self.assertIn('embed', call_args.kwargs)

    async def test_rolldice_embed_content(self):
        """Test that rolldice embed has correct content"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command with fixed random value
        rolldice_command = self.commands['rolldice']['func']

        with patch('random.randint', return_value=6):
            await rolldice_command(interaction)

        # Get the embed that was sent
        call_args = interaction.response.send_message.call_args
        embed = call_args.kwargs['embed']

        # Verify embed has dice roll info
        self.assertIn("Dice Roll", embed.title)
        self.assertIn("6", embed.description)

    async def test_rolldice_all_values(self):
        """Test that rolldice can produce all dice values"""
        # Mock interaction
        interaction = AsyncMock()

        rolldice_command = self.commands['rolldice']['func']

        # Test all possible dice values
        for value in range(1, 7):
            interaction.reset_mock()
            interaction.response.send_message = AsyncMock()

            with patch('random.randint', return_value=value):
                await rolldice_command(interaction)

            call_args = interaction.response.send_message.call_args
            embed = call_args.kwargs['embed']
            self.assertIn(str(value), embed.description)

    async def test_flipcoin_command(self):
        """Test the flipcoin command"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command
        flipcoin_command = self.commands['flipcoin']['func']

        with patch('random.choice', return_value="Heads"):
            await flipcoin_command(interaction)

        # Verify response was sent
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        self.assertIn('embed', call_args.kwargs)

    async def test_flipcoin_heads(self):
        """Test flipcoin command returns heads"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        flipcoin_command = self.commands['flipcoin']['func']

        with patch('random.choice', return_value="Heads"):
            await flipcoin_command(interaction)

        call_args = interaction.response.send_message.call_args
        embed = call_args.kwargs['embed']
        self.assertIn("Heads", embed.description)

    async def test_flipcoin_tails(self):
        """Test flipcoin command returns tails"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        flipcoin_command = self.commands['flipcoin']['func']

        with patch('random.choice', return_value="Tails"):
            await flipcoin_command(interaction)

        call_args = interaction.response.send_message.call_args
        embed = call_args.kwargs['embed']
        self.assertIn("Tails", embed.description)

    async def test_choose_command_with_options(self):
        """Test the choose command with multiple options"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command
        choose_command = self.commands['choose']['func']
        options = "pizza, burgers, tacos"

        with patch('random.choice', return_value="pizza"):
            await choose_command(interaction, options=options)

        # Verify response was sent
        interaction.response.send_message.assert_called_once()

    async def test_choose_command_single_option(self):
        """Test the choose command with a single option"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        choose_command = self.commands['choose']['func']

        with patch('random.choice', return_value="only option"):
            await choose_command(interaction, options="only option")

        call_args = interaction.response.send_message.call_args
        embed = call_args.kwargs['embed']
        self.assertIn("only option", embed.description)

    async def test_choose_command_with_spaces(self):
        """Test the choose command handles options with spaces"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        choose_command = self.commands['choose']['func']
        options = "option one, option two, option three"

        with patch('random.choice', return_value="option two"):
            await choose_command(interaction, options=options)

        call_args = interaction.response.send_message.call_args
        embed = call_args.kwargs['embed']
        self.assertIn("option two", embed.description)

    async def test_choose_command_many_options(self):
        """Test the choose command with many options"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        choose_command = self.commands['choose']['func']
        options = "a, b, c, d, e, f, g, h, i, j"

        with patch('random.choice', return_value="f"):
            await choose_command(interaction, options=options)

        call_args = interaction.response.send_message.call_args
        embed = call_args.kwargs['embed']
        self.assertIsNotNone(embed.description)


if __name__ == '__main__':
    unittest.main()

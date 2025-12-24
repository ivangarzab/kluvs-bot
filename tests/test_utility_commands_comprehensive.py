"""
Comprehensive tests for utility commands (weather, funfact, robot)
"""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

from cogs.utility_commands import setup_utility_commands


class TestUtilityCommandsComprehensive(unittest.TestCase):
    """Comprehensive test cases for utility commands"""

    def setUp(self):
        """Set up common test fixtures"""
        # Create a mock bot
        self.bot = MagicMock()
        self.bot.tree = MagicMock()
        self.bot.config = MagicMock()
        self.bot.config.KEY_WEATHER = "test_weather_key"
        self.bot.openai_service = MagicMock()
        self.bot.openai_service.get_response = AsyncMock(return_value="AI response here")

        # Store the registered commands
        self.commands = {}
        self.prefix_commands = {}

        # Mock the bot.tree.command decorator
        def mock_command(**kwargs):
            def decorator(func):
                self.commands[kwargs.get('name')] = {
                    'func': func,
                    'kwargs': kwargs
                }
                return func
            return decorator

        # Mock the bot.command decorator for prefix commands
        def mock_prefix_command(**kwargs):
            def decorator(func):
                self.prefix_commands[func.__name__] = {
                    'func': func,
                    'kwargs': kwargs
                }
                return func
            return decorator

        self.bot.tree.command = mock_command
        self.bot.command = mock_prefix_command

        # Register the commands
        with patch('cogs.utility_commands.WeatherService'):
            setup_utility_commands(self.bot)

        # Verify commands were registered
        self.assertIn('weather', self.commands)
        self.assertIn('funfact', self.commands)
        self.assertIn('robot', self.commands)
        self.assertIn('robot', self.prefix_commands)

    @patch('cogs.utility_commands.WeatherService')
    async def test_weather_command_success(self, mock_weather_service_class):
        """Test the weather command with successful response"""
        # Mock weather service
        mock_weather_service = AsyncMock()
        mock_weather_service.get_weather = AsyncMock(return_value="Sunny, 75°F")
        mock_weather_service_class.return_value = mock_weather_service

        # Re-setup to use mocked service
        self.setUp()
        setup_utility_commands(self.bot)

        # Mock interaction
        interaction = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Run the command
        weather_command = self.commands['weather']['func']
        await weather_command(interaction, location="San Francisco")

        # Verify defer was called
        interaction.response.defer.assert_called_once()

        # Verify followup was sent
        interaction.followup.send.assert_called_once()

    async def test_funfact_command(self):
        """Test the funfact command"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command
        funfact_command = self.commands['funfact']['func']
        await funfact_command(interaction)

        # Verify response was sent
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        self.assertIn('embed', call_args.kwargs)

    async def test_funfact_command_embed_content(self):
        """Test that funfact command embed has correct content"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Run the command
        funfact_command = self.commands['funfact']['func']
        await funfact_command(interaction)

        # Get the embed that was sent
        call_args = interaction.response.send_message.call_args
        embed = call_args.kwargs['embed']

        # Verify embed properties
        self.assertIn("Fun Fact", embed.title)
        self.assertIsNotNone(embed.description)

    async def test_robot_slash_command(self):
        """Test the robot slash command"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Run the command
        robot_command = self.commands['robot']['func']
        await robot_command(interaction, prompt="What is Python?")

        # Verify defer was called
        interaction.response.defer.assert_called_once()

        # Verify OpenAI service was called
        self.bot.openai_service.get_response.assert_called_once_with("What is Python?")

        # Verify followup was sent
        interaction.followup.send.assert_called_once()

    async def test_robot_slash_command_embed_content(self):
        """Test that robot slash command embed has AI response"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Run the command
        robot_command = self.commands['robot']['func']
        await robot_command(interaction, prompt="Tell me a joke")

        # Get the embed that was sent
        call_args = interaction.followup.send.call_args
        embed = call_args.kwargs['embed']

        # Verify embed has AI response
        self.assertIn("Robot Response", embed.title)
        self.assertEqual(embed.description, "AI response here")

    async def test_robot_prefix_command(self):
        """Test the robot prefix command"""
        # Mock context
        ctx = AsyncMock()
        ctx.send = AsyncMock()

        # Run the command
        robot_prefix_command = self.prefix_commands['robot']['func']
        await robot_prefix_command(ctx, prompt="Hello AI")

        # Verify OpenAI service was called
        self.bot.openai_service.get_response.assert_called_with("Hello AI")

        # Verify response was sent
        ctx.send.assert_called_once()

    async def test_weather_command_different_locations(self):
        """Test weather command with different location inputs"""
        # Mock interaction
        interaction = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        weather_command = self.commands['weather']['func']

        # Test with different locations
        for location in ["New York", "London", "Tokyo", "sydney"]:
            interaction.reset_mock()
            await weather_command(interaction, location=location)
            interaction.response.defer.assert_called_once()
            interaction.followup.send.assert_called_once()


if __name__ == '__main__':
    unittest.main()

"""
Tests for utility commands (weather, funfact, robot)
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from cogs.utility_commands import setup_utility_commands
from services.weather_service import WeatherService
from utils.embeds import create_embed
from utils.constants import FUN_FACTS, FACT_CLOSERS

class TestUtilityCommands(unittest.IsolatedAsyncioTestCase):
    """Test cases for utility commands - PROPERLY ASYNC"""
    
    def setUp(self):
        """Set up common test fixtures"""
        # Create a mock bot
        self.bot = MagicMock()
        self.bot.tree = MagicMock()
        self.bot.command = MagicMock()
        
        # Configure bot config
        self.bot.config = MagicMock()
        self.bot.config.KEY_WEATHER = "test_weather_key"
        
        # Set up mock for OpenAI service
        self.bot.openai_service = MagicMock()
        self.bot.openai_service.get_response = AsyncMock(return_value="This is a test AI response.")
        
        # Store the registered commands
        self.commands = {}
        self.text_commands = {}
        
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
        
        # Mock the bot.command decorator
        def mock_text_command():
            def decorator(func):
                self.text_commands[func.__name__] = func
                return func
            return decorator
        
        self.bot.command = mock_text_command
        
        # Mock WeatherService
        self.mock_weather_service = MagicMock(spec=WeatherService)
        self.mock_weather_service.get_weather = AsyncMock(return_value="Weather information for test city")

        # Patch the WeatherService constructor
        with patch('cogs.utility_commands.WeatherService', return_value=self.mock_weather_service):
            # Register the commands
            setup_utility_commands(self.bot)
        
        # Verify commands were registered
        self.assertIn('weather', self.commands)
        self.assertIn('funfact', self.commands)
        self.assertIn('robot', self.commands)

    @patch('cogs.utility_commands.create_embed')
    async def test_weather_command(self, mock_create_embed):
        """Test the weather command"""
        # Mock an interaction
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()
        
        # Mock the embed creation
        mock_embed = MagicMock()
        mock_create_embed.return_value = mock_embed
        
        # Run the command
        weather_command = self.commands['weather']['func']
        await weather_command(interaction, location="Seattle")
        
        # Verify the interaction was deferred
        interaction.response.defer.assert_called_once()
        
        # Verify weather service was called
        self.mock_weather_service.get_weather.assert_called_once_with("Seattle")
        
        # Verify the embed was created with the right parameters
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        self.assertEqual(kwargs['title'], "🌤 Weather for Seattle")
        self.assertEqual(kwargs['description'], "Weather information for test city")
        self.assertEqual(kwargs['color_key'], "info")
        self.assertTrue(kwargs['timestamp'])
        self.assertEqual(kwargs['footer'], "Weather information last updated")
        
        # Verify the followup was sent
        interaction.followup.send.assert_called_once_with(embed=mock_embed)

    @patch('cogs.utility_commands.create_embed')
    @patch('random.choice')
    async def test_funfact_command(self, mock_choice, mock_create_embed):
        """Test the funfact command"""
        # Configure random.choice to return predictable values
        mock_choice.side_effect = ["Abibliophobia is the fear of running out of reading material.", "Did you know? 🤓"]
        
        # Mock an interaction
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        
        # Mock the embed creation
        mock_embed = MagicMock()
        mock_create_embed.return_value = mock_embed
        
        # Run the command
        funfact_command = self.commands['funfact']['func']
        await funfact_command(interaction)
        
        # Verify random.choice was called with the correct arguments
        mock_choice.assert_any_call(FUN_FACTS)
        mock_choice.assert_any_call(FACT_CLOSERS)
        
        # Verify the embed was created with the right parameters
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        self.assertEqual(kwargs['title'], "📚 Book Fun Fact")
        self.assertEqual(kwargs['description'], "Abibliophobia is the fear of running out of reading material.")
        self.assertEqual(kwargs['color_key'], "purp")
        self.assertEqual(kwargs['footer'], "Did you know? 🤓")
        
        # Verify the interaction response was sent
        interaction.response.send_message.assert_called_once_with(embed=mock_embed)

    @patch('cogs.utility_commands.create_embed')
    async def test_robot_command_slash(self, mock_create_embed):
        """Test the robot slash command"""
        # Mock an interaction
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()
        
        # Mock the embed creation
        mock_embed = MagicMock()
        mock_create_embed.return_value = mock_embed
        
        # Run the command
        robot_command = self.commands['robot']['func']
        await robot_command(interaction, prompt="Tell me about books")
        
        # Verify the interaction was deferred
        interaction.response.defer.assert_called_once()
        
        # Verify OpenAI service was called
        self.bot.openai_service.get_response.assert_called_once_with("Tell me about books")
        
        # Verify the embed was created with the right parameters
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        self.assertEqual(kwargs['title'], "🤖 Robot Response")
        self.assertEqual(kwargs['description'], "This is a test AI response.")
        self.assertEqual(kwargs['color_key'], "blank")
        
        # Verify the followup was sent
        interaction.followup.send.assert_called_once_with(embed=mock_embed)

    @patch('cogs.utility_commands.create_embed')
    async def test_robot_command_text(self, mock_create_embed):
        """Test the robot text command"""
        # Check if text command was registered
        self.assertIn('robot', self.text_commands)

        # Mock the context
        ctx = AsyncMock()
        
        # Mock the embed creation
        mock_embed = MagicMock()
        mock_create_embed.return_value = mock_embed
        
        # Run the command
        robot_text_command = self.text_commands['robot']
        await robot_text_command(ctx, prompt="Tell me about books")
        
        # Verify OpenAI service was called
        self.bot.openai_service.get_response.assert_called_once_with("Tell me about books")
        
        # Verify the embed was created with the right parameters
        mock_create_embed.assert_called_once()
        args, kwargs = mock_create_embed.call_args
        self.assertEqual(kwargs['title'], "🤖 Robot Response")
        self.assertEqual(kwargs['description'], "This is a test AI response.")
        self.assertEqual(kwargs['color_key'], "blank")
        
        # Verify the response was sent
        ctx.send.assert_called_once_with(embed=mock_embed)

if __name__ == '__main__':
    unittest.main()
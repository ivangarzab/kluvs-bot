"""
Tests for admin commands
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
import os

from cogs.admin_commands import setup_admin_commands


class TestAdminCommands(unittest.IsolatedAsyncioTestCase):
    """Test cases for admin commands - PROPERLY ASYNC"""

    def setUp(self):
        """Set up common test fixtures"""
        # Create a mock bot
        self.bot = MagicMock()

        # Store the registered commands
        self.commands = {}

        # Mock the bot.command decorator
        def mock_command(**kwargs):
            def decorator(func):
                # Store the command and its properties
                self.commands[kwargs.get('name')] = {
                    'func': func,
                    'kwargs': kwargs
                }
                return func
            return decorator

        self.bot.command = mock_command

        # Register the commands
        setup_admin_commands(self.bot)

        # Verify command was registered
        self.assertIn('version', self.commands)

    async def test_version_command_success(self):
        """Test the version command with successful version extraction"""
        # Create mock context
        ctx = AsyncMock()
        ctx.send = AsyncMock()

        # Mock setup.py content
        setup_content = '''
from setuptools import setup, find_packages

setup(
    name="quill-bot",
    version="0.0.1",
    description="A Discord bot for book clubs",
    packages=find_packages(),
)
'''

        with patch('builtins.open', mock_open(read_data=setup_content)):
            with patch('os.path.join', return_value='setup.py'):
                with patch('os.path.dirname', return_value='/mock/path'):
                    # Call the version command
                    await self.commands['version']['func'](ctx)

        # Verify that ctx.send was called with an embed
        ctx.send.assert_called_once()
        call_args = ctx.send.call_args
        self.assertIn('embed', call_args.kwargs)

    async def test_version_command_no_version_found(self):
        """Test the version command when version is not found in setup.py"""
        # Create mock context
        ctx = AsyncMock()
        ctx.send = AsyncMock()

        # Mock setup.py content without version
        setup_content = '''
from setuptools import setup

setup(
    name="quill-bot",
)
'''

        with patch('builtins.open', mock_open(read_data=setup_content)):
            with patch('os.path.join', return_value='setup.py'):
                with patch('os.path.dirname', return_value='/mock/path'):
                    # Call the version command
                    await self.commands['version']['func'](ctx)

        # Verify that ctx.send was called with an error embed
        ctx.send.assert_called_once()
        call_args = ctx.send.call_args
        self.assertIn('embed', call_args.kwargs)

    async def test_version_command_file_not_found(self):
        """Test the version command when setup.py is not found"""
        # Create mock context
        ctx = AsyncMock()
        ctx.send = AsyncMock()

        with patch('builtins.open', side_effect=FileNotFoundError("setup.py not found")):
            with patch('os.path.join', return_value='setup.py'):
                with patch('os.path.dirname', return_value='/mock/path'):
                    # Call the version command
                    await self.commands['version']['func'](ctx)

        # Verify that ctx.send was called with an error embed
        ctx.send.assert_called_once()
        call_args = ctx.send.call_args
        self.assertIn('embed', call_args.kwargs)

    async def test_version_command_general_exception(self):
        """Test the version command with a general exception"""
        # Create mock context
        ctx = AsyncMock()
        ctx.send = AsyncMock()

        with patch('builtins.open', side_effect=Exception("Unexpected error")):
            with patch('os.path.join', return_value='setup.py'):
                with patch('os.path.dirname', return_value='/mock/path'):
                    # Call the version command
                    await self.commands['version']['func'](ctx)

        # Verify that ctx.send was called with an error embed
        ctx.send.assert_called_once()
        call_args = ctx.send.call_args
        self.assertIn('embed', call_args.kwargs)


if __name__ == '__main__':
    unittest.main()

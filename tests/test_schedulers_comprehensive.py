"""
Comprehensive tests for scheduled tasks
"""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import pytz

from utils.schedulers import setup_scheduled_tasks


class TestSchedulersComprehensive(unittest.TestCase):
    """Comprehensive test cases for scheduled tasks"""

    def setUp(self):
        """Set up common test fixtures"""
        # Create a mock bot
        self.bot = MagicMock()
        self.bot.config = MagicMock()
        self.bot.config.DEFAULT_CHANNEL = 123456
        self.bot.get_channel = MagicMock()

    @patch('utils.schedulers.tasks.loop')
    def test_setup_scheduled_tasks(self, mock_loop):
        """Test that scheduled tasks are set up correctly"""
        # Mock the loop decorator
        mock_loop_instance = MagicMock()
        mock_loop.return_value = lambda func: mock_loop_instance

        # Call setup
        result = setup_scheduled_tasks(self.bot)

        # Verify loop was called with hours=1
        mock_loop.assert_called_once_with(hours=1)

    @patch('utils.schedulers.tasks.loop')
    async def test_reminder_at_5pm_pacific(self, mock_loop):
        """Test that reminders are sent at 5PM Pacific"""
        # Create a mock datetime for 5PM Pacific
        sf_timezone = pytz.timezone('US/Pacific')
        mock_time = datetime(2025, 1, 15, 17, 30, 0, tzinfo=sf_timezone)

        mock_channel = AsyncMock()
        mock_channel.send = AsyncMock()
        self.bot.get_channel.return_value = mock_channel

        # Mock the loop to capture the function
        captured_func = None

        def capture_loop(*args, **kwargs):
            def decorator(func):
                nonlocal captured_func
                captured_func = func
                mock_task = MagicMock()
                mock_task.start = MagicMock()
                return mock_task
            return decorator

        with patch('utils.schedulers.tasks.loop', side_effect=capture_loop):
            setup_scheduled_tasks(self.bot)

        # Now test the captured function
        with patch('utils.schedulers.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            with patch('random.random', return_value=0.3):  # Under 0.4 threshold
                await captured_func()

        # Verify message was sent
        mock_channel.send.assert_called_once()

    @patch('utils.schedulers.tasks.loop')
    async def test_reminder_not_at_5pm(self, mock_loop):
        """Test that reminders are NOT sent at other times"""
        # Create a mock datetime for 3PM Pacific (not 5PM)
        sf_timezone = pytz.timezone('US/Pacific')
        mock_time = datetime(2025, 1, 15, 15, 30, 0, tzinfo=sf_timezone)

        mock_channel = AsyncMock()
        mock_channel.send = AsyncMock()
        self.bot.get_channel.return_value = mock_channel

        # Capture the loop function
        captured_func = None

        def capture_loop(*args, **kwargs):
            def decorator(func):
                nonlocal captured_func
                captured_func = func
                mock_task = MagicMock()
                mock_task.start = MagicMock()
                return mock_task
            return decorator

        with patch('utils.schedulers.tasks.loop', side_effect=capture_loop):
            setup_scheduled_tasks(self.bot)

        # Test the captured function
        with patch('utils.schedulers.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            with patch('random.random', return_value=0.3):
                await captured_func()

        # Verify NO message was sent (wrong hour)
        mock_channel.send.assert_not_called()

    @patch('utils.schedulers.tasks.loop')
    async def test_reminder_probability(self, mock_loop):
        """Test that reminders have 40% probability"""
        # Create a mock datetime for 5PM Pacific
        sf_timezone = pytz.timezone('US/Pacific')
        mock_time = datetime(2025, 1, 15, 17, 0, 0, tzinfo=sf_timezone)

        mock_channel = AsyncMock()
        self.bot.get_channel.return_value = mock_channel

        # Capture the loop function
        captured_func = None

        def capture_loop(*args, **kwargs):
            def decorator(func):
                nonlocal captured_func
                captured_func = func
                mock_task = MagicMock()
                mock_task.start = MagicMock()
                return mock_task
            return decorator

        with patch('utils.schedulers.tasks.loop', side_effect=capture_loop):
            setup_scheduled_tasks(self.bot)

        # Test with random value above 0.4 (should NOT send)
        with patch('utils.schedulers.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            with patch('random.random', return_value=0.5):
                await captured_func()

        # Verify NO message was sent (probability check failed)
        mock_channel.send.assert_not_called()

    @patch('utils.schedulers.tasks.loop')
    async def test_reminder_no_channel(self, mock_loop):
        """Test reminder when channel doesn't exist"""
        # Create a mock datetime for 5PM Pacific
        sf_timezone = pytz.timezone('US/Pacific')
        mock_time = datetime(2025, 1, 15, 17, 0, 0, tzinfo=sf_timezone)

        # Return None for channel
        self.bot.get_channel.return_value = None

        # Capture the loop function
        captured_func = None

        def capture_loop(*args, **kwargs):
            def decorator(func):
                nonlocal captured_func
                captured_func = func
                mock_task = MagicMock()
                mock_task.start = MagicMock()
                return mock_task
            return decorator

        with patch('utils.schedulers.tasks.loop', side_effect=capture_loop):
            setup_scheduled_tasks(self.bot)

        # Test the captured function - should not crash
        with patch('utils.schedulers.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            with patch('random.random', return_value=0.3):
                await captured_func()

        # No exception should be raised


if __name__ == '__main__':
    unittest.main()

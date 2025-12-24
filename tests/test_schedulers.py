"""
Tests for scheduled tasks
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import pytz

from utils.schedulers import setup_scheduled_tasks


class TestSchedulers(unittest.IsolatedAsyncioTestCase):
    """Test cases for scheduled tasks - PROPERLY ASYNC"""

    def setUp(self):
        """Set up common test fixtures"""
        self.bot = MagicMock()
        self.bot.config = MagicMock()
        self.bot.config.DEFAULT_CHANNEL = 123456
        self.bot.get_channel = MagicMock()

    @patch('utils.schedulers.tasks.loop')
    async def test_reminder_at_5pm_pacific_triggers(self, mock_loop):
        """Test that reminders trigger at 5PM Pacific with correct probability"""
        # Create mock datetime for 5PM Pacific
        sf_timezone = pytz.timezone('US/Pacific')
        mock_time = datetime(2025, 1, 15, 17, 30, 0, tzinfo=sf_timezone)

        # Mock channel
        mock_channel = AsyncMock()
        mock_channel.send = AsyncMock()
        self.bot.get_channel.return_value = mock_channel

        # Capture the scheduled function
        captured_func = None

        def capture_loop(*args, **kwargs):
            def decorator(func):
                nonlocal captured_func
                captured_func = func
                mock_task = MagicMock()
                mock_task.start = MagicMock()
                return mock_task
            return decorator

        mock_loop.side_effect = capture_loop

        # Setup and capture the function
        setup_scheduled_tasks(self.bot)
        self.assertIsNotNone(captured_func)

        # Test with correct time and probability
        with patch('utils.schedulers.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            with patch('random.random', return_value=0.1):  # 0.3 < 0.4, should send
                with patch('random.choice', return_value="Keep reading!"):
                    await captured_func()

        # Verify message was sent
        mock_channel.send.assert_called_once()
        call_args = mock_channel.send.call_args
        self.assertIn('embed', call_args.kwargs)

    @patch('utils.schedulers.tasks.loop')
    async def test_reminder_wrong_hour_no_send(self, mock_loop):
        """Test that reminders DON'T trigger at wrong hours"""
        # Create mock datetime for 3PM Pacific (not 5PM)
        sf_timezone = pytz.timezone('US/Pacific')
        mock_time = datetime(2025, 1, 15, 15, 0, 0, tzinfo=sf_timezone)

        mock_channel = AsyncMock()
        self.bot.get_channel.return_value = mock_channel

        # Capture the scheduled function
        captured_func = None

        def capture_loop(*args, **kwargs):
            def decorator(func):
                nonlocal captured_func
                captured_func = func
                mock_task = MagicMock()
                mock_task.start = MagicMock()
                return mock_task
            return decorator

        mock_loop.side_effect = capture_loop
        setup_scheduled_tasks(self.bot)

        # Test with wrong time
        with patch('utils.schedulers.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            with patch('random.random', return_value=0.3):  # Would trigger if time was right
                await captured_func()

        # Verify NO message was sent
        mock_channel.send.assert_not_called()

    @patch('utils.schedulers.tasks.loop')
    async def test_reminder_probability_check(self, mock_loop):
        """Test that probability check works (40% threshold)"""
        sf_timezone = pytz.timezone('US/Pacific')
        mock_time = datetime(2025, 1, 15, 17, 0, 0, tzinfo=sf_timezone)

        mock_channel = AsyncMock()
        self.bot.get_channel.return_value = mock_channel

        # Capture the scheduled function
        captured_func = None

        def capture_loop(*args, **kwargs):
            def decorator(func):
                nonlocal captured_func
                captured_func = func
                mock_task = MagicMock()
                mock_task.start = MagicMock()
                return mock_task
            return decorator

        mock_loop.side_effect = capture_loop
        setup_scheduled_tasks(self.bot)

        # Test with random value ABOVE threshold (should NOT send)
        with patch('utils.schedulers.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            with patch('random.random', return_value=0.5):  # 0.5 >= 0.4, should NOT send
                await captured_func()

        # Verify NO message was sent
        mock_channel.send.assert_not_called()

    @patch('utils.schedulers.tasks.loop')
    async def test_reminder_no_channel(self, mock_loop):
        """Test reminder handles missing channel gracefully"""
        sf_timezone = pytz.timezone('US/Pacific')
        mock_time = datetime(2025, 1, 15, 17, 0, 0, tzinfo=sf_timezone)

        # Return None for channel
        self.bot.get_channel.return_value = None

        # Capture the scheduled function
        captured_func = None

        def capture_loop(*args, **kwargs):
            def decorator(func):
                nonlocal captured_func
                captured_func = func
                mock_task = MagicMock()
                mock_task.start = MagicMock()
                return mock_task
            return decorator

        mock_loop.side_effect = capture_loop
        setup_scheduled_tasks(self.bot)

        # Should not crash even with no channel
        with patch('utils.schedulers.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            with patch('random.random', return_value=0.3):
                await captured_func()

        # No exception should be raised

    @patch('utils.schedulers.tasks.loop')
    def test_setup_scheduled_tasks_returns_task(self, mock_loop):
        """Test that setup returns the scheduled task"""
        mock_task = MagicMock()
        mock_task.start = MagicMock()

        def mock_loop_decorator(*args, **kwargs):
            def decorator(func):
                return mock_task
            return decorator

        mock_loop.side_effect = mock_loop_decorator

        result = setup_scheduled_tasks(self.bot)

        # Verify task was returned
        self.assertEqual(result, mock_task)

    @patch('utils.schedulers.tasks.loop')
    def test_loop_configured_correctly(self, mock_loop):
        """Test that the task loop is configured for 1 hour intervals"""
        mock_task = MagicMock()

        def mock_loop_decorator(*args, **kwargs):
            # Verify hours=1 was passed
            self.assertEqual(kwargs.get('hours'), 1)

            def decorator(func):
                return mock_task
            return decorator

        mock_loop.side_effect = mock_loop_decorator

        setup_scheduled_tasks(self.bot)

        # Verify loop was called with correct parameters
        mock_loop.assert_called_once_with(hours=1)


if __name__ == '__main__':
    unittest.main()

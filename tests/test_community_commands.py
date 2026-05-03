"""
Tests for community support & utility commands (support, donate, bug, feedback)
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from cogs.general_commands import setup_general_commands, BugReportModal, FeedbackModal


class TestCommunityCommands(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.bot = MagicMock()
        self.bot.tree = MagicMock()
        self.commands = {}

        def mock_command(**kwargs):
            def decorator(func):
                self.commands[kwargs.get('name')] = {'func': func, 'kwargs': kwargs}
                return func
            return decorator

        self.bot.tree.command = mock_command
        setup_general_commands(self.bot)

    # --- /support ---

    async def test_support_command_registered(self):
        self.assertIn('support', self.commands)

    async def test_support_sends_ephemeral_embed_with_view(self):
        interaction = AsyncMock()
        await self.commands['support']['func'](interaction)

        interaction.response.send_message.assert_called_once()
        call_kwargs = interaction.response.send_message.call_args.kwargs
        self.assertTrue(call_kwargs.get('ephemeral'))
        self.assertIn('embed', call_kwargs)
        self.assertIn('view', call_kwargs)

    async def test_support_embed_content(self):
        interaction = AsyncMock()
        await self.commands['support']['func'](interaction)

        embed = interaction.response.send_message.call_args.kwargs['embed']
        self.assertIn("Support", embed.title)

    # --- /donate ---

    async def test_donate_command_registered(self):
        self.assertIn('donate', self.commands)

    async def test_donate_sends_ephemeral_embed_with_view(self):
        interaction = AsyncMock()
        await self.commands['donate']['func'](interaction)

        interaction.response.send_message.assert_called_once()
        call_kwargs = interaction.response.send_message.call_args.kwargs
        self.assertTrue(call_kwargs.get('ephemeral'))
        self.assertIn('embed', call_kwargs)
        self.assertIn('view', call_kwargs)

    async def test_donate_embed_content(self):
        interaction = AsyncMock()
        await self.commands['donate']['func'](interaction)

        embed = interaction.response.send_message.call_args.kwargs['embed']
        self.assertIn("Kluvs", embed.title)

    # --- /bug ---

    async def test_bug_command_registered(self):
        self.assertIn('bug', self.commands)

    async def test_bug_sends_modal(self):
        interaction = AsyncMock()
        await self.commands['bug']['func'](interaction)

        interaction.response.send_modal.assert_called_once()
        modal = interaction.response.send_modal.call_args.args[0]
        self.assertIsInstance(modal, BugReportModal)

    # --- /feedback ---

    async def test_feedback_command_registered(self):
        self.assertIn('feedback', self.commands)

    async def test_feedback_sends_modal(self):
        interaction = AsyncMock()
        await self.commands['feedback']['func'](interaction)

        interaction.response.send_modal.assert_called_once()
        modal = interaction.response.send_modal.call_args.args[0]
        self.assertIsInstance(modal, FeedbackModal)

    # --- BugReportModal.on_submit ---

    @patch('cogs.general_commands.aiohttp.ClientSession')
    @patch('cogs.general_commands.discord.Webhook.from_url')
    @patch('cogs.general_commands.os.getenv')
    async def test_bug_modal_on_submit_sends_webhook_and_ephemeral_reply(
        self, mock_getenv, mock_from_url, mock_session_cls
    ):
        mock_getenv.return_value = "https://example.com/bug-webhook"

        mock_webhook = AsyncMock()
        mock_from_url.return_value = mock_webhook

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        interaction = AsyncMock()
        interaction.user.name = "TestUser"
        interaction.user.id = 123456
        interaction.guild.name = "Test Server"

        modal = BugReportModal()
        modal.issue_title = MagicMock()
        modal.issue_title.value = "Crash on startup"
        modal.steps = MagicMock()
        modal.steps.value = "Open the app, it crashes."

        await modal.on_submit(interaction)

        mock_webhook.send.assert_called_once()
        send_kwargs = mock_webhook.send.call_args.kwargs
        self.assertEqual(send_kwargs['thread_name'], "Crash on startup")
        self.assertIn('embed', send_kwargs)

        interaction.response.send_message.assert_called_once()
        reply_kwargs = interaction.response.send_message.call_args
        self.assertTrue(reply_kwargs.kwargs.get('ephemeral'))
        self.assertIn("Thank you", reply_kwargs.args[0])

    # --- FeedbackModal.on_submit ---

    @patch('cogs.general_commands.aiohttp.ClientSession')
    @patch('cogs.general_commands.discord.Webhook.from_url')
    @patch('cogs.general_commands.os.getenv')
    async def test_feedback_modal_on_submit_sends_webhook_and_ephemeral_reply(
        self, mock_getenv, mock_from_url, mock_session_cls
    ):
        mock_getenv.return_value = "https://example.com/feedback-webhook"

        mock_webhook = AsyncMock()
        mock_from_url.return_value = mock_webhook

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        interaction = AsyncMock()
        interaction.user.name = "TestUser"
        interaction.user.id = 789012
        interaction.guild.name = "Test Server"

        modal = FeedbackModal()
        modal.topic = MagicMock()
        modal.topic.value = "UI Suggestion"
        modal.feedback = MagicMock()
        modal.feedback.value = "Please add a dark mode."

        await modal.on_submit(interaction)

        mock_webhook.send.assert_called_once()
        send_kwargs = mock_webhook.send.call_args.kwargs
        self.assertEqual(send_kwargs['thread_name'], "UI Suggestion")
        self.assertIn('embed', send_kwargs)

        interaction.response.send_message.assert_called_once()
        reply_kwargs = interaction.response.send_message.call_args
        self.assertTrue(reply_kwargs.kwargs.get('ephemeral'))
        self.assertIn("Thank you", reply_kwargs.args[0])


if __name__ == '__main__':
    unittest.main()

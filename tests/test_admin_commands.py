"""
Tests for admin commands (slash command version)
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
import discord

from cogs.admin_commands import setup_admin_commands
from api.bookclub_api import APIError


def _make_bot():
    """Creates a mock bot with api, tree, and wait_for."""
    bot = MagicMock()
    bot.api = MagicMock()
    bot.wait_for = AsyncMock()
    bot.tree = MagicMock()
    commands = {}

    def mock_command(**kwargs):
        def decorator(func):
            commands[kwargs.get("name")] = {"func": func, "kwargs": kwargs}
            return func
        return decorator

    def mock_describe(**kwargs):
        def decorator(func):
            return func
        return decorator

    def mock_default_permissions(**kwargs):
        def decorator(func):
            return func
        return decorator

    bot.tree.command = mock_command
    bot.tree.describe = mock_describe
    from discord import app_commands
    app_commands.describe = mock_describe
    app_commands.default_permissions = mock_default_permissions

    setup_admin_commands(bot)
    return bot, commands


def _make_interaction(*, is_owner=True, user_id="111", channel_id="999", guild_id="888"):
    """Creates a mock interaction."""
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = int(user_id)
    interaction.user.display_name = "Test User"
    interaction.channel = MagicMock()
    interaction.channel.id = int(channel_id)
    interaction.channel.mention = f"<#{channel_id}>"
    interaction.guild = MagicMock()
    interaction.guild_id = int(guild_id)
    interaction.guild.id = int(guild_id)
    interaction.guild.name = "Test Server"
    interaction.guild.owner = interaction.user if is_owner else MagicMock()
    return interaction


def _club_with_admin(user_id, club_id="club-1", session_id="sess-1"):
    """Returns club data where the user is an admin."""
    return {
        "id": club_id,
        "name": "Test Club",
        "discord_channel": "999",
        "members": [{"discord_id": str(user_id), "role": "admin"}],
        "active_session": {"id": session_id, "book": {"title": "Dune", "author": "Herbert"}},
    }


class TestVersionCommand(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()

    async def test_version_success(self):
        interaction = _make_interaction()
        setup_content = 'setup(name="kluvs-bot", version="0.0.1")'
        with patch("builtins.open", mock_open(read_data=setup_content)):
            with patch("cogs.admin_commands.os.path.join", return_value="setup.py"):
                with patch("cogs.admin_commands.os.path.dirname", return_value="/mock"):
                    await self.commands["version"]["func"](interaction)
        interaction.response.send_message.assert_called_once()
        self.assertIn("embed", interaction.response.send_message.call_args.kwargs)

    async def test_version_not_found(self):
        interaction = _make_interaction()
        with patch("builtins.open", mock_open(read_data="setup(name='kluvs-bot')")):
            with patch("os.path.join", return_value="setup.py"):
                with patch("os.path.dirname", return_value="/mock"):
                    await self.commands["version"]["func"](interaction)
        interaction.response.send_message.assert_called_once()

    async def test_version_file_error(self):
        interaction = _make_interaction()
        with patch("builtins.open", side_effect=FileNotFoundError()):
            with patch("os.path.join", return_value="setup.py"):
                with patch("os.path.dirname", return_value="/mock"):
                    await self.commands["version"]["func"](interaction)
        interaction.response.send_message.assert_called_once()


class TestServerCommands(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()

    async def test_server_register_success(self):
        interaction = _make_interaction()
        self.bot.api.register_server.return_value = {"success": True}
        await self.commands["server_register"]["func"](interaction)
        self.bot.api.register_server.assert_called_once_with("888", "Test Server")
        interaction.response.defer.assert_called_once()
        interaction.followup.send.assert_called_once()
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_server_register_api_error(self):
        interaction = _make_interaction()
        self.bot.api.register_server.side_effect = APIError("connection failed")
        await self.commands["server_register"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_server_update_success(self):
        interaction = _make_interaction()
        self.bot.api.update_server.return_value = {"success": True}
        await self.commands["server_update"]["func"](interaction, name="Updated Name")
        self.bot.api.update_server.assert_called_once_with("888", "Updated Name")
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_server_update_api_error(self):
        interaction = _make_interaction()
        self.bot.api.update_server.side_effect = APIError("update failed")
        await self.commands["server_update"]["func"](interaction, name="New Name")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])


class TestCanManageClubs(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()

    async def test_guild_owner_can_create_club_without_being_admin(self):
        """Guild owner should be able to create a club even if not a club admin."""
        interaction = _make_interaction(user_id="111", is_owner=True)
        self.bot.api.create_club.return_value = {"success": True}
        self.bot.api.get_member_by_discord_id.return_value = None
        self.bot.api.create_member.return_value = {"member": {"id": 1, "name": "Owner"}}
        await self.commands["club_create"]["func"](interaction, name="New Club")
        self.bot.api.create_club.assert_called_once()

    async def test_non_owner_denied_when_not_admin(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = {
            "id": "club-1",
            "name": "Test Club",
            "members": [{"discord_id": "111", "role": "admin"}],
        }
        await self.commands["club_create"]["func"](interaction, name="New Club")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_club_create_denied_when_no_club(self):
        interaction = _make_interaction(user_id="111", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["club_create"]["func"](interaction, name="New Club")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])


class TestClubCommands(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()
        self.club = _club_with_admin("111")

    async def test_club_create_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.get_member_by_discord_id.return_value = None
        self.bot.api.create_member.return_value = {"member": {"id": 1, "name": "Owner"}}
        self.bot.api.create_club.return_value = {"success": True}
        await self.commands["club_create"]["func"](interaction, name="Sci-Fi Club")
        call_payload = self.bot.api.create_club.call_args[0][0]
        self.assertEqual(call_payload["members"], [{"id": 1, "name": "Owner"}])
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_club_create_empty_name(self):
        interaction = _make_interaction(user_id="111")
        await self.commands["club_create"]["func"](interaction, name="")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.create_club.assert_not_called()

    async def test_club_create_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.get_member_by_discord_id.return_value = {"id": 99, "name": "Alice"}
        self.bot.api.create_club.side_effect = APIError("server error")
        await self.commands["club_create"]["func"](interaction, name="Sci-Fi Club")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_club_update_name_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_club.return_value = {"success": True}
        await self.commands["club_update"]["func"](interaction, name="New Name")
        self.bot.api.update_club.assert_called_once_with("club-1", {"name": "New Name"}, "888")

    async def test_club_update_no_args(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["club_update"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_club.assert_not_called()

    async def test_club_update_no_club_in_channel(self):
        interaction = _make_interaction(user_id="111", is_owner=True)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["club_update"]["func"](interaction, name="X")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])


class TestMemberCommands(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()
        self.club = _club_with_admin("111")

    async def test_member_add_new_member(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member_by_discord_id.return_value = None
        self.bot.api.create_member.return_value = {"success": True}
        new_member = MagicMock()
        new_member.id = 222
        new_member.display_name = "Alice"
        await self.commands["member_add"]["func"](interaction, member=new_member)
        self.bot.api.create_member.assert_called_once_with({
            "name": "Alice",
            "discord_id": "222",
            "clubs": ["club-1"],
        })

    async def test_member_add_already_in_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member_by_discord_id.return_value = {
            "id": 99,
            "name": "Alice",
            "discord_id": "222",
            "clubs": [{"id": "club-1"}],
        }
        new_member = MagicMock()
        new_member.id = 222
        new_member.display_name = "Alice"
        await self.commands["member_add"]["func"](interaction, member=new_member)
        self.bot.api.create_member.assert_not_called()
        self.assertIn("already a member", interaction.followup.send.call_args.args[0])

    async def test_member_add_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member_by_discord_id.return_value = None
        self.bot.api.create_member.side_effect = APIError("failed")
        new_member = MagicMock()
        new_member.id = 222
        new_member.display_name = "Alice"
        await self.commands["member_add"]["func"](interaction, member=new_member)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_member_remove_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.delete_member.side_effect = APIError("delete failed")

        async def auto_confirm(self):
            self.confirmed = True

        with patch.object(discord.ui.View, "wait", auto_confirm):
            await self.commands["member_remove"]["func"](interaction, member_id=42)
        self.assertIn("❌", interaction.followup.send.call_args_list[-1].args[0])

    async def test_member_role_invalid_role(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["member_role"]["func"](interaction, member_id=42, role="superadmin")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_member.assert_not_called()


class TestSessionCommands(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()
        self.club = _club_with_admin("111")

    async def test_session_create_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.create_session.return_value = {"success": True}
        await self.commands["session_create"]["func"](
            interaction,
            book_title="Dune",
            author="Frank Herbert"
        )
        self.bot.api.create_session.assert_called_once_with({
            "club_id": "club-1",
            "book": {"title": "Dune", "author": "Frank Herbert"},
        })

    async def test_session_create_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.create_session.side_effect = APIError("failed")
        await self.commands["session_create"]["func"](
            interaction,
            book_title="Dune",
            author="Frank Herbert"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_session_update_due_date(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_session.return_value = {"success": True}
        await self.commands["session_update"]["func"](interaction, due_date="2026-06-01")
        self.bot.api.update_session.assert_called_once_with("sess-1", {"due_date": "2026-06-01"})

    async def test_session_update_no_args(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["session_update"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_session_update_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_session.side_effect = APIError("update failed")
        await self.commands["session_update"]["func"](interaction, due_date="2026-06-01")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_session_delete_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.delete_session.side_effect = APIError("delete failed")

        async def auto_confirm(self):
            self.confirmed = True

        with patch.object(discord.ui.View, "wait", auto_confirm):
            await self.commands["session_delete"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args_list[-1].args[0])


class TestAdminHelpCommand(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()

    async def test_help_denied_for_non_admin(self):
        interaction = _make_interaction(is_owner=False, user_id="999")
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["admin_help"]["func"](interaction)
        self.assertIn("❌", interaction.response.send_message.call_args.args[0])

    async def test_help_allowed_for_guild_owner(self):
        interaction = _make_interaction(is_owner=True)
        await self.commands["admin_help"]["func"](interaction)
        interaction.response.send_message.assert_called_once()
        self.assertIn("embed", interaction.response.send_message.call_args.kwargs)
        embed = interaction.response.send_message.call_args.kwargs["embed"]
        self.assertIn("Admin Commands", embed.title)

    async def test_help_allowed_for_club_admin(self):
        interaction = _make_interaction(is_owner=False, user_id="111")
        club = _club_with_admin("111")
        self.bot.api.find_club_in_channel.return_value = club
        await self.commands["admin_help"]["func"](interaction)
        interaction.response.send_message.assert_called_once()
        self.assertIn("embed", interaction.response.send_message.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()

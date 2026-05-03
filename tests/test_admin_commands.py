"""
Tests for admin commands (slash command version)
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
import discord

from cogs.admin_commands import setup_admin_commands
from api.bookclub_api import APIError, ResourceNotFoundError


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


def _make_interaction(*, is_owner=True, user_id="111", channel_id="999", guild_id="888", has_admin_perms=False):
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
    interaction.user.guild_permissions = MagicMock()
    interaction.user.guild_permissions.administrator = has_admin_perms
    interaction.user.guild_permissions.manage_guild = has_admin_perms
    interaction.channel = MagicMock()
    interaction.channel.id = int(channel_id)
    interaction.channel.mention = f"<#{channel_id}>"
    interaction.guild = MagicMock()
    interaction.channel_id = int(channel_id)
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


def _auto_confirm():
    """Returns an async function that sets view.confirmed = True immediately."""
    async def _impl(self):
        self.confirmed = True
    return _impl


def _no_confirm():
    """Returns an async function that leaves view.confirmed = False."""
    async def _impl(self):
        pass
    return _impl


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
            with patch("cogs.admin_commands.os.path.join", return_value="setup.py"):
                with patch("cogs.admin_commands.os.path.dirname", return_value="/mock"):
                    await self.commands["version"]["func"](interaction)
        interaction.response.send_message.assert_called_once()

    async def test_version_file_error(self):
        interaction = _make_interaction()
        with patch("builtins.open", side_effect=FileNotFoundError()):
            with patch("cogs.admin_commands.os.path.join", return_value="setup.py"):
                with patch("cogs.admin_commands.os.path.dirname", return_value="/mock"):
                    await self.commands["version"]["func"](interaction)
        interaction.response.send_message.assert_called_once()


class TestSetupCommand(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()

    def _mock_message(self, content):
        msg = MagicMock()
        msg.content = content
        self.bot.wait_for = AsyncMock(return_value=msg)

    async def test_setup_success_new_member(self):
        interaction = _make_interaction()
        self._mock_message("My Book Club")
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.get_member_by_discord_id.return_value = None
        self.bot.api.create_member.return_value = {"member": {"id": 1, "name": "Test User"}}
        self.bot.api.create_club.return_value = {"success": True}
        await self.commands["setup"]["func"](interaction)
        self.bot.api.create_club.assert_called_once()
        call_kwargs = self.bot.api.create_club.call_args[0][0]
        self.assertEqual(call_kwargs["name"], "My Book Club")
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_setup_success_existing_member(self):
        interaction = _make_interaction()
        self._mock_message("Reader Club")
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.get_member_by_discord_id.return_value = {"id": 99, "name": "Test User"}
        self.bot.api.create_club.return_value = {"success": True}
        await self.commands["setup"]["func"](interaction)
        self.bot.api.create_member.assert_not_called()
        self.bot.api.create_club.assert_called_once()

    async def test_setup_server_already_registered(self):
        interaction = _make_interaction()
        self._mock_message("Reader Club")
        self.bot.api.register_server.side_effect = APIError("server already registered")
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.get_member_by_discord_id.return_value = {"id": 99, "name": "Test User"}
        self.bot.api.create_club.return_value = {"success": True}
        await self.commands["setup"]["func"](interaction)
        # should continue to club creation despite the error
        self.bot.api.create_club.assert_called_once()

    async def test_setup_channel_collision(self):
        interaction = _make_interaction()
        self._mock_message("My Book Club")
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.api.find_club_in_channel.return_value = {"id": "club-1", "name": "Existing Club"}
        self.bot.api.get_member_by_discord_id.return_value = {"id": 99, "name": "Test User"}
        await self.commands["setup"]["func"](interaction)
        self.bot.api.create_club.assert_not_called()
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.assertIn("already hosting", interaction.followup.send.call_args.args[0])

    async def test_setup_register_fails(self):
        interaction = _make_interaction()
        self.bot.api.register_server.side_effect = APIError("connection refused")
        await self.commands["setup"]["func"](interaction)
        self.bot.api.create_club.assert_not_called()
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_setup_timeout(self):
        interaction = _make_interaction()
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.wait_for = AsyncMock(side_effect=TimeoutError())
        await self.commands["setup"]["func"](interaction)
        self.bot.api.create_club.assert_not_called()
        self.assertIn("⏰", interaction.followup.send.call_args.args[0])

    async def test_setup_empty_club_name(self):
        interaction = _make_interaction()
        self._mock_message("   ")
        self.bot.api.register_server.return_value = {"success": True}
        await self.commands["setup"]["func"](interaction)
        self.bot.api.create_club.assert_not_called()
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_setup_create_club_api_error(self):
        interaction = _make_interaction()
        self._mock_message("Sci-Fi Club")
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.api.get_member_by_discord_id.return_value = {"id": 99, "name": "Test User"}
        self.bot.api.create_club.side_effect = APIError("club creation failed")
        await self.commands["setup"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])


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

    async def test_server_delete_confirmed_success(self):
        interaction = _make_interaction()
        self.bot.api.delete_server.return_value = {"success": True}
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["server_delete"]["func"](interaction)
        self.bot.api.delete_server.assert_called_once_with("888")
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_server_delete_api_error(self):
        interaction = _make_interaction()
        self.bot.api.delete_server.side_effect = APIError("delete failed")
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["server_delete"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_server_delete_cancelled(self):
        interaction = _make_interaction()
        with patch.object(discord.ui.View, "wait", _no_confirm()):
            await self.commands["server_delete"]["func"](interaction)
        self.bot.api.delete_server.assert_not_called()
        self.assertIn("cancelled", interaction.followup.send.call_args.args[0])


class TestCanManageClubs(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()

    async def test_guild_owner_can_create_club_without_being_admin(self):
        """Guild owner should be able to create a club even if not a club admin."""
        interaction = _make_interaction(user_id="111", is_owner=True)
        self.bot.api.find_club_in_channel.return_value = None
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

    async def test_club_create_denied_when_role_is_member(self):
        interaction = _make_interaction(user_id="111", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = {
            "id": "club-1",
            "name": "Test Club",
            "members": [{"discord_id": "111", "role": "member"}],
        }
        await self.commands["club_create"]["func"](interaction, name="New Club")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.create_club.assert_not_called()

    async def test_club_update_allowed_for_owner(self):
        interaction = _make_interaction(user_id="111", is_owner=True)
        self.bot.api.find_club_in_channel.return_value = {
            "id": "club-1",
            "name": "Test Club",
            "members": [{"discord_id": "111", "role": "owner"}],
        }
        self.bot.api.update_club.return_value = {"success": True}
        await self.commands["club_update"]["func"](interaction, name="Updated")
        self.bot.api.update_club.assert_called_once()

    async def test_guild_admin_perms_can_manage_clubs(self):
        """Users with administrator or manage_guild perms should pass _check_guild_admin."""
        interaction = _make_interaction(user_id="222", is_owner=False, has_admin_perms=True)
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.get_member_by_discord_id.return_value = None
        self.bot.api.create_member.return_value = {"member": {"id": 2, "name": "Admin User"}}
        self.bot.api.create_club.return_value = {"success": True}
        await self.commands["club_create"]["func"](interaction, name="New Club")
        self.bot.api.create_club.assert_called_once()

    async def test_club_update_denied_when_no_members_in_club(self):
        interaction = _make_interaction(user_id="111", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = {
            "id": "club-1",
            "name": "Test Club",
            "members": [],
        }
        await self.commands["club_update"]["func"](interaction, name="X")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_club.assert_not_called()


class TestClubCommands(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()
        self.club = _club_with_admin("111")

    async def test_club_create_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.get_member_by_discord_id.return_value = None
        self.bot.api.create_member.return_value = {"member": {"id": 1, "name": "Owner"}}
        self.bot.api.create_club.return_value = {"success": True}
        await self.commands["club_create"]["func"](interaction, name="Sci-Fi Club")
        call_payload = self.bot.api.create_club.call_args[0][0]
        self.assertEqual(call_payload["members"], [{"id": 1, "name": "Owner"}])
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_club_create_success_existing_member(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.get_member_by_discord_id.return_value = {"id": 99, "name": "Alice"}
        self.bot.api.create_club.return_value = {"success": True}
        await self.commands["club_create"]["func"](interaction, name="Sci-Fi Club")
        call_payload = self.bot.api.create_club.call_args[0][0]
        self.assertEqual(call_payload["members"], [{"id": 99, "name": "Alice"}])
        self.bot.api.create_member.assert_not_called()

    async def test_club_create_channel_collision(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = {
            "id": "club-1", "name": "Existing Club",
            "members": [{"discord_id": "111", "role": "owner"}],
        }
        await self.commands["club_create"]["func"](interaction, name="New Club")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.assertIn("already hosting", interaction.followup.send.call_args.args[0])
        self.bot.api.create_club.assert_not_called()

    async def test_club_create_empty_name(self):
        interaction = _make_interaction(user_id="111")
        await self.commands["club_create"]["func"](interaction, name="")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.create_club.assert_not_called()

    async def test_club_create_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
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

    async def test_club_update_new_channel(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_club.return_value = {"success": True}
        new_ch = MagicMock()
        new_ch.id = 777
        await self.commands["club_update"]["func"](interaction, new_channel=new_ch)
        self.bot.api.update_club.assert_called_once_with(
            "club-1", {"discord_channel": "777"}, "888"
        )

    async def test_club_update_no_args(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["club_update"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_club.assert_not_called()

    async def test_club_update_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["club_update"]["func"](interaction, name="X")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_club.assert_not_called()

    async def test_club_update_no_club_in_channel(self):
        interaction = _make_interaction(user_id="111", is_owner=True)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["club_update"]["func"](interaction, name="X")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_club_update_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_club.side_effect = APIError("update failed")
        await self.commands["club_update"]["func"](interaction, name="New Name")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_club_delete_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["club_delete"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.delete_club.assert_not_called()

    async def test_club_delete_no_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["club_delete"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.delete_club.assert_not_called()

    async def test_club_delete_cancelled(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        with patch.object(discord.ui.View, "wait", _no_confirm()):
            await self.commands["club_delete"]["func"](interaction)
        self.bot.api.delete_club.assert_not_called()
        self.assertIn("cancelled", interaction.followup.send.call_args.args[0])

    async def test_club_delete_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.delete_club.return_value = {"success": True}
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["club_delete"]["func"](interaction)
        self.bot.api.delete_club.assert_called_once_with("club-1", "888")
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_club_delete_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.delete_club.side_effect = APIError("delete failed")
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["club_delete"]["func"](interaction)
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

    async def test_member_add_existing_not_in_club(self):
        """Existing member in a different club should be added via update_member."""
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member_by_discord_id.return_value = {
            "id": 99,
            "name": "Alice",
            "discord_id": "222",
            "clubs": [{"id": "club-other"}],
        }
        self.bot.api.update_member.return_value = {"success": True}
        new_member = MagicMock()
        new_member.id = 222
        new_member.display_name = "Alice"
        await self.commands["member_add"]["func"](interaction, member=new_member)
        self.bot.api.update_member.assert_called_once_with(
            99, {"clubs": ["club-other", "club-1"]}
        )
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_member_add_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        new_member = MagicMock()
        new_member.id = 222
        await self.commands["member_add"]["func"](interaction, member=new_member)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.create_member.assert_not_called()

    async def test_member_add_no_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        new_member = MagicMock()
        new_member.id = 222
        await self.commands["member_add"]["func"](interaction, member=new_member)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.create_member.assert_not_called()

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
        self.bot.api.get_member.return_value = {"id": 42, "clubs": [{"id": "club-1"}]}
        self.bot.api.delete_member.side_effect = APIError("delete failed")

        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["member_remove"]["func"](interaction, member_id=42)
        self.assertIn("❌", interaction.followup.send.call_args_list[-1].args[0])

    async def test_member_remove_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["member_remove"]["func"](interaction, member_id=42)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.delete_member.assert_not_called()

    async def test_member_remove_no_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["member_remove"]["func"](interaction, member_id=42)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.delete_member.assert_not_called()

    async def test_member_remove_not_in_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member.return_value = {"id": 42, "clubs": [{"id": "club-other"}]}
        await self.commands["member_remove"]["func"](interaction, member_id=42)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.delete_member.assert_not_called()

    async def test_member_remove_not_found(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member.side_effect = ResourceNotFoundError("not found")
        await self.commands["member_remove"]["func"](interaction, member_id=42)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.delete_member.assert_not_called()

    async def test_member_remove_cancelled(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member.return_value = {"id": 42, "clubs": [{"id": "club-1"}]}
        with patch.object(discord.ui.View, "wait", _no_confirm()):
            await self.commands["member_remove"]["func"](interaction, member_id=42)
        self.bot.api.delete_member.assert_not_called()
        self.assertIn("cancelled", interaction.followup.send.call_args.args[0])

    async def test_member_remove_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member.return_value = {"id": 42, "clubs": [{"id": "club-1"}]}
        self.bot.api.delete_member.return_value = {"success": True}
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["member_remove"]["func"](interaction, member_id=42)
        self.bot.api.delete_member.assert_called_once_with(42)
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_member_role_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_member.return_value = {"success": True}
        await self.commands["member_role"]["func"](interaction, member_id=42, role="admin")
        self.bot.api.update_member.assert_called_once_with(
            42, {"club_roles": {"club-1": "admin"}}
        )
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_member_role_no_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["member_role"]["func"](interaction, member_id=42, role="member")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_member.assert_not_called()

    async def test_member_role_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_member.side_effect = APIError("update failed")
        await self.commands["member_role"]["func"](interaction, member_id=42, role="member")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])


class TestBookAutocomplete(unittest.IsolatedAsyncioTestCase):
    async def test_book_autocomplete_success(self):
        """Test autocomplete returns formatted choices"""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.client.api = AsyncMock()
        interaction.client.api.search_books.return_value = [
            {
                "external_google_id": "abc123",
                "title": "Dune",
                "author": "Frank Herbert"
            },
            {
                "external_google_id": "def456",
                "title": "Foundation",
                "author": "Isaac Asimov"
            }
        ]

        from cogs.admin_commands import book_autocomplete
        choices = await book_autocomplete(interaction, "dun")

        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0].name, "Dune — Frank Herbert")
        self.assertEqual(choices[0].value, "abc123|Dune|Frank Herbert")
        self.assertEqual(choices[1].name, "Foundation — Isaac Asimov")
        self.assertEqual(choices[1].value, "def456|Foundation|Isaac Asimov")

    async def test_book_autocomplete_min_query_length(self):
        """Test autocomplete requires at least 2 characters"""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.client.api = AsyncMock()

        from cogs.admin_commands import book_autocomplete
        choices = await book_autocomplete(interaction, "a")

        self.assertEqual(choices, [])
        interaction.client.api.search_books.assert_not_called()

    async def test_book_autocomplete_api_error(self):
        """Test autocomplete returns empty list on API error"""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.client.api = AsyncMock()
        interaction.client.api.search_books.side_effect = APIError("Connection failed")

        from cogs.admin_commands import book_autocomplete
        choices = await book_autocomplete(interaction, "dune")

        self.assertEqual(choices, [])

    async def test_book_autocomplete_max_25_results(self):
        """Test autocomplete caps at 25 results"""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.client.api = AsyncMock()
        # Return 30 books
        books = [{"external_google_id": f"id{i}", "title": f"Book {i}", "author": f"Author {i}"} for i in range(30)]
        interaction.client.api.search_books.return_value = books

        from cogs.admin_commands import book_autocomplete
        choices = await book_autocomplete(interaction, "book")

        self.assertEqual(len(choices), 25)

    async def test_book_autocomplete_value_truncation(self):
        """Test autocomplete value is truncated if needed for Discord's 100-char limit"""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.client.api = AsyncMock()
        # Long title and author that would exceed 100 chars
        interaction.client.api.search_books.return_value = [
            {
                "external_google_id": "short_id",
                "title": "A" * 80,  # Very long title
                "author": "B" * 40  # Long author
            }
        ]

        from cogs.admin_commands import book_autocomplete
        choices = await book_autocomplete(interaction, "test")

        self.assertEqual(len(choices), 1)
        self.assertLessEqual(len(choices[0].value), 100)


class TestSessionCommands(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()
        self.club = _club_with_admin("111")

    async def test_session_create_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.register_book = AsyncMock(return_value={"id": 42, "title": "Dune", "author": "Frank Herbert"})
        self.bot.api.create_session.return_value = {"success": True}
        await self.commands["session_create"]["func"](
            interaction,
            book="gid-123|Dune|Frank Herbert",
            start_date="2026-05-15",
            end_date="2026-06-15"
        )
        self.bot.api.register_book.assert_called_once_with("Dune", "Frank Herbert", external_google_id="gid-123")
        self.bot.api.create_session.assert_called_once_with({
            "club_id": "club-1",
            "book_id": 42,
            "start_date": "2026-05-15",
            "end_date": "2026-06-15",
        })

    async def test_session_create_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["session_create"]["func"](
            interaction,
            book="gid-123|Dune|Herbert",
            start_date="2026-05-15",
            end_date="2026-06-15"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.create_session.assert_not_called()

    async def test_session_create_no_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        with self.assertRaises(APIError):
            await self.commands["session_create"]["func"](
                interaction,
                book="gid-123|Dune|Herbert",
                start_date="2026-05-15",
                end_date="2026-06-15"
            )
        self.bot.api.create_session.assert_not_called()

    async def test_session_create_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.register_book = AsyncMock(return_value={"id": 42, "title": "Dune", "author": "Frank Herbert"})
        self.bot.api.create_session.side_effect = APIError("failed")
        with self.assertRaises(APIError):
            await self.commands["session_create"]["func"](
                interaction,
                book="gid-123|Dune|Frank Herbert",
                start_date="2026-05-15",
                end_date="2026-06-15"
            )

    async def test_session_create_invalid_date_format(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["session_create"]["func"](
            interaction,
            book="gid-123|Dune|Frank Herbert",
            start_date="2026/05/15",  # Wrong format
            end_date="2026-06-15"
        )
        self.assertIn("❌ Dates must be in **YYYY-MM-DD** format", interaction.followup.send.call_args.args[0])
        self.bot.api.create_session.assert_not_called()

    async def test_session_create_start_after_end(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["session_create"]["func"](
            interaction,
            book="gid-123|Dune|Frank Herbert",
            start_date="2026-06-15",
            end_date="2026-05-15"  # End before start
        )
        self.assertIn("❌ Start date must be before end date", interaction.followup.send.call_args.args[0])
        self.bot.api.create_session.assert_not_called()

    async def test_session_create_invalid_book_format(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["session_create"]["func"](
            interaction,
            book="invalid",  # Missing pipes
            start_date="2026-05-15",
            end_date="2026-06-15"
        )
        self.assertIn("❌ Invalid book selection", interaction.followup.send.call_args.args[0])
        self.bot.api.create_session.assert_not_called()

    async def test_session_update_due_date(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_session.return_value = {"success": True}
        await self.commands["session_update"]["func"](interaction, due_date="2026-06-01")
        self.bot.api.update_session.assert_called_once_with("sess-1", {"due_date": "2026-06-01"})

    async def test_session_update_book_fields(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_session.return_value = {"success": True}
        await self.commands["session_update"]["func"](
            interaction, book_title="Foundation", book_author="Asimov"
        )
        self.bot.api.update_session.assert_called_once_with(
            "sess-1", {"book": {"title": "Foundation", "author": "Asimov"}}
        )

    async def test_session_update_no_args(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["session_update"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_session_update_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["session_update"]["func"](interaction, due_date="2026-06-01")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_session_update_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["session_update"]["func"](interaction, due_date="2026-06-01")
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

        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["session_delete"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args_list[-1].args[0])

    async def test_session_delete_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["session_delete"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.delete_session.assert_not_called()

    async def test_session_delete_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["session_delete"]["func"](interaction)
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.delete_session.assert_not_called()

    async def test_session_delete_cancelled(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        with patch.object(discord.ui.View, "wait", _no_confirm()):
            await self.commands["session_delete"]["func"](interaction)
        self.bot.api.delete_session.assert_not_called()
        self.assertIn("cancelled", interaction.followup.send.call_args.args[0])

    async def test_session_delete_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.delete_session.return_value = {"success": True}
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["session_delete"]["func"](interaction)
        self.bot.api.delete_session.assert_called_once_with("sess-1")
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)


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

    async def test_help_allowed_for_guild_admin_perms(self):
        interaction = _make_interaction(is_owner=False, user_id="222", has_admin_perms=True)
        await self.commands["admin_help"]["func"](interaction)
        interaction.response.send_message.assert_called_once()
        self.assertIn("embed", interaction.response.send_message.call_args.kwargs)

    async def test_help_allowed_for_club_admin(self):
        interaction = _make_interaction(is_owner=False, user_id="111")
        club = _club_with_admin("111")
        self.bot.api.find_club_in_channel.return_value = club
        await self.commands["admin_help"]["func"](interaction)
        interaction.response.send_message.assert_called_once()
        self.assertIn("embed", interaction.response.send_message.call_args.kwargs)

    async def test_help_denied_for_non_admin(self):
        interaction = _make_interaction(is_owner=False, user_id="999", has_admin_perms=False)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["admin_help"]["func"](interaction)
        self.assertIn("❌", interaction.response.send_message.call_args.args[0])

    @patch("builtins.open", new_callable=MagicMock)
    @patch("re.search")
    async def test_version_success(self, mock_search, mock_open):
        """Test version command displays version."""
        interaction = _make_interaction()
        mock_match = MagicMock()
        mock_match.group.return_value = "1.0.0"
        mock_search.return_value = mock_match

        mock_file_handle = MagicMock()
        mock_file_handle.read.return_value = 'version = "1.0.0"'
        mock_open.return_value.__enter__.return_value = mock_file_handle

        await self.commands["version"]["func"](interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        self.assertIn("embed", call_args.kwargs)

    @patch("builtins.open")
    async def test_version_file_not_found(self, mock_open):
        """Test version command when setup.py not found."""
        interaction = _make_interaction()
        mock_open.side_effect = FileNotFoundError()

        await self.commands["version"]["func"](interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        self.assertIn("embed", call_args.kwargs)
        # Should show error message
        self.assertIn("Error", call_args.kwargs["embed"].title)

    @patch("builtins.open")
    @patch("re.search")
    async def test_version_no_match(self, mock_search, mock_open):
        """Test version command when version not found in file."""
        interaction = _make_interaction()
        mock_search.return_value = None
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = 'no version here'
        mock_open.return_value = mock_file

        await self.commands["version"]["func"](interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        self.assertIn("embed", call_args.kwargs)
        self.assertIn("Error", call_args.kwargs["embed"].title)


class TestBookAutocompleteAdvanced(unittest.IsolatedAsyncioTestCase):
    """Additional tests for book autocomplete edge cases."""

    async def test_book_autocomplete_empty_title(self):
        """Test autocomplete handles missing title gracefully."""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.client.api = AsyncMock()
        interaction.client.api.search_books.return_value = [
            {
                "external_google_id": "abc123",
                "title": "",  # Empty title
                "author": "Frank Herbert"
            }
        ]

        from cogs.admin_commands import book_autocomplete
        choices = await book_autocomplete(interaction, "dune")

        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].name, " — Frank Herbert")

    async def test_book_autocomplete_missing_author(self):
        """Test autocomplete handles missing author."""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.client.api = AsyncMock()
        interaction.client.api.search_books.return_value = [
            {
                "external_google_id": "abc123",
                "title": "Unknown Book",
                "author": ""  # Empty author
            }
        ]

        from cogs.admin_commands import book_autocomplete
        choices = await book_autocomplete(interaction, "unknown")

        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].name, "Unknown Book")

    async def test_book_autocomplete_none_values(self):
        """Test autocomplete handles None values."""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.client.api = AsyncMock()
        interaction.client.api.search_books.return_value = [
            {
                "external_google_id": "abc123",
                "title": "Book",
                "author": None  # None author
            }
        ]

        from cogs.admin_commands import book_autocomplete
        choices = await book_autocomplete(interaction, "book")

        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].name, "Book")


class TestDiscussionCommands(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()
        self.club = _club_with_admin("111")
        self.session_with_discussions = {
            "id": "sess-1",
            "discussions": [
                {"id": "disc-1", "title": "Chapters 1-5", "date": "2026-06-01", "location": "Discord"},
                {"id": "disc-2", "title": "Chapters 6-10", "date": "2026-06-15"},
            ]
        }

    # ── discussion_add ────────────────────────────────────────────────────────

    async def test_discussion_add_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_session.return_value = {"success": True}
        await self.commands["discussion_add"]["func"](
            interaction, title="Chapters 1-5", date="2026-06-01", location="Discord"
        )
        self.bot.api.update_session.assert_called_once_with(
            "sess-1", {"discussions": [{"title": "Chapters 1-5", "date": "2026-06-01", "location": "Discord"}]}
        )
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_discussion_add_no_location(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_session.return_value = {"success": True}
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01"
        )
        self.bot.api.update_session.assert_called_once_with(
            "sess-1", {"discussions": [{"title": "Intro", "date": "2026-06-01"}]}
        )

    async def test_discussion_add_invalid_date(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="06/01/2026"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_discussion_add_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_discussion_add_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_discussion_add_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_session.side_effect = APIError("failed")
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    # ── discussion_update ─────────────────────────────────────────────────────

    async def test_discussion_update_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = self.session_with_discussions
        self.bot.api.update_session.return_value = {"success": True}
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", title="Updated Title"
        )
        self.bot.api.update_session.assert_called_once_with(
            "sess-1",
            {"discussions": [{"id": "disc-1", "title": "Updated Title", "date": "2026-06-01", "location": "Discord"}]}
        )
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_discussion_update_no_args(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_discussion_update_invalid_date(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", date="01-06-2026"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_discussion_update_not_found(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = self.session_with_discussions
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-999", title="New Title"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_discussion_update_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", title="New"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_discussion_update_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", title="New"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_discussion_update_api_error_on_get(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.side_effect = APIError("get failed")
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", title="New"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_discussion_update_api_error_on_update(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = self.session_with_discussions
        self.bot.api.update_session.side_effect = APIError("update failed")
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", title="New"
        )
        self.assertIn("❌", interaction.followup.send.call_args.args[0])

    # ── discussion_delete ─────────────────────────────────────────────────────

    async def test_discussion_delete_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_session.return_value = {"success": True}
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["discussion_delete"]["func"](interaction, discussion_id="disc-1")
        self.bot.api.update_session.assert_called_once_with(
            "sess-1", {"discussion_ids_to_delete": ["disc-1"]}
        )
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_discussion_delete_cancelled(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        with patch.object(discord.ui.View, "wait", _no_confirm()):
            await self.commands["discussion_delete"]["func"](interaction, discussion_id="disc-1")
        self.bot.api.update_session.assert_not_called()
        self.assertIn("cancelled", interaction.followup.send.call_args.args[0])

    async def test_discussion_delete_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_delete"]["func"](interaction, discussion_id="disc-1")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_discussion_delete_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["discussion_delete"]["func"](interaction, discussion_id="disc-1")
        self.assertIn("❌", interaction.followup.send.call_args.args[0])
        self.bot.api.update_session.assert_not_called()

    async def test_discussion_delete_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_session.side_effect = APIError("delete failed")
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["discussion_delete"]["func"](interaction, discussion_id="disc-1")
        self.assertIn("❌", interaction.followup.send.call_args_list[-1].args[0])


class TestDiscussionAutocomplete(unittest.IsolatedAsyncioTestCase):
    async def test_returns_choices_for_active_session(self):
        interaction = AsyncMock()
        interaction.channel_id = 999
        interaction.guild_id = 888
        interaction.client = MagicMock()
        interaction.client.api.find_club_in_channel.return_value = {
            "id": "club-1",
            "active_session": {"id": "sess-1"}
        }
        interaction.client.api.get_session.return_value = {
            "discussions": [
                {"id": "disc-1", "title": "Chapters 1-5", "date": "2026-06-01"},
                {"id": "disc-2", "title": "Chapters 6-10", "date": "2026-06-15"},
            ]
        }

        from cogs.admin_commands import discussion_autocomplete
        choices = await discussion_autocomplete(interaction, "")
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0].value, "disc-1")
        self.assertEqual(choices[1].value, "disc-2")

    async def test_filters_by_current_text(self):
        interaction = AsyncMock()
        interaction.channel_id = 999
        interaction.guild_id = 888
        interaction.client = MagicMock()
        interaction.client.api.find_club_in_channel.return_value = {
            "id": "club-1",
            "active_session": {"id": "sess-1"}
        }
        interaction.client.api.get_session.return_value = {
            "discussions": [
                {"id": "disc-1", "title": "Chapters 1-5", "date": "2026-06-01"},
                {"id": "disc-2", "title": "Final meeting", "date": "2026-07-01"},
            ]
        }

        from cogs.admin_commands import discussion_autocomplete
        choices = await discussion_autocomplete(interaction, "final")
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].value, "disc-2")

    async def test_returns_empty_when_no_club(self):
        interaction = AsyncMock()
        interaction.channel_id = 999
        interaction.guild_id = 888
        interaction.client = MagicMock()
        interaction.client.api.find_club_in_channel.return_value = None

        from cogs.admin_commands import discussion_autocomplete
        choices = await discussion_autocomplete(interaction, "")
        self.assertEqual(choices, [])

    async def test_returns_empty_when_no_active_session(self):
        interaction = AsyncMock()
        interaction.channel_id = 999
        interaction.guild_id = 888
        interaction.client = MagicMock()
        interaction.client.api.find_club_in_channel.return_value = {
            "id": "club-1",
            "active_session": None
        }

        from cogs.admin_commands import discussion_autocomplete
        choices = await discussion_autocomplete(interaction, "")
        self.assertEqual(choices, [])

    async def test_returns_empty_on_exception(self):
        interaction = AsyncMock()
        interaction.channel_id = 999
        interaction.guild_id = 888
        interaction.client = MagicMock()
        interaction.client.api.find_club_in_channel.side_effect = Exception("API down")

        from cogs.admin_commands import discussion_autocomplete
        choices = await discussion_autocomplete(interaction, "")
        self.assertEqual(choices, [])


if __name__ == "__main__":
    unittest.main()

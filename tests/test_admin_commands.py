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
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.get_member_by_discord_id.return_value = None
        self.bot.api.create_member.return_value = {"member": {"id": 1, "name": "Test User"}}
        self.bot.api.create_club.return_value = {"success": True}
        await self.commands["setup"]["func"](interaction, club_name="My Book Club")
        self.bot.api.create_club.assert_called_once()
        call_kwargs = self.bot.api.create_club.call_args[0][0]
        self.assertEqual(call_kwargs["name"], "My Book Club")
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.assertEqual(interaction.followup.send.call_args.kwargs["ephemeral"], False)

    async def test_setup_success_existing_member(self):
        interaction = _make_interaction()
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.get_member_by_discord_id.return_value = {"id": 99, "name": "Test User"}
        self.bot.api.create_club.return_value = {"success": True}
        await self.commands["setup"]["func"](interaction, club_name="Reader Club")
        self.bot.api.create_member.assert_not_called()
        self.bot.api.create_club.assert_called_once()
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.assertEqual(interaction.followup.send.call_args.kwargs["ephemeral"], False)

    async def test_setup_server_already_registered(self):
        interaction = _make_interaction()
        self.bot.api.register_server.side_effect = APIError("server already registered")
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.get_member_by_discord_id.return_value = {"id": 99, "name": "Test User"}
        self.bot.api.create_club.return_value = {"success": True}
        await self.commands["setup"]["func"](interaction, club_name="Reader Club")
        # should continue to club creation despite the error
        self.bot.api.create_club.assert_called_once()

    async def test_setup_channel_collision(self):
        interaction = _make_interaction()
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.api.find_club_in_channel.return_value = {"id": "club-1", "name": "Existing Club"}
        self.bot.api.get_member_by_discord_id.return_value = {"id": 99, "name": "Test User"}
        await self.commands["setup"]["func"](interaction, club_name="My Book Club")
        self.bot.api.create_club.assert_not_called()
        # Check response.send_message was called with ephemeral=True
        interaction.response.send_message.assert_called_once()
        self.assertIn("embed", interaction.response.send_message.call_args.kwargs)
        self.assertEqual(interaction.response.send_message.call_args.kwargs["ephemeral"], True)

    async def test_setup_register_fails(self):
        interaction = _make_interaction()
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.register_server.side_effect = APIError("connection refused")
        await self.commands["setup"]["func"](interaction, club_name="Test Club")
        self.bot.api.create_club.assert_not_called()
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_setup_create_club_api_error(self):
        interaction = _make_interaction()
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.api.get_member_by_discord_id.return_value = {"id": 99, "name": "Test User"}
        self.bot.api.create_club.side_effect = APIError("club creation failed")
        await self.commands["setup"]["func"](interaction, club_name="Sci-Fi Club")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)


class TestLinkClubCommand(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()
        self.club_id = "club-uuid-1"

    def _make_club(self, discord_channel=None):
        return {
            "id": self.club_id,
            "name": "Dashboard Club",
            "discord_channel": discord_channel,
        }

    def _make_caller(self, role=None):
        clubs = []
        if role:
            clubs = [{"id": self.club_id, "name": "Dashboard Club", "role": role}]
        return {"id": 42, "name": "Test User", "discord_id": "111", "clubs": clubs}

    async def test_link_club_success_owner(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.get_club_by_uuid.return_value = self._make_club()
        self.bot.api.get_member_by_discord_id.return_value = self._make_caller(role="owner")
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.api.update_club.return_value = {"success": True}

        await self.commands["link_club"]["func"](interaction, club_id=self.club_id)

        self.bot.api.update_club.assert_called_once()
        call_args = self.bot.api.update_club.call_args[0]
        self.assertEqual(call_args[0], self.club_id)
        self.assertIn("discord_channel", call_args[1])
        interaction.followup.send.assert_called_once()
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_link_club_success_admin(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.get_club_by_uuid.return_value = self._make_club()
        self.bot.api.get_member_by_discord_id.return_value = self._make_caller(role="admin")
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.api.update_club.return_value = {"success": True}

        await self.commands["link_club"]["func"](interaction, club_id=self.club_id)

        self.bot.api.update_club.assert_called_once()

    async def test_link_club_club_not_found(self):
        interaction = _make_interaction()
        self.bot.api.get_club_by_uuid.side_effect = ResourceNotFoundError("club", "bad-id")

        await self.commands["link_club"]["func"](interaction, club_id="bad-id")

        self.bot.api.update_club.assert_not_called()
        msg = interaction.followup.send.call_args
        self.assertIn("❌", msg.args[0] if msg.args else str(msg.kwargs))

    async def test_link_club_already_linked(self):
        interaction = _make_interaction()
        self.bot.api.get_club_by_uuid.return_value = self._make_club(discord_channel="999")

        await self.commands["link_club"]["func"](interaction, club_id=self.club_id)

        self.bot.api.update_club.assert_not_called()
        msg = interaction.followup.send.call_args
        self.assertIn("❌", msg.args[0] if msg.args else str(msg.kwargs))

    async def test_link_club_discord_not_linked(self):
        interaction = _make_interaction()
        self.bot.api.get_club_by_uuid.return_value = self._make_club()
        self.bot.api.get_member_by_discord_id.return_value = None

        await self.commands["link_club"]["func"](interaction, club_id=self.club_id)

        self.bot.api.update_club.assert_not_called()
        msg = interaction.followup.send.call_args
        self.assertIn("❌", msg.args[0] if msg.args else str(msg.kwargs))

    async def test_link_club_insufficient_role_member(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.get_club_by_uuid.return_value = self._make_club()
        self.bot.api.get_member_by_discord_id.return_value = self._make_caller(role="member")

        await self.commands["link_club"]["func"](interaction, club_id=self.club_id)

        self.bot.api.update_club.assert_not_called()
        msg = interaction.followup.send.call_args
        self.assertIn("❌", msg.args[0] if msg.args else str(msg.kwargs))

    async def test_link_club_insufficient_role_not_in_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.get_club_by_uuid.return_value = self._make_club()
        self.bot.api.get_member_by_discord_id.return_value = self._make_caller(role=None)

        await self.commands["link_club"]["func"](interaction, club_id=self.club_id)

        self.bot.api.update_club.assert_not_called()

    async def test_link_club_register_server_idempotent(self):
        """register_server raising a duplicate error should not abort the flow."""
        interaction = _make_interaction(user_id="111")
        self.bot.api.get_club_by_uuid.return_value = self._make_club()
        self.bot.api.get_member_by_discord_id.return_value = self._make_caller(role="owner")
        self.bot.api.register_server.side_effect = APIError("409 already exists")
        self.bot.api.update_club.return_value = {"success": True}

        await self.commands["link_club"]["func"](interaction, club_id=self.club_id)

        self.bot.api.update_club.assert_called_once()

    async def test_link_club_register_server_hard_fail(self):
        """A non-duplicate register_server error should abort."""
        interaction = _make_interaction(user_id="111")
        self.bot.api.get_club_by_uuid.return_value = self._make_club()
        self.bot.api.get_member_by_discord_id.return_value = self._make_caller(role="owner")
        self.bot.api.register_server.side_effect = APIError("connection refused")

        await self.commands["link_club"]["func"](interaction, club_id=self.club_id)

        self.bot.api.update_club.assert_not_called()

    async def test_link_club_update_fails(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.get_club_by_uuid.return_value = self._make_club()
        self.bot.api.get_member_by_discord_id.return_value = self._make_caller(role="owner")
        self.bot.api.register_server.return_value = {"success": True}
        self.bot.api.update_club.side_effect = APIError("update failed")

        await self.commands["link_club"]["func"](interaction, club_id=self.club_id)

        msg = interaction.followup.send.call_args
        content = msg.args[0] if msg.args else str(msg.kwargs)
        self.assertIn("❌", content)

    async def test_link_club_fetch_api_error(self):
        interaction = _make_interaction()
        self.bot.api.get_club_by_uuid.side_effect = APIError("server error")

        await self.commands["link_club"]["func"](interaction, club_id=self.club_id)

        self.bot.api.update_club.assert_not_called()


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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_server_delete_cancelled(self):
        interaction = _make_interaction()
        with patch.object(discord.ui.View, "wait", _no_confirm()):
            await self.commands["server_delete"]["func"](interaction)
        self.bot.api.delete_server.assert_not_called()
        # Check for cancellation message in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("cancelled", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)


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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_club_create_denied_when_no_club(self):
        interaction = _make_interaction(user_id="111", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["club_create"]["func"](interaction, name="New Club")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_club_create_denied_when_role_is_member(self):
        interaction = _make_interaction(user_id="111", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = {
            "id": "club-1",
            "name": "Test Club",
            "members": [{"discord_id": "111", "role": "member"}],
        }
        await self.commands["club_create"]["func"](interaction, name="New Club")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("already hosting", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.create_club.assert_not_called()

    async def test_club_create_empty_name(self):
        interaction = _make_interaction(user_id="111")
        await self.commands["club_create"]["func"](interaction, name="")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.create_club.assert_not_called()

    async def test_club_create_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        self.bot.api.get_member_by_discord_id.return_value = {"id": 99, "name": "Alice"}
        self.bot.api.create_club.side_effect = APIError("server error")
        await self.commands["club_create"]["func"](interaction, name="Sci-Fi Club")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_club.assert_not_called()

    async def test_club_update_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["club_update"]["func"](interaction, name="X")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_club.assert_not_called()

    async def test_club_update_no_club_in_channel(self):
        interaction = _make_interaction(user_id="111", is_owner=True)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["club_update"]["func"](interaction, name="X")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_club_update_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_club.side_effect = APIError("update failed")
        await self.commands["club_update"]["func"](interaction, name="New Name")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_club_delete_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["club_delete"]["func"](interaction)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.delete_club.assert_not_called()

    async def test_club_delete_no_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["club_delete"]["func"](interaction)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.delete_club.assert_not_called()

    async def test_club_delete_cancelled(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        with patch.object(discord.ui.View, "wait", _no_confirm()):
            await self.commands["club_delete"]["func"](interaction)
        self.bot.api.delete_club.assert_not_called()
        # Check for cancellation message in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("cancelled", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)


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
        new_member.name = "alice_handle"
        new_member.display_avatar.url = "https://discord.com/avatar/222"
        await self.commands["member_add"]["func"](interaction, member=new_member)
        call_args = self.bot.api.create_member.call_args[0][0]
        self.assertEqual(call_args["name"], "Alice")
        self.assertEqual(call_args["discord_id"], "222")
        self.assertEqual(call_args["handle"], "alice_handle")
        self.assertEqual(call_args["clubs"], ["club-1"])

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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.create_member.assert_not_called()

    async def test_member_add_no_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        new_member = MagicMock()
        new_member.id = 222
        await self.commands["member_add"]["func"](interaction, member=new_member)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_member_remove_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member_by_discord_id.return_value = {"id": 42, "clubs": [{"id": "club-1"}]}
        self.bot.api.delete_member.side_effect = APIError("delete failed")

        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            member = MagicMock()
            member.id = 42
            await self.commands["member_remove"]["func"](interaction, member=member)
        self.assertIn("❌", interaction.followup.send.call_args_list[-1].args[0])

    async def test_member_remove_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        member = MagicMock()
        member.id = 42
        await self.commands["member_remove"]["func"](interaction, member=member)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.delete_member.assert_not_called()

    async def test_member_remove_no_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        member = MagicMock()
        member.id = 42
        await self.commands["member_remove"]["func"](interaction, member=member)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.delete_member.assert_not_called()

    async def test_member_remove_not_in_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member_by_discord_id.return_value = {"id": 42, "clubs": [{"id": "club-other"}]}
        member = MagicMock()
        member.id = 42
        await self.commands["member_remove"]["func"](interaction, member=member)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.delete_member.assert_not_called()

    async def test_member_remove_not_found(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member_by_discord_id.side_effect = ResourceNotFoundError("not found")
        member = MagicMock()
        member.id = 42
        await self.commands["member_remove"]["func"](interaction, member=member)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.delete_member.assert_not_called()

    async def test_member_remove_cancelled(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member_by_discord_id.return_value = {"id": 42, "clubs": [{"id": "club-1"}]}
        with patch.object(discord.ui.View, "wait", _no_confirm()):
            member = MagicMock()
            member.id = 42
            await self.commands["member_remove"]["func"](interaction, member=member)
        self.bot.api.delete_member.assert_not_called()
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_member_remove_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member_by_discord_id.return_value = {"id": 42, "clubs": [{"id": "club-1"}]}
        self.bot.api.delete_member.return_value = {"success": True}
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            member = MagicMock()
            member.id = 42
            await self.commands["member_remove"]["func"](interaction, member=member)
        self.bot.api.delete_member.assert_called_once_with(42)
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_member_role_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_member_by_discord_id.return_value = {"id": 42}
        self.bot.api.update_member.return_value = {"success": True}
        member = MagicMock()
        member.id = 42
        await self.commands["member_role"]["func"](interaction, member=member, role="admin")
        self.bot.api.update_member.assert_called_once_with(
            42, {"club_roles": {"club-1": "admin"}}
        )
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_member_role_no_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        member = MagicMock()
        member.id = 42
        await self.commands["member_role"]["func"](interaction, member=member, role="member")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_member.assert_not_called()

    async def test_member_role_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_member.side_effect = APIError("update failed")
        member = MagicMock()
        member.id = 42
        await self.commands["member_role"]["func"](interaction, member=member, role="member")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)


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
        self.bot.api.search_books = AsyncMock(return_value=[{"external_google_id": "gid-123", "title": "Dune", "author": "Frank Herbert"}])
        self.bot.api.register_book = AsyncMock(return_value={"id": 42, "title": "Dune", "author": "Frank Herbert"})
        self.bot.api.create_session.return_value = {"success": True}
        await self.commands["session_create"]["func"](
            interaction,
            book="gid-123|Dune|Frank Herbert",
            due_date="2026-06-15"
        )
        # Check that register_book was called with the right positional args and external_google_id
        call_args = self.bot.api.register_book.call_args
        self.assertEqual(call_args[0], ("Dune", "Frank Herbert"))  # positional args
        self.assertEqual(call_args[1]["external_google_id"], "gid-123")
        self.bot.api.create_session.assert_called_once_with({
            "club_id": "club-1",
            "book_id": 42,
            "due_date": "2026-06-15",
        })

    async def test_session_create_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["session_create"]["func"](
            interaction,
            book="gid-123|Dune|Herbert",
            due_date="2026-06-15"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.create_session.assert_not_called()

    async def test_session_create_no_club(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = None
        with self.assertRaises(APIError):
            await self.commands["session_create"]["func"](
                interaction,
                book="gid-123|Dune|Herbert",
                due_date="2026-06-15"
            )
        self.bot.api.create_session.assert_not_called()

    async def test_session_create_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.search_books = AsyncMock(return_value=[{"external_google_id": "gid-123", "title": "Dune", "author": "Frank Herbert"}])
        self.bot.api.register_book = AsyncMock(return_value={"id": 42, "title": "Dune", "author": "Frank Herbert"})
        self.bot.api.create_session.side_effect = APIError("failed")
        with self.assertRaises(APIError):
            await self.commands["session_create"]["func"](
                interaction,
                book="gid-123|Dune|Frank Herbert",
                due_date="2026-06-15"
            )

    async def test_session_create_invalid_date_format(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["session_create"]["func"](
            interaction,
            book="gid-123|Dune|Frank Herbert",
            due_date="2026/06/15"  # Wrong format
        )
        self.assertIn("❌ Due date must be in **YYYY-MM-DD** format", interaction.followup.send.call_args.args[0])
        self.bot.api.create_session.assert_not_called()

    async def test_session_create_invalid_book_format(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["session_create"]["func"](
            interaction,
            book="invalid",  # Missing pipes
            due_date="2026-06-15"
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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_session.assert_not_called()

    async def test_session_update_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = None
        await self.commands["session_update"]["func"](interaction, due_date="2026-06-01")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_session.assert_not_called()

    async def test_session_update_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["session_update"]["func"](interaction, due_date="2026-06-01")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_session.assert_not_called()

    async def test_session_update_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.update_session.side_effect = APIError("update failed")
        await self.commands["session_update"]["func"](interaction, due_date="2026-06-01")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

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
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.delete_session.assert_not_called()

    async def test_session_delete_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["session_delete"]["func"](interaction)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.delete_session.assert_not_called()

    async def test_session_delete_cancelled(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        with patch.object(discord.ui.View, "wait", _no_confirm()):
            await self.commands["session_delete"]["func"](interaction)
        self.bot.api.delete_session.assert_not_called()
        # Check for cancellation message in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("cancelled", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_session_delete_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.delete_session.return_value = {"success": True}
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["session_delete"]["func"](interaction)
        self.bot.api.delete_session.assert_called_once_with("sess-1")
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    # ── session_finish tests ──────────────────────────────────────────────────

    def _club_with_members(self, user_id="111"):
        """Club whose active session has members with explicit is_reading flags."""
        return {
            "id": "club-1",
            "name": "Test Club",
            "discord_channel": "999",
            "members": [{"discord_id": str(user_id), "role": "admin"}],
            "active_session": {
                "id": "sess-1",
                "book": {"title": "Dune"},
                "members": [
                    {"member_id": 1, "is_reading": True},
                    {"member_id": 2, "is_reading": False},
                    {"member_id": 3, "is_reading": True},
                ],
            },
        }

    async def test_session_finish_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self._club_with_members()
        self.bot.api.finish_session.return_value = {
            "success": True,
            "members_credited": 2,
        }
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["session_finish"]["func"](interaction)
        self.bot.api.finish_session.assert_called_once_with("sess-1")
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_session_finish_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["session_finish"]["func"](interaction)
        self.bot.api.finish_session.assert_not_called()
        last_call = interaction.followup.send.call_args
        self.assertIn("❌", last_call.args[0] if last_call.args else "")

    async def test_session_finish_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["session_finish"]["func"](interaction)
        self.bot.api.finish_session.assert_not_called()
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_session_finish_club_lookup_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.side_effect = APIError("network failure")
        await self.commands["session_finish"]["func"](interaction)
        self.bot.api.finish_session.assert_not_called()
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])

    async def test_session_finish_cancelled(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self._club_with_members()
        with patch.object(discord.ui.View, "wait", _no_confirm()):
            await self.commands["session_finish"]["func"](interaction)
        self.bot.api.finish_session.assert_not_called()

    async def test_session_finish_already_finished_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self._club_with_members()
        self.bot.api.finish_session.side_effect = APIError("Session is already finished")
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["session_finish"]["func"](interaction)
        last_msg = interaction.followup.send.call_args_list[-1].args[0]
        self.assertIn("already finished", last_msg.lower())

    async def test_session_finish_generic_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self._club_with_members()
        self.bot.api.finish_session.side_effect = APIError("unexpected server error")
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["session_finish"]["func"](interaction)
        last_msg = interaction.followup.send.call_args_list[-1].args[0]
        self.assertIn("❌", last_msg)

    async def test_session_finish_reading_count_uses_true_default(self):
        """Members missing is_reading default to True (matches DB column DEFAULT true)."""
        interaction = _make_interaction(user_id="111")
        club = self._club_with_members()
        # Add a member with no is_reading field — DB defaults it to true, so count it
        club["active_session"]["members"].append({"member_id": 4})
        self.bot.api.find_club_in_channel.return_value = club
        self.bot.api.finish_session.return_value = {"success": True, "members_credited": 3}

        captured_prompt = []

        async def capture_wait(self_view):
            call_args = interaction.followup.send.call_args
            if call_args and call_args.args:
                captured_prompt.append(call_args.args[0])
            self_view.confirmed = True

        with patch.object(discord.ui.View, "wait", capture_wait):
            await self.commands["session_finish"]["func"](interaction)

        # 2 explicit True + 1 missing field (defaults True) = 3 in the prompt
        self.assertTrue(any("3 member" in p for p in captured_prompt),
                        f"Expected '3 member' in prompt, got: {captured_prompt}")


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
        self.bot.api.create_discussion.return_value = {
            "id": "disc-new", "title": "Chapters 1-5", "date": "2026-06-01", "location": "Discord"
        }
        interaction.guild.create_scheduled_event = AsyncMock()
        await self.commands["discussion_add"]["func"](
            interaction, title="Chapters 1-5", date="2026-06-01", time="18:00"
        )
        self.bot.api.create_discussion.assert_called_once_with(
            {"session_id": "sess-1", "title": "Chapters 1-5", "date": "2026-06-01", "time": "18:00:00", "location": "Discord"}
        )
        interaction.guild.create_scheduled_event.assert_called_once()
        call_kwargs = interaction.guild.create_scheduled_event.call_args.kwargs
        self.assertIn("discussion_id:disc-new", call_kwargs["description"])
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_discussion_add_embeds_id_in_event_description(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.create_discussion.return_value = {"id": "disc-abc", "title": "Intro", "date": "2026-06-01"}
        interaction.guild.create_scheduled_event = AsyncMock()
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01", time="18:00"
        )
        desc = interaction.guild.create_scheduled_event.call_args.kwargs["description"]
        self.assertIn("discussion_id:disc-abc", desc)

    async def test_discussion_add_event_created_without_id_when_response_lacks_id(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.create_discussion.return_value = {"title": "Intro", "date": "2026-06-01"}
        interaction.guild.create_scheduled_event = AsyncMock()
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01", time="18:00"
        )
        # Event should still be created, just without an embedded ID
        interaction.guild.create_scheduled_event.assert_called_once()
        desc = interaction.guild.create_scheduled_event.call_args.kwargs["description"]
        self.assertNotIn("discussion_id:", desc)

    async def test_discussion_add_custom_location(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.create_discussion.return_value = {"id": "disc-new"}
        interaction.guild.create_scheduled_event = AsyncMock()
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01", time="19:00", location="Library"
        )
        self.bot.api.create_discussion.assert_called_once_with(
            {"session_id": "sess-1", "title": "Intro", "date": "2026-06-01", "time": "19:00:00", "location": "Library"}
        )
        call_kwargs = interaction.guild.create_scheduled_event.call_args.kwargs
        self.assertEqual(call_kwargs["location"], "Library")

    async def test_discussion_add_default_location_is_discord(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.create_discussion.return_value = {"id": "disc-new"}
        interaction.guild.create_scheduled_event = AsyncMock()
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01", time="18:00"
        )
        saved = self.bot.api.create_discussion.call_args.args[0]
        self.assertEqual(saved["location"], "Discord")
        call_kwargs = interaction.guild.create_scheduled_event.call_args.kwargs
        self.assertEqual(call_kwargs["location"], "Discord")

    async def test_discussion_add_invalid_date(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="06/01/2026", time="18:00"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.create_discussion.assert_not_called()

    async def test_discussion_add_invalid_time(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01", time="6pm"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.create_discussion.assert_not_called()

    async def test_discussion_add_invalid_duration(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01", time="18:00", duration=0
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.create_discussion.assert_not_called()

    async def test_discussion_add_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01", time="18:00"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.create_discussion.assert_not_called()

    async def test_discussion_add_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01", time="18:00"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.create_discussion.assert_not_called()

    async def test_discussion_add_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.create_discussion.side_effect = APIError("failed")
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01", time="18:00"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_discussion_add_forbidden_warns_but_succeeds(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.create_discussion.return_value = {"id": "disc-new"}
        interaction.guild.create_scheduled_event = AsyncMock(
            side_effect=discord.Forbidden(MagicMock(), "Missing Permissions")
        )
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01", time="18:00"
        )
        self.bot.api.create_discussion.assert_called_once()
        embed = interaction.followup.send.call_args.kwargs["embed"]
        self.assertIn("Manage Events", embed.description)

    async def test_discussion_add_http_exception_warns_but_succeeds(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.create_discussion.return_value = {"id": "disc-new"}
        interaction.guild.create_scheduled_event = AsyncMock(
            side_effect=discord.HTTPException(MagicMock(), "Bad Request")
        )
        await self.commands["discussion_add"]["func"](
            interaction, title="Intro", date="2026-06-01", time="18:00"
        )
        self.bot.api.create_discussion.assert_called_once()
        embed = interaction.followup.send.call_args.kwargs["embed"]
        self.assertIn("Discord event creation failed", embed.description)

    # ── discussion_update ─────────────────────────────────────────────────────

    async def test_discussion_update_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = self.session_with_discussions
        self.bot.api.update_discussion.return_value = {"success": True}
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", title="Updated Title"
        )
        self.bot.api.update_discussion.assert_called_once_with(
            "disc-1",
            {"title": "Updated Title", "date": "2026-06-01", "location": "Discord"}
        )
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_discussion_update_no_args(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_discussion.assert_not_called()

    async def test_discussion_update_invalid_date(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", date="01-06-2026"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_discussion.assert_not_called()

    async def test_discussion_update_not_found(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = self.session_with_discussions
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-999", title="New Title"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_discussion.assert_not_called()

    async def test_discussion_update_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", title="New"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_discussion.assert_not_called()

    async def test_discussion_update_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", title="New"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_discussion.assert_not_called()

    async def test_discussion_update_api_error_on_get(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.side_effect = APIError("get failed")
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", title="New"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.update_discussion.assert_not_called()

    async def test_discussion_update_api_error_on_update(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = self.session_with_discussions
        self.bot.api.update_discussion.side_effect = APIError("update failed")
        await self.commands["discussion_update"]["func"](
            interaction, discussion_id="disc-1", title="New"
        )
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    # ── discussion_delete ─────────────────────────────────────────────────────

    async def test_discussion_delete_success(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.delete_discussion.return_value = {"success": True}
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["discussion_delete"]["func"](interaction, discussion_id="disc-1")
        self.bot.api.delete_discussion.assert_called_once_with("disc-1")
        self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_discussion_delete_cancelled(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        with patch.object(discord.ui.View, "wait", _no_confirm()):
            await self.commands["discussion_delete"]["func"](interaction, discussion_id="disc-1")
        self.bot.api.delete_discussion.assert_not_called()
        # Check for cancellation message in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("cancelled", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_discussion_delete_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_delete"]["func"](interaction, discussion_id="disc-1")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.delete_discussion.assert_not_called()

    async def test_discussion_delete_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["discussion_delete"]["func"](interaction, discussion_id="disc-1")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.bot.api.delete_discussion.assert_not_called()

    async def test_discussion_delete_api_error(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.delete_discussion.side_effect = APIError("delete failed")
        with patch.object(discord.ui.View, "wait", _auto_confirm()):
            await self.commands["discussion_delete"]["func"](interaction, discussion_id="disc-1")
        self.assertIn("❌", interaction.followup.send.call_args_list[-1].args[0])


class TestDiscussionSync(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot, self.commands = _make_bot()
        self.club = _club_with_admin("111")
        self.discussions = [
            {"id": "disc-1", "title": "Chapters 1-5", "date": "2026-06-01", "location": "Discord"},
            {"id": "disc-2", "title": "Chapters 6-10", "date": "2026-06-15"},
        ]

    def _make_event(self, description=""):
        event = MagicMock()
        event.description = description
        return event

    async def test_sync_creates_missing_events(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = {"discussions": self.discussions}
        interaction.guild.fetch_scheduled_events = AsyncMock(return_value=[])
        interaction.guild.create_scheduled_event = AsyncMock()
        await self.commands["discussion_sync"]["func"](interaction)
        self.assertEqual(interaction.guild.create_scheduled_event.call_count, 2)
        embed = interaction.followup.send.call_args.kwargs["embed"]
        self.assertIn("Created 2", embed.description)

    async def test_sync_skips_already_covered_discussions(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = {"discussions": self.discussions}
        existing = self._make_event("Book club discussion: Chapters 1-5\ndiscussion_id:disc-1")
        interaction.guild.fetch_scheduled_events = AsyncMock(return_value=[existing])
        interaction.guild.create_scheduled_event = AsyncMock()
        await self.commands["discussion_sync"]["func"](interaction)
        self.assertEqual(interaction.guild.create_scheduled_event.call_count, 1)
        embed = interaction.followup.send.call_args.kwargs["embed"]
        self.assertIn("Created 1", embed.description)
        self.assertIn("Already had events", embed.description)

    async def test_sync_all_already_covered(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = {"discussions": self.discussions}
        existing = [
            self._make_event("discussion_id:disc-1"),
            self._make_event("discussion_id:disc-2"),
        ]
        interaction.guild.fetch_scheduled_events = AsyncMock(return_value=existing)
        interaction.guild.create_scheduled_event = AsyncMock()
        await self.commands["discussion_sync"]["func"](interaction)
        interaction.guild.create_scheduled_event.assert_not_called()
        embed = interaction.followup.send.call_args.kwargs["embed"]
        self.assertIn("Already had events", embed.description)

    async def test_sync_embeds_discussion_id_in_new_events(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = {"discussions": [self.discussions[0]]}
        interaction.guild.fetch_scheduled_events = AsyncMock(return_value=[])
        interaction.guild.create_scheduled_event = AsyncMock()
        await self.commands["discussion_sync"]["func"](interaction)
        desc = interaction.guild.create_scheduled_event.call_args.kwargs["description"]
        self.assertIn("discussion_id:disc-1", desc)

    async def test_sync_skips_discussions_with_unparseable_date(self):
        interaction = _make_interaction(user_id="111")
        bad_discussion = {"id": "disc-bad", "title": "Bad Date", "date": "sometime in June"}
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = {"discussions": [bad_discussion]}
        interaction.guild.fetch_scheduled_events = AsyncMock(return_value=[])
        interaction.guild.create_scheduled_event = AsyncMock()
        await self.commands["discussion_sync"]["func"](interaction)
        interaction.guild.create_scheduled_event.assert_not_called()
        embed = interaction.followup.send.call_args.kwargs["embed"]
        self.assertIn("Failed to create", embed.description)

    async def test_sync_no_discussions(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = {"discussions": []}
        await self.commands["discussion_sync"]["func"](interaction)
        self.assertIn("No discussions", interaction.followup.send.call_args.args[0])

    async def test_sync_permission_denied(self):
        interaction = _make_interaction(user_id="999", is_owner=False)
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_sync"]["func"](interaction)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_sync_no_session(self):
        interaction = _make_interaction(user_id="111")
        club_no_session = dict(self.club)
        club_no_session["active_session"] = None
        self.bot.api.find_club_in_channel.return_value = club_no_session
        await self.commands["discussion_sync"]["func"](interaction)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_sync_invalid_default_time(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_sync"]["func"](interaction, default_time="6pm")
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_sync_invalid_default_duration(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        await self.commands["discussion_sync"]["func"](interaction, default_duration=0)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)

    async def test_sync_forbidden_on_fetch_events(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.return_value = {"discussions": self.discussions}
        interaction.guild.fetch_scheduled_events = AsyncMock(
            side_effect=discord.Forbidden(MagicMock(), "Missing Permissions")
        )
        await self.commands["discussion_sync"]["func"](interaction)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)
        self.assertIn("Manage Events", interaction.followup.send.call_args.args[0])

    async def test_sync_api_error_on_get_session(self):
        interaction = _make_interaction(user_id="111")
        self.bot.api.find_club_in_channel.return_value = self.club
        self.bot.api.get_session.side_effect = APIError("unavailable")
        await self.commands["discussion_sync"]["func"](interaction)
        # Check for error in either positional or keyword arguments
        if interaction.followup.send.call_args.args:
            self.assertIn("❌", interaction.followup.send.call_args.args[0])
        else:
            self.assertIn("embed", interaction.followup.send.call_args.kwargs)


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

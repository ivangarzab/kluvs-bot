"""
Admin commands (version, server, club, member, session management)
"""
import re
import os
from typing import Literal
import discord
from discord import app_commands

from utils.embeds import create_embed
from api.bookclub_api import APIError, ResourceNotFoundError


def setup_admin_commands(bot):
    """
    Setup admin slash commands

    Args:
        bot: The bot instance
    """

    def _check_guild_admin(interaction: discord.Interaction):
        """Returns True if the user is the guild owner or has administrator/manage_guild permissions."""
        if interaction.user == interaction.guild.owner:
            return True
        perms = interaction.user.guild_permissions
        return perms.administrator or perms.manage_guild

    def _can_manage_clubs(interaction: discord.Interaction, club_data: dict):
        """Returns True if user is guild admin OR club admin in club_data."""
        if _check_guild_admin(interaction):
            return True
        if not club_data:
            return False
        for member in club_data.get("members", []):
            if str(member.get("discord_id")) == str(interaction.user.id):
                return member.get("role") in ("admin", "owner")
        return False

    async def _confirm(interaction: discord.Interaction, prompt: str):
        """Shows confirm/cancel buttons; returns True if confirmed."""

        class ConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.confirmed = False

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.red)
            async def confirm_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                if button_interaction.user.id != interaction.user.id:
                    await button_interaction.response.send_message("❌ You can't use this button.", ephemeral=True)
                    return
                self.confirmed = True
                for item in self.children:
                    item.disabled = True
                self.stop()
                await button_interaction.response.edit_message(view=self)

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                if button_interaction.user.id != interaction.user.id:
                    await button_interaction.response.send_message("❌ You can't use this button.", ephemeral=True)
                    return
                for item in self.children:
                    item.disabled = True
                self.stop()
                await button_interaction.response.edit_message(view=self)

        view = ConfirmView()
        await interaction.followup.send(prompt, view=view)
        await view.wait()
        return view.confirmed

    # ── Version ──────────────────────────────────────────────────────────────

    @bot.tree.command(name="version", description="Shows the current version of the bot")
    async def version(interaction: discord.Interaction):
        """Extracts and displays the current version from setup.py"""
        try:
            setup_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "setup.py")
            with open(setup_path, "r") as file:
                setup_content = file.read()

            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', setup_content)
            if version_match:
                v = version_match.group(1)
                embed = create_embed(
                    title=f"📚 Quill Bot version: v{v}",
                    color_key="blank",
                    timestamp=True
                )
                await interaction.response.send_message(embed=embed)
            else:
                embed = create_embed(
                    title="❌ Error",
                    description="Couldn't find version information in setup.py",
                    color_key="error"
                )
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Error retrieving version: {str(e)}",
                color_key="error"
            )
            await interaction.response.send_message(embed=embed)

    # ── Admin Help (guild owner or club admin+) ──────────────────────────────

    @bot.tree.command(name="admin_help", description="Show admin command reference")
    async def admin_help(interaction: discord.Interaction):
        """Display admin command reference for guild owners and club admins."""
        if not _check_guild_admin(interaction):
            channel_id = str(interaction.channel_id)
            club_data = bot.api.find_club_in_channel(channel_id, str(interaction.guild_id))
            if not _can_manage_clubs(interaction, club_data):
                await interaction.response.send_message(
                    "❌ You need to be a guild owner or club admin to use this command.",
                    ephemeral=True
                )
                return

        embed = create_embed(
            title="📖 Admin Commands Reference",
            description="Commands for managing your book club",
            color_key="info",
            fields=[
                {
                    "name": "🔧 Setup & Server",
                    "value": (
                        "`/setup` — First-run wizard: register server and create a club\n"
                        "`/server_register` — Register this Discord server\n"
                        "`/server_update` — Update server name\n"
                        "`/server_delete` — Delete server and all data"
                    ),
                    "inline": False
                },
                {
                    "name": "📚 Club Management",
                    "value": (
                        "`/club_create` — Create a new book club\n"
                        "`/club_update` — Update club details\n"
                        "`/club_delete` — Delete the club in this channel"
                    ),
                    "inline": False
                },
                {
                    "name": "👥 Member Management",
                    "value": (
                        "`/member_add` — Add a member to the club\n"
                        "`/member_remove` — Remove a member\n"
                        "`/member_role` — Set member role"
                    ),
                    "inline": False
                },
                {
                    "name": "📖 Session Management",
                    "value": (
                        "`/session_create` — Create a reading session\n"
                        "`/session_update` — Update session\n"
                        "`/session_delete` — Delete the active session"
                    ),
                    "inline": False
                },
                {
                    "name": "ℹ️ Other",
                    "value": "`/version` — Show bot version",
                    "inline": False
                }
            ],
            footer="Use a command name for more details via Discord's help menu"
        )
        await interaction.response.send_message(embed=embed)

    # ── Setup wizard (manage_guild permission only) ──────────────────────────

    @bot.tree.command(name="setup", description="First-run wizard: register server and create a book club")
    @app_commands.default_permissions(manage_guild=True)
    async def setup(interaction: discord.Interaction):
        """Guided onboarding for new servers."""
        await interaction.response.defer()
        guild_id = str(interaction.guild_id)

        try:
            bot.api.register_server(guild_id, interaction.guild.name)
        except APIError as e:
            if "already" in str(e).lower() or "duplicate" in str(e).lower():
                await interaction.followup.send("ℹ️ This server is already registered. Continuing to club setup…")
            else:
                await interaction.followup.send(f"❌ Failed to register server: {e}")
                return

        await interaction.followup.send("✅ Server registered! What should I call your book club?")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", timeout=60.0, check=check)
        except TimeoutError:
            await interaction.followup.send("⏰ Setup timed out. Run `/setup` again when you're ready.")
            return

        club_name = msg.content.strip()
        if not club_name:
            await interaction.followup.send("❌ Club name can't be empty. Run `/setup` again.")
            return

        channel_id = str(interaction.channel_id)

        if bot.api.find_club_in_channel(channel_id, guild_id):
            await interaction.followup.send(
                "❌ This channel is already hosting a book club. "
                "Please use a different channel or delete the existing club first."
            )
            return

        try:
            existing = bot.api.get_member_by_discord_id(str(interaction.user.id))
            if existing:
                caller = {"id": existing["id"], "name": existing["name"]}
            else:
                created = bot.api.create_member({
                    "name": interaction.user.display_name,
                    "discord_id": str(interaction.user.id),
                })
                member_data = created.get("member", created)
                caller = {"id": member_data["id"], "name": member_data["name"]}

            bot.api.create_club(
                {"name": club_name, "discord_channel": channel_id, "members": [caller]},
                guild_id
            )
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to create club: {e}")
            return

        embed = create_embed(
            title="🎉 You're all set!",
            description=(
                f"**{club_name}** has been created in {interaction.channel.mention}.\n\n"
                "**Available commands:**\n"
                "`/session` — view the current reading session\n"
                "`/book` — see the current book\n"
                "`/duedate` — check the due date\n"
                "`/discussions` — view scheduled discussions\n"
                "`/session_create` — start a new session\n"
                "`/member_add` — add members to the club"
            ),
            color_key="success",
            footer="Happy reading! 📖"
        )
        await interaction.followup.send(embed=embed)

    # ── Server commands (manage_guild permission only) ────────────────────────

    @bot.tree.command(name="server_register", description="Register this Discord server with the bot")
    @app_commands.default_permissions(manage_guild=True)
    async def server_register(interaction: discord.Interaction):
        """Registers the Discord server."""
        await interaction.response.defer()
        try:
            bot.api.register_server(str(interaction.guild_id), interaction.guild.name)
            embed = create_embed(
                title="✅ Server Registered",
                description=f"**{interaction.guild.name}** has been registered.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to register server: {e}")

    @bot.tree.command(name="server_update", description="Update this server's registered name")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(name="The new name for the server")
    async def server_update(interaction: discord.Interaction, name: str):
        """Updates the server's registered name."""
        await interaction.response.defer()
        try:
            bot.api.update_server(str(interaction.guild_id), name)
            embed = create_embed(
                title="✅ Server Updated",
                description=f"Server name updated to **{name}**.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to update server: {e}")

    @bot.tree.command(name="server_delete", description="Delete this server's registration and all data")
    @app_commands.default_permissions(manage_guild=True)
    async def server_delete(interaction: discord.Interaction):
        """Deletes the server registration and all associated data."""
        await interaction.response.defer()
        confirmed = await _confirm(
            interaction,
            "⚠️ This will delete **all server data** including clubs, members, and sessions. "
            "Click **Confirm** to proceed or **Cancel** to abort."
        )
        if not confirmed:
            await interaction.followup.send("Action cancelled.")
            return
        try:
            bot.api.delete_server(str(interaction.guild_id))
            embed = create_embed(
                title="✅ Server Deleted",
                description="Server registration and all associated data have been removed.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to delete server: {e}")

    # ── Club commands (club admin+) ───────────────────────────────────────────

    @bot.tree.command(name="club_create", description="Create a new book club in a channel")
    @app_commands.describe(
        name="The name of the new club",
        channel="The channel to create the club in (defaults to current channel)"
    )
    async def club_create(interaction: discord.Interaction, name: str, channel: discord.TextChannel = None):
        """Creates a new book club. Caller is automatically assigned as owner."""
        await interaction.response.defer()
        channel_id = str(channel.id) if channel else str(interaction.channel_id)
        guild_id = str(interaction.guild_id)

        if not name or not name.strip():
            await interaction.followup.send("❌ Please provide a club name.")
            return

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await interaction.followup.send(
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if club_data:
            await interaction.followup.send(
                "❌ This channel is already hosting a book club. "
                "Please use a different channel or delete the existing club first."
            )
            return
        try:
            existing = bot.api.get_member_by_discord_id(str(interaction.user.id))
            if existing:
                caller = {"id": existing["id"], "name": existing["name"]}
            else:
                created = bot.api.create_member({
                    "name": interaction.user.display_name,
                    "discord_id": str(interaction.user.id),
                })
                member_data = created.get("member", created)
                caller = {"id": member_data["id"], "name": member_data["name"]}

            bot.api.create_club(
                {"name": name, "discord_channel": channel_id, "members": [caller]},
                guild_id
            )
            embed = create_embed(
                title="✅ Club Created",
                description=f"Book club **{name}** created in <#{channel_id}>. You are the owner.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to create club: {e}")

    @bot.tree.command(name="club_update", description="Update the club name or discord channel")
    @app_commands.describe(
        name="The new club name",
        new_channel="The new channel to move the club to",
        channel="The channel containing the club to update (defaults to current channel)"
    )
    async def club_update(
        interaction: discord.Interaction,
        name: str = None,
        new_channel: discord.TextChannel = None,
        channel: discord.TextChannel = None
    ):
        """Updates club details."""
        await interaction.response.defer()
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await interaction.followup.send(
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data:
            await interaction.followup.send("❌ No book club found in that channel.")
            return

        update = {}
        if name and name.strip():
            update["name"] = name.strip()
        if new_channel:
            update["discord_channel"] = str(new_channel.id)
        if not update:
            await interaction.followup.send(
                "❌ Provide at least a new name or new channel."
            )
            return
        try:
            bot.api.update_club(club_data["id"], update, guild_id)
            embed = create_embed(
                title="✅ Club Updated",
                description="Club details updated successfully.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to update club: {e}")

    @bot.tree.command(name="club_delete", description="Delete the book club in a channel")
    @app_commands.describe(
        channel="The channel containing the club to delete (defaults to current channel)"
    )
    async def club_delete(interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Deletes a book club and all its data."""
        await interaction.response.defer()
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await interaction.followup.send(
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data:
            await interaction.followup.send("❌ No book club found in that channel.")
            return

        confirmed = await _confirm(
            interaction,
            f"⚠️ This will delete **{club_data['name']}** and all its data. "
            "Click **Confirm** to proceed or **Cancel** to abort."
        )
        if not confirmed:
            await interaction.followup.send("Action cancelled.")
            return
        try:
            bot.api.delete_club(club_data["id"], guild_id)
            embed = create_embed(
                title="✅ Club Deleted",
                description=f"**{club_data['name']}** has been deleted.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to delete club: {e}")

    # ── Member commands (club admin+) ─────────────────────────────────────────

    @bot.tree.command(name="member_add", description="Add a Discord user to a book club")
    @app_commands.describe(
        member="The member to add to the club",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def member_add(interaction: discord.Interaction, member: discord.Member, channel: discord.TextChannel = None):
        """Adds a mentioned Discord user to a club. Creates member record if needed."""
        await interaction.response.defer()
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await interaction.followup.send(
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data:
            await interaction.followup.send("❌ No book club found in that channel.")
            return
        try:
            existing = bot.api.get_member_by_discord_id(str(member.id))
            if existing:
                current_club_ids = [c["id"] for c in existing.get("clubs", [])]
                if club_data["id"] in current_club_ids:
                    await interaction.followup.send(f"**{member.display_name}** is already a member of this club.")
                    return
                bot.api.update_member(existing["id"], {"clubs": current_club_ids + [club_data["id"]]})
            else:
                bot.api.create_member({
                    "name": member.display_name,
                    "discord_id": str(member.id),
                    "clubs": [club_data["id"]]
                })
            embed = create_embed(
                title="✅ Member Added",
                description=f"**{member.display_name}** has been added to the club.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to add member: {e}")

    @bot.tree.command(name="member_remove", description="Remove a member from a book club")
    @app_commands.describe(
        member_id="The ID of the member to remove",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def member_remove(interaction: discord.Interaction, member_id: int, channel: discord.TextChannel = None):
        """Removes a member by their ID."""
        await interaction.response.defer()
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await interaction.followup.send(
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data:
            await interaction.followup.send("❌ No book club found in that channel.")
            return

        try:
            member_data = bot.api.get_member(member_id)
            member_club_ids = [c["id"] for c in member_data.get("clubs", [])]
            if club_data["id"] not in member_club_ids:
                await interaction.followup.send(f"❌ Member `{member_id}` is not in this club.")
                return
        except ResourceNotFoundError:
            await interaction.followup.send(f"❌ Member `{member_id}` not found.")
            return

        confirmed = await _confirm(
            interaction,
            f"⚠️ Remove member `{member_id}` from the club? "
            "Click **Confirm** to proceed or **Cancel** to abort."
        )
        if not confirmed:
            await interaction.followup.send("Action cancelled.")
            return
        try:
            bot.api.delete_member(member_id)
            embed = create_embed(
                title="✅ Member Removed",
                description=f"Member `{member_id}` has been removed.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to remove member: {e}")

    @bot.tree.command(name="member_role", description="Update a member's role in a club")
    @app_commands.describe(
        member_id="The ID of the member",
        role="The new role (admin or member)",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def member_role(
        interaction: discord.Interaction,
        member_id: int,
        role: Literal["admin", "member"],
        channel: discord.TextChannel = None
    ):
        """Sets a member's role to admin or member."""
        await interaction.response.defer()

        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await interaction.followup.send(
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data:
            await interaction.followup.send("❌ No book club found in that channel.")
            return
        try:
            bot.api.update_member(member_id, {"club_roles": {club_data["id"]: role}})
            embed = create_embed(
                title="✅ Role Updated",
                description=f"Member `{member_id}` is now **{role}**.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to update role: {e}")

    # ── Session commands (club admin+) ────────────────────────────────────────

    @bot.tree.command(name="session_create", description="Create a new reading session")
    @app_commands.describe(
        book_title="The title of the book",
        author="The author of the book",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def session_create(
        interaction: discord.Interaction,
        book_title: str,
        author: str,
        channel: discord.TextChannel = None
    ):
        """Creates a reading session for a club."""
        await interaction.response.defer()
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await interaction.followup.send(
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data:
            await interaction.followup.send("❌ No book club found in that channel.")
            return
        try:
            bot.api.create_session({
                "club_id": club_data["id"],
                "book": {"title": book_title, "author": author}
            })
            embed = create_embed(
                title="✅ Session Created",
                description=f"Now reading **{book_title}** by {author}.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to create session: {e}")

    @bot.tree.command(name="session_update", description="Update the active reading session")
    @app_commands.describe(
        due_date="The new due date (YYYY-MM-DD format)",
        book_title="The new book title",
        book_author="The new book author",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def session_update(
        interaction: discord.Interaction,
        due_date: str = None,
        book_title: str = None,
        book_author: str = None,
        channel: discord.TextChannel = None
    ):
        """Updates the active session."""
        await interaction.response.defer()
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await interaction.followup.send(
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data or not club_data.get("active_session"):
            await interaction.followup.send("❌ No active session found in that channel.")
            return

        session_id = club_data["active_session"]["id"]
        update = {}
        if due_date and due_date.strip():
            update["due_date"] = due_date.strip()
        if book_title and book_author and book_title.strip() and book_author.strip():
            update["book"] = {
                "title": book_title.strip(),
                "author": book_author.strip()
            }
        if not update:
            await interaction.followup.send(
                "❌ Provide at least a due date or both book title and author."
            )
            return
        try:
            bot.api.update_session(session_id, update)
            embed = create_embed(
                title="✅ Session Updated",
                description="Session details updated successfully.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to update session: {e}")

    @bot.tree.command(name="session_delete", description="Delete the active reading session")
    @app_commands.describe(
        channel="The channel containing the club (defaults to current channel)"
    )
    async def session_delete(interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Deletes the active session for a club."""
        await interaction.response.defer()
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await interaction.followup.send(
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data or not club_data.get("active_session"):
            await interaction.followup.send("❌ No active session found in that channel.")
            return

        session_id = club_data["active_session"]["id"]
        confirmed = await _confirm(
            interaction,
            "⚠️ This will permanently delete the active reading session. "
            "Click **Confirm** to proceed or **Cancel** to abort."
        )
        if not confirmed:
            await interaction.followup.send("Action cancelled.")
            return
        try:
            bot.api.delete_session(session_id)
            embed = create_embed(
                title="✅ Session Deleted",
                description="The active reading session has been deleted.",
                color_key="success"
            )
            await interaction.followup.send(embed=embed)
        except APIError as e:
            await interaction.followup.send(f"❌ Failed to delete session: {e}")

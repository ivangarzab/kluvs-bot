"""
Admin commands (version, server, club, member, session management)
"""
import re
import os
from datetime import datetime, timezone, timedelta
from typing import Literal
import discord
from discord import app_commands

from utils.embeds import create_embed
from api.bookclub_api import APIError, ResourceNotFoundError

# Marker embedded in Discord event descriptions so discussion_sync can match them.
_DISC_ID_RE = re.compile(r"discussion_id:(\S+)")


async def discussion_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Autocomplete discussion IDs from the active session for update/delete commands."""
    try:
        channel_id = str(interaction.channel_id)
        guild_id = str(interaction.guild_id)
        club_data = interaction.client.api.find_club_in_channel(channel_id, guild_id)
        if not club_data or not club_data.get("active_session"):
            return []
        session_id = club_data["active_session"]["id"]
        session = interaction.client.api.get_session(session_id)
        discussions = session.get("discussions", [])
        choices = []
        for d in discussions:
            label = f"{d.get('title', 'Untitled')} — {d.get('date', '')}"
            if not current or current.lower() in label.lower():
                choices.append(app_commands.Choice(name=label[:100], value=d["id"]))
        return choices[:25]
    except Exception:
        return []


async def book_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if len(current) < 2:
        return []
    try:
        books = await interaction.client.api.search_books(current)
        print(f"[AUTOCOMPLETE] query={current!r} → {len(books)} results")
    except Exception as e:
        print(f"[AUTOCOMPLETE] search_books failed: {type(e).__name__}: {e}")
        return []

    choices = []
    for book in books:
        gid = book.get("external_google_id", "")
        title = book.get("title", "Unknown")
        author = book.get("author") or ""

        # Display name shown to the user (max 100 chars)
        display = f"{title} — {author}" if author else title

        # Value carries registration data: "{gid}|{title}|{author}", max 100 chars.
        # Budget: 100 - len(gid) - 2 pipes. Author capped at 30; title fills the rest.
        budget = 100 - len(gid) - 2
        author_part = author[:min(len(author), 30)] if author else ""
        title_part = title[:max(1, budget - len(author_part))]
        value = f"{gid}|{title_part}|{author_part}"

        choices.append(app_commands.Choice(name=display[:100], value=value))

    return choices[:25]


def setup_admin_commands(bot):
    """
    Setup admin slash commands

    Args:
        bot: The bot instance
    """

    async def send_ephemeral(interaction: discord.Interaction, *args, **kwargs):
        """Send an ephemeral followup (defaults to ephemeral=True)."""
        kwargs.setdefault('ephemeral', True)
        return await interaction.followup.send(*args, **kwargs)

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
                    await button_interaction.response.send_message("❌ You can't use this button.")
                    return
                self.confirmed = True
                for item in self.children:
                    item.disabled = True
                self.stop()
                await button_interaction.response.edit_message(view=self)

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                if button_interaction.user.id != interaction.user.id:
                    await button_interaction.response.send_message("❌ You can't use this button.")
                    return
                for item in self.children:
                    item.disabled = True
                self.stop()
                await button_interaction.response.edit_message(view=self)

        view = ConfirmView()
        await send_ephemeral(interaction,prompt, view=view)
        await view.wait()
        return view.confirmed

    # ── Version ──────────────────────────────────────────────────────────────

    @bot.tree.command(name="version", description="Shows the current version of the bot")
    @app_commands.guild_only()
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
                    title=f"📚 Kluvs Bot version: v{v}",
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
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
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
                    "name": "💬 Discussion Management",
                    "value": (
                        "`/discussion_add` — Add a discussion and create a Discord event\n"
                        "`/discussion_update` — Update an existing discussion\n"
                        "`/discussion_delete` — Delete a discussion\n"
                        "`/discussion_sync` — Create Discord events for all discussions missing one"
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
    @app_commands.guild_only()
    @app_commands.describe(club_name="Name for your new book club")
    async def setup(interaction: discord.Interaction, club_name: str):
        """Guided onboarding for new servers."""
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        channel_id = str(interaction.channel_id)

        # Fail fast: check if a club already exists in this channel before doing anything
        if bot.api.find_club_in_channel(channel_id, guild_id):
            embed = create_embed(
                title="❌ Club Already Exists",
                description=(
                    "This channel is already hosting a book club. "
                    "Please use a different channel or delete the existing club first."
                ),
                color_key="error"
            )
            await send_ephemeral(interaction,embed=embed)
            return

        try:
            bot.api.register_server(guild_id, interaction.guild.name)
        except APIError as e:
            if "already" in str(e).lower() or "duplicate" in str(e).lower():
                pass  # Server already registered — continue to club creation
            else:
                embed = create_embed(
                    title="❌ Setup Failed",
                    description=f"Failed to register server: {e}",
                    color_key="error"
                )
                await send_ephemeral(interaction,embed=embed)
                return

        try:
            existing = bot.api.get_member_by_discord_id(str(interaction.user.id))
            if existing:
                caller = {"id": existing["id"], "name": existing["name"]}
            else:
                created = bot.api.create_member({
                    "name": interaction.user.display_name,
                    "discord_id": str(interaction.user.id),
                    "avatar_url": str(interaction.user.display_avatar.url),
                })
                member_data = created.get("member", created)
                caller = {"id": member_data["id"], "name": member_data["name"]}

            bot.api.create_club(
                {
                    "name": club_name,
                    "discord_channel": channel_id,
                    "founded_date": datetime.now().strftime("%Y-%m-%d"),
                    "members": [caller],
                },
                guild_id
            )
        except APIError as e:
            embed = create_embed(
                title="❌ Setup Failed",
                description=f"Failed to create club: {e}",
                color_key="error"
            )
            await send_ephemeral(interaction,embed=embed)
            return

        embed = create_embed(
            title="🎉 Welcome to your book club!",
            description=(
                f"**{club_name}** has been created in {interaction.channel.mention}.\n\n"
                "Here's what to do next:"
            ),
            color_key="success",
            fields=[
                {
                    "name": "📖 Admin — pick your first book",
                    "value": "Use `/session_create` to start your first reading session and choose what the club reads.",
                    "inline": False,
                },
                {
                    "name": "👥 Everyone else — join the club",
                    "value": "Type `/join` to get on the roster so you can track progress and participate in discussions.",
                    "inline": False,
                },
                {
                    "name": "📚 Other useful commands",
                    "value": (
                        "`/session` — view the current session\n"
                        "`/book` — see the current book\n"
                        "`/duedate` — check the due date\n"
                        "`/discussions` — view scheduled discussions\n"
                        "`/usage` — view all other commands"
                    ),
                    "inline": False,
                },
            ],
            footer="Happy reading! 📖"
        )
        await send_ephemeral(interaction,embed=embed)

    # ── Server commands (manage_guild permission only) ────────────────────────

    @bot.tree.command(name="server_register", description="Register this Discord server with the bot")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def server_register(interaction: discord.Interaction):
        """Registers the Discord server."""
        await interaction.response.defer(ephemeral=True)
        try:
            bot.api.register_server(str(interaction.guild_id), interaction.guild.name)
            embed = create_embed(
                title="✅ Server Registered",
                description=f"**{interaction.guild.name}** has been registered.",
                color_key="success"
            )
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to register server: {e}")

    @bot.tree.command(name="server_update", description="Update this server's registered name")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(name="The new name for the server")
    async def server_update(interaction: discord.Interaction, name: str):
        """Updates the server's registered name."""
        await interaction.response.defer(ephemeral=True)
        try:
            bot.api.update_server(str(interaction.guild_id), name)
            embed = create_embed(
                title="✅ Server Updated",
                description=f"Server name updated to **{name}**.",
                color_key="success"
            )
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to update server: {e}")

    @bot.tree.command(name="server_delete", description="Delete this server's registration and all data")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def server_delete(interaction: discord.Interaction):
        """Deletes the server registration and all associated data."""
        await interaction.response.defer(ephemeral=True)
        confirmed = await _confirm(
            interaction,
            "⚠️ This will delete **all server data** including clubs, members, and sessions. "
            "Click **Confirm** to proceed or **Cancel** to abort."
        )
        if not confirmed:
            embed = create_embed(
                title="❌ Action Cancelled",
                description="No changes were made.",
                color_key="error"
            )
            await send_ephemeral(interaction,embed=embed)
            return
        try:
            bot.api.delete_server(str(interaction.guild_id))
            embed = create_embed(
                title="✅ Server Deleted",
                description="Server registration and all associated data have been removed.",
                color_key="success"
            )
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            err = str(e).lower()
            if any(k in err for k in ("foreign key", "fk_", "club", "violates")):
                embed = create_embed(
                    title="❌ Cannot Delete Server",
                    description=(
                        "This server still contains active book clubs. "
                        "To prevent accidental data loss, please use `/club_delete` on each club individually "
                        "before removing the server registration."
                    ),
                    color_key="error"
                )
                await send_ephemeral(interaction,embed=embed)
            else:
                await send_ephemeral(interaction,f"❌ Failed to delete server: {e}")

    # ── Club commands (club admin+) ───────────────────────────────────────────

    @bot.tree.command(name="club_create", description="Create a new book club in a channel")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        name="The name of the new club",
        channel="The channel to create the club in (defaults to current channel)"
    )
    async def club_create(interaction: discord.Interaction, name: str, channel: discord.TextChannel = None):
        """Creates a new book club. Caller is automatically assigned as owner."""
        await interaction.response.defer(ephemeral=True)
        channel_id = str(channel.id) if channel else str(interaction.channel_id)
        guild_id = str(interaction.guild_id)

        if not name or not name.strip():
            await send_ephemeral(interaction,"❌ Please provide a club name.")
            return

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if club_data:
            await send_ephemeral(interaction,
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
                    "avatar_url": str(interaction.user.display_avatar.url),
                })
                member_data = created.get("member", created)
                caller = {"id": member_data["id"], "name": member_data["name"]}

            bot.api.create_club(
                {
                    "name": name,
                    "discord_channel": channel_id,
                    "founded_date": datetime.now().strftime("%Y-%m-%d"),
                    "members": [caller],
                },
                guild_id
            )
            embed = create_embed(
                title="✅ Club Created",
                description=f"Book club **{name}** created in <#{channel_id}>. You are the owner.",
                color_key="success"
            )
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to create club: {e}")

    @bot.tree.command(name="club_update", description="Update the club name or discord channel")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
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
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data:
            await send_ephemeral(interaction,"❌ No book club found in that channel.")
            return

        update = {}
        if name and name.strip():
            update["name"] = name.strip()
        if new_channel:
            update["discord_channel"] = str(new_channel.id)
        if not update:
            await send_ephemeral(interaction,
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
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to update club: {e}")

    @bot.tree.command(name="club_delete", description="Delete the book club in a channel")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        channel="The channel containing the club to delete (defaults to current channel)"
    )
    async def club_delete(interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Deletes a book club and all its data."""
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data:
            await send_ephemeral(interaction,"❌ No book club found in that channel.")
            return

        confirmed = await _confirm(
            interaction,
            f"⚠️ This will delete **{club_data['name']}** and all its data. "
            "Click **Confirm** to proceed or **Cancel** to abort."
        )
        if not confirmed:
            embed = create_embed(
                title="❌ Action Cancelled",
                description="No changes were made.",
                color_key="error"
            )
            await send_ephemeral(interaction,embed=embed)
            return
        try:
            bot.api.delete_club(club_data["id"], guild_id)
            embed = create_embed(
                title="✅ Club Deleted",
                description=f"**{club_data['name']}** has been deleted.",
                color_key="success"
            )
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to delete club: {e}")

    # ── Member commands (club admin+) ─────────────────────────────────────────

    @bot.tree.command(name="member_add", description="Add a Discord user to a book club")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        member="The member to add to the club",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def member_add(interaction: discord.Interaction, member: discord.Member, channel: discord.TextChannel = None):
        """Adds a mentioned Discord user to a club. Creates member record if needed."""
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data:
            await send_ephemeral(interaction,"❌ No book club found in that channel.")
            return
        try:
            existing = bot.api.get_member_by_discord_id(str(member.id))
            if existing:
                current_club_ids = [c["id"] for c in existing.get("clubs", [])]
                if club_data["id"] in current_club_ids:
                    await send_ephemeral(interaction,f"**{member.display_name}** is already a member of this club.")
                    return
                bot.api.update_member(existing["id"], {"clubs": current_club_ids + [club_data["id"]]})
            else:
                bot.api.create_member({
                    "name": member.display_name,
                    "discord_id": str(member.id),
                    "avatar_url": str(member.display_avatar.url),
                    "clubs": [club_data["id"]]
                })
            embed = create_embed(
                title="✅ Member Added",
                description=f"**{member.display_name}** has been added to the club.",
                color_key="success"
            )
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to add member: {e}")

    @bot.tree.command(name="member_remove", description="Remove a member from a book club")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        member="The Discord member to remove",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def member_remove(interaction: discord.Interaction, member: discord.Member, channel: discord.TextChannel = None):
        """Removes a member from a club."""
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data:
            await send_ephemeral(interaction,"❌ No book club found in that channel.")
            return

        try:
            member_data = bot.api.get_member_by_discord_id(str(member.id))
            if not member_data:
                await send_ephemeral(interaction,
                    f"❌ **{member.display_name}** is not registered in the bot.",
                    ephemeral=True
                )
                return
            member_club_ids = [c["id"] for c in member_data.get("clubs", [])]
            if club_data["id"] not in member_club_ids:
                await send_ephemeral(interaction,f"❌ **{member.display_name}** is not in this club.")
                return
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to look up member: {e}")
            return

        confirmed = await _confirm(
            interaction,
            f"⚠️ Remove **{member.display_name}** from the club? "
            "Click **Confirm** to proceed or **Cancel** to abort."
        )
        if not confirmed:
            embed = create_embed(
                title="❌ Action Cancelled",
                description="No changes were made.",
                color_key="error"
            )
            await send_ephemeral(interaction,embed=embed)
            return
        try:
            bot.api.delete_member(member_data["id"])
            embed = create_embed(
                title="✅ Member Removed",
                description=f"**{member.display_name}** has been removed.",
                color_key="success"
            )
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to remove member: {e}")

    @bot.tree.command(name="member_role", description="Update a member's role in a club")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        member="The Discord member to update",
        role="The new role (admin or member)",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def member_role(
        interaction: discord.Interaction,
        member: discord.Member,
        role: Literal["admin", "member"],
        channel: discord.TextChannel = None
    ):
        """Sets a member's role to admin or member."""
        await interaction.response.defer(ephemeral=True)

        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data:
            await send_ephemeral(interaction,"❌ No book club found in that channel.")
            return
        try:
            member_data = bot.api.get_member_by_discord_id(str(member.id))
            if not member_data:
                await send_ephemeral(interaction,
                    f"❌ **{member.display_name}** is not registered in the bot.",
                    ephemeral=True
                )
                return
            bot.api.update_member(member_data["id"], {"club_roles": {club_data["id"]: role}})
            embed = create_embed(
                title="✅ Role Updated",
                description=f"**{member.display_name}** is now **{role}**.",
                color_key="success"
            )
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to update role: {e}")

    # ── Session commands (club admin+) ────────────────────────────────────────

    @bot.tree.command(name="session_create", description="Start a new reading session for the club.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.autocomplete(book=book_autocomplete)
    @app_commands.describe(
        book="Search and select a book from the library",
        due_date="Reading deadline (YYYY-MM-DD, e.g. 2026-06-01)"
    )
    async def session_create_command(
        interaction: discord.Interaction,
        book: str,
        due_date: str
    ):
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        channel_id = str(interaction.channel_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not club_data:
            raise ResourceNotFoundError(f"No book club found in channel {channel_id}")

        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be an Admin to create a session.",
                ephemeral=True
            )
            return

        # Validate due_date format (YYYY-MM-DD)
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            await send_ephemeral(interaction,
                "❌ Due date must be in **YYYY-MM-DD** format (e.g., `2026-06-01`).",
                ephemeral=True
            )
            return

        # Value from autocomplete is "{external_google_id}|{title}|{author}"
        parts = book.split("|", 2)
        if len(parts) != 3 or not parts[1] or not parts[2]:
            await send_ephemeral(interaction,"❌ Invalid book selection. Please use the autocomplete dropdown.")
            return
        gid, title, author = parts

        # Register (or retrieve) the book in the local DB — idempotent via external_google_id
        registered = await bot.api.register_book(title, author, external_google_id=gid)

        session_data = {
            "club_id": club_data["id"],
            "book_id": registered["id"],
            "due_date": due_date,
        }

        print(f"[DEBUG] Sending session_data to backend: {session_data}")
        bot.api.create_session(session_data)

        embed = create_embed(
            title="📚 Session Created",
            description=f"✅ Successfully created a new reading session with deadline {due_date}.",
            color_key="success"
        )
        await send_ephemeral(interaction,embed=embed)
        print(f"[SUCCESS] Created session: [Server: {guild_id}, Club: {club_data['id']}, Book: {registered['id']} '{title}']")

    @bot.tree.command(name="session_update", description="Update the active reading session")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
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
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data or not club_data.get("active_session"):
            await send_ephemeral(interaction,"❌ No active session found in that channel.")
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
            await send_ephemeral(interaction,
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
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to update session: {e}")

    @bot.tree.command(name="session_delete", description="Delete the active reading session")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        channel="The channel containing the club (defaults to current channel)"
    )
    async def session_delete(interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Deletes the active session for a club."""
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data or not club_data.get("active_session"):
            await send_ephemeral(interaction,"❌ No active session found in that channel.")
            return

        session_id = club_data["active_session"]["id"]
        confirmed = await _confirm(
            interaction,
            "⚠️ This will permanently delete the active reading session. "
            "Click **Confirm** to proceed or **Cancel** to abort."
        )
        if not confirmed:
            embed = create_embed(
                title="❌ Action Cancelled",
                description="No changes were made.",
                color_key="error"
            )
            await send_ephemeral(interaction,embed=embed)
            return
        try:
            bot.api.delete_session(session_id)
            embed = create_embed(
                title="✅ Session Deleted",
                description="The active reading session has been deleted.",
                color_key="success"
            )
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to delete session: {e}")

    # ── Discussion commands (club admin+) ─────────────────────────────────────

    @bot.tree.command(name="discussion_add", description="Add a discussion to the active session")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        title="Discussion title (e.g. 'Chapters 1-5')",
        date="Discussion date (YYYY-MM-DD)",
        time="Discussion start time in 24h format (HH:MM, e.g. 18:00)",
        duration="Duration in hours (default: 1)",
        location="Location (default: Discord)",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def discussion_add(
        interaction: discord.Interaction,
        title: str,
        date: str,
        time: str,
        duration: float = 1.0,
        location: str = "Discord",
        channel: discord.TextChannel = None
    ):
        """Adds a new discussion to the active reading session and creates a Discord scheduled event."""
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data or not club_data.get("active_session"):
            await send_ephemeral(interaction,"❌ No active session found in that channel.")
            return

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            await send_ephemeral(interaction,
                "❌ Date must be in **YYYY-MM-DD** format (e.g., `2026-05-15`).",
                ephemeral=True
            )
            return

        try:
            datetime.strptime(time, "%H:%M")
        except ValueError:
            await send_ephemeral(interaction,
                "❌ Time must be in **HH:MM** 24h format (e.g., `18:00`).",
                ephemeral=True
            )
            return

        if duration <= 0:
            await send_ephemeral(interaction,
                "❌ Duration must be greater than 0.",
                ephemeral=True
            )
            return

        session_id = club_data["active_session"]["id"]
        resolved_location = location.strip() if location and location.strip() else "Discord"
        new_discussion = {"title": title.strip(), "date": date.strip(), "time": f"{time.strip()}:00", "location": resolved_location}

        try:
            bot.api.update_session(session_id, {"discussions": [new_discussion]})
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to add discussion: {e}")
            return

        # Retrieve the server-assigned discussion ID so we can embed it in the event.
        disc_id = None
        try:
            session = bot.api.get_session(session_id)
            match = next(
                (d for d in session.get("discussions", [])
                 if d.get("title") == new_discussion["title"] and d.get("date") == new_discussion["date"]),
                None
            )
            if match:
                disc_id = match["id"]
        except APIError:
            pass  # Non-fatal — event will be created without an embedded ID

        # Build timezone-aware datetimes for the Discord event (explicitly UTC)
        start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(hours=duration)

        event_description = f"Book club discussion: {title.strip()}"
        if disc_id:
            event_description += f"\ndiscussion_id:{disc_id}"

        event_warning = ""
        try:
            await interaction.guild.create_scheduled_event(
                name=title.strip(),
                start_time=start_dt,
                end_time=end_dt,
                entity_type=discord.EntityType.external,
                privacy_level=discord.PrivacyLevel.guild_only,
                location=resolved_location,
                description=event_description,
            )
        except discord.Forbidden:
            event_warning = "\n⚠️ Discussion saved, but couldn't create a Discord event — the bot is missing **Manage Events** permission."
        except discord.HTTPException as e:
            event_warning = f"\n⚠️ Discussion saved, but Discord event creation failed: {e}"

        description = f"Added **{title}** on {date} at {time} ({resolved_location})"
        embed = create_embed(
            title="✅ Discussion Added",
            description=description + "." + event_warning,
            color_key="success"
        )
        await send_ephemeral(interaction,embed=embed)

    @bot.tree.command(name="discussion_update", description="Update an existing discussion in the active session")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.autocomplete(discussion_id=discussion_autocomplete)
    @app_commands.describe(
        discussion_id="The discussion to update (select from autocomplete)",
        title="New title",
        date="New date (YYYY-MM-DD)",
        location="New location",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def discussion_update_command(
        interaction: discord.Interaction,
        discussion_id: str,
        title: str = None,
        date: str = None,
        location: str = None,
        channel: discord.TextChannel = None
    ):
        """Updates an existing discussion in the active reading session."""
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data or not club_data.get("active_session"):
            await send_ephemeral(interaction,"❌ No active session found in that channel.")
            return

        if not any([title, date, location]):
            await send_ephemeral(interaction,
                "❌ Provide at least one field to update (title, date, or location)."
            )
            return

        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                await send_ephemeral(interaction,
                    "❌ Date must be in **YYYY-MM-DD** format (e.g., `2026-05-15`).",
                    ephemeral=True
                )
                return

        session_id = club_data["active_session"]["id"]
        try:
            session = bot.api.get_session(session_id)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to retrieve session: {e}")
            return

        discussions = session.get("discussions", [])
        current = next((d for d in discussions if d["id"] == discussion_id), None)
        if not current:
            await send_ephemeral(interaction,"❌ Discussion not found in the active session.")
            return

        updated = {
            "id": discussion_id,
            "title": title.strip() if title else current["title"],
            "date": date.strip() if date else current["date"],
        }
        resolved_location = location.strip() if location else current.get("location")
        if resolved_location:
            updated["location"] = resolved_location

        try:
            bot.api.update_session(session_id, {"discussions": [updated]})
            description = f"Updated **{updated['title']}** on {updated['date']}"
            if updated.get("location"):
                description += f" at {updated['location']}"
            embed = create_embed(
                title="✅ Discussion Updated",
                description=description + ".",
                color_key="success"
            )
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to update discussion: {e}")

    @bot.tree.command(name="discussion_delete", description="Delete a discussion from the active session")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.autocomplete(discussion_id=discussion_autocomplete)
    @app_commands.describe(
        discussion_id="The discussion to delete (select from autocomplete)",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def discussion_delete_command(
        interaction: discord.Interaction,
        discussion_id: str,
        channel: discord.TextChannel = None
    ):
        """Deletes a discussion from the active reading session."""
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data or not club_data.get("active_session"):
            await send_ephemeral(interaction,"❌ No active session found in that channel.")
            return

        confirmed = await _confirm(
            interaction,
            "⚠️ This will permanently delete the selected discussion. "
            "Click **Confirm** to proceed or **Cancel** to abort."
        )
        if not confirmed:
            embed = create_embed(
                title="❌ Action Cancelled",
                description="No changes were made.",
                color_key="error"
            )
            await send_ephemeral(interaction,embed=embed)
            return

        session_id = club_data["active_session"]["id"]
        try:
            bot.api.update_session(session_id, {"discussion_ids_to_delete": [discussion_id]})
            embed = create_embed(
                title="✅ Discussion Deleted",
                description="The discussion has been removed from the session.",
                color_key="success"
            )
            await send_ephemeral(interaction,embed=embed)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to delete discussion: {e}")

    @bot.tree.command(name="discussion_sync", description="Create Discord events for any discussions that don't have one")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        default_time="Start time for created events in HH:MM 24h format (default: 18:00)",
        default_duration="Duration in hours for created events (default: 1.0)",
        channel="The channel containing the club (defaults to current channel)"
    )
    async def discussion_sync(
        interaction: discord.Interaction,
        default_time: str = "18:00",
        default_duration: float = 1.0,
        channel: discord.TextChannel = None
    ):
        """Ensures every discussion in the active session has a corresponding Discord scheduled event."""
        await interaction.response.defer(ephemeral=True)
        target_channel = channel or interaction.channel
        channel_id = str(target_channel.id)
        guild_id = str(interaction.guild_id)

        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        if not _can_manage_clubs(interaction, club_data):
            await send_ephemeral(interaction,
                "❌ You need to be a club admin or owner to use this command.",
                ephemeral=True
            )
            return
        if not club_data or not club_data.get("active_session"):
            await send_ephemeral(interaction,"❌ No active session found in that channel.")
            return

        try:
            datetime.strptime(default_time, "%H:%M")
        except ValueError:
            await send_ephemeral(interaction,
                "❌ default_time must be in **HH:MM** 24h format (e.g., `18:00`).",
                ephemeral=True
            )
            return

        if default_duration <= 0:
            await send_ephemeral(interaction,
                "❌ default_duration must be greater than 0.",
                ephemeral=True
            )
            return

        session_id = club_data["active_session"]["id"]
        try:
            session = bot.api.get_session(session_id)
        except APIError as e:
            await send_ephemeral(interaction,f"❌ Failed to retrieve session: {e}")
            return

        discussions = session.get("discussions", [])
        if not discussions:
            await send_ephemeral(interaction,"ℹ️ No discussions found in the active session.")
            return

        # Build the set of discussion IDs already covered by an existing guild event.
        try:
            existing_events = await interaction.guild.fetch_scheduled_events()
        except discord.Forbidden:
            await send_ephemeral(interaction,
                "❌ Couldn't fetch guild events — the bot is missing **Manage Events** permission."
            )
            return

        covered_ids = set()
        for event in existing_events:
            m = _DISC_ID_RE.search(event.description or "")
            if m:
                covered_ids.add(m.group(1))

        created, skipped, failed = [], [], []

        for disc in discussions:
            disc_id = disc.get("id")
            disc_title = disc.get("title", "Untitled")

            if disc_id in covered_ids:
                skipped.append(disc_title)
                continue

            # Parse the date; skip gracefully if it's not in the expected format.
            raw_date = disc.get("date", "")
            try:
                start_dt = datetime.strptime(f"{raw_date} {default_time}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            except ValueError:
                failed.append(f"{disc_title} (unparseable date: {raw_date!r})")
                continue

            end_dt = start_dt + timedelta(hours=default_duration)
            event_description = f"Book club discussion: {disc_title}"
            if disc_id:
                event_description += f"\ndiscussion_id:{disc_id}"

            try:
                await interaction.guild.create_scheduled_event(
                    name=disc_title,
                    start_time=start_dt,
                    end_time=end_dt,
                    entity_type=discord.EntityType.external,
                    privacy_level=discord.PrivacyLevel.guild_only,
                    location=disc.get("location") or "Discord",
                    description=event_description,
                )
                created.append(disc_title)
            except (discord.Forbidden, discord.HTTPException) as e:
                failed.append(f"{disc_title} ({e})")

        lines = []
        if created:
            lines.append(f"✅ Created {len(created)} event(s): {', '.join(f'**{t}**' for t in created)}")
        if skipped:
            lines.append(f"⏭️ Already had events: {', '.join(f'**{t}**' for t in skipped)}")
        if failed:
            lines.append(f"⚠️ Failed to create: {', '.join(failed)}")
        if not lines:
            lines.append("ℹ️ Nothing to sync.")

        embed = create_embed(
            title="🔄 Discussion Sync Complete",
            description="\n".join(lines),
            color_key="info"
        )
        await send_ephemeral(interaction,embed=embed)
